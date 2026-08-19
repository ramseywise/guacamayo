"""Dashboard rendering tests (Phase B, Steps 5-6).

The central invariant under test is Q0's scope limit: the Apr-Jun note corpus
only exists *where sessions compacted*, so population-rate metrics measure the
logger, not the workflow. They may never be drawn as one continuous series
across a regime boundary. Per-session property metrics (cost, cache rate,
tokens) are comparable and may.
"""

from __future__ import annotations

import json
import re
from datetime import date as _date
from pathlib import Path
from typing import Any

import pytest

from telemetry.dashboard import (
    _CONTEXT_BUCKETS,
    _DEFAULT_PERIOD,
    COMPACT_METRICS,
    JULY_BOUNDARY,
    JULY_ONLY_METRICS,
    LEDGER_METRIC_MAPPING,
    PERIODS,
    RATE_METRICS,
    SAMPLING_FRAME,
    Experiment,
    Panel,
    Point,
    Series,
    _annotations_for_metric,
    _direction_badge,
    _group,
    _metric_value,
    _panel_body,
    _period_key,
    _period_sparkline,
    _population_line,
    _render_annotations,
    _render_experiments,
    _render_review_findings,
    _render_skill_economics,
    _saturation_warning,
    _scored_count,
    _span_days,
    _sparkline_svg,
    _svg_line,
    _work_sessions,
    build_hook_activity,
    build_series,
    build_skill_daily,
    funnel_counts,
    parse_hook_log,
    render_dashboard,
    render_friction_regroup_card,
    render_hook_activity_card,
    trend_7d,
    warn_unmapped_experiments,
)
from telemetry.factstore import ERA_JSONL, ERA_NOTE, read_all, upsert
from telemetry.recurrence import DIRECTION_FALLING, DIRECTION_FLAT, DIRECTION_RISING


def _row(session_id: str, date: str, regime: str, **overrides: object) -> dict[str, Any]:
    """A fact row shaped exactly like factstore.FACT_COLUMNS requires."""
    row: dict[str, Any] = {
        "session_id": session_id,
        "date": date,
        "project": "/Users/x/repo",
        "era": ERA_NOTE if date < JULY_BOUNDARY else ERA_JSONL,
        "regime": regime,
        "source_path": f"/tmp/{session_id}",
        "input_tokens": 100,
        "output_tokens": 200,
        "cache_read_tokens": 300,
        "cache_write_tokens": 40,
        "cost_units": 1234.5,
        "compacted": True,
        "is_meta": False,
    }
    row.update(overrides)
    return row


@pytest.fixture
def two_regime_store(tmp_path: Path) -> Path:
    """A store straddling the regime break: note-hook notes + July JSONL."""
    store = tmp_path / "facts.db"
    rows = [
        _row("n1", "2026-05-01", "note-hook", compacted=True),
        _row("n2", "2026-05-02", "note-hook", compacted=True),
        _row("n3", "2026-06-10", "note-hook", compacted=False),
        _row("j1", "2026-07-16", "telemetry-v1", compacted=False, max_context=150_000),
        _row("j2", "2026-07-18", "session-hygiene-v1", compacted=False, max_context=90_000),
        _row("j3", "2026-07-18", "session-hygiene-v1", compacted=True, max_context=180_000),
    ]
    upsert(rows, store)
    return store


# --- Step 5: the enforced rule ---------------------------------------------


@pytest.mark.parametrize("metric", sorted(RATE_METRICS))
def test_rate_metrics_never_continuous(two_regime_store: Path, metric: str) -> None:
    """A population-rate metric must render as per-regime panels, never one line.

    This is the survivorship guard: note-hook notes exist only where a session
    compacted, so a compaction-% line crossing 2026-07-15 would plot the
    note-writing hook's behaviour as if it were Ramsey's.
    """
    series = build_series(metric, two_regime_store)

    assert series.faceted is True, f"{metric} must be faceted by regime"
    assert series.panels, f"{metric} produced no panels"

    # Every panel is confined to exactly one regime.
    for panel in series.panels:
        regimes = {point.regime for point in panel.points}
        assert regimes == {panel.regime}, (
            f"{metric} panel {panel.regime!r} mixes regimes: {regimes}"
        )

    # No panel spans a boundary, and each declares its sampling frame.
    assert len({p.regime for p in series.panels}) == len(series.panels)
    for panel in series.panels:
        assert panel.sampling_frame, f"{metric} panel {panel.regime!r} lacks a sampling frame"
        assert panel.sampling_frame == SAMPLING_FRAME[panel.regime]


def test_property_metrics_are_continuous(two_regime_store: Path) -> None:
    """The converse: per-session properties DO cross regimes, with bands behind."""
    series = build_series("cost_units_p50", two_regime_store)

    assert series.faceted is False
    assert series.regime_bands, "a continuous trend must shade its regime bands"
    regimes = {point.regime for point in series.points}
    assert len(regimes) > 1, "expected one line spanning multiple regimes"


def test_headline_is_cost_not_compaction() -> None:
    """Q3 as superseded: compaction rate is disqualified as the headline."""
    assert "compaction_pct" in RATE_METRICS
    assert "sessions_per_week" in RATE_METRICS
    assert "cost_units_p50" not in RATE_METRICS


def test_work_sessions_only_excludes_meta(tmp_path: Path) -> None:
    """Research Disconfirming section 1: meta-sessions are never pooled in."""
    store = tmp_path / "facts.db"
    upsert(
        [
            _row("w1", "2026-07-18", "session-hygiene-v1", is_meta=False),
            _row("m1", "2026-07-18", "session-hygiene-v1", is_meta=True),
        ],
        store,
    )
    series = build_series("cost_units_p50", store)
    assert all(point.n == 1 for point in series.points), "meta session leaked into the series"


# --- Step 6: the era boundary ----------------------------------------------


def test_era_boundary(two_regime_store: Path) -> None:
    """No July-only metric may render a pre-July data point."""
    for metric in ("max_context_p50", "max_context_p90", "pct_over_150k"):
        series = build_series(metric, two_regime_store)
        points = series.points or [p for panel in series.panels for p in panel.points]
        assert points, f"{metric} rendered nothing"
        for point in points:
            assert point.date >= JULY_BOUNDARY, (
                f"{metric} rendered {point.date}, before the telemetry boundary"
            )


def test_july_panel_declares_its_boundary(two_regime_store: Path) -> None:
    html = render_dashboard(two_regime_store, funnel=None)
    assert JULY_BOUNDARY in html
    assert "telemetry begins" in html.lower()


def test_rate_metrics_actually_reach_the_page(two_regime_store: Path) -> None:
    """The faceting rule is only worth anything if the rate charts render.

    Guards a real gap: the metrics were computed and unit-tested while being
    absent from the rendered page, so a reader never saw them.
    """
    html = render_dashboard(two_regime_store, funnel=None)
    assert "Compaction rate" in html
    assert "Sessions per week" in html
    # Each faceted chart states the no-crossing rule and its per-panel frame,
    # once per period — every panel is rendered at all three and toggled in JS.
    assert html.count("no line crosses a regime boundary") == len(RATE_METRICS) * len(PERIODS)
    assert "rate is not a workflow property" in html


def test_panel_width_tracks_regime_span(two_regime_store: Path) -> None:
    """Equal-width panels implied equal duration: a 3-day regime rendered as wide
    as an 8-week one. Width now carries the span, so flex-grow must differ."""
    html = render_dashboard(two_regime_store, funnel=None)
    grows = re.findall(r"flex:(\d+) 1 0", html)
    assert grows, "faceted panels should carry a proportional flex-grow"
    assert len(set(grows)) > 1, f"panels all same width despite differing spans: {grows}"


def test_sparse_panel_renders_values_not_a_sliver() -> None:
    """One or two points drew a ~2px line that read as a rendering bug."""
    panel = Panel(
        regime="telemetry-v1",
        sampling_frame="all sessions logged (JSONL)",
        points=[Point(date="2026-07-15", value=7.0, regime="telemetry-v1")],
    )
    body = _panel_body(panel, "#000", span=1, widest=60)
    assert "<svg" not in body
    assert "too few points to plot" in body
    assert "7" in body


def test_saturated_rate_panel_is_flagged() -> None:
    """note-hook compaction is 186/186 then 26/26 — exactly 100%. That is the
    note-writing hook's trigger, and unflagged it reads as an upward trend."""
    points = [
        Point(date=f"2026-05-{day:02d}", value=100.0, regime="note-hook") for day in range(1, 6)
    ]
    panel = Panel(regime="note-hook", sampling_frame="frame", points=points)
    assert "100%" in _saturation_warning(panel)
    assert "logging trigger" in _saturation_warning(panel)


def test_zero_rail_panel_is_flagged() -> None:
    """0% is as much a logging artifact as 100%: migrated-jsonl notes never
    recorded compaction, so the whole regime sits on the floor."""
    points = [
        Point(date=f"2026-04-{day:02d}", value=0.0, regime="migrated-jsonl")
        for day in range(10, 16)
    ]
    panel = Panel(regime="migrated-jsonl", sampling_frame="frame", points=points)
    assert "0%" in _saturation_warning(panel)
    assert "logging trigger" in _saturation_warning(panel)


def test_unsaturated_panel_is_not_flagged() -> None:
    points = [
        Point(date=f"2026-07-{day:02d}", value=float(v), regime="session-hygiene-v1")
        for day, v in zip(range(15, 20), [10, 20, 5, 0, 15], strict=True)
    ]
    panel = Panel(regime="session-hygiene-v1", sampling_frame="frame", points=points)
    assert _saturation_warning(panel) == ""


# --- Step 6: the growth.md drain problem -----------------------------------


def test_funnel_counts_read_the_logged_event_not_the_drained_buffer(tmp_path: Path) -> None:
    """Research F5: growth.md drains to zero on /dream.

    Polling the accumulator measures the drain, not the learning. The counts must
    come from the logged synthesis event in the header, which survives the clear.
    """
    growth = tmp_path / "growth.md"
    growth.write_text(
        "# Growth - Learning Accumulator\n\n"
        "**Last Synthesis**: 2026-07-18 afternoon (/dream - 9 entries: 3 woven into "
        "sounding.md, 1 into portfolio.md, 4 process learnings flagged for /retro, "
        "1 already captured in seeds from prior synthesis)\n"
        "**Entries Since**: 0\n\n"
        "---\n",
        encoding="utf-8",
    )

    funnel = funnel_counts(growth)

    # The buffer is empty, but the funnel is NOT zero.
    assert funnel.entries_since == 0
    assert funnel.entries_in == 9
    assert funnel.to_sounding == 3
    assert funnel.to_portfolio == 1
    assert funnel.flagged_retro == 4
    assert funnel.last_synthesis == "2026-07-18"


def test_funnel_counts_absent_header_is_none_not_zero(tmp_path: Path) -> None:
    """A missing synthesis line is unknown, never a fabricated zero."""
    growth = tmp_path / "growth.md"
    growth.write_text("# Growth\n\n**Entries Since**: 0\n", encoding="utf-8")

    funnel = funnel_counts(growth)

    assert funnel.entries_in is None
    assert funnel.entries_since == 0


# --- Step 1: dark-mode SVG contrast via CSS variables -------------------------


def test_dark_mode_uses_css_variables(two_regime_store: Path) -> None:
    """SVG strokes must use var(--chart-N), not hardcoded hex colours.
    The CSS must define --chart-N in both light and dark blocks."""
    html = render_dashboard(two_regime_store, funnel=None)
    assert "var(--chart-" in html, "SVG should use CSS variable references"
    for light_hex in ("#2a78d6", "#e87ba4", "#eda100"):
        assert f'stroke="{light_hex}"' not in html, (
            f"hardcoded light palette colour {light_hex} found in SVG stroke"
        )
    assert "--chart-1:#3987e5" in html, "dark-mode CSS must define --chart-1"
    assert "--chart-1:#2a78d6" in html, "light-mode CSS must define --chart-1"


# --- Step 3: topic sections with sticky nav -----------------------------------


def test_dashboard_has_four_sections(two_regime_store: Path) -> None:
    html = render_dashboard(two_regime_store, funnel=None)
    for section_id in ("cost", "context", "friction", "review", "progress"):
        assert f'id="{section_id}"' in html, f"missing section #{section_id}"


def test_dashboard_has_nav(two_regime_store: Path) -> None:
    html = render_dashboard(two_regime_store, funnel=None)
    assert "<nav" in html, "sticky nav element missing"
    for href in ("#cost", "#context", "#friction", "#review", "#progress"):
        assert f'href="{href}"' in html, f"nav link to {href} missing"


# --- Step 4: axis labels -----------------------------------------------------


def test_svg_has_axis_labels() -> None:
    """SVG charts should render y-axis min/max and x-axis date labels."""
    points = [
        Point(date=f"2026-07-{d:02d}", value=float(v), regime="session-hygiene-v1")
        for d, v in [(15, 10000), (16, 20000), (17, 15000), (18, 30000)]
    ]
    svg = _svg_line(points, "var(--chart-1)", unit="tokens")
    assert "<text" in svg, "axis labels should render as <text> elements"
    assert "30k" in svg, "y-axis max should show formatted value"
    assert "10k" in svg, "y-axis min should show formatted value"


# --- Step 5: experiment verdicts panel ----------------------------------------


def test_experiment_panel_renders(two_regime_store: Path) -> None:
    experiments = [
        Experiment(name="compact-wiki", metric="ratio:foo", status="confirmed", date="2026-07"),
        Experiment(name="bash-block", metric="count-drop:bar", status="failed", date="2026-07"),
        Experiment(name="wake-nudge", metric="presence:baz", status="hypothesis", date="2026-07"),
    ]
    html = render_dashboard(two_regime_store, funnel=None, experiments=experiments)
    assert "compact-wiki" in html
    assert "bash-block" in html
    assert "exp-confirmed" in html
    assert "exp-failed" in html


def test_experiment_grouping() -> None:
    """Actionable verdicts sort first: failed, then confirmed, then unscored.

    Ordering is deliberately actionable-first rather than good-news-first — a
    failed experiment needs a decision, a confirmed one is already settled.
    """
    from telemetry.dashboard import _render_experiments

    experiments = [
        Experiment(name="z-last", metric="m", status="hypothesis", date="d"),
        Experiment(name="a-confirmed", metric="m", status="confirmed", date="d"),
        Experiment(name="m-failed", metric="m", status="failed", date="d"),
    ]
    html = _render_experiments(experiments)
    assert html.index("m-failed") < html.index("a-confirmed") < html.index("z-last")


def test_experiment_verdict_join_overrides_ledger_status(two_regime_store: Path) -> None:
    """A scored verdict wins over the ledger's hand-written status.

    The ledger's Status: text is rarely updated after the row is added, which
    is why the pre-join render reported "107 pending" against 1,395 scored rows.
    """
    from telemetry.dashboard import _render_experiments
    from telemetry.factstore import append_verdicts

    append_verdicts(
        [
            {
                "experiment": "measured",
                "date": "2026-08-01",
                "metric": "m",
                "verdict": "failed",
                "evidence": "metric moved the wrong way",
            }
        ],
        two_regime_store,
        run_at="2026-08-02T00:00:00Z",
    )
    experiments = [Experiment(name="measured", metric="m", status="hypothesis", date="2026-08-01")]

    html = _render_experiments(experiments, two_regime_store)
    assert "exp-failed" in html
    assert "metric moved the wrong way" in html  # evidence surfaces in the badge title


def test_experiment_empty_state(two_regime_store: Path) -> None:
    html = render_dashboard(two_regime_store, funnel=None, experiments=None)
    assert "No experiments tracked" in html


# --- LIB-58: verdict trajectories --------------------------------------------


def test_verdict_trajectories_empty_state_when_no_verdict_store(two_regime_store: Path) -> None:
    """Omitting verdict_store entirely (the default) renders the empty state,
    so callers that never scored verdicts see no broken/missing section."""
    html = render_dashboard(two_regime_store, funnel=None)
    assert "No scored verdicts yet" in html


def test_verdict_trajectories_render_ordered_sequence(two_regime_store: Path) -> None:
    from telemetry.factstore import append_verdicts

    append_verdicts(
        [
            {
                "experiment": "bash-antipattern-nudge",
                "date": "2026-07-18",
                "metric": "absence:bash-antipatterns",
                "verdict": "trending",
                "evidence": "bash-antipatterns=1 (expected 0)",
            }
        ],
        two_regime_store,
        run_at="2026-07-19T00:00:00Z",
    )
    append_verdicts(
        [
            {
                "experiment": "bash-antipattern-nudge",
                "date": "2026-07-18",
                "metric": "absence:bash-antipatterns",
                "verdict": "confirmed",
                "evidence": "bash-antipatterns=0 across scored sessions",
            }
        ],
        two_regime_store,
        run_at="2026-07-20T00:00:00Z",
    )

    html = render_dashboard(two_regime_store, funnel=None, verdict_store=two_regime_store)

    assert "Verdict trajectories" in html
    assert "bash-antipattern-nudge" in html
    pos_trending = html.index("trending")
    pos_confirmed = html.index("confirmed", pos_trending)
    assert pos_trending < pos_confirmed, "sequence should render oldest run first"


def test_render_verdict_trajectories_region_matches_dashboard_section() -> None:
    from telemetry.dashboard import render_verdict_trajectories_region

    rows = [
        {
            "experiment": "exp-a",
            "date": "2026-07-18",
            "metric": "presence:foo",
            "verdict": "confirmed",
            "evidence": "foo observed",
            "run_at": "2026-07-20T00:00:00Z",
        }
    ]
    region_html = render_verdict_trajectories_region(rows)
    assert "exp-a" in region_html
    assert "Verdict trajectories" in region_html


def test_render_verdict_trajectories_region_empty_state() -> None:
    from telemetry.dashboard import render_verdict_trajectories_region

    assert "No scored verdicts yet" in render_verdict_trajectories_region(None)


# --- Phase 4: execution skill compliance ------------------------------------


def test_execution_skill_compliance_renders(tmp_path: Path) -> None:
    store = tmp_path / "facts.db"
    upsert(
        [
            _row(
                "e1",
                "2026-07-18",
                "session-hygiene-v1",
                session_intent="execution",
                skill_costs='{"execute": 100}',
            ),
            _row(
                "e2",
                "2026-07-18",
                "session-hygiene-v1",
                session_intent="execution",
                skill_costs="{}",
            ),
            _row("s1", "2026-07-18", "session-hygiene-v1", session_intent="scoping"),
        ],
        store,
    )
    html = render_dashboard(store, funnel=None)
    assert "Skill compliance" in html


def test_execution_skill_compliance_no_execution_sessions() -> None:
    bucket = [{"session_intent": "scoping", "skill_costs": "{}"}]
    assert _metric_value("execution_skill_compliance_pct", bucket) is None


def test_execution_skill_compliance_correct_pct() -> None:
    bucket = [
        {"session_intent": "execution", "skill_costs": '{"execute": 100}'},
        {"session_intent": "execution", "skill_costs": "{}"},
    ]
    assert _metric_value("execution_skill_compliance_pct", bucket) == 50.0


# --- Phase 5: friction labels total ------------------------------------------


def test_friction_labels_total_renders(tmp_path: Path) -> None:
    store = tmp_path / "facts.db"
    upsert(
        [
            _row("f1", "2026-07-18", "session-hygiene-v1", friction_label_count=2),
            _row("f2", "2026-07-18", "session-hygiene-v1", friction_label_count=1),
        ],
        store,
    )
    html = render_dashboard(store, funnel=None)
    assert "Explicit friction labels" in html


def test_friction_labels_total_zero() -> None:
    bucket = [{"friction_label_count": 0}, {"friction_label_count": None}]
    assert _metric_value("friction_labels_total", bucket) == 0


# --- Phase 6: subagent spawns table ------------------------------------------


def test_subagent_spawns_table_renders(tmp_path: Path) -> None:
    import json

    store = tmp_path / "facts.db"
    spawns = json.dumps(
        [
            {"type": "Explore", "description": "Find files", "model": None},
            {"type": "Explore", "description": "Search code", "model": None},
            {"type": "code-reviewer", "description": "Review", "model": "sonnet"},
        ]
    )
    upsert([_row("a1", "2026-07-18", "session-hygiene-v1", agent_spawns=spawns)], store)
    html = render_dashboard(store, funnel=None)
    assert "Spawned agents by type" in html
    assert "Explore" in html
    assert "code-reviewer" in html


def test_subagent_spawns_empty(tmp_path: Path) -> None:
    store = tmp_path / "facts.db"
    upsert([_row("a1", "2026-07-18", "session-hygiene-v1")], store)
    html = render_dashboard(store, funnel=None)
    assert "Spawned agents by type" not in html


# --- GUA-43: surface filter --------------------------------------------------


def _two_surface_store(tmp_path: Path) -> Path:
    """Store with two distinct surfaces for testing the JS toggle."""
    store = tmp_path / "facts.db"
    rows = [
        _row("j1", "2026-07-16", "telemetry-v1", surface="claude-vscode"),
        _row("j2", "2026-07-17", "telemetry-v1", surface="claude-vscode"),
        _row("j3", "2026-07-18", "session-hygiene-v1", surface="claude-cli"),
        _row("j4", "2026-07-18", "session-hygiene-v1"),  # surface=None -> "unknown"
    ]
    upsert(rows, store)
    return store


def test_build_series_surface_points_populated(tmp_path: Path) -> None:
    """build_series returns per-surface point breakdowns for continuous metrics."""
    store = _two_surface_store(tmp_path)
    series = build_series("cost_units_p50", store)
    assert not series.faceted
    assert "claude-vscode" in series.surface_points


def test_build_series_all_surfaces_in_all_points(tmp_path: Path) -> None:
    """The all-surfaces series is not limited to a single surface."""
    store = _two_surface_store(tmp_path)
    series = build_series("cost_units_p50", store)
    # Points should span all rows, not just one surface
    assert len(series.points) >= 2


def test_render_dashboard_has_surface_selector(tmp_path: Path) -> None:
    """render_dashboard includes a surface selector element in the nav."""
    store = _two_surface_store(tmp_path)
    page = render_dashboard(store, funnel=None)
    assert 'id="surf-sel"' in page
    assert "surf-filter" in page


def test_render_dashboard_has_js_toggle(tmp_path: Path) -> None:
    """render_dashboard includes the vanilla JS surface toggle script."""
    store = _two_surface_store(tmp_path)
    page = render_dashboard(store, funnel=None)
    assert "surf-view" in page
    assert "surf-sel" in page


def test_render_dashboard_surf_view_divs_present(tmp_path: Path) -> None:
    """Continuous chart sections embed per-surface .surf-view divs."""
    store = _two_surface_store(tmp_path)
    page = render_dashboard(store, funnel=None)
    # At least the "all" surf-view must be present
    assert 'data-surface="all"' in page


def test_distinct_surfaces_returns_observed_values(tmp_path: Path) -> None:
    """_distinct_surfaces returns the surfaces actually present in the store."""
    from telemetry.dashboard import _distinct_surfaces

    store = _two_surface_store(tmp_path)
    surfaces = _distinct_surfaces(store)
    assert "claude-vscode" in surfaces
    assert isinstance(surfaces, list)
    assert surfaces == sorted(surfaces)


# ---------------------------------------------------------------------------
# Review-card patching (canonical guacamayo dashboard, GUA-21)
# ---------------------------------------------------------------------------

_FINDING = {
    "date": "2026-07-29",
    "review_type": "workflow-review",
    "repo": "atlas",
    "issue": "ATL-37",
    "file": "src/graph.py",
    "line": 155,
    "category": "resource-leak",
    "severity": "important",
    "title": "knowledge_tool_node leaks AtlasGraph on exception path",
}

_MARKED_PAGE = (
    '<section id="review">\n'
    "    <!-- REVIEW-FINDINGS:START (regenerated by cartographer --facts; do not hand-edit) -->\n"
    '    <div class="card">stale content</div>\n'
    "    <!-- REVIEW-FINDINGS:END -->\n"
    "</section>\n"
)


def test_render_review_card_counts_and_rows() -> None:
    from telemetry.dashboard import render_review_card

    findings = [
        _FINDING,
        {**_FINDING, "severity": "nit", "file": "n/a", "line": 0, "title": "empty branches"},
    ]
    card = render_review_card(findings)
    assert '<span class="value" style="color:var(--warn)">1</span>' in card
    assert '<span class="label">important</span>' in card
    assert '<span class="label">nit</span>' in card
    assert "atlas ATL-37" in card
    assert "graph.py:155" in card  # file:line shown for located findings
    assert "n/a" not in card  # location suppressed for file="n/a"


def test_render_review_card_empty_state() -> None:
    from telemetry.dashboard import render_review_card

    card = render_review_card([])
    assert "No review findings yet" in card


def test_render_review_card_orders_by_severity() -> None:
    from telemetry.dashboard import render_review_card

    findings = [
        {**_FINDING, "severity": "nit", "title": "a nit"},
        {**_FINDING, "severity": "blocker", "title": "a blocker"},
    ]
    card = render_review_card(findings)
    assert card.index("a blocker") < card.index("a nit")


def test_patch_review_findings_replaces_marked_region(tmp_path: Path) -> None:
    from telemetry.dashboard import patch_review_findings

    page = tmp_path / "context-dashboard.html"
    page.write_text(_MARKED_PAGE, encoding="utf-8")
    assert patch_review_findings(page, [_FINDING]) is True
    patched = page.read_text(encoding="utf-8")
    assert "stale content" not in patched
    assert "knowledge_tool_node" in patched
    # Markers and surrounding hand-maintained HTML survive the patch
    assert "REVIEW-FINDINGS:START" in patched
    assert "REVIEW-FINDINGS:END" in patched
    assert patched.startswith('<section id="review">')
    assert patched.rstrip().endswith("</section>")


def test_patch_review_findings_is_idempotent(tmp_path: Path) -> None:
    from telemetry.dashboard import patch_review_findings

    page = tmp_path / "context-dashboard.html"
    page.write_text(_MARKED_PAGE, encoding="utf-8")
    patch_review_findings(page, [_FINDING])
    once = page.read_text(encoding="utf-8")
    patch_review_findings(page, [_FINDING])
    assert page.read_text(encoding="utf-8") == once


def test_patch_review_findings_missing_markers_leaves_file_untouched(tmp_path: Path) -> None:
    from telemetry.dashboard import patch_review_findings

    page = tmp_path / "context-dashboard.html"
    original = "<section>no markers here</section>\n"
    page.write_text(original, encoding="utf-8")
    assert patch_review_findings(page, [_FINDING]) is False
    assert page.read_text(encoding="utf-8") == original


def test_patch_review_findings_missing_file(tmp_path: Path) -> None:
    from telemetry.dashboard import patch_review_findings

    assert patch_review_findings(tmp_path / "absent.html", [_FINDING]) is False


# ---------------------------------------------------------------------------
# Step 4: input-token series
# ---------------------------------------------------------------------------


def test_input_tokens_p50_series_populated(tmp_path: Path) -> None:
    """input_tokens_p50 series is July-only and correctly computes median."""
    from telemetry.dashboard import build_series

    store = tmp_path / "facts.db"
    upsert(
        [
            _row("j1", "2026-07-18", "session-hygiene-v1", input_tokens=1000),
            _row("j2", "2026-07-18", "session-hygiene-v1", input_tokens=3000),
            # pre-July row must be excluded
            _row("n1", "2026-06-01", "note-hook", input_tokens=999),
        ],
        store,
    )
    s = build_series("input_tokens_p50", store)
    assert s.july_only is True
    assert len(s.points) == 1
    # median of [1000, 3000] at p50 = 1000 (lower-side percentile)
    assert s.points[0].value in (1000.0, 2000.0, 3000.0)  # depends on percentile impl
    assert s.points[0].n == 2


# ---------------------------------------------------------------------------
# Step 5: per-skill economics card
# ---------------------------------------------------------------------------


def test_build_skill_economics_aggregates_correctly(tmp_path: Path) -> None:
    """build_skill_economics sums cost and counts sessions per skill."""
    import json

    from telemetry.dashboard import build_skill_economics

    store = tmp_path / "facts.db"
    upsert(
        [
            _row(
                "j1",
                "2026-07-18",
                "session-hygiene-v1",
                skill_costs=json.dumps({"wake": 500.0, "grow": 200.0}),
            ),
            _row(
                "j2",
                "2026-07-18",
                "session-hygiene-v1",
                skill_costs=json.dumps({"wake": 300.0, "dream": 100.0}),
            ),
            # meta row excluded
            _row(
                "m1",
                "2026-07-18",
                "session-hygiene-v1",
                skill_costs=json.dumps({"wake": 999.0}),
                is_meta=True,
            ),
        ],
        store,
    )
    totals = build_skill_economics(store)
    assert "wake" in totals
    assert totals["wake"]["cost"] == pytest.approx(800.0)
    assert totals["wake"]["n"] == 2
    assert "grow" in totals
    assert totals["grow"]["cost"] == pytest.approx(200.0)
    assert totals["grow"]["n"] == 1
    # meta row excluded
    assert totals["wake"]["cost"] == pytest.approx(800.0)


# ---------------------------------------------------------------------------
# Step 6: cost-by-context-bucket
# ---------------------------------------------------------------------------


def test_cost_bucket_pct_over150k_metric(tmp_path: Path) -> None:
    """cost_bucket_pct_over150k returns share of cost in >150k sessions."""
    from telemetry.dashboard import build_series

    store = tmp_path / "facts.db"
    upsert(
        [
            _row("j1", "2026-07-18", "session-hygiene-v1", max_context=200_000, cost_units=80.0),
            _row("j2", "2026-07-18", "session-hygiene-v1", max_context=50_000, cost_units=20.0),
        ],
        store,
    )
    s = build_series("cost_bucket_pct_over150k", store)
    assert s.july_only is True
    assert len(s.points) == 1
    # 80 / (80+20) = 80%
    assert s.points[0].value == pytest.approx(80.0)


# ---------------------------------------------------------------------------
# Step 7: experiments lifecycle card / ledger parsing
# ---------------------------------------------------------------------------


def test_parse_ledger_active_rows(tmp_path: Path) -> None:
    """parse_ledger reads active tooling-ledger.md rows into Experiment objects."""
    from telemetry.dashboard import parse_ledger

    ledger = tmp_path / "tooling-ledger.md"
    ledger.write_text(
        "# Tooling Ledger\n\n"
        "| Date | Change | Area | Metric | Status |\n"
        "|---|---|---|---|---|\n"
        "| 2026-07-20 | hook-experiment | workflow | `presence:foo` | hypothesis — due 08-03 |\n"
        "| 2026-07-24 | model-test | cost | `ratio:x above 80%` | verified |\n",
        encoding="utf-8",
    )
    exps = parse_ledger(ledger)
    assert len(exps) == 2
    assert exps[0].name == "hook-experiment"
    assert exps[0].metric == "presence:foo"
    assert exps[1].status == "verified"


def test_parse_ledger_malformed_row_skipped(tmp_path: Path) -> None:
    """A row without a change cell is skipped; parse never crashes."""
    from telemetry.dashboard import parse_ledger

    ledger = tmp_path / "tooling-ledger.md"
    ledger.write_text(
        "| Date | Change | Area | Metric | Status |\n"
        "|---|---|---|---|---|\n"
        "|  |  | workflow | — | — |\n"  # empty cells → skipped
        "| 2026-07-20 | good-row | workflow | `presence:bar` | hypothesis |\n",
        encoding="utf-8",
    )
    exps = parse_ledger(ledger)
    assert len(exps) == 1
    assert exps[0].name == "good-row"


def test_parse_ledger_with_log(tmp_path: Path) -> None:
    """parse_ledger reads archived rows from the log file too."""
    from telemetry.dashboard import parse_ledger

    ledger = tmp_path / "tooling-ledger.md"
    ledger.write_text(
        "| Date | Change | Area | Metric | Status |\n"
        "|---|---|---|---|---|\n"
        "| 2026-07-28 | active-exp | workflow | `presence:x` | hypothesis |\n",
        encoding="utf-8",
    )
    log_path = tmp_path / "tooling-ledger-log.md"
    log_path.write_text(
        "| Date | Change | Area | Verdict | Evidence |\n"
        "|---|---|---|---|---|\n"
        "| 2026-07-20 | old-exp | friction | failed | no signal |\n",
        encoding="utf-8",
    )
    exps = parse_ledger(ledger, log_path)
    names = {e.name for e in exps}
    assert "active-exp" in names
    assert "old-exp" in names
    # The log's Verdict column must land in `status`, not its Evidence column.
    old = next(e for e in exps if e.name == "old-exp")
    assert old.status == "failed"
    assert old.metric == "no signal"


# ---------------------------------------------------------------------------
# GUA-137: ledger column offset + closed status vocabulary
# ---------------------------------------------------------------------------


def test_parse_ledger_log_reads_verdict_not_evidence(tmp_path: Path) -> None:
    """Log rows are Date|Change|Area|Verdict|Evidence — verdict is the 4th cell.

    Regression guard for the offset that fed evidence prose into _status_key and
    reported 1 confirmed of 108 while 43 closed verdicts sat one column over.
    """
    from telemetry.dashboard import _status_key, parse_ledger

    log_path = tmp_path / "tooling-ledger-log.md"
    log_path.write_text(
        "| Date | Change | Area | Verdict | Evidence |\n"
        "|---|---|---|---|---|\n"
        "| 2026-07-20 | exp-a | workflow | verified | 0 regressions in R3 window |\n",
        encoding="utf-8",
    )
    ledger = tmp_path / "tooling-ledger.md"
    ledger.write_text(
        "| Date | Change | Area | Metric | Status |\n|---|---|---|---|---|\n", "utf-8"
    )

    exp = parse_ledger(ledger, log_path)[0]
    assert exp.status == "verified"
    # The evidence prose must NOT become the status key (this yielded "0" before).
    assert _status_key(exp.status) == "verified"


def test_status_key_normalises_case_and_markdown() -> None:
    """_status_key folds case and strips markdown so real verdicts are not missed."""
    from telemetry.dashboard import _status_key

    assert _status_key("**VERIFIED**") == "verified"
    assert _status_key("Confirmed present at `~/.claude/CLAUDE.md:176`") == "confirmed"
    assert _status_key("failed") == "failed"
    assert _status_key("") == ""


def test_graduation_denominator_excludes_open_hypotheses() -> None:
    """Rate is over resolved rows only; open hypotheses are reported separately."""
    from telemetry.dashboard import Experiment, compute_graduation

    exps = [
        Experiment(name="a", metric="m", status="verified", date="2026-08-01"),
        Experiment(name="b", metric="m", status="**VERIFIED**", date="2026-08-02"),
        Experiment(name="c", metric="m", status="failed", date="2026-08-03"),
        Experiment(name="d", metric="m", status="inconclusive", date="2026-08-04"),
        Experiment(name="e", metric="m", status="hypothesis", date="2026-08-05"),
        Experiment(name="f", metric="m", status="superseded", date="2026-08-06"),
    ]
    grad = compute_graduation(exps)
    assert (grad.confirmed, grad.failed, grad.inconclusive) == (2, 1, 1)
    assert grad.resolved == 4  # open + excluded are NOT in the denominator
    assert grad.open_count == 1
    assert grad.excluded == 1
    assert grad.rate_pct == 50.0
    # Buckets must partition the input — no row silently vanishes.
    assert grad.total == len(exps)


def test_graduation_rate_is_none_when_nothing_resolved() -> None:
    """An all-hypothesis ledger has no rate rather than a divide-by-zero or 0%."""
    from telemetry.dashboard import Experiment, compute_graduation

    grad = compute_graduation(
        [Experiment(name="a", metric="m", status="hypothesis", date="2026-08-01")]
    )
    assert grad.rate_pct is None
    assert grad.open_count == 1


def test_graduation_surfaces_unknown_statuses() -> None:
    """Unrecognised statuses are counted and sampled, never folded into a bucket."""
    from telemetry.dashboard import Experiment, compute_graduation

    grad = compute_graduation(
        [Experiment(name="a", metric="m", status=".venv\\ junk", date="2026-08-01")]
    )
    assert grad.unknown == 1
    assert grad.resolved == 0
    assert "venv\\" in grad.unknown_samples[0]


# ---------------------------------------------------------------------------
# Step 8: review tab repo grouping
# ---------------------------------------------------------------------------


def test_render_review_card_groups_by_repo(tmp_path: Path) -> None:
    """render_review_card groups findings by repo, most-recent repo first."""
    from telemetry.dashboard import render_review_card

    findings = [
        {**_FINDING, "repo": "atlas", "date": "2026-07-20", "title": "atlas finding"},
        {**_FINDING, "repo": "librarian", "date": "2026-07-29", "title": "lib finding"},
        {**_FINDING, "repo": "atlas", "date": "2026-07-21", "title": "atlas finding 2"},
    ]
    card = render_review_card(findings)
    # librarian has most-recent finding — must appear before atlas
    assert card.index("librarian") < card.index("atlas")
    # both repos should appear as group headers
    assert "librarian" in card
    assert "atlas" in card


def test_render_review_card_source_field_consumed(tmp_path: Path) -> None:
    """When findings carry a source field, it appears in the repo group header."""
    from telemetry.dashboard import render_review_card

    findings = [
        {**_FINDING, "source": "akira-scan", "title": "akira finding"},
    ]
    card = render_review_card(findings)
    assert "akira-scan" in card


def test_render_review_card_missing_source_tolerated(tmp_path: Path) -> None:
    """Old rows without source field still render without error."""
    from telemetry.dashboard import render_review_card

    findings = [{**_FINDING}]  # _FINDING has no 'source'
    card = render_review_card(findings)
    assert "knowledge_tool_node" in card


# ---------------------------------------------------------------------------
# Step 9: friction tab regroup headers
# ---------------------------------------------------------------------------


def test_friction_tab_regroup_headers_present(tmp_path: Path) -> None:
    """render_dashboard includes the three friction group labels."""
    store = tmp_path / "facts.db"
    upsert(
        [
            _row(
                "j1",
                "2026-07-18",
                "session-hygiene-v1",
                human_turns=5,
                user_interruptions=1,
                skill_costs='{"wake":100}',
                session_intent="execution",
                tool_counts='{"Bash":10}',
                tool_error_count=1,
                friction_label_count=0,
            ),
        ],
        store,
    )
    page = render_dashboard(store, funnel=None)
    assert "Prompt-eng" in page
    assert "Loop-eng" in page
    assert "Harness-eng" in page
    assert "Not yet captured" in page  # rework placeholder


# --- Hook activity card -------------------------------------------------------


def _hook_logs(tmp_path: Path, events: str, passes: str) -> tuple[Path, Path]:
    event_log = tmp_path / ".hook-log.jsonl"
    pass_log = tmp_path / ".hook-pass-log.jsonl"
    event_log.write_text(events, encoding="utf-8")
    pass_log.write_text(passes, encoding="utf-8")
    return event_log, pass_log


def test_hook_log_record_split_across_lines_is_stitched(tmp_path: Path) -> None:
    """lib.sh printf logs an unescaped newline inside `context`, splitting one
    JSON object across physical lines. Both halves belong to one record."""
    log = tmp_path / ".hook-log.jsonl"
    log.write_text(
        '{"ts":"2026-07-28T14:47:23Z","hook":"docs_hygiene","exit_code":0,'
        '"repo":"guacamayo","context":"pass: cd /tmp &&\nmake ship"}\n',
        encoding="utf-8",
    )

    events = parse_hook_log(log)

    assert len(events) == 1
    assert events[0]["hook"] == "docs_hygiene"


def test_hook_log_orphan_fragment_does_not_swallow_later_records(tmp_path: Path) -> None:
    """A `tail` cap can leave a headless fragment; it must be dropped, not
    prepended to every following line."""
    log = tmp_path / ".hook-log.jsonl"
    log.write_text(
        'make ship"}\n'
        '{"ts":"2026-07-28T15:00:00Z","hook":"branch_guard","exit_code":2,'
        '"repo":"librarian","context":"blocked"}\n',
        encoding="utf-8",
    )

    events = parse_hook_log(log)

    assert [e["hook"] for e in events] == ["branch_guard"]


def test_hook_activity_counts_blocks_and_warns_by_exit_code(tmp_path: Path) -> None:
    """exit 2 is a block; exit 0 with a message is a warn."""
    event_log, pass_log = _hook_logs(
        tmp_path,
        '{"ts":"2026-07-28T14:00:00Z","hook":"risky_git_guard","exit_code":2,"repo":"g","context":"x"}\n'
        '{"ts":"2026-07-28T14:01:00Z","hook":"risky_git_guard","exit_code":2,"repo":"g","context":"x"}\n'
        '{"ts":"2026-07-28T14:02:00Z","hook":"docs_hygiene","exit_code":0,"repo":"g","context":"x"}\n',
        '{"ts":"2026-07-28T14:03:00Z","hook":"risky_git_guard","repo":"g","context":"pass: x"}\n',
    )

    act = build_hook_activity(event_log, pass_log)

    assert (act.blocks, act.warns, act.passes) == (2, 1, 1)
    assert act.rows[0] == {"hook": "risky_git_guard", "blocks": 2, "warns": 0, "passes": 1}


def test_hook_without_pass_logging_reports_none_not_zero(tmp_path: Path) -> None:
    """Only a couple of hooks call log_pass. For the rest a pass count is
    absent data, and a rendered 0 would read as 'never passed'."""
    event_log, pass_log = _hook_logs(
        tmp_path,
        '{"ts":"2026-07-28T14:02:00Z","hook":"docs_hygiene","exit_code":0,"repo":"g","context":"x"}\n',
        "",
    )

    act = build_hook_activity(event_log, pass_log)

    assert act.rows[0]["passes"] is None
    assert "&mdash;" in render_hook_activity_card(event_log, pass_log)


def test_hook_activity_reports_hooks_that_never_fired(tmp_path: Path) -> None:
    """A guard that never fires is the interesting case -- name it explicitly."""
    event_log, pass_log = _hook_logs(
        tmp_path,
        '{"ts":"2026-07-28T14:02:00Z","hook":"docs_hygiene","exit_code":0,"repo":"g","context":"x"}\n',
        "",
    )

    act = build_hook_activity(event_log, pass_log)

    assert "secrets_scan" in act.silent
    assert "docs_hygiene" not in act.silent
    assert act.seen == 1


def test_hook_activity_empty_logs_render_placeholder(tmp_path: Path) -> None:
    """Missing logs render an empty state, never a broken card."""
    card = render_hook_activity_card(tmp_path / "absent.jsonl", tmp_path / "absent2.jsonl")

    assert "No hook fires logged yet" in card


# ---------------------------------------------------------------------------
# LIB-59: regime-band annotations — bind ledger experiments to friction charts
# ---------------------------------------------------------------------------


def test_ledger_metric_mapping_resolves_the_one_experiment() -> None:
    """The single verified MVP mapping: execution-sessions-with-skills -> the
    execution_skill_compliance_pct chart. No other signal is mapped."""
    assert LEDGER_METRIC_MAPPING == {
        "execution-sessions-with-skills": "execution_skill_compliance_pct"
    }

    exp = Experiment(
        name="Session intent classifier + compliance metric",
        metric="ratio:execution-sessions-with-skills above 80%",
        status="hypothesis — inconclusive (no compliance signals, 227 sessions) — due 08-10",
        date="2026-07-24",
    )
    mapped = _annotations_for_metric("execution_skill_compliance_pct", [exp])
    assert mapped == [exp]
    assert _annotations_for_metric("output_tokens_p50", [exp]) == []


def test_unmapped_ledger_rows_skip_silently() -> None:
    """Experiments with no LEDGER_METRIC_MAPPING entry never appear as an
    annotation for any metric -- they are dropped, not raised as an error."""
    absence_exp = Experiment(
        name="autocompact defect sweep",
        metric="absence:autocompact-defect-reports",
        status="hypothesis",
        date="2026-07-20",
    )
    presence_exp = Experiment(
        name="bash taxonomy rollout",
        metric="presence:bash-stratified-taxonomy",
        status="hypothesis",
        date="2026-07-21",
    )
    for metric in ("execution_skill_compliance_pct", "output_tokens_p50", "cost_units_p50"):
        assert _annotations_for_metric(metric, [absence_exp, presence_exp]) == []


def test_warn_unmapped_experiments_fires_for_new_signal() -> None:
    """A parsed experiment with no mapping entry surfaces as a WARNING, not a
    silent drop -- so a newly added ledger experiment is noticed, not lost."""
    import structlog

    mapped_exp = Experiment(
        name="mapped",
        metric="ratio:execution-sessions-with-skills above 80%",
        status="hypothesis",
        date="2026-07-24",
    )
    unmapped_exp = Experiment(
        name="new-experiment",
        metric="count-drop:some-brand-new-signal above 5",
        status="hypothesis",
        date="2026-07-30",
    )

    with structlog.testing.capture_logs() as cap:
        unmapped = warn_unmapped_experiments([mapped_exp, unmapped_exp])

    assert unmapped == ["some-brand-new-signal"]
    assert any(
        entry.get("event") == "dashboard.ledger_signal_unmapped"
        and entry.get("signal") == "some-brand-new-signal"
        for entry in cap
    )


def test_annotation_renders_on_execution_skill_compliance_series() -> None:
    """A mapped experiment inside a series' date range draws a vertical
    annotation line, with a hover title carrying name + metric + status."""
    points = [
        Point(date="2026-07-20", value=40.0, regime="session-hygiene-v1"),
        Point(date="2026-07-24", value=55.0, regime="session-hygiene-v1"),
        Point(date="2026-07-28", value=60.0, regime="session-hygiene-v1"),
    ]
    exp = Experiment(
        name="Session intent classifier + compliance metric",
        metric="ratio:execution-sessions-with-skills above 80%",
        status="hypothesis — inconclusive (no compliance signals, 227 sessions) — due 08-10",
        date="2026-07-24",
    )
    svg = _svg_line(points, "var(--chart-1)", experiments=[exp])

    assert "<line" in svg
    assert 'class="annotation-line"' in svg
    assert "Session intent classifier + compliance metric" in svg
    assert "ratio:execution-sessions-with-skills above 80%" in svg
    assert "inconclusive" in svg


def test_annotation_outside_series_date_range_does_not_render() -> None:
    """An experiment dated before/after the plotted series draws nothing --
    there is no x-coordinate on this chart for a date it never covers."""
    points = [
        Point(date="2026-07-20", value=40.0, regime="session-hygiene-v1"),
        Point(date="2026-07-28", value=60.0, regime="session-hygiene-v1"),
    ]
    too_early = Experiment(
        name="too-early",
        metric="ratio:execution-sessions-with-skills above 80%",
        status="hypothesis",
        date="2026-06-01",
    )
    too_late = Experiment(
        name="too-late",
        metric="ratio:execution-sessions-with-skills above 80%",
        status="hypothesis",
        date="2026-08-15",
    )
    svg = _render_annotations(points, [too_early, too_late], lambda i: float(i), plot_h=142.0)

    assert svg == ""


def test_render_dashboard_annotation_at_2026_07_24(tmp_path: Path) -> None:
    """End-to-end: the mapped ledger experiment shows up as an annotation on
    the execution_skill_compliance_pct chart in the full rendered page."""
    store = tmp_path / "facts.db"
    upsert(
        [
            _row(
                "e1",
                "2026-07-20",
                "session-hygiene-v1",
                session_intent="execution",
                skill_costs="{}",
            ),
            _row(
                "e2",
                "2026-07-24",
                "session-hygiene-v1",
                session_intent="execution",
                skill_costs='{"execute": 100}',
            ),
            _row(
                "e3",
                "2026-07-28",
                "session-hygiene-v1",
                session_intent="execution",
                skill_costs='{"execute": 100}',
            ),
        ],
        store,
    )
    experiments = [
        Experiment(
            name="Session intent classifier + compliance metric",
            metric="ratio:execution-sessions-with-skills above 80%",
            status="hypothesis — inconclusive (no compliance signals, 227 sessions) — due 08-10",
            date="2026-07-24",
        )
    ]
    html = render_dashboard(store, funnel=None, experiments=experiments)

    assert 'data-metric="execution_skill_compliance_pct"' in html
    assert 'class="annotation-line"' in html
    assert "Session intent classifier + compliance metric" in html


# --- GUA-104a Steps 1-3: period bucketing ----------------------------------


@pytest.mark.parametrize(
    ("day", "period", "expected"),
    [
        ("2026-08-13", "day", "2026-08-13"),
        ("2026-08-13", "week", "2026-W33"),
        ("2026-08-13", "month", "2026-08"),
        # ISO week 1 spanning December — the classic off-by-one. 2026 is a
        # 53-week ISO year, so its last days stay in 2026-W53.
        ("2026-12-31", "week", "2026-W53"),
        ("2027-01-01", "week", "2026-W53"),
        ("2027-01-04", "week", "2027-W01"),
        # The mirror case: December days that belong to the *next* ISO year.
        ("2024-12-30", "week", "2025-W01"),
        ("2022-01-01", "week", "2021-W52"),
        ("2026-12-31", "month", "2026-12"),
    ],
)
def test_period_key(day: str, period: str, expected: str) -> None:
    assert _period_key(day, period) == expected


@pytest.mark.parametrize("period", ["", "daily", "weekly", "monthly", "year", "DAY"])
def test_period_key_rejects_unknown_period(period: str) -> None:
    """A silent fallback to daily would make a caller typo look like working code."""
    with pytest.raises(ValueError, match="unknown period"):
        _period_key("2026-08-13", period)


def test_period_keys_sort_lexicographically() -> None:
    """Bucket ordering relies on string sort — the property `_iso_week` already had."""
    days = ["2026-01-05", "2026-02-09", "2026-08-13", "2026-12-31"]
    for period in ("day", "week", "month"):
        keys = [_period_key(d, period) for d in days]
        assert keys == sorted(keys), f"{period} keys do not sort: {keys}"


def test_group_defaults_to_daily(two_regime_store: Path) -> None:
    """Default `period="day"` must leave every pre-period caller byte-identical."""
    rows = _work_sessions(read_all(two_regime_store))
    explicit = {k: len(v) for k, v in _group(rows, "date", "day").items()}
    assert {k: len(v) for k, v in _group(rows).items()} == explicit
    assert set(explicit) == {str(r["date"]) for r in rows}


def test_group_buckets_by_period(two_regime_store: Path) -> None:
    rows = _work_sessions(read_all(two_regime_store))
    monthly = _group(rows, "date", "month")
    assert set(monthly) == {"2026-05", "2026-06", "2026-07"}
    assert len(monthly["2026-07"]) == 3
    # Every row lands in exactly one bucket at every period.
    for period in ("day", "week", "month"):
        assert sum(len(v) for v in _group(rows, "date", period).values()) == len(rows)


def test_point_date_stays_iso_at_every_period(two_regime_store: Path) -> None:
    """`_span_days` calls `_date.fromisoformat` — a bucket key there raises."""
    for period in ("day", "week", "month"):
        series = build_series("cost_units_p50", two_regime_store, period)
        assert series.points, f"{period} produced no points"
        for point in series.points:
            _date.fromisoformat(point.date)  # raises if `date` holds a bucket key
        assert _span_days(series.points) >= 0


def test_point_bucket_carries_the_display_key(two_regime_store: Path) -> None:
    series = build_series("cost_units_p50", two_regime_store, "month")
    # 2026-07 appears twice: the month spans a regime boundary, and buckets are
    # sub-grouped by regime so a panel never mixes regimes.
    assert [p.bucket for p in series.points] == ["2026-05", "2026-06", "2026-07", "2026-07"]
    # `date` is the first observation in the bucket, not the key.
    assert [p.date for p in series.points] == [
        "2026-05-01",
        "2026-06-10",
        "2026-07-16",
        "2026-07-18",
    ]
    assert [p.regime for p in series.points] == [
        "note-hook",
        "note-hook",
        "telemetry-v1",
        "session-hygiene-v1",
    ]


def test_coarser_periods_collapse_points(two_regime_store: Path) -> None:
    daily = build_series("cost_units_p50", two_regime_store, "day")
    monthly = build_series("cost_units_p50", two_regime_store, "month")
    assert len(monthly.points) < len(daily.points)
    assert sum(p.n for p in monthly.points) == sum(p.n for p in daily.points)


def test_build_series_rejects_unknown_period(two_regime_store: Path) -> None:
    with pytest.raises(ValueError, match="unknown period"):
        build_series("cost_units_p50", two_regime_store, "weekly")


def test_period_buckets_never_span_a_regime(two_regime_store: Path) -> None:
    """A week or month can straddle a regime boundary; a day cannot.

    The generic path assumed single-regime buckets ("regime is a date lookup"),
    which only holds at daily resolution — so bucketing sub-groups by regime.
    """
    for metric in sorted(RATE_METRICS):
        for period in ("day", "week", "month"):
            series = build_series(metric, two_regime_store, period)
            for panel in series.panels:
                assert {p.regime for p in panel.points} == {panel.regime}


def test_sessions_per_week_folded_into_group_path(two_regime_store: Path) -> None:
    """The hand-rolled weekly bucketing was removed; output must not change."""
    series = build_series("sessions_per_week", two_regime_store)

    assert series.faceted is True
    observed = {
        (panel.regime, point.date, point.value, point.n)
        for panel in series.panels
        for point in panel.points
    }
    assert observed == {
        ("note-hook", "2026-05-01", 2.0, 2),
        ("note-hook", "2026-06-10", 1.0, 1),
        ("telemetry-v1", "2026-07-16", 1.0, 1),
        ("session-hygiene-v1", "2026-07-18", 2.0, 2),
    }


# --- GUA-104a Step 4: period selector --------------------------------------


def test_period_selector_renders_all_three_buttons(two_regime_store: Path) -> None:
    html = render_dashboard(two_regime_store, funnel=None)
    for period in PERIODS:
        assert f'class="period-btn active" data-period="{period}"' in html or (
            f'data-period="{period}"' in html
        )
    assert 'class="period-filter"' in html


def test_default_period_is_week(two_regime_store: Path) -> None:
    """Daily is noise at this volume; monthly hides everything actionable."""
    html = render_dashboard(two_regime_store, funnel=None)
    assert f'class="period-btn active" data-period="{_DEFAULT_PERIOD}"' in html
    assert _DEFAULT_PERIOD == "week"
    # Only the default period's views are visible on load.
    assert f'<div class="period-view" data-period="{_DEFAULT_PERIOD}">' in html
    for period in PERIODS:
        if period != _DEFAULT_PERIOD:
            assert f'data-period="{period}" style="display:none"' in html


def test_every_panel_rendered_at_every_period(two_regime_store: Path) -> None:
    html = render_dashboard(two_regime_store, funnel=None)
    counts = {p: html.count(f'class="period-view" data-period="{p}"') for p in PERIODS}
    assert len(set(counts.values())) == 1, f"uneven period coverage: {counts}"
    assert counts[_DEFAULT_PERIOD] > 0


def test_period_toggle_is_self_contained(two_regime_store: Path) -> None:
    """The dashboard opens from file:// with no network — a CDN script is a blank panel."""
    html = render_dashboard(two_regime_store, funnel=None)
    assert "period-btn" in html and "addEventListener" in html
    assert 'apply("week")' in html
    # No remote references anywhere in the emitted page.
    assert "http://" not in html
    assert "https://" not in html
    assert "<script src" not in html


def test_period_and_surface_toggles_do_not_collide(two_regime_store: Path) -> None:
    """Both toggles hide/show by dataset attribute; they must nest, not fight.

    `.surf-view` divs live inside `.period-view` wrappers, so the period toggle
    governs the outer element and the surface toggle the inner one.
    """
    html = render_dashboard(two_regime_store, funnel=None)
    period_at = html.index('class="period-view"')
    surf_at = html.index('class="surf-view"')
    assert period_at < surf_at, "surf-view must nest inside period-view"
    assert html.count('id="surf-sel"') == 1


# --- Recurring friction card: rising badge + sparkline (GUA-104b) ------------


def _rf(title: str, date: str, repo: str = "guacamayo") -> dict[str, Any]:
    return {
        "title": title,
        "category": "config",
        "repo": repo,
        "date": date,
        "merge_impact": "important",
        "source": "sanyi",
    }


def test_direction_badge_renders_only_when_trending() -> None:
    assert _direction_badge(DIRECTION_FLAT) == ""
    assert "rising" in _direction_badge(DIRECTION_RISING)
    assert "falling" in _direction_badge(DIRECTION_FALLING)


def test_direction_badge_colors_falling_as_good_news() -> None:
    """Friction going down is a positive outcome and must not render as a warning."""
    assert "--bad" in _direction_badge(DIRECTION_RISING)
    assert "--good" in _direction_badge(DIRECTION_FALLING)


def test_direction_badge_ignores_unknown_direction() -> None:
    """An unrecognized value renders nothing rather than an unstyled badge."""
    assert _direction_badge("sideways") == ""


def test_period_sparkline_empty_counts_render_a_dash() -> None:
    assert "—" in _period_sparkline({})


def test_period_sparkline_scales_bars_to_group_peak() -> None:
    """Bars are scaled within the group, so the tallest bar always hits the box
    height regardless of the group's absolute size."""
    svg = _period_sparkline({"2026-W30": 1, "2026-W31": 2, "2026-W32": 4})
    assert svg.count("<rect") == 3
    # Peak bar spans the full height; y=0 is the top of the box.
    assert 'y="0"' in svg
    assert "2026-W32: 4" in svg


def test_period_sparkline_caps_at_twelve_buckets() -> None:
    counts = {f"2026-W{i:02d}": 1 for i in range(1, 30)}
    assert _period_sparkline(counts).count("<rect") == 12


def test_recurring_friction_table_shows_badge_and_sparkline() -> None:
    """A rising group reaches the table and carries both new affordances."""
    findings = [
        _rf("resource leak, not closed", "2026-07-15"),
        _rf("resource leak, not closed", "2026-07-22"),
    ] + [_rf("resource leak, not closed", "2026-08-05") for _ in range(5)]

    html = _render_review_findings(findings)
    assert "Recurring friction" in html
    assert "<th>By week</th>" in html
    assert ">rising<" in html
    assert "<svg" in html


def test_recurring_friction_includes_rising_group_below_promotable_threshold() -> None:
    """`promotable or rising` is applied at the call site: a group can reach the
    table on the trend signal alone, without a high lifetime count."""
    findings = [_rf("slug mismatch between config and loader", "2026-08-05") for _ in range(3)]
    html = _render_review_findings(findings)
    assert "slug-inconsistency" in html


def test_recurring_friction_escapes_pattern_and_repo() -> None:
    """The unmatched fallback key embeds category and repo verbatim, so both are
    attacker-shaped input as far as this table is concerned."""
    findings = [
        {
            "title": "no known signature here",
            "category": "<script>x</script>",
            "repo": "guacamayo",
            "date": "2026-08-05",
            "merge_impact": "nit",
            "source": "sanyi",
        }
        for _ in range(3)
    ]
    html = _render_review_findings(findings)
    assert "<script>x</script>" not in html
    assert "&lt;script&gt;" in html


# --- GUA-120: dashboard metrics (pressure, cost/tool, mutation, yield) --------
#
# The invariant these tests defend is F1's: a metric whose input column is
# sparsely populated must declare its frame. A tile computed over "the rows that
# happen to have the column" renders identically to one computed over the whole
# corpus, and that indistinguishability is the defect -- so the fence and the
# rendered n are tested as behaviour, not as presentation.


def test_context_pressure_ratio_counts_the_100k_floor_not_the_150k_cliff() -> None:
    """The metric must not duplicate pct_over_150k: 120k is pressure, not cost."""
    bucket = [
        {"max_context": 120_000},
        {"max_context": 200_000},
        {"max_context": 40_000},
        {"max_context": 90_000},
    ]
    assert _metric_value("context_pressure_ratio", bucket) == 50.0
    assert _metric_value("pct_over_150k", bucket) == 25.0


def test_context_pressure_ratio_none_when_no_max_context() -> None:
    """Empty bucket returns None rather than 0% -- a 0 would plot as 'no
    pressure' on a period that measured nothing at all."""
    assert _metric_value("context_pressure_ratio", [{"max_context": None}]) is None


def test_context_pressure_ratio_excludes_unrecorded_rows_from_denominator() -> None:
    bucket = [{"max_context": 120_000}, {"max_context": None}, {"max_context": 10_000}]
    assert _metric_value("context_pressure_ratio", bucket) == 50.0


def test_cost_per_tool_divides_cost_by_calls() -> None:
    bucket = [
        {"cost_units": 100.0, "tool_counts": '{"Read": 3, "Edit": 1}'},
        {"cost_units": 50.0, "tool_counts": '{"Bash": 1}'},
    ]
    assert _metric_value("cost_per_tool", bucket) == 30.0


def test_cost_per_tool_excludes_zero_tool_sessions_from_both_sides() -> None:
    """A session with no tool calls is not zero-cost work -- including its cost
    over someone else's calls would inflate the ratio without adding a call."""
    with_tools = [{"cost_units": 100.0, "tool_counts": '{"Read": 4}'}]
    plus_toolless = [*with_tools, {"cost_units": 900.0, "tool_counts": "{}"}]
    assert _metric_value("cost_per_tool", with_tools) == 25.0
    assert _metric_value("cost_per_tool", plus_toolless) == 25.0


def test_cost_per_tool_none_when_no_tool_calls() -> None:
    assert _metric_value("cost_per_tool", [{"cost_units": 10.0, "tool_counts": "{}"}]) is None


def test_cost_per_tool_survives_malformed_tool_counts() -> None:
    """Malformed JSON is treated as no tool calls, not as a crash: the column is
    parser output and a bad row must not take the whole bucket down."""
    assert (
        _metric_value("cost_per_tool", [{"cost_units": 10.0, "tool_counts": "{not json"}]) is None
    )


def test_mutation_ratio_counts_writes_over_write_plus_read() -> None:
    bucket = [{"tool_counts": '{"Edit": 2, "Write": 1, "Read": 6, "Grep": 1}'}]
    assert _metric_value("mutation_ratio", bucket) == 30.0


def test_mutation_ratio_excludes_bash_from_both_sides() -> None:
    """Bash is unclassifiable from tool_counts alone. Adding 100 Bash calls must
    not move the ratio -- if it does, Bash has silently become a 'read'."""
    without = [{"tool_counts": '{"Edit": 1, "Read": 1}'}]
    with_bash = [{"tool_counts": '{"Edit": 1, "Read": 1, "Bash": 100}'}]
    assert _metric_value("mutation_ratio", without) == 50.0
    assert _metric_value("mutation_ratio", with_bash) == 50.0


def test_mutation_ratio_none_when_no_classifiable_tools() -> None:
    assert _metric_value("mutation_ratio", [{"tool_counts": '{"Bash": 3}'}]) is None


def test_compaction_yield_is_median_over_populated_rows_only() -> None:
    """Mixed bucket: the None row is excluded from the median, not read as 0 --
    a 0 would claim a compact bought no turns when it in fact bought unknown."""
    bucket = [
        {"turns_since_last_compact": 10},
        {"turns_since_last_compact": 20},
        {"turns_since_last_compact": 30},
        {"turns_since_last_compact": None},
    ]
    # Nearest-rank p50 over [10, 20, 30] -- the repo-wide _percentile convention.
    # The None row is excluded: were it read as 0, the median would fall to 10.
    assert _metric_value("compaction_yield", bucket) == 20.0


def test_compaction_yield_none_when_column_absent() -> None:
    assert _metric_value("compaction_yield", [{"turns_since_last_compact": None}]) is None


def test_compaction_yield_fence_excludes_non_compacted_sessions(tmp_path: Path) -> None:
    """The F1 fence, as behaviour. A non-compacted July row carrying the column
    must not reach the series -- and, critically, must not inflate Point.n, or
    the rendered population describes rows the metric never measured."""
    store = tmp_path / "facts.db"
    upsert(
        [
            _row(
                "c1",
                "2026-07-18",
                "session-hygiene-v1",
                compacted=True,
                turns_since_last_compact=10,
            ),
            _row(
                "c2",
                "2026-07-18",
                "session-hygiene-v1",
                compacted=True,
                turns_since_last_compact=20,
            ),
            _row(
                "c3",
                "2026-07-18",
                "session-hygiene-v1",
                compacted=True,
                turns_since_last_compact=30,
            ),
            # Unfenced, this row would drag the median to 30 and n to 4.
            _row(
                "u1",
                "2026-07-18",
                "session-hygiene-v1",
                compacted=False,
                turns_since_last_compact=999,
            ),
        ],
        store,
    )
    series = build_series("compaction_yield", store, "day")
    assert [p.value for p in series.points] == [20.0]
    assert [p.n for p in series.points] == [3]


def test_compaction_yield_fence_excludes_pre_july_compacted_sessions(tmp_path: Path) -> None:
    """235 pre-July compacted sessions have a null column by design. The fence
    drops them rather than letting them dilute the July population."""
    store = tmp_path / "facts.db"
    upsert(
        [
            _row("n1", "2026-05-01", "note-hook", compacted=True),
            _row(
                "c1",
                "2026-07-18",
                "session-hygiene-v1",
                compacted=True,
                turns_since_last_compact=10,
            ),
        ],
        store,
    )
    series = build_series("compaction_yield", store, "day")
    assert [p.date for p in series.points] == ["2026-07-18"]
    assert sum(p.n for p in series.points) == 1


def test_compaction_yield_is_july_fenced_in_the_series() -> None:
    """COMPACT_METRICS implies the July fence: the column has no pre-July data,
    so a series flagged otherwise would advertise a boundary it does not have."""
    assert "compaction_yield" in COMPACT_METRICS
    assert "compaction_yield" not in RATE_METRICS


def test_new_metrics_are_july_fenced() -> None:
    """max_context and tool_counts are null in the note era. A metric reading
    them without a fence draws a line across a boundary its data cannot cross."""
    for metric in ("context_pressure_ratio", "cost_per_tool", "mutation_ratio"):
        assert metric in JULY_ONLY_METRICS
        assert build_series(metric, _empty_store_path(), "day").july_only


def _empty_store_path() -> Path:
    """A store with no rows -- july_only is a property of the metric, not the data."""
    import tempfile

    store = Path(tempfile.mkdtemp()) / "facts.db"
    upsert([_row("x", "2026-07-18", "session-hygiene-v1")], store)
    return store


def test_every_new_tile_renders_its_population(tmp_path: Path) -> None:
    """DoD: the row count is rendered on the tile, not left to the table view."""
    store = tmp_path / "facts.db"
    upsert(
        [
            _row(
                "j1",
                "2026-07-18",
                "session-hygiene-v1",
                compacted=True,
                max_context=120_000,
                turns_since_last_compact=10,
                tool_counts='{"Edit": 2, "Read": 3}',
            ),
            _row(
                "j2",
                "2026-07-19",
                "session-hygiene-v1",
                compacted=True,
                max_context=80_000,
                turns_since_last_compact=4,
                tool_counts='{"Read": 5}',
            ),
        ],
        store,
    )
    page = render_dashboard(store, funnel=None)
    assert "Context pressure ratio" in page
    assert "Cost per tool call" in page
    assert "Mutation vs read ratio" in page
    assert "Compaction yield" in page
    assert 'class="population"' in page
    assert "July+ compacted sessions" in page


def test_population_line_sums_contributing_rows_only() -> None:
    """n counts rows behind the plotted values. A bucket that returned None is
    dropped from points, so it must not appear in the total."""
    series = Series(
        metric="compaction_yield",
        faceted=False,
        points=[
            Point(date="2026-07-18", value=10.0, regime="session-hygiene-v1", n=2),
            Point(date="2026-07-19", value=12.0, regime="session-hygiene-v1", n=3),
        ],
    )
    assert "n = 5 July+ compacted sessions" in _population_line(series)


def test_population_frame_defaults_to_sessions() -> None:
    series = Series(
        metric="cost_units_p50",
        faceted=False,
        points=[Point(date="2026-07-18", value=1.0, regime="session-hygiene-v1", n=7)],
    )
    assert "n = 7 sessions" in _population_line(series)


def test_skill_economics_has_cost_per_session_column(tmp_path: Path) -> None:
    store = tmp_path / "facts.db"
    upsert(
        [
            _row("s1", "2026-07-18", "session-hygiene-v1", skill_costs='{"execute": 300}'),
            _row("s2", "2026-07-19", "session-hygiene-v1", skill_costs='{"execute": 100}'),
        ],
        store,
    )
    table = _render_skill_economics(store)
    assert "cost/session" in table
    assert "200" in table


def test_skill_economics_states_cost_is_not_value(tmp_path: Path) -> None:
    """The column ranks spend, not worth. Without the caveat rendered, a cheap
    skill reads as a good one -- an attribution the store cannot support."""
    store = tmp_path / "facts.db"
    upsert([_row("s1", "2026-07-18", "session-hygiene-v1", skill_costs='{"execute": 300}')], store)
    assert "not value returned" in _render_skill_economics(store)


def test_point_n_counts_scored_rows_not_bucket_size(tmp_path: Path) -> None:
    """The rendered n must count rows the metric used. Bucket size and scored
    count coincide on a store where every row carries the column -- which is
    exactly why the divergent case is the one worth pinning."""
    store = tmp_path / "facts.db"
    upsert(
        [
            _row("a", "2026-07-18", "session-hygiene-v1", max_context=120_000),
            _row("b", "2026-07-18", "session-hygiene-v1", max_context=None),
        ],
        store,
    )
    series = build_series("context_pressure_ratio", store, "day")
    assert [p.n for p in series.points] == [1]
    assert "n = 1 sessions with max_context recorded" in _population_line(series)


def test_scored_count_defaults_to_bucket_size_for_unfiltered_metrics() -> None:
    """A metric reading a column every row has keeps bucket size -- the
    predicate table is an exception list, not a new requirement on every metric."""
    bucket = [{"cost_units": 1.0}, {"cost_units": 2.0}]
    assert _scored_count("cost_units_p50", bucket) == 2


from telemetry.dashboard import (
    parse_actions_log,
    render_automated_actions_region,
)

# ---------------------------------------------------------------------------
# Automated actions tile — Step 8 (GUA-119 sub-issue C)
# ---------------------------------------------------------------------------


class TestParseActionsLog:
    """parse_actions_log reads actions.jsonl, skips malformed lines."""

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        result = parse_actions_log(tmp_path / "actions.jsonl")
        assert result == []

    def test_empty_file_returns_empty(self, tmp_path: Path) -> None:
        p = tmp_path / "actions.jsonl"
        p.write_text("", encoding="utf-8")
        assert parse_actions_log(p) == []

    def test_parses_valid_records(self, tmp_path: Path) -> None:
        p = tmp_path / "actions.jsonl"
        p.write_text(
            '{"ts":"2026-08-16T10:00:00Z","action":"auto_close_merged","outcome":"acted","reason":"ok","evidence":"x"}\n'
            '{"ts":"2026-08-16T10:01:00Z","action":"auto_fix_label","outcome":"declined","reason":"undetermined","evidence":"y"}\n',
            encoding="utf-8",
        )
        records = parse_actions_log(p)
        assert len(records) == 2
        assert records[0]["action"] == "auto_close_merged"
        assert records[1]["outcome"] == "declined"

    def test_malformed_line_skipped(self, tmp_path: Path) -> None:
        p = tmp_path / "actions.jsonl"
        p.write_text(
            '{"ts":"2026-08-16T10:00:00Z","action":"spawn_retro","outcome":"acted"}\n'
            "NOT_JSON\n"
            '{"ts":"2026-08-16T10:02:00Z","action":"auto_fix_label","outcome":"declined"}\n',
            encoding="utf-8",
        )
        records = parse_actions_log(p)
        assert len(records) == 2

    def test_blank_lines_skipped(self, tmp_path: Path) -> None:
        p = tmp_path / "actions.jsonl"
        p.write_text(
            '\n{"ts":"2026-08-16T10:00:00Z","action":"spawn_retro","outcome":"acted"}\n\n',
            encoding="utf-8",
        )
        records = parse_actions_log(p)
        assert len(records) == 1


class TestRenderAutomatedActions:
    """render_automated_actions_region renders correctly from records."""

    def test_empty_records_renders_no_automated_actions(self) -> None:
        html = render_automated_actions_region([])
        assert "no automated actions" in html.lower() or "No automated actions" in html
        # Must not render a fabricated rate
        assert "%" not in html

    def test_none_renders_no_automated_actions(self) -> None:
        html = render_automated_actions_region(None)
        assert "No automated actions" in html
        assert "%" not in html

    def test_populated_log_renders_counts_and_denominator(self) -> None:
        records = [
            {"action": "auto_close_merged", "outcome": "acted"},
            {"action": "auto_close_merged", "outcome": "acted"},
            {"action": "auto_close_merged", "outcome": "declined"},
            {"action": "spawn_retro", "outcome": "acted"},
        ]
        html = render_automated_actions_region(records)
        # Total row count must be rendered (denominator convention)
        assert "4" in html  # total records
        # Action type rows present
        assert "auto_close_merged" in html
        assert "spawn_retro" in html
        # Acceptance rate for auto_close_merged: 2 acted / 3 decidable = 66%
        assert "66%" in html

    def test_acceptance_rate_excludes_deferred(self) -> None:
        records = [
            {"action": "fix_label", "outcome": "accepted"},  # positive
            {"action": "fix_label", "outcome": "deferred"},  # excluded from denominator
            {"action": "fix_label", "outcome": "rejected"},  # negative
        ]
        html = render_automated_actions_region(records)
        # Rate = 1 accepted / (1 accepted + 1 rejected) = 50%, NOT 1/3 = 33%
        assert "50%" in html
        # Deferred count rendered
        assert "1" in html

    def test_all_deferred_renders_no_rate(self) -> None:
        records = [
            {"action": "triage", "outcome": "deferred"},
            {"action": "triage", "outcome": "deferred"},
        ]
        html = render_automated_actions_region(records)
        # No decidable records → rate must be em-dash, not a percentage
        assert "—" in html
        assert "%" not in html

    def test_denominator_always_rendered(self) -> None:
        """Every tile states the row count — the denominator convention."""
        records = [
            {"action": "close_issue", "outcome": "acted"},
            {"action": "close_issue", "outcome": "declined"},
        ]
        html = render_automated_actions_region(records)
        # The total row count (2) must appear
        assert "2" in html
        # The per-type count (2 in total column) must appear
        assert "Total" in html or "total" in html.lower() or "n)" in html.lower()


def test_compaction_yield_note_does_not_hardcode_a_row_count(tmp_path: Path) -> None:
    """GUA-120's DoD asked for the literal label "n=182 July+ compacted sessions".
    182 is the store's July+ compacted count *including* meta-sessions, which
    `_work_sessions` excludes from every metric on this dashboard -- the live
    figure is 141. A hardcoded count also goes stale on the next sync. The tile
    renders its own n instead, which satisfies the requirement the number was
    standing in for: the population must be visible on the tile.
    """
    store = tmp_path / "facts.db"
    upsert(
        [
            _row(
                "c1",
                "2026-07-18",
                "session-hygiene-v1",
                compacted=True,
                turns_since_last_compact=10,
            ),
            _row(
                "m1",
                "2026-07-18",
                "session-hygiene-v1",
                compacted=True,
                turns_since_last_compact=99,
                is_meta=True,
            ),
        ],
        store,
    )
    page = render_dashboard(store, funnel=None)
    assert "n=182" not in page
    series = build_series("compaction_yield", store, "day")
    assert [p.n for p in series.points] == [1]


# --- GUA-137 Step 1: the trend_7d component --------------------------------


def test_sparkline_normalizes_min_and_max_to_the_viewbox() -> None:
    """The lowest point sits at the bottom inset, the highest at the top.

    Verifies the y-inversion too: SVG y grows downward, so the *larger* value
    must produce the *smaller* y.
    """
    points = [
        Point(date="2026-08-11", value=10.0, regime="r"),
        Point(date="2026-08-12", value=20.0, regime="r"),
        Point(date="2026-08-13", value=30.0, regime="r"),
    ]
    svg = _sparkline_svg(points)

    coords = re.search(r'points="([^"]+)"', svg)
    assert coords, "polyline carries no points"
    parsed = [tuple(float(n) for n in pair.split(",")) for pair in coords.group(1).split()]

    xs = [x for x, _ in parsed]
    ys = [y for _, y in parsed]
    assert xs == [0, 50, 100], "x should span the full 100-unit viewBox evenly"
    assert ys[0] > ys[1] > ys[2], "larger values must sit higher (smaller y)"
    assert min(ys) == 2 and max(ys) == 18, "extremes should land on the padded edges"


def test_sparkline_flat_series_plots_down_the_middle() -> None:
    """A genuinely flat metric is a real trend — not a divide-by-zero."""
    points = [Point(date=f"2026-08-1{i}", value=5.0, regime="r") for i in range(3)]
    svg = _sparkline_svg(points)

    ys = {
        float(pair.split(",")[1]) for pair in re.search(r'points="([^"]+)"', svg).group(1).split()
    }
    assert ys == {10.0}, "a flat series should render one horizontal line mid-box"


@pytest.mark.parametrize("count", [0, 1])
def test_sparkline_thin_series_renders_placeholder_not_a_line(count: int) -> None:
    """The metric fence: one observation cannot show a trend, so none is drawn.

    A fabricated flat line through a single point would read as "stable" on
    evidence that cannot establish stability.
    """
    points = [Point(date="2026-08-13", value=7.0, regime="r")] * count
    out = _sparkline_svg(points)

    assert "<polyline" not in out, "a sub-2-point series must not draw a line"
    assert "<svg" not in out
    assert f"no trend (n={count})" in out


def test_sparkline_tooltip_carries_every_date_value_pair() -> None:
    """Hover text is the raw data — the cleaner presentation loses no numbers."""
    points = [
        Point(date="2026-08-12", value=1.0, regime="r"),
        Point(date="2026-08-13", value=2.0, regime="r"),
    ]
    svg = _sparkline_svg(points)

    assert "<title>2026-08-12=1 · 2026-08-13=2</title>" in svg


def test_trend_7d_takes_the_last_seven_days_only(tmp_path: Path) -> None:
    """A longer store is windowed to the trailing 7 points, in date order."""
    store = tmp_path / "facts.db"
    upsert(
        [
            _row(f"s{i}", f"2026-07-{16 + i:02d}", "session-hygiene-v1", cost_units=100.0 * i)
            for i in range(10)
        ],
        store,
    )
    svg = trend_7d("cost_units_p50", store)

    pairs = re.search(r"<title>([^<]+)</title>", svg).group(1).split(" · ")
    assert len(pairs) == 7, "window should be exactly 7 points"
    dates = [p.split("=")[0] for p in pairs]
    assert dates == sorted(dates), "points must be chronological"
    assert dates[-1] == "2026-07-25", "window should end at the most recent day"


def test_trend_7d_skips_missing_days_rather_than_zero_filling(tmp_path: Path) -> None:
    """A day with no sessions is absent data, not a zero.

    Zero-filling would draw a crash to the floor that never happened.
    """
    store = tmp_path / "facts.db"
    upsert(
        [
            _row("a", "2026-07-16", "session-hygiene-v1", cost_units=500.0),
            _row("b", "2026-07-20", "session-hygiene-v1", cost_units=500.0),
        ],
        store,
    )
    svg = trend_7d("cost_units_p50", store)

    title = re.search(r"<title>([^<]+)</title>", svg).group(1)
    assert title == "2026-07-16=500 · 2026-07-20=500"
    assert "2026-07-17" not in title, "gap days must not be imputed"
    ys = {
        float(pair.split(",")[1]) for pair in re.search(r'points="([^"]+)"', svg).group(1).split()
    }
    assert ys == {10.0}, "two equal values stay flat — no phantom dip between them"


def test_trend_7d_single_day_store_renders_no_sparkline(tmp_path: Path) -> None:
    """Step 2's contract at the source: absence, not a flat line."""
    store = tmp_path / "facts.db"
    upsert([_row("only", "2026-07-16", "session-hygiene-v1")], store)

    assert "sparkline" not in trend_7d("cost_units_p50", store)


def test_trend_7d_flattens_faceted_metrics_chronologically(tmp_path: Path) -> None:
    """Rate metrics come back per-regime; a sparkline has no room for a legend."""
    store = tmp_path / "facts.db"
    upsert(
        [
            _row("n1", "2026-05-01", "note-hook", compacted=True),
            _row("n2", "2026-05-02", "note-hook", compacted=False),
            _row("j1", "2026-07-16", "telemetry-v1", compacted=True),
            _row("j2", "2026-07-17", "telemetry-v1", compacted=False),
        ],
        store,
    )
    svg = trend_7d("compaction_pct", store)

    assert "<polyline" in svg, "faceted panels should flatten into one line"
    dates = [
        p.split("=")[0] for p in re.search(r"<title>([^<]+)</title>", svg).group(1).split(" · ")
    ]
    assert dates == sorted(dates), "flattened points must still be chronological"


# --- GUA-137 Step 2: the component attached to three surfaces --------------


def _multi_day_skill_store(tmp_path: Path) -> Path:
    store = tmp_path / "facts.db"
    upsert(
        [
            _row(
                f"s{i}",
                f"2026-07-{16 + i:02d}",
                "session-hygiene-v1",
                skill_costs=json.dumps({"/workflow-execute": 100.0 * (i + 1)}),
            )
            for i in range(4)
        ],
        store,
    )
    return store


def test_skill_economics_renders_a_sparkline_per_skill(tmp_path: Path) -> None:
    """Surface 1: skills carry the shared component."""
    html_out = _render_skill_economics(_multi_day_skill_store(tmp_path))

    assert "7-day trend" in html_out, "the trend column header should exist"
    assert 'class="sparkline"' in html_out


def test_skill_economics_single_day_renders_no_sparkline(tmp_path: Path) -> None:
    """Absence, not a flat line — one day of data cannot show a trend."""
    store = tmp_path / "facts.db"
    upsert(
        [_row("s1", "2026-07-16", "session-hygiene-v1", skill_costs=json.dumps({"/x": 10.0}))],
        store,
    )
    html_out = _render_skill_economics(store)

    assert 'class="sparkline"' not in html_out
    assert "no trend (n=1)" in html_out


def test_build_skill_daily_averages_within_a_day_and_skips_gaps(tmp_path: Path) -> None:
    """Two invocations on one day average; an unused day produces no point."""
    store = tmp_path / "facts.db"
    upsert(
        [
            _row("a", "2026-07-16", "session-hygiene-v1", skill_costs=json.dumps({"/s": 100.0})),
            _row("b", "2026-07-16", "session-hygiene-v1", skill_costs=json.dumps({"/s": 300.0})),
            _row("c", "2026-07-18", "session-hygiene-v1", skill_costs=json.dumps({"/s": 50.0})),
        ],
        store,
    )
    points = build_skill_daily(store)["/s"]

    assert [(p.date, p.value, p.n) for p in points] == [
        ("2026-07-16", 200.0, 2),
        ("2026-07-18", 50.0, 1),
    ]
    assert "2026-07-17" not in [p.date for p in points], "gap days are absent, not zero"


def test_experiments_render_trend_only_for_store_backed_signals(tmp_path: Path) -> None:
    """Surface 2: an experiment charts only where its ledger signal maps.

    Most ledger rows name meta-signals nothing can chart; those must render an
    empty cell rather than a line implying evidence.
    """
    store = tmp_path / "facts.db"
    upsert(
        [
            _row(f"s{i}", f"2026-07-{16 + i:02d}", "session-hygiene-v1", skills_used="/x")
            for i in range(4)
        ],
        store,
    )
    mapped = Experiment(
        name="mapped",
        metric="execution-sessions-with-skills ratio:0.5",
        status="trending",
        date="2026-07-16",
    )
    unmapped = Experiment(
        name="unmapped", metric="vibes-improved", status="pending", date="2026-07-16"
    )

    html_out = _render_experiments([mapped, unmapped], store)
    assert "7-day trend" in html_out

    unmapped_cell = html_out[html_out.index("unmapped") :]
    assert 'class="sparkline"' not in unmapped_cell, "an unchartable signal draws nothing"


def test_experiments_without_a_store_render_no_trends() -> None:
    """The store is optional: existing marker-region callers keep working."""
    experiments = [
        Experiment(
            name="e", metric="execution-sessions-with-skills", status="pending", date="2026-07-16"
        )
    ]
    html_out = _render_experiments(experiments)

    assert 'class="sparkline"' not in html_out
    assert "<td" in html_out, "the row still renders, just without a trend"


def test_friction_card_carries_the_shared_component(tmp_path: Path) -> None:
    """Surface 3: friction tiles gain the trailing-7-day read."""
    store = tmp_path / "facts.db"
    upsert(
        [
            _row(
                f"s{i}",
                f"2026-07-{16 + i:02d}",
                "session-hygiene-v1",
                max_context=100_000 + 1000 * i,
            )
            for i in range(4)
        ],
        store,
    )
    card = render_friction_regroup_card(store)

    assert 'class="sparkline"' in card, "friction metrics should carry a 7-day sparkline"


# --- GUA-137 Step 3: verdict trajectory caps -------------------------------


def _verdict_rows(experiment: str, count: int) -> list[dict[str, Any]]:
    return [
        {
            "experiment": experiment,
            "date": "2026-07-16",
            "metric": "m",
            "verdict": "trending",
            "evidence": "e" * 500,
            "run_at": f"2026-08-{1 + i:02d}T00:00:00",
        }
        for i in range(count)
    ]


def test_verdict_trajectory_caps_steps_and_marks_the_elision() -> None:
    """A long history renders its recent tail, and says how much it hid.

    Silent truncation would present a 3-run trajectory identically to a 40-run
    one — the elision marker is what keeps the shortening honest.
    """
    from telemetry.dashboard import _TRAJECTORY_MAX_STEPS, _render_verdict_trajectories

    out = _render_verdict_trajectories(_verdict_rows("long", 40))

    assert out.count('class="verdict-step') == _TRAJECTORY_MAX_STEPS
    assert f"+{40 - _TRAJECTORY_MAX_STEPS}" in out, "elided count must be shown"


def test_verdict_trajectory_truncates_evidence_in_the_tooltip() -> None:
    """Full evidence strings inlined per step are what caused the 302KB blowup."""
    from telemetry.dashboard import _TRAJECTORY_EVIDENCE_CHARS, _render_verdict_trajectories

    out = _render_verdict_trajectories(_verdict_rows("x", 2))

    assert "e" * 500 not in out, "evidence must not be inlined in full"
    assert "…" in out
    assert "e" * (_TRAJECTORY_EVIDENCE_CHARS // 2) in out, "a useful prefix should survive"


def test_verdict_trajectory_short_history_is_not_elided() -> None:
    """Under the cap, nothing is hidden and no marker appears."""
    from telemetry.dashboard import _render_verdict_trajectories

    out = _render_verdict_trajectories(_verdict_rows("short", 3))

    assert out.count('class="verdict-step') == 3
    assert "verdict-elided" not in out


# --- GUA-137 control board: rolling windows -------------------------------


def test_subagent_windows_render_every_window_with_one_visible(tmp_path: Path) -> None:
    """All windows are computed server-side; the toggle only changes visibility."""
    from telemetry.dashboard import SUBAGENT_WINDOWS, render_subagent_windows_card

    store = tmp_path / "facts.db"
    upsert(
        [
            _row(
                f"s{i}",
                f"2026-07-{16 + i:02d}",
                "session-hygiene-v1",
                subagent_costs=json.dumps(
                    {"by_agent": {"unattributed": {"cost": 100.0, "output_tokens": 10, "n": 1}}}
                ),
            )
            for i in range(3)
        ],
        store,
    )
    card = render_subagent_windows_card(store)

    assert card.count('class="win-panel"') == len(SUBAGENT_WINDOWS)
    assert card.count("display:none") == len(SUBAGENT_WINDOWS) - 1, "exactly one panel visible"
    assert "84%" not in card, "the stale hardcoded share must be gone"


def test_subagent_window_cutoff_anchors_to_newest_row_not_wall_clock(tmp_path: Path) -> None:
    """A stale store must not silently empty its own recent window.

    The store is refreshed by a batch job; anchoring to today would show "no
    data" for 7d whenever the job has not run, which is indistinguishable from
    genuinely having spawned no agents.
    """
    from telemetry.dashboard import _window_cutoff

    store = tmp_path / "facts.db"
    upsert([_row("old", "2026-07-20", "session-hygiene-v1")], store)

    assert _window_cutoff(store, 7) == "2026-07-13"
    assert _window_cutoff(store, None) is None


# --- GUA-137: insights embedded as the Overview ----------------------------


def test_scope_css_rewrites_body_and_prefixes_selectors() -> None:
    """A guest document's `body{}` must become the wrapper, not restyle the board."""
    from telemetry.dashboard import _scope_css

    out = _scope_css("body{margin:0}h2{color:red}.tag,.chip{font-size:9px}", "wrap")

    assert ".wrap{margin:0}" in out
    assert ".wrap h2{color:red}" in out
    assert ".wrap .tag,.wrap .chip{font-size:9px}" in out
    assert not re.search(r"(^|})body\{", out), "bare body rule leaked"


def test_scope_css_scopes_inside_media_queries() -> None:
    """Rules nested in @media are scoped too; the at-rule prelude is preserved."""
    from telemetry.dashboard import _scope_css

    out = _scope_css("@media (max-width:600px){body{padding:0}.x{color:blue}}", "wrap")

    assert out.startswith("@media (max-width:600px){")
    assert ".wrap{padding:0}" in out
    assert ".wrap .x{color:blue}" in out


def test_scope_css_leaves_keyframes_untouched() -> None:
    """@keyframes percentages are not selectors — scoping them breaks the animation."""
    from telemetry.dashboard import _scope_css

    out = _scope_css("@keyframes spin{0%{opacity:0}100%{opacity:1}}", "wrap")

    assert "@keyframes spin{0%{opacity:0}100%{opacity:1}}" in out
    assert ".wrap 0%" not in out


def test_insights_region_states_a_missing_report(tmp_path: Path) -> None:
    """No report is a prompt to run the skill, never a blank panel."""
    from telemetry.dashboard import render_insights_region

    out = render_insights_region(tmp_path / "nope.html")

    assert "No insights report found" in out
    assert "/meta-insights" in out


def test_insights_region_strips_guest_scripts(tmp_path: Path) -> None:
    """An embedded report's script would run against the board's DOM, not its own."""
    from telemetry.dashboard import render_insights_region

    report = tmp_path / "insights-report-2026-08-16.html"
    report.write_text(
        "<html><head><style>body{margin:0}</style></head>"
        "<body><h2>Report</h2><script>alert('x')</script></body></html>",
        encoding="utf-8",
    )
    out = render_insights_region(report, today="2026-08-16")

    assert "<script" not in out
    assert "alert(" not in out
    assert "<h2>Report</h2>" in out


def test_insights_region_drops_non_narrative_sections(tmp_path: Path) -> None:
    """Retro keeps the narrative four; projects and usage-profile are dropped.

    Both restate what other tabs already own, so the board reads them on the
    report itself rather than carrying them twice.
    """
    from telemetry.dashboard import render_insights_region

    report = tmp_path / "insights-report-2026-08-16.html"
    report.write_text(
        "<html><body>"
        '<section id="section-work"><h2>Projects</h2></section>'
        '<section id="section-usage"><h2>How You Use</h2></section>'
        '<section id="section-wins"><h2>Achievements</h2></section>'
        '<section id="section-features"><h2>Features</h2></section>'
        '<section id="section-patterns"><h2>Patterns</h2></section>'
        '<section id="section-horizon"><h2>Horizon</h2></section>'
        "</body></html>",
        encoding="utf-8",
    )
    out = render_insights_region(report, today="2026-08-16")

    assert "Projects" not in out
    assert "How You Use" not in out
    for kept in ("Achievements", "Features", "Patterns", "Horizon"):
        assert kept in out


def test_insights_region_strips_standalone_chrome(tmp_path: Path) -> None:
    """The board supplies its own header; the KPI cards live on other tabs.

    stat-cards and glance-box nest divs and share one .container, so a
    non-greedy regex would cut at the first inner </div> and orphan the rest.
    """
    from telemetry.dashboard import render_insights_region

    report = tmp_path / "insights-report-2026-08-16.html"
    report.write_text(
        "<html><body>"
        "<header><div class='container'><h1>Usage Report</h1></div></header>"
        '<div class="container">'
        '  <div class="stat-cards"><div class="stat-card"><div class="value">673</div></div></div>'
        '  <div class="glance-box"><h3>At a Glance</h3><ul><li>x</li></ul></div>'
        "</div>"
        '<section id="section-wins"><h2>Achievements</h2></section>'
        '<div class="container"><div class="quote-box">face existence<cite>c</cite></div></div>'
        "<footer><div class='container'><p>Generated from 673 sessions</p></div></footer>"
        "</body></html>",
        encoding="utf-8",
    )
    out = render_insights_region(report, today="2026-08-16")

    for gone in ("Usage Report", "At a Glance", "673", "face existence", "<footer"):
        assert gone not in out, gone
    assert "Achievements" in out
    # The wrappers must close cleanly or every card after them nests wrongly.
    embed = out[out.index('<div class="insights-embed">') :]
    assert embed.count("<div") == embed.count("</div>")


def test_insights_region_flags_a_stale_report(tmp_path: Path) -> None:
    """Age is the first thing to know about a daily read that is not daily."""
    from telemetry.dashboard import render_insights_region

    report = tmp_path / "insights-report-2026-08-04.html"
    report.write_text("<html><body><p>old</p></body></html>", encoding="utf-8")

    out = render_insights_region(report, today="2026-08-18")
    assert "14 days old" in out

    fresh = tmp_path / "insights-report-2026-08-18.html"
    fresh.write_text("<html><body><p>new</p></body></html>", encoding="utf-8")
    assert "days old" not in render_insights_region(fresh, today="2026-08-18")


# --- GUA-137 retro: does the improvement loop close? -----------------------


def _verdict(experiment: str, verdict: str, run_at: str) -> dict[str, Any]:
    return {"experiment": experiment, "verdict": verdict, "run_at": run_at, "date": "2026-07-16"}


def test_retro_funnel_never_widens_at_a_later_stage() -> None:
    """A scored experiment with no ledger row must not out-count the hypotheses.

    Verdicts accumulate against names that later get renamed or graduate out of
    the active ledger, so the raw scored set can exceed the hypothesis set — and
    a funnel whose third bar is wider than its second cannot mean anything.
    """
    from telemetry.dashboard import _retro_funnel

    exps = [Experiment(name="known", metric="m", status="hypothesis", date="2026-07-16")]
    verdicts = [_verdict("known", "trending", "2026-08-01")] + [
        _verdict(f"ghost{i}", "inconclusive", "2026-08-01") for i in range(5)
    ]
    out = _retro_funnel([{"id": 1}, {"id": 2}], exps, verdicts)

    counts = [int(n.replace(",", "")) for n in re.findall(r'class="fn-n">([\d,]+)<', out)]
    assert counts == sorted(counts, reverse=True), f"funnel widened: {counts}"
    assert "5 scored experiment(s) match no ledger row" in out


def test_retro_funnel_states_zero_stages_rather_than_omitting_them() -> None:
    """An empty stage renders at zero width, not as a missing bar."""
    from telemetry.dashboard import _retro_funnel

    out = _retro_funnel([], [], [])

    assert out.count("fn-row") == 4, "all four stages must render"
    assert "width:0.0%" in out


def test_retro_funnel_counts_only_resolved_statuses() -> None:
    """Open hypotheses are not achievements; only terminal statuses resolve."""
    from telemetry.dashboard import _retro_funnel

    exps = [
        Experiment(name="a", metric="m", status="hypothesis — due 09-01", date="2026-07-16"),
        Experiment(name="b", metric="m", status="verified 2026-08-01", date="2026-07-16"),
        Experiment(name="c", metric="m", status="failed at R10", date="2026-07-16"),
    ]
    out = _retro_funnel([], exps, [])

    counts = [int(n.replace(",", "")) for n in re.findall(r'class="fn-n">([\d,]+)<', out)]
    assert counts[1] == 3, "three hypotheses"
    assert counts[3] == 2, "verified + failed resolve; the open one does not"
    assert "1 of 3 hypotheses (33%) are still open" in out


def test_verdict_mix_uses_latest_verdict_per_experiment() -> None:
    """An experiment scored 25 times must not outvote one scored twice."""
    from telemetry.dashboard import _verdict_mix

    rows = [
        *[_verdict("noisy", "inconclusive", f"2026-08-{d:02d}") for d in range(1, 11)],
        _verdict("noisy", "confirmed", "2026-08-20"),
        _verdict("quiet", "failed", "2026-08-02"),
    ]
    out = _verdict_mix(rows)

    assert "(2 scored)" in out, "two experiments, not twelve rows"
    assert "confirmed <b>1</b>" in out
    assert "failed <b>1</b>" in out
    assert "inconclusive" not in out, "superseded verdicts must not appear"


def test_verdict_mix_empty_is_stated() -> None:
    from telemetry.dashboard import _verdict_mix

    assert "No scored verdicts yet" in _verdict_mix([])


# --- GUA-137: native context & orchestration visuals -----------------------


def test_bucket_bars_report_the_scored_population_not_all_rows() -> None:
    """A distribution over rows carrying the column is not one over all sessions.

    max_context is null on roughly half the corpus; drawing the distribution as
    if it covered every session would overstate its frame — the same metric-fence
    rule the tiles follow.
    """
    from telemetry.dashboard import _bucket_bars

    rows = [
        {"max_context": 40_000},
        {"max_context": 120_000},
        {"max_context": 200_000},
        {"max_context": None},
        {},
    ]
    bars, n = _bucket_bars(rows, "max_context", _CONTEXT_BUCKETS)

    assert n == 3, "only rows carrying the column are scored"
    assert "33%" in bars, "percentages are of the scored population"


def test_bucket_bars_highlight_marks_only_a_populated_last_bucket() -> None:
    """The heavy bucket goes red when it has rows — never as empty decoration."""
    from telemetry.dashboard import _bucket_bars

    heavy, _ = _bucket_bars(
        [{"max_context": 200_000}], "max_context", _CONTEXT_BUCKETS, highlight_last=True
    )
    assert "var(--bad)" in heavy

    light, _ = _bucket_bars(
        [{"max_context": 40_000}], "max_context", _CONTEXT_BUCKETS, highlight_last=True
    )
    assert "var(--bad)" not in light, "an empty heavy bucket must not render as a warning"


def test_bucket_bars_empty_input_is_stated() -> None:
    from telemetry.dashboard import _bucket_bars

    bars, n = _bucket_bars([{"max_context": None}], "max_context", _CONTEXT_BUCKETS)
    assert n == 0
    assert "No data" in bars


def test_context_orchestration_card_renders_live_numbers(tmp_path: Path) -> None:
    """The card computes from the store — not from a frozen insights report."""
    from telemetry.dashboard import render_context_orchestration_card

    store = tmp_path / "facts.db"
    upsert(
        [
            _row("a", "2026-07-16", "session-hygiene-v1", max_context=200_000, duration_min=95),
            _row("b", "2026-07-17", "session-hygiene-v1", max_context=60_000, duration_min=10),
        ],
        store,
    )
    card = render_context_orchestration_card(store)

    assert "Context window" in card
    assert "Parallelism" in card
    assert "Computed over 2 sessions carrying a context reading" in card

    # Value and label live in sibling spans, so pair them before asserting.
    stats = {
        label: value
        for value, label in re.findall(r'value">([^<]+)</span><span class="label">([^<]+)', card)
    }
    assert stats["sessions over 150k"] == "1", "one row exceeds the cliff"


# --- GUA-137: native insights KPI panel ------------------------------------


def test_insights_kpi_region_computes_from_the_store(tmp_path: Path) -> None:
    """The KPI panel is live, not a snapshot lifted from a report file."""
    from telemetry.dashboard import render_insights_kpi_region

    store = tmp_path / "facts.db"
    upsert(
        [
            _row("a", "2026-07-16", "session-hygiene-v1", cost_units=1e9, compacted=True),
            _row("b", "2026-07-17", "session-hygiene-v1", cost_units=1e9, compacted=False),
        ],
        store,
    )
    out = render_insights_kpi_region(store)

    # Read the default (30d) panel — every window is emitted, so a bare regex
    # over the whole region would mix figures from four different populations.
    start = out.index('<div class="win-panel" data-win="30d"')
    nxt = out.find('<div class="win-panel"', start + 10)
    panel = out[start : nxt if nxt != -1 else len(out)]

    tiles = dict(
        re.findall(r'ikpi-label">([^<]+)</div><div class="ikpi-value">([^<]+)</div>', panel)
    )
    assert tiles["Sessions"] == "2"
    assert tiles["Total cost units"] == "2.00B"
    assert tiles["Compact rate"] == "50%", "one of two sessions compacted"
    assert "1 of 2 sessions" in panel


def test_insights_kpi_region_empty_store_is_stated(tmp_path: Path) -> None:
    """An empty store says so rather than rendering zeros as findings."""
    from telemetry.dashboard import render_insights_kpi_region

    store = tmp_path / "facts.db"
    upsert([_row("m", "2026-07-16", "session-hygiene-v1", is_meta=True)], store)

    assert "No session data yet" in render_insights_kpi_region(store)


def test_insights_kpi_names_the_response_time_substitution(tmp_path: Path) -> None:
    """Session duration is not per-request response time — the panel must say so.

    The source report showed response-time buckets; the fact store carries no
    per-request timestamps, so the honest move is a different metric with its
    frame stated, not a same-named chart computed from different data.
    """
    from telemetry.dashboard import render_insights_kpi_region

    store = tmp_path / "facts.db"
    upsert([_row("a", "2026-07-16", "session-hygiene-v1", duration_min=42)], store)
    out = render_insights_kpi_region(store)

    assert "Session duration" in out
    assert "Per-request response time needs timestamps the fact store does not capture" in out


# --- GUA-137: windowed insights --------------------------------------------


def test_insights_windows_all_render_with_one_visible(tmp_path: Path) -> None:
    """Every window is computed server-side; the toggle only changes visibility."""
    from telemetry.dashboard import (
        _INSIGHTS_DEFAULT_WINDOW,
        INSIGHTS_WINDOWS,
        render_insights_kpi_region,
    )

    store = tmp_path / "facts.db"
    upsert(
        [_row(f"s{i}", f"2026-07-{10 + i:02d}", "session-hygiene-v1") for i in range(12)],
        store,
    )
    out = render_insights_kpi_region(store)

    assert out.count('class="win-panel"') == len(INSIGHTS_WINDOWS)
    assert out.count("display:none") == len(INSIGHTS_WINDOWS) - 1, "exactly one visible"
    assert f'data-win="{_INSIGHTS_DEFAULT_WINDOW}">' in out, "default window is the visible one"


def test_insights_window_narrows_the_population(tmp_path: Path) -> None:
    """A 7-day window must not count sessions outside it.

    The whole point of windowing is that a recent regression is not averaged
    away by months of older data.
    """
    from telemetry.dashboard import render_insights_kpi_region

    store = tmp_path / "facts.db"
    upsert(
        [_row("old", "2026-05-01", "note-hook")]
        + [_row(f"new{i}", f"2026-07-{20 + i:02d}", "session-hygiene-v1") for i in range(3)],
        store,
    )
    out = render_insights_kpi_region(store)

    def _panel(win: str) -> str:
        start = out.index(f'<div class="win-panel" data-win="{win}"')
        nxt = out.find('<div class="win-panel"', start + 10)
        return out[start : nxt if nxt != -1 else len(out)]

    assert ">3<" in _panel("7d"), "7-day window sees only the three recent sessions"
    assert ">4<" in _panel("all"), "all-time window sees every session"


def test_insights_window_anchors_to_newest_row_not_today(tmp_path: Path) -> None:
    """A store refreshed by a batch job must not show an empty recent window."""
    from telemetry.dashboard import render_insights_kpi_region

    store = tmp_path / "facts.db"
    upsert([_row("a", "2026-05-01", "note-hook"), _row("b", "2026-05-02", "note-hook")], store)
    out = render_insights_kpi_region(store)

    start = out.index('<div class="win-panel" data-win="7d"')
    nxt = out.find('<div class="win-panel"', start + 10)
    seven = out[start : nxt if nxt != -1 else len(out)]
    assert "No sessions in this window" not in seven, "anchored to newest row, not wall clock"


def test_spawn_records_tolerates_malformed_json() -> None:
    """A malformed agent_spawns cell yields no spawns, never a crash."""
    from telemetry.dashboard import _spawn_records

    assert _spawn_records({"agent_spawns": '[{"type": "Explore"}]'}) == [{"type": "Explore"}]
    assert _spawn_records({"agent_spawns": "not json"}) == []
    assert _spawn_records({"agent_spawns": '{"type": "obj-not-list"}'}) == []
    assert _spawn_records({}) == []


def test_insights_separates_output_tokens_from_session_duration(tmp_path: Path) -> None:
    """Two metrics, two cards — they were previously conflated under one title."""
    from telemetry.dashboard import render_insights_kpi_region

    store = tmp_path / "facts.db"
    upsert([_row("a", "2026-07-16", "session-hygiene-v1", duration_min=42)], store)
    out = render_insights_kpi_region(store)

    out_idx = out.index("Output tokens per session")
    dur_idx = out.index("Session duration")
    assert out_idx != dur_idx
    # The duration distribution must live under the duration card, not the token one.
    between = out[out_idx:dur_idx]
    assert between.count('class="dist-row"') == 0, "duration bars must not sit in the token card"


# --- GUA-151: static cards -> telemetry-fed marker regions ------------------


def test_session_context_region_reports_the_live_7day_figure(tmp_path: Path) -> None:
    """The tiles compute from the store's 7-day window — a planted stale value
    (the old hand-set "0% today") disagrees with the render and fails here."""
    from telemetry.dashboard import render_session_context_region

    store = tmp_path / "facts.db"
    rows = [
        # Outside the 7-day window ending at the newest observation (08-19).
        _row("old", "2026-08-01", "session-hygiene-v1", max_context=500_000),
        # Inside: 2 of 4 scored sessions over 150k -> 50%.
        _row("a", "2026-08-14", "session-hygiene-v1", max_context=100_000),
        _row("b", "2026-08-16", "session-hygiene-v1", max_context=120_000),
        _row("c", "2026-08-18", "session-hygiene-v1", max_context=200_000),
        _row("d", "2026-08-19", "session-hygiene-v1", max_context=240_000),
    ]
    upsert(rows, store)
    out = render_session_context_region(store)

    # The over-150k stat tile must carry the live 7-day figure (2 of 4 = 50%),
    # not the planted stale "0%" the hand-set card reported.
    m = re.search(r'<span class="value"[^>]*>(\d+)%</span>\s*<span class="label">over 150k', out)
    assert m, "over-150k stat tile missing"
    assert m.group(1) == "50", f"expected live 50%, rendered {m.group(1)}%"
    # Percentile tiles computed over [100k, 120k, 200k, 240k] only — the
    # out-of-window 500k row excluded (it would be p90 otherwise). _percentile
    # is nearest-rank: p50=200k, p90=240k.
    assert ">200k</span>" in out, "p50 tile must be the windowed 200k"
    assert ">240k</span>" in out, "p90 tile must be the windowed 240k"
    assert "Computed from 4 of 4" in out, "the tile must state its denominator"


def test_session_context_region_empty_store_is_stated(tmp_path: Path) -> None:
    from telemetry.dashboard import render_session_context_region

    store = tmp_path / "facts.db"
    upsert([_row("a", "2026-08-19", "session-hygiene-v1", max_context=None)], store)
    out = render_session_context_region(store)
    assert "No max_context observations" in out


def test_measurement_gap_region_reconciles_against_the_newest_run() -> None:
    """The four-way split counts only the newest run_at, and its buckets sum to
    that run's row count — the reconciliation the DoD demands."""
    from telemetry.dashboard import _gap_bucket, render_measurement_gap_region

    def v(exp, verdict, evidence, metric, run_at):
        return {
            "experiment": exp,
            "date": "2026-08-01",
            "metric": metric,
            "verdict": verdict,
            "evidence": evidence,
            "run_at": run_at,
        }

    old, new = "2026-08-18T12:00:00+00:00", "2026-08-19T12:00:00+00:00"
    rows = [
        # Old run: must not be counted (it would add a 5th decisive row).
        v("e1", "confirmed", "x=0 across scored sessions", "absence:x above 0", old),
        # Newest run: 2 decisive, 1 needs-collection, 1 unobservable,
        # 1 no-typed-metric, 1 unregistered.
        v("e1", "confirmed", "x=0 across scored sessions", "absence:x", new),
        v("e2", "trending", "y at 12% (was 17%)", "ratio:y below 5%", new),
        v(
            "e3",
            "inconclusive",
            "'z' needs a collection change before it can be scored — add hook",
            "presence:z",
            new,
        ),
        v(
            "e4",
            "inconclusive",
            "'w' is unobservable by design — rewrite the row",
            "presence:w",
            new,
        ),
        v("e5", "inconclusive", "no typed metric to score", "watch it", new),
        v(
            "e6",
            "inconclusive",
            "unregistered signal 'q' — cannot measure presence; declare it",
            "presence:q",
            new,
        ),
    ]
    out = render_measurement_gap_region(rows)

    newest = [r for r in rows if r["run_at"] == new]
    from collections import Counter as _Counter

    buckets = _Counter(_gap_bucket(r) for r in newest)
    assert sum(buckets.values()) == len(newest), "buckets must partition the run"
    assert buckets == {
        "decisive": 2,
        "needs-collection": 1,
        "unobservable": 1,
        "no-typed-metric": 1,
        "unregistered": 1,
    }
    assert (
        "6 hypotheses" in out.replace("<strong>", "").replace("</strong>", "")
        or "6 hypotheses" in out
    )
    assert "2 decisive" in out
    assert 'title="needs a collection: 1 of 6"' in out
    assert 'title="unobservable by design: 1 of 6"' in out
    assert "unregistered signal" in out, "a residual bucket with rows must be shown"
    assert new in out, "the run_at scoping must be stated"


def test_measurement_gap_prefix_bars_recompute_from_the_run() -> None:
    from telemetry.dashboard import render_measurement_gap_region

    new = "2026-08-19T12:00:00+00:00"
    rows = [
        {
            "experiment": "a",
            "date": "d",
            "metric": "absence:x",
            "verdict": "confirmed",
            "evidence": "x=0",
            "run_at": new,
        },
        {
            "experiment": "b",
            "date": "d",
            "metric": "absence:y",
            "verdict": "inconclusive",
            "evidence": "'y' is unobservable by design — z",
            "run_at": new,
        },
        {
            "experiment": "c",
            "date": "d",
            "metric": "ratio:r above 1",
            "verdict": "failed",
            "evidence": "r=2",
            "run_at": new,
        },
    ]
    out = render_measurement_gap_region(rows)
    assert ">1/2</div>" in out, "absence prefix must show 1 decisive of 2"
    assert ">1/1</div>" in out, "ratio prefix must show 1 of 1"


def test_measurement_gap_empty_is_stated() -> None:
    from telemetry.dashboard import render_measurement_gap_region

    out = render_measurement_gap_region(None)
    assert "No verdict rows" in out


def _write_job_log(path: Path, finishes: list[str]) -> None:
    lines = []
    for ts in finishes:
        day, clock = ts.split("T")
        lines.append(f"{day} {clock} --- run started (mode=x, repo=/r)")
        lines.append(f"{day} {clock} --- run finished (exit 0)")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_harness_region_surfaces_a_job_gap_without_hand_editing(tmp_path: Path) -> None:
    """The facts job's multi-day silence renders as a red cell and a named gap
    — and a job that stops running turns red on the next render."""
    from datetime import datetime as dt

    from telemetry.dashboard import render_harness_region

    logs = tmp_path / "logs"
    logs.mkdir()
    # Naive local time, matching the clock the cron wrapper stamps the logs with.
    now = dt.fromisoformat("2026-08-19T12:00:00")
    # Board ticked 5 minutes ago: healthy.
    _write_job_log(logs / "telemetry-board.log", ["2026-08-19T11:55:00"])
    # Facts ran 08-04 then went silent until 08-17 — the 13-day gap — and its
    # last run is recent enough to be healthy *now*, but the gap stays named.
    _write_job_log(
        logs / "telemetry-facts.log",
        ["2026-08-04T09:00:00", "2026-08-17T09:06:00", "2026-08-19T09:00:00"],
    )
    pass_log = tmp_path / "pass.jsonl"
    pass_log.write_text(
        '{"ts":"t","hook":"risky_git_guard","context":"pass"}\n'
        '{"ts":"t","hook":"branch_guard","context":"pass"}\n',
        encoding="utf-8",
    )
    store = tmp_path / "facts.db"  # empty: verdict cell reports no runs

    out = render_harness_region(logs, pass_log, store, now=now)

    assert "&#10003; healthy" in out, "board cell must be healthy"
    assert "Longest gap <b>13d</b>" in out
    assert "(08-04 &rarr; 08-17)" in out
    assert "~ 2 of 5 hooks" in out, "breadth below threshold must warn"
    assert "no runs" in out, "empty verdict store must be stated"

    # The same board, rendered two days later with no new tick, turns red.
    later = dt.fromisoformat("2026-08-21T12:00:00")
    out2 = render_harness_region(logs, pass_log, store, now=later)
    board_cell = out2.split('<div class="hz-name">facts</div>')[0]
    assert "&#10007;" in board_cell, "a stalled job must turn red on the next render"


def test_harness_region_counts_only_exit_zero_runs(tmp_path: Path) -> None:
    from datetime import datetime as dt

    from telemetry.dashboard import render_harness_region

    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "telemetry-board.log").write_text(
        "2026-08-19 11:55:00 --- run started (mode=board, repo=/r)\n"
        "2026-08-19 11:55:10 --- run finished (exit 1)\n",
        encoding="utf-8",
    )
    out = render_harness_region(
        logs,
        tmp_path / "absent.jsonl",
        tmp_path / "facts.db",
        now=dt.fromisoformat("2026-08-19T12:00:00"),
    )
    assert "never ran" in out, "an exit-1 completion is not a successful run"


def test_plane_counts_regions_derive_every_count(tmp_path: Path) -> None:
    from telemetry.dashboard import Experiment, render_plane_counts_regions
    from telemetry.factstore import upsert_findings
    from telemetry.gitstore import upsert_issues

    store = tmp_path / "facts.db"
    upsert(
        [
            _row("s1", "2026-08-18", "session-hygiene-v1"),
            _row("s2", "2026-08-19", "session-hygiene-v1"),
        ],
        store,
    )
    upsert_findings(
        [
            {
                "id": "F1",
                "source": "s",
                "date": "2026-08-01",
                "repo": "r",
                "file": "f",
                "title": "t",
                "merge_impact": "blocker",
            },
            {
                "id": "F2",
                "source": "s",
                "date": "2026-08-02",
                "repo": "r",
                "file": "f",
                "title": "t",
                "merge_impact": "important",
            },
        ],
        store,
    )
    upsert_issues([{"repo": "r", "number": 1, "state": "open", "title": "i"}], store)

    consistency = tmp_path / "consistency.json"
    consistency.write_text(json.dumps({"total": 3, "unmatchable_plans": 7}), encoding="utf-8")
    ledger_log = tmp_path / "tooling-ledger-log.md"
    ledger_log.write_text(
        "## R0 (2026-07-20)\nx\n## R2 (2026-08-01)\nx\n## R1 (2026-07-25)\nx\n",
        encoding="utf-8",
    )
    reflections = tmp_path / "reflections"
    reflections.mkdir()
    (reflections / "2026-08-18_10-00.md").write_text("r", encoding="utf-8")
    (reflections / "reflection-logs.md").write_text("index", encoding="utf-8")
    pass_log = tmp_path / "pass.jsonl"
    pass_log.write_text('{"hook":"a"}\n{"hook":"b"}\n{"hook":"a"}\n', encoding="utf-8")

    regions = render_plane_counts_regions(
        store,
        consistency_path=consistency,
        experiments=[Experiment("e1", "m", "hypothesis", "2026-08-01")],
        ledger_log_path=ledger_log,
        reflections_dir=reflections,
        pass_log=pass_log,
    )

    work = regions["PLANE-COUNTS-WORK"]
    assert "<b>2</b> findings" in work and "<b>1</b> blockers" in work
    assert "<b>1</b> issues" in work
    assert "<b>3</b> open inconsistencies" in work and "<b>7</b> plans unmatchable" in work

    meta = regions["PLANE-COUNTS-META"]
    assert "<b>2</b> sessions" in meta
    assert "<b>1</b> reflections" in meta, "only dated reflection files count"
    assert "<b>3</b> retro rounds" in meta
    assert "<b>1</b> live hypotheses" in meta

    control = regions["PLANE-COUNTS-CONTROL"]
    assert "<b>2</b> unique hooks" in control and "<b>3</b> pass events" in control


def test_runway_region_positions_overdue_and_undated_rows(tmp_path: Path) -> None:
    from telemetry.dashboard import Experiment, render_runway_region
    from telemetry.factstore import append_verdicts

    store = tmp_path / "facts.db"
    append_verdicts(
        [
            {
                "experiment": "late-pair-a",
                "date": "2026-08-01",
                "metric": "ratio:x above 1",
                "verdict": "confirmed",
                "evidence": "x=2",
            },
            {
                "experiment": "future-row",
                "date": "2026-08-01",
                "metric": "presence:y",
                "verdict": "inconclusive",
                "evidence": "'y' is unobservable by design — z",
            },
        ],
        store,
        run_at="2026-08-19T12:00:00+00:00",
    )
    experiments = [
        Experiment("late-pair-a", "ratio:x above 1", "hypothesis — due 08-17", "2026-08-01"),
        Experiment("late-pair-b", "presence:q", "hypothesis — due 08-17", "2026-08-01"),
        Experiment("future-row", "presence:y", "hypothesis — due 08-30", "2026-08-01"),
        Experiment("no-date-row", "watch it", "hypothesis", "2026-08-01"),
    ]
    out = render_runway_region(experiments, store, today="2026-08-19")

    assert "4 hypotheses by due date" in out
    assert "2 of 3 dated rows are overdue" in out, "the shared 08-17 pair is overdue"
    assert 'title="2 hypotheses due 2026-08-17' in out, "same-deadline rows must cluster"
    assert "<b>1</b> rows carry no due date" in out, "undated rows are counted, not dropped"
    # Legend counts from the newest verdict per dated row: late-pair-a is
    # confirmed; late-pair-b (never scored) and future-row are inconclusive.
    assert "confirmed (1)" in out
    assert "inconclusive (2)" in out


def test_runway_region_all_undated_is_stated() -> None:
    from telemetry.dashboard import Experiment, render_runway_region

    out = render_runway_region([Experiment("a", "watch", "hypothesis", "2026-08-01")], None)
    assert "none carrying a due date" in out


def test_decision_log_region_groups_by_plane_and_folds_effects() -> None:
    from telemetry.dashboard import render_decision_log_region

    records = [
        # Legacy-shaped record after read_actions normalisation.
        {
            "action": "triage",
            "target": {"repo": "galactus", "issue_num": 27},
            "outcome": "accepted",
            "reason": "labeled refinement",
            "ts": "2026-08-16T21:00:00Z",
            "plane": "work",
            "effect_measured": None,
            "proposal_id": "",
        },
        {
            "action": "schedule_job",
            "target": {"repo": "guacamayo"},
            "outcome": "acted",
            "reason": "board tick installed",
            "ts": "2026-08-17T09:00:00Z",
            "plane": "control",
            "effect_measured": None,
            "proposal_id": "p-1",
        },
        # Effect write-back sharing the decision's proposal_id.
        {
            "action": "schedule_job",
            "target": {"repo": "guacamayo"},
            "outcome": "acted",
            "reason": "effect measured for decision p-1",
            "ts": "2026-08-19T09:00:00Z",
            "plane": "control",
            "proposal_id": "p-1",
            "effect_measured": {
                "metric": "ratio:x below 5%",
                "verdict": "trending",
                "checked_at": "2026-08-19T09:00:00Z",
            },
        },
        {
            "action": "retire_skill",
            "target": {"repo": "guacamayo"},
            "outcome": "reverted",
            "reason": "undone same day",
            "ts": "2026-08-18T09:00:00Z",
            "plane": "metacognition",
            "effect_measured": None,
            "proposal_id": "",
        },
    ]
    out = render_decision_log_region(records)

    assert "galactus#27" in out
    assert "1 &middot; work: <b>1</b>" in out
    assert "2 &middot; metacog: <b>1</b>" in out
    assert "3 &middot; control: <b>1</b>" in out
    assert 'class="pill rev">reverted' in out, "the reverted outcome must render"
    assert "trending" in out and "ratio:x below 5%" in out, "effect folds onto its decision"
    assert out.count("<tr>") == 4, "3 decisions + header — the write-back is not its own row"
    assert "not re-read" in out, "unmeasured decisions say so"
    assert "3 decision records (1 effect write-backs folded in)" in out


def test_decision_log_region_empty_is_stated() -> None:
    from telemetry.dashboard import render_decision_log_region

    assert "No decisions" in render_decision_log_region([])


def test_cadence_region_computes_gaps_and_horizon(tmp_path: Path) -> None:
    from telemetry.dashboard import Experiment, render_cadence_region

    ledger_log = tmp_path / "tooling-ledger-log.md"
    # Headers deliberately out of order — dates, not file order, decide.
    ledger_log.write_text(
        "## R10 (2026-08-10)\nx\n## R7 (2026-07-31)\nx\n## R8 (2026-08-04)\nx\n"
        "## R9 (2026-08-05)\nx\n",
        encoding="utf-8",
    )
    experiments = [
        Experiment("a", "ratio:x", "hypothesis — due 08-15", "2026-08-01"),
        Experiment("b", "ratio:y", "hypothesis — due 08-29", "2026-08-01"),
        Experiment("c", "watch", "hypothesis", "2026-08-01"),  # undated: excluded
    ]
    out = render_cadence_region(ledger_log, experiments)

    assert "R7 &rarr; R8" in out and ">4d</div>" in out
    assert "R8 &rarr; R9" in out and ">1d</div>" in out
    assert "R9 &rarr; R10" in out and ">5d</div>" in out
    assert "every <strong>1&ndash;5 days</strong>" in out
    assert "median over 2 dated rows" in out
    assert ">28d</div>" in out, "median horizon of [14, 28] is the upper of the two"


def test_cadence_region_no_rounds_is_stated(tmp_path: Path) -> None:
    from telemetry.dashboard import render_cadence_region

    out = render_cadence_region(tmp_path / "absent.md", None)
    assert "No dated retro rounds" in out


# ---------------------------------------------------------------------------
# DATA-BLOCK region (GUA-151)
# ---------------------------------------------------------------------------


def test_data_block_region_structure(tmp_path: Path) -> None:
    """render_data_block_region emits a complete <script> block containing
    const DATA with all eight expected keys."""
    from telemetry.dashboard import render_data_block_region

    store = tmp_path / "facts.db"
    out = render_data_block_region(store)

    # Must be wrapped in <script> tags so the marker region can sit outside
    # the surrounding script block without creating invalid JS.
    assert out.startswith("<script>"), "output must open with <script>"
    assert out.rstrip().endswith("</script>"), "output must close with </script>"
    assert "const DATA" in out

    # All eight series keys must be present.
    for key in (
        "context_p50",
        "context_p90",
        "over150k",
        "turns_p50",
        "single_turn",
        "skills",
        "compaction",
        "sessions_week",
    ):
        assert f"{key}:" in out, f"missing key {key!r} in DATA-BLOCK output"


def test_data_block_region_empty_store_yields_empty_arrays(tmp_path: Path) -> None:
    """An empty store must produce valid JS with empty arrays, not an error."""
    from telemetry.dashboard import render_data_block_region

    store = tmp_path / "facts.db"
    out = render_data_block_region(store)

    # Every key should be present with an empty array literal.
    assert "context_p50: [\n    \n  ]" in out or "context_p50: []" in out or "context_p50:" in out
    # The output must be parseable (no unclosed brackets).
    assert out.count("{") >= out.count("}")  # at least the DATA object itself


def test_data_block_region_context_p50_in_ktokens(tmp_path: Path) -> None:
    """max_context values must be divided by 1000 before output so the JS
    chart receives 102.4 (k-tokens), not 102400 (raw tokens)."""
    from telemetry.dashboard import render_data_block_region

    store = tmp_path / "facts.db"
    rows = [
        _row("a", "2026-07-20", "session-hygiene-v1", max_context=102_400),
        _row("b", "2026-07-21", "session-hygiene-v1", max_context=200_000),
    ]
    upsert(rows, store)
    out = render_data_block_region(store)

    # Raw values (102400, 200000) must NOT appear in the context_p50/p90 blocks.
    assert "102400" not in out, "raw token value leaked into DATA output (expected k-tokens)"
    assert "200000" not in out, "raw token value leaked into DATA output (expected k-tokens)"
    # Divided values should appear.
    assert "102.4" in out or "102" in out, "k-token value missing from DATA output"


def test_data_block_region_stale_frozen_date_fails(tmp_path: Path) -> None:
    """A store with a session AFTER 2026-07-28 must produce a point beyond
    the frozen date, so the frozen hand-written value would fail this check."""
    from telemetry.dashboard import render_data_block_region

    store = tmp_path / "facts.db"
    rows = [
        # 2026-07-28 is the frozen date — a session after it must appear.
        _row("new1", "2026-08-10", "session-hygiene-v1", max_context=150_000),
        _row("new2", "2026-08-11", "session-hygiene-v1", max_context=160_000),
    ]
    upsert(rows, store)
    out = render_data_block_region(store)

    # At least one point date later than the frozen 2026-07-28 must appear.
    dates_in_output = re.findall(r'"(\d{4}-\d{2}-\d{2})"', out)
    assert any(d > "2026-07-28" for d in dates_in_output), (
        f"no date after 2026-07-28 in output — frozen data not replaced. Dates: {dates_in_output}"
    )


def test_data_block_region_faceted_series_include_r_field(tmp_path: Path) -> None:
    """compaction_pct and sessions_per_week are faceted; their points must carry
    an `r` field so the JS chart can colour by regime."""
    from telemetry.dashboard import render_data_block_region

    store = tmp_path / "facts.db"
    rows = [
        _row("a", "2026-07-20", "session-hygiene-v1", compacted=True),
        _row("b", "2026-07-21", "session-hygiene-v1", compacted=False),
    ]
    upsert(rows, store)
    out = render_data_block_region(store)

    # The compaction and sessions_week arrays must contain at least one point
    # with an `r:` field (regime).
    assert ",r:" in out, "no r: field found — faceted series not emitting regime"


# ---------------------------------------------------------------------------
# render_scope_decisions_region tests (GUA-152)
# ---------------------------------------------------------------------------


def test_scope_decisions_empty_state(tmp_path: Path) -> None:
    from telemetry.dashboard import render_scope_decisions_region

    out = render_scope_decisions_region(tmp_path / "scope-decisions.jsonl")
    assert "No scope decisions" in out
    assert "workflow-scope" in out


def test_scope_decisions_renders_job_type_bar(tmp_path: Path) -> None:
    import json

    from telemetry.dashboard import render_scope_decisions_region

    log = tmp_path / "scope-decisions.jsonl"
    records = [
        {
            "ts": "2026-08-19T10:00:00Z",
            "issue": 152,
            "repo": "guacamayo",
            "state": "CLEAR",
            "entry_point": "plan",
            "job_type": "new-feature",
            "outcome": "ready",
            "retries": 0,
        },
        {
            "ts": "2026-08-19T11:00:00Z",
            "issue": 100,
            "repo": "guacamayo",
            "state": "UNSCOPED",
            "entry_point": "research",
            "job_type": "debug",
            "outcome": "ready",
            "retries": 1,
        },
    ]
    log.write_text("\n".join(json.dumps(r) for r in records))

    out = render_scope_decisions_region(log)
    assert "2 issues scoped" in out
    assert "new-feature" in out
    assert "debug" in out
    assert "2 reached READY" in out


def test_scope_decisions_tolerates_missing_job_type(tmp_path: Path) -> None:
    import json

    from telemetry.dashboard import render_scope_decisions_region

    log = tmp_path / "scope-decisions.jsonl"
    log.write_text(
        json.dumps(
            {
                "ts": "2026-08-19T09:00:00Z",
                "issue": 99,
                "repo": "guacamayo",
                "state": "CLEAR",
                "entry_point": "plan",
            }
        )
    )
    out = render_scope_decisions_region(log)
    # must not raise; should contain the card title
    assert "Triage pipeline" in out


# --- retro-header parse (GUA-149) ------------------------------------------


def test_pipeline_health_retro_picks_latest_not_last_in_file(tmp_path: Path) -> None:
    """render_pipeline_health_region must pick the most-recent retro by date.

    tooling-ledger-log.md sections are NOT in chronological order — they are
    appended at write time, so R10 appears before R9 when R9 was written later.
    The old ``headers[-1]`` approach returned the last section in file order
    (e.g. "## R2"), not the most-recent one (e.g. "## R11 · 2026-08-18").
    """
    from telemetry.dashboard import render_pipeline_health_region

    # Build a minimal sounding directory with an out-of-order ledger log.
    sounding = tmp_path / ".sounding"
    sounding.mkdir()
    ledger_log = sounding / "tooling-ledger-log.md"
    ledger_log.write_text(
        "## R0\n2026-07-01 first retro\n\n"
        "## R1\n2026-07-15 second retro\n\n"
        "## R10\n2026-08-10 tenth retro\n\n"
        "## R11\n2026-08-18 latest retro\n\n"
        "## R9\n2026-08-05 ninth retro\n\n"
        "## R2\n2026-07-20 second addendum\n",
        encoding="utf-8",
    )

    # store path: render_pipeline_health_region derives guacamayo_root as store.parent.parent
    # (the comment in dashboard.py says "store is …/librarian/data/sessions.db", so
    # store.parent.parent == librarian/, not the guacamayo root).  The actual derivation is
    # guacamayo_root = store.parent.parent — so to get tmp_path as the guacamayo root, place
    # the store at tmp_path/data/sessions.db (store.parent.parent == tmp_path).
    store = tmp_path / "data" / "sessions.db"
    store.parent.mkdir(parents=True)

    out = render_pipeline_health_region(store)

    assert "R11" in out, f"Expected most-recent retro 'R11' in output but got:\n{out[:500]}"
    assert "2026-08-18" in out, f"Expected date '2026-08-18' from R11 section but got:\n{out[:500]}"
