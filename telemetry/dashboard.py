"""Render the context-engineering dashboard from the fact table.

Reads `factstore` rows only — never rescans the corpus, so charts are recomputed
from stored history rather than an ever-shrinking JSONL window (local retention
is ~5 days).

Two metric classes render differently, and the distinction is load-bearing (Q0):

  * **Per-session properties** (cost, cache hit-rate, tokens) are comparable
    across instrumentation regimes -> one continuous trend line, regime bands
    shaded behind it.
  * **Population rates** (compaction %, sessions/week) are NOT comparable. In the
    Apr-Jun regime a session produced a note *only because it compacted*, so a
    rate line crossing that boundary plots the note-writing hook's behaviour, not
    Ramsey's. These render as separate per-regime panels, each labelled with its
    sampling frame.
"""

from __future__ import annotations

import html
import json
import re
import sqlite3
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, timedelta
from datetime import date as _date
from datetime import datetime as _datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

import structlog

from telemetry.factstore import (
    ERROR_CATEGORY_CODE,
    ERROR_CATEGORY_ENV,
    ERROR_CATEGORY_TOOL,
    ERROR_CATEGORY_UNKNOWN,
    SUBAGENT_ATTRIBUTION_CLI,
    SUBAGENT_ATTRIBUTION_SINCE,
    UNATTRIBUTED_AGENT,
    classify_error_kind,
    read_all,
    read_verdicts,
)
from telemetry.gitstore import read_git_activity, read_issues, read_prs
from telemetry.loop import (
    PlanDoc,
    detect_drift,
    label_counts,
    non_conforming,
    status_counts,
)
from telemetry.periods import DEFAULT_PERIOD, PERIODS, iso_week, period_key
from telemetry.recurrence import (
    DIRECTION_FALLING,
    DIRECTION_FLAT,
    DIRECTION_RISING,
    compute_recurrence,
)
from telemetry.verdicts import parse_metric

log = structlog.get_logger(__name__)

# Telemetry (per-request usage, max_context) begins with the JSONL era. Metrics
# derived from it must not render a single point before this date.
JULY_BOUNDARY = "2026-07-15"

# Date the friction columns entered the factstore. Data before this is backfilled
# from retained transcripts, not collected prospectively -- stated on the panel so
# the distinction stays visible.
FRICTION_STORED = "2026-07-20"

# Population-rate metrics: the sampling frame differs per regime, so these are
# faceted and never drawn as a continuous series.
RATE_METRICS = {"compaction_pct", "sessions_per_week"}

# July-forward only: the underlying columns are null in the note era.
JULY_ONLY_METRICS = {
    "max_context_p50",
    "max_context_p90",
    "pct_over_150k",
    "tool_error_rate",
    "interruptions_p50",
    "turns_per_session_p50",
    "single_turn_pct",
    "execution_skill_compliance_pct",
    "friction_labels_total",
    # Step 4: input tokens — telemetry era only (no pre-July per-request data)
    "input_tokens_p50",
    "input_tokens_sum",
    # Step 6: cost-by-context-bucket — needs max_context per session (July+)
    "cost_bucket_pct_over150k",
    # LIB-57: failure attribution + bash antipatterns — parsed since the JSONL
    # era only, same as tool_error_rate.
    "errors_code_total",
    "errors_env_total",
    "errors_tool_total",
    "errors_unknown_total",
    "bash_antipatterns_p50",
    # GUA-120: context pressure, cost-per-tool, mutation ratio — all read
    # max_context / tool_counts, which are null in the note era.
    "context_pressure_ratio",
    "cost_per_tool",
    "mutation_ratio",
}

# GUA-120: a fence narrower than JULY_ONLY_METRICS. `turns_since_last_compact`
# is non-null only where `compacted=1`, and only in the July era -- 182 of 939
# rows as of 2026-08-15, which is exactly the July+ compacted population, not a
# sample of it. Computing over "the rows that happen to have the column" would
# describe 44% of compaction events and render identically to one that described
# all of them. These metrics are therefore restricted to July+ compacted
# sessions and must render that sub-population, not the whole corpus, as their n.
COMPACT_METRICS = {"compaction_yield"}

# Tool names counted as mutations vs reads for `mutation_ratio`. Bash is
# deliberately absent from both: it is read-or-write depending on the command
# string, which `tool_counts` does not retain, so counting it either way would
# be an attribution guess. The denominator is mutation + read calls, not all
# calls, so excluding Bash removes it from both sides rather than diluting one.
_MUTATION_TOOLS = frozenset({"Edit", "Write", "NotebookEdit", "MultiEdit"})
_READ_TOOLS = frozenset({"Read", "Grep", "Glob", "NotebookRead"})

# What the rendered n counts, per metric. The default ("sessions") is right for
# every metric whose bucket is the whole fenced population; a metric with a
# narrower frame must name it here, so the number on the tile cannot be read as
# a corpus-wide count.
_POPULATION_FRAME = {
    "compaction_yield": "July+ compacted sessions",
    "cost_per_tool": "sessions with ≥1 tool call",
    "mutation_ratio": "sessions with tool counts",
    "context_pressure_ratio": "sessions with max_context recorded",
}

# Top N tools to trend individually; everything else is aggregated as "other".
# Determined empirically from the tool_counts column; extend as usage evolves.
_TOP_TOOLS_N = 5

# What each regime's corpus actually sampled. Rendered on every rate panel so a
# reader cannot mistake a logging artifact for a workflow change.
SAMPLING_FRAME = {
    "migrated-jsonl": "notes migrated from JSONL - compaction was never recorded, so 0% is structural",
    "note-hook": "notes written only when a session compacted - rate is not a workflow property",
    "telemetry-v1": "all sessions logged (JSONL)",
    "session-hygiene-v1": "all sessions logged (JSONL)",
    "unclassified": "sampling frame unknown - dates outside the regime table",
}

_CONTEXT_LIMIT = 150_000

# GUA-120: the pressure threshold, deliberately below _CONTEXT_LIMIT. 150k is
# where the 5x cost cliff has already been paid; 100k is where the global rule
# (`~/.claude/rules/context-health.md`) says to compact. Measuring approach to
# the cliff is a different question from measuring arrival at it, so this is a
# second metric rather than a re-tuning of pct_over_150k.
_CONTEXT_PRESSURE_FLOOR = 100_000


@dataclass(frozen=True)
class Point:
    """One plotted observation. `n` carries the sample size behind it.

    `date` is always a real ISO date — the first observation in the bucket — so
    `_span_days` can parse it at every period. `bucket` carries the display key
    (`2026-08-13`, `2026-W33`, `2026-08`), which is not a parseable date above
    daily resolution. Empty `bucket` means the point predates period bucketing.
    """

    date: str
    value: float
    regime: str
    n: int = 1
    bucket: str = ""


@dataclass(frozen=True)
class Panel:
    """A single-regime facet. Never spans a boundary."""

    regime: str
    sampling_frame: str
    points: list[Point]


@dataclass(frozen=True)
class Series:
    """Either a continuous trend (`points`) or faceted panels (`panels`).

    `surface_points` carries per-surface breakdowns for continuous metrics,
    enabling the JS surface toggle. Keys are surface names (e.g. "claude-vscode")
    plus "unknown" for None-surface rows. Empty dict for rate/faceted metrics.
    """

    metric: str
    faceted: bool
    points: list[Point] = field(default_factory=list)
    panels: list[Panel] = field(default_factory=list)
    regime_bands: list[tuple[str, str, str]] = field(default_factory=list)
    july_only: bool = False
    surface_points: dict[str, list[Point]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------


def _work_sessions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Work-sessions only. Meta-sessions depress median size independently of any
    hygiene rule (research Disconfirming section 1) and are never pooled."""
    return [r for r in rows if not r.get("is_meta")]


# Period bucketing lives in `telemetry/periods.py` (GUA-104b) so `recurrence.py`
# can share it without importing this module. These aliases keep every existing
# call site here unchanged.
_iso_week = iso_week
_period_key = period_key
_DEFAULT_PERIOD = DEFAULT_PERIOD


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    idx = min(round((pct / 100) * (len(ordered) - 1)), len(ordered) - 1)
    return float(ordered[idx])


def _group(
    rows: list[dict[str, Any]], key: str = "date", period: str = "day"
) -> dict[str, list[dict[str, Any]]]:
    """Group `rows` by `key`, bucketed at `period`.

    `period="day"` keys on the raw value, preserving every pre-period caller.
    """
    out: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        out.setdefault(_period_key(str(row[key]), period), []).append(row)
    return out


def _cache_hit_rate(bucket: list[dict[str, Any]]) -> float:
    read = sum(r.get("cache_read_tokens") or 0 for r in bucket)
    written = sum(r.get("cache_write_tokens") or 0 for r in bucket)
    fresh = sum(r.get("input_tokens") or 0 for r in bucket)
    denominator = read + written + fresh
    return round(100 * read / denominator, 2) if denominator else 0.0


def _metric_value(metric: str, bucket: list[dict[str, Any]]) -> float | None:
    """Compute `metric` over one date-bucket, or None when it does not apply."""
    if metric == "compaction_pct":
        return round(100 * sum(1 for r in bucket if r.get("compacted")) / len(bucket), 2)
    if metric == "cost_units_p50":
        return _percentile([float(r.get("cost_units") or 0) for r in bucket], 50)
    if metric == "cost_units_p90":
        return _percentile([float(r.get("cost_units") or 0) for r in bucket], 90)
    if metric == "cache_hit_rate":
        return _cache_hit_rate(bucket)
    if metric == "output_tokens_p50":
        return _percentile([float(r.get("output_tokens") or 0) for r in bucket], 50)
    if metric == "total_tokens_p50":
        return _percentile(
            [float((r.get("input_tokens") or 0) + (r.get("output_tokens") or 0)) for r in bucket],
            50,
        )
    if metric in {"max_context_p50", "max_context_p90"}:
        values = [float(r["max_context"]) for r in bucket if r.get("max_context")]
        if not values:
            return None
        return _percentile(values, 50 if metric.endswith("p50") else 90)
    if metric == "pct_over_150k":
        values = [r["max_context"] for r in bucket if r.get("max_context")]
        if not values:
            return None
        return round(100 * sum(1 for v in values if v >= _CONTEXT_LIMIT) / len(values), 2)
    if metric == "tool_error_rate":
        # Errors per 100 tool calls -- normalised, so a long session is not
        # counted as more friction than a short one doing the same work.
        scored = [r for r in bucket if r.get("tool_error_count") is not None]
        if not scored:
            return None
        calls = sum(_tool_call_total(r) for r in scored)
        if not calls:
            return None
        errors = sum(int(r.get("tool_error_count") or 0) for r in scored)
        return round(100 * errors / calls, 2)
    if metric == "turns_per_session_p50":
        values = [float(r["human_turns"]) for r in bucket if r.get("human_turns") is not None]
        if not values:
            return None
        return _percentile(values, 50)
    if metric == "single_turn_pct":
        values = [r["human_turns"] for r in bucket if r.get("human_turns") is not None]
        if not values:
            return None
        return round(100 * sum(1 for v in values if v <= 1) / len(values), 2)
    if metric == "interruptions_p50":
        values = [
            float(r["user_interruptions"])
            for r in bucket
            if r.get("user_interruptions") is not None
        ]
        if not values:
            return None
        return _percentile(values, 50)
    if metric == "execution_skill_compliance_pct":
        exec_rows = [r for r in bucket if r.get("session_intent") == "execution"]
        if not exec_rows:
            return None
        guardrail_skills = {
            "workflow-execute",
            "workflow-review",
            "code-review",
            "code-debug",
            "code-refactor",
        }
        with_skills = sum(
            1 for r in exec_rows if guardrail_skills & set(json.loads(r.get("skill_costs") or "{}"))
        )
        return round(100 * with_skills / len(exec_rows), 2)
    if metric == "friction_labels_total":
        return sum(int(r.get("friction_label_count") or 0) for r in bucket)
    # LIB-57: failure attribution + bash antipatterns, computed at parse time in
    # factstore._to_fact_from_jsonl (ported from the workflow-insights step-9
    # lookup table) since the parser discards raw error text after reducing it
    # to an error_kind count dict.
    if metric in {
        "errors_code_total",
        "errors_env_total",
        "errors_tool_total",
        "errors_unknown_total",
    }:
        column = metric.removesuffix("_total")
        return float(sum(int(r.get(column) or 0) for r in bucket))
    if metric == "bash_antipatterns_p50":
        values = [
            float(r["bash_antipatterns"]) for r in bucket if r.get("bash_antipatterns") is not None
        ]
        if not values:
            return None
        return _percentile(values, 50)
    # Step 4: input-token series
    if metric == "input_tokens_p50":
        values = [float(r.get("input_tokens") or 0) for r in bucket]
        if not values:
            return None
        return _percentile(values, 50)
    if metric == "input_tokens_sum":
        return float(sum(r.get("input_tokens") or 0 for r in bucket))
    # Step 6: cost share in >150k context bucket
    if metric == "cost_bucket_pct_over150k":
        scored = [r for r in bucket if r.get("max_context") is not None]
        if not scored:
            return None
        total_cost = sum(float(r.get("cost_units") or 0) for r in scored)
        if not total_cost:
            return None
        over_cost = sum(
            float(r.get("cost_units") or 0)
            for r in scored
            if (r.get("max_context") or 0) >= _CONTEXT_LIMIT
        )
        return round(100 * over_cost / total_cost, 2)
    # GUA-120 Step 1: context pressure. Distinct from pct_over_150k -- that one
    # measures the 5x cost cliff; this measures approach to it, so a session at
    # 120k registers as pressure here and as nothing there.
    if metric == "context_pressure_ratio":
        values = [r["max_context"] for r in bucket if r.get("max_context") is not None]
        if not values:
            return None
        return round(100 * sum(1 for v in values if v >= _CONTEXT_PRESSURE_FLOOR) / len(values), 2)
    # GUA-120 Step 2: cost per tool call. Same filtered-bucket shape as
    # tool_error_rate -- sessions with no tool calls are excluded from both the
    # numerator and the denominator rather than counted as zero-cost work.
    if metric == "cost_per_tool":
        scored = [r for r in bucket if _tool_call_total(r) > 0]
        if not scored:
            return None
        calls = sum(_tool_call_total(r) for r in scored)
        if not calls:
            return None
        cost = sum(float(r.get("cost_units") or 0) for r in scored)
        return round(cost / calls, 2)
    # GUA-120 Step 3: mutation vs read. Denominator is mutation + read calls,
    # not all tool calls -- tools that are neither (Task, WebFetch, Bash) would
    # otherwise drag the ratio down as if they were reads.
    if metric == "mutation_ratio":
        mutations = 0
        reads = 0
        for row in bucket:
            counts = _tool_counts(row)
            mutations += sum(int(v) for k, v in counts.items() if k in _MUTATION_TOOLS)
            reads += sum(int(v) for k, v in counts.items() if k in _READ_TOOLS)
        total = mutations + reads
        if not total:
            return None
        return round(100 * mutations / total, 2)
    # GUA-120 Step 4: compaction yield. Median, not mean -- the distribution is
    # right-skewed (a few very long post-compact runs), and a mean would report
    # a typical session as longer than any typical session actually is. Rows are
    # already fenced to July+ compacted by COMPACT_METRICS in build_series; the
    # None-guard here covers a bucket that survived the fence with no column.
    if metric == "compaction_yield":
        values = [
            float(r["turns_since_last_compact"])
            for r in bucket
            if r.get("turns_since_last_compact") is not None
        ]
        if not values:
            return None
        return _percentile(values, 50)
    raise ValueError(f"unknown metric: {metric}")


def _tool_counts(row: dict[str, Any]) -> dict[str, int]:
    """Parsed tool_counts JSON, or {} when absent or malformed."""
    try:
        counts = json.loads(row.get("tool_counts") or "{}")
    except (TypeError, ValueError):
        return {}
    return counts if isinstance(counts, dict) else {}


def _tool_call_total(row: dict[str, Any]) -> int:
    """Total tool invocations in a session, from the stored tool_counts JSON."""
    return sum(int(v) for v in _tool_counts(row).values())


# GUA-120: which rows a metric actually computed over. `Point.n` counts bucket
# size, which equals the scored count only when a metric reads a column every
# row has -- so a tile rendering bucket size next to a filtered value overstates
# its population the moment one row is null. Metrics with a narrower frame than
# their bucket register the predicate here; everything else keeps bucket size.
_SCORED_ROW: dict[str, Callable[[dict[str, Any]], bool]] = {
    "context_pressure_ratio": lambda r: r.get("max_context") is not None,
    "cost_per_tool": lambda r: _tool_call_total(r) > 0,
    "mutation_ratio": lambda r: any(
        k in _MUTATION_TOOLS or k in _READ_TOOLS for k in _tool_counts(r)
    ),
    "compaction_yield": lambda r: r.get("turns_since_last_compact") is not None,
}


def _scored_count(metric: str, bucket: list[dict[str, Any]]) -> int:
    """Rows in `bucket` that contributed to `metric`'s value."""
    predicate = _SCORED_ROW.get(metric)
    if predicate is None:
        return len(bucket)
    return sum(1 for r in bucket if predicate(r))


def _regime_bands(points: list[Point]) -> list[tuple[str, str, str]]:
    """(regime, first_date, last_date) spans, for shading behind a trend line."""
    bands: list[tuple[str, str, str]] = []
    for point in points:
        if bands and bands[-1][0] == point.regime:
            regime, start, _ = bands[-1]
            bands[-1] = (regime, start, point.date)
        else:
            bands.append((point.regime, point.date, point.date))
    return bands


def _period_points(rows: list[dict[str, Any]], metric: str, period: str) -> list[Point]:
    """Bucket `rows` at `period` and reduce each bucket to a Point.

    Sub-grouped by regime because a week or month can span a regime boundary —
    only a *day* bucket is single-regime by construction. `date` is the bucket's
    first observation (a real ISO date); `bucket` is the display key.
    """
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = _period_key(str(row["date"]), period)
        grouped.setdefault((key, str(row["regime"])), []).append(row)

    points: list[Point] = []
    for (key, regime), bucket in sorted(grouped.items()):
        value = (
            float(len(bucket)) if metric == "sessions_per_week" else _metric_value(metric, bucket)
        )
        if value is None:
            continue
        points.append(
            Point(
                date=min(str(r["date"]) for r in bucket),
                value=value,
                regime=regime,
                n=_scored_count(metric, bucket),
                bucket=key,
            )
        )
    points.sort(key=lambda p: p.date)
    return points


def build_series(metric: str, store: Path, period: str = "day") -> Series:
    """Build `metric` from the fact table at `period` resolution.

    Rate metrics come back faceted by regime; per-session properties come back as
    one continuous line with regime bands. July-only metrics drop every row
    before the telemetry boundary rather than imputing across it.
    """
    rows = _work_sessions(read_all(store))
    july_only = metric in JULY_ONLY_METRICS or metric in COMPACT_METRICS
    if july_only:
        rows = [r for r in rows if str(r["date"]) >= JULY_BOUNDARY]
    # GUA-120: the narrower fence. Restricting to compacted sessions *before*
    # bucketing is what makes the rendered n the sub-population's n -- filtering
    # inside _metric_value would leave Point.n counting rows the metric did not
    # describe, which is the exact misreading the fence exists to prevent.
    if metric in COMPACT_METRICS:
        rows = [r for r in rows if r.get("compacted")]

    if metric == "sessions_per_week":
        # Counts sessions per bucket; "per_week" is the metric's name, not its
        # resolution — at period="day" it is sessions per day.
        by_regime: dict[str, list[Point]] = {}
        for point in _period_points(rows, metric, "week" if period == "day" else period):
            by_regime.setdefault(point.regime, []).append(point)
        return Series(
            metric=metric,
            faceted=True,
            panels=[
                Panel(regime=regime, sampling_frame=_frame(regime), points=points)
                for regime, points in sorted(by_regime.items())
            ],
        )

    points = _period_points(rows, metric, period)

    if metric in RATE_METRICS:
        by_regime = {}
        for point in points:
            by_regime.setdefault(point.regime, []).append(point)
        return Series(
            metric=metric,
            faceted=True,
            panels=[
                Panel(regime=regime, sampling_frame=_frame(regime), points=pts)
                for regime, pts in sorted(by_regime.items())
            ],
            july_only=july_only,
        )

    # Per-surface breakdown for the JS toggle. "unknown" buckets None-surface rows
    # (pre-July / pre-entrypoint transcripts). Only computed for continuous metrics.
    distinct_surfaces = sorted(
        {str(r.get("surface") or "unknown") for r in rows},
    )
    surface_points: dict[str, list[Point]] = {}
    for surf in distinct_surfaces:
        surf_rows = [r for r in rows if (r.get("surface") or "unknown") == surf]
        s_pts = _period_points(surf_rows, metric, period)
        if s_pts:
            surface_points[surf] = s_pts

    return Series(
        metric=metric,
        faceted=False,
        points=points,
        regime_bands=_regime_bands(points),
        july_only=july_only,
        surface_points=surface_points,
    )


def _frame(regime: str) -> str:
    return SAMPLING_FRAME.get(regime, SAMPLING_FRAME["unclassified"])


# ---------------------------------------------------------------------------
# trend_7d — the reusable sparkline component (GUA-137)
# ---------------------------------------------------------------------------

# Distinct from the _SPARK_* constants at :1835 — those size the friction bar
# sparkline, which is a different component with a different geometry.
_TREND_W = 100
_TREND_H = 20
# Inset so a 2px stroke at the extremes is not clipped by the viewBox edge.
_TREND_PAD = 2


def _sparkline_svg(points: list[Point], *, unit: str = "") -> str:
    """Render `points` as a 100x20 inline-SVG polyline.

    Pure: takes points, returns markup, touches no store. Fewer than two points
    renders a placeholder rather than a line — one observation is not a trend,
    and a flat line drawn through it would read as "stable" on evidence that
    cannot show stability (metric-fence convention).
    """
    if len(points) < 2:
        return (
            f'<span class="trend-none" title="not enough daily observations to plot a trend">'
            f"no trend (n={len(points)})</span>"
        )

    values = [p.value for p in points]
    lo, hi = min(values), max(values)
    span = hi - lo
    usable = _TREND_H - 2 * _TREND_PAD
    step = _TREND_W / (len(points) - 1)

    coords = []
    for i, value in enumerate(values):
        x = i * step
        # Flat series (span == 0) plots down the middle rather than dividing by
        # zero — a real, if uneventful, trend.
        frac = 0.5 if span == 0 else (value - lo) / span
        # SVG y grows downward; invert so larger values sit higher.
        y = _TREND_PAD + (1 - frac) * usable
        coords.append(f"{x:g},{y:g}")

    tooltip = " · ".join(f"{p.date}={_fmt_value(p.value, unit)}" for p in points)
    return (
        f'<svg class="sparkline" viewBox="0 0 {_TREND_W} {_TREND_H}" '
        f'width="120" height="20" role="img" aria-label="7-day trend">'
        f"<title>{html.escape(tooltip)}</title>"
        f'<polyline points="{" ".join(coords)}" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
        f"</svg>"
    )


def trend_7d(metric: str, store: Path, *, days: int = 7, unit: str = "") -> str:
    """Inline-SVG sparkline of `metric`'s last `days` daily observations.

    One component, many call sites: skills, experiments and friction tiles all
    render the same markup. Faceted (per-regime) metrics are flattened to a
    single chronological line — a sparkline has no room for a legend, and the
    full faceted view already exists in the main trend charts.

    Days with no observation are *skipped*, never zero-filled: a day with no
    sessions is missing data, and imputing zero would draw a crash that did not
    happen.
    """
    series = build_series(metric, store, period="day")
    if series.faceted:
        points = sorted(
            (p for panel in series.panels for p in panel.points),
            key=lambda p: p.date,
        )
    else:
        points = list(series.points)
    return _sparkline_svg(points[-days:], unit=unit)


def _distinct_surfaces(store: Path) -> list[str]:
    """Sorted list of distinct surface values in the fact table (work sessions only).

    "unknown" is included only if any row has a null/missing surface -- it is never
    fabricated when all rows carry a real surface value.
    """
    surfaces: set[str] = set()
    for row in _work_sessions(read_all(store)):
        surfaces.add(str(row.get("surface") or "unknown"))
    return sorted(surfaces)


def build_tool_trends(store: Path) -> tuple[list[str], dict[str, list[Point]]]:
    """Daily call-count trend for the top N tools plus an 'other' bucket.

    Returns (ordered_tool_names, {tool_name: [Point]}). July-forward only —
    tool_counts is null in the note era. The top-N selection is by total calls
    across the whole window, so the legend is stable over time.
    """
    rows = [r for r in _work_sessions(read_all(store)) if str(r.get("date") or "") >= JULY_BOUNDARY]
    # First pass: total calls per tool across the full window.
    total_by_tool: dict[str, int] = {}
    for row in rows:
        try:
            counts: dict[str, int] = json.loads(row.get("tool_counts") or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        for tool, n in counts.items():
            total_by_tool[tool] = total_by_tool.get(tool, 0) + int(n)
    top_tools = [t for t, _ in sorted(total_by_tool.items(), key=lambda kv: -kv[1])[:_TOP_TOOLS_N]]

    # Second pass: daily buckets per top tool + 'other'.
    daily: dict[str, dict[str, int]] = {}
    for row in rows:
        day = str(row.get("date") or "")
        try:
            counts = json.loads(row.get("tool_counts") or "{}")
        except (TypeError, json.JSONDecodeError):
            counts = {}
        bucket = daily.setdefault(day, dict.fromkeys(top_tools, 0))
        bucket.setdefault("other", 0)
        for tool, n in counts.items():
            if tool in top_tools:
                bucket[tool] += int(n)
            else:
                bucket["other"] += int(n)

    ordered = top_tools + (["other"] if any(d.get("other", 0) for d in daily.values()) else [])
    regime_rows = {str(r["date"]): str(r["regime"]) for r in rows}
    series: dict[str, list[Point]] = {}
    for tool in ordered:
        pts: list[Point] = []
        for day in sorted(daily):
            v = daily[day].get(tool, 0)
            pts.append(Point(date=day, value=float(v), regime=regime_rows.get(day, ""), n=1))
        if pts:
            series[tool] = pts
    return ordered, series


def _render_tool_trends(store: Path) -> str:
    """Daily tool-call trends for the top N tools plus 'other'.

    Step 6(b): shows which tools dominate invocation volume, how that shifts over
    time, and whether the Bash-over-dedicated-tool antipattern is structural.
    """
    ordered, series = build_tool_trends(store)
    if not series:
        return (
            '<section class="chart"><h3>Tool call trends (daily)</h3>'
            '<p class="note">No tool-count data yet. July-forward only.</p></section>'
        )
    colors = [
        "var(--chart-1)",
        "var(--chart-2)",
        "var(--chart-3)",
        "var(--chart-4)",
        "var(--muted)",
    ]
    charts = "".join(
        (
            f'<div style="margin-bottom:8px"><strong style="font-size:12px">'
            f"{html.escape(tool)}</strong>"
            f"{_svg_line(series[tool], colors[min(i, len(colors) - 1)], unit='count')}</div>"
        )
        for i, tool in enumerate(ordered)
        if tool in series
    )
    return (
        '<section class="chart"><h3>Tool call trends (daily)</h3>'
        '<p class="note">Daily call count for the top 5 tools by volume, '
        "plus an 'other' bucket. July-forward only. Bash volume is structural "
        "(28.7/session median from insights-log) — track for antipattern changes, "
        "not for absolute reduction.</p>"
        f"{charts}</section>"
    )


# ---------------------------------------------------------------------------
# Guacamayo promotion funnel (research F5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Funnel:
    """Promotion-funnel counts from the last logged synthesis event.

    `entries_in is None` means no synthesis has been logged - which is NOT zero.
    """

    last_synthesis: str | None = None
    entries_in: int | None = None
    to_sounding: int | None = None
    to_portfolio: int | None = None
    flagged_retro: int | None = None
    entries_since: int = 0


@dataclass(frozen=True)
class Experiment:
    """One tooling-ledger experiment row."""

    name: str
    metric: str
    status: str
    date: str


_SYNTHESIS = re.compile(r"\*\*Last Synthesis\*\*:\s*(\d{4}-\d{2}-\d{2})(.*)", re.IGNORECASE)
_SINCE = re.compile(r"\*\*Entries Since\*\*:\s*(\d+)", re.IGNORECASE)
_ENTRIES_IN = re.compile(r"(\d+)\s+entries", re.IGNORECASE)
_TO_SOUNDING = re.compile(r"(\d+)\s+woven into\s+sounding", re.IGNORECASE)
_TO_PORTFOLIO = re.compile(r"(\d+)\s+into\s+portfolio", re.IGNORECASE)
_FLAGGED = re.compile(r"(\d+)\s+process learnings flagged", re.IGNORECASE)


def funnel_counts(growth_md: Path) -> Funnel:
    """Read promotion-funnel counts from growth.md's logged synthesis header.

    Research F5: growth.md is a *draining* buffer - `/dream` clears it and resets
    "Entries Since" to 0. Polling the accumulator body therefore measures the
    drain, not the learning, and would render the funnel as flat zero. The counts
    that survive the clear live in the `**Last Synthesis**` header line, which
    records what the last `/dream` actually promoted.

    This is a read of an already-logged event, not a poll - the durable fix is
    for `/dream` to emit these counts at synthesis time (plan Step 10 note:
    out of scope here, needs its own plan).
    """
    if not growth_md.exists():
        log.warning("dashboard.funnel_missing", path=str(growth_md))
        return Funnel()

    text = growth_md.read_text(encoding="utf-8", errors="replace")
    since_match = _SINCE.search(text)
    entries_since = int(since_match.group(1)) if since_match else 0

    header = _SYNTHESIS.search(text)
    if not header:
        # No logged synthesis: unknown, never a fabricated zero.
        return Funnel(entries_since=entries_since)

    detail = header.group(2)

    def _first(pattern: re.Pattern[str]) -> int | None:
        match = pattern.search(detail)
        return int(match.group(1)) if match else None

    return Funnel(
        last_synthesis=header.group(1),
        entries_in=_first(_ENTRIES_IN),
        to_sounding=_first(_TO_SOUNDING),
        to_portfolio=_first(_TO_PORTFOLIO),
        flagged_retro=_first(_FLAGGED),
        entries_since=entries_since,
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

_TIER1 = [
    (
        "cost_units_p50",
        "Cost per session (p50)",
        "Lower is better. Each unit ≈ the cost of reading 1M input tokens.",
        "Work sessions only; meta-sessions excluded",
        "cost",
    ),
    (
        "cost_units_p90",
        "Cost per session (p90)",
        "Tail cost — the expensive sessions. Spikes = runaway context or long opus runs.",
        "",
        "cost",
    ),
    # Step 4: input-token series. Validates the 'context health is about input' intuition —
    # cache hit rate is a reuse proxy, not direct input-volume visibility.
    (
        "input_tokens_p50",
        "Input tokens per session (p50)",
        "Median input-token volume. High = large context carried in; rising = context growth.",
        "July-forward only; no pre-telemetry data",
        "tokens",
    ),
    (
        "input_tokens_sum",
        "Input tokens total (daily)",
        "Total input-token volume per day. Use alongside cache hit rate to read context cost.",
        "July-forward only",
        "tokens",
    ),
    (
        "cache_hit_rate",
        "Cache hit rate",
        "Higher is better. Below 90% means context churn is breaking prompt cache.",
        "",
        "pct",
    ),
    (
        "output_tokens_p50",
        "Output tokens per session (p50)",
        "Output volume per session. Output is 5× the cost of input.",
        "",
        "tokens",
    ),
]

_TIER2 = [
    (
        "max_context_p50",
        "Max context (p50)",
        "Median peak context. Staying below 150k avoids the 5× cost cliff.",
        "",
        "tokens",
    ),
    (
        "max_context_p90",
        "Max context (p90)",
        "The worst 10% of sessions. Shows how bad the outliers get.",
        "",
        "tokens",
    ),
    (
        "pct_over_150k",
        "% sessions over 150k context",
        "Share of sessions hitting the cost cliff. Was 66% in early July, target <30%.",
        "",
        "pct",
    ),
    # Step 6: cost-concentration in the >150k bucket — validates the '52% of spend' claim.
    (
        "cost_bucket_pct_over150k",
        "Cost share in >150k context sessions (%)",
        "Share of daily session cost in sessions that hit the 150k cliff. "
        "Validates or falsifies the '52% of spend' claim from insights-log.",
        "July-forward only; sessions without max_context excluded",
        "pct",
    ),
    # GUA-120 Step 1: approach to the cliff, not arrival at it.
    (
        "context_pressure_ratio",
        "Context pressure ratio (% over 100k)",
        "Share of sessions reaching the 100k compact-now threshold. Leads "
        "% over 150k — pressure here becomes cost there.",
        "July-forward only. Denominator: sessions with max_context recorded, not all sessions",
        "pct",
    ),
]

# GUA-120: work economics — what a unit of work costs, and what kind of work it
# was. Separate from Tier 1 (cost per *session*) because a session is a
# container, not a unit of work: two sessions of equal cost can do very
# different amounts of it.
_TIER_WORK = [
    (
        "cost_per_tool",
        "Cost per tool call",
        "Cost units per tool invocation. Falling = the same work for less; "
        "rising = more reasoning per action, which is not automatically worse.",
        "July-forward only. Sessions with zero tool calls are excluded from both "
        "the numerator and the denominator, not counted as zero-cost",
        "cost",
    ),
    (
        "mutation_ratio",
        "Mutation vs read ratio (%)",
        "Share of file-touching tool calls that write rather than read. Low = "
        "heavy exploration; high = editing with little context gathering.",
        "July-forward only. Denominator is mutation + read calls only. Bash is "
        "excluded from both sides — tool_counts does not retain the command, so "
        "classifying it either way would be a guess",
        "pct",
    ),
    (
        "compaction_yield",
        "Compaction yield (turns after compact, p50)",
        "Median human turns a session runs after compacting. Higher = compaction "
        "bought more work; near-zero = the session ended anyway and the compact was wasted.",
        "July+ compacted work sessions only — the tile renders its own n; this "
        "note does not restate it, because a hardcoded count goes stale against a "
        "live store. The column is null on every pre-July compacted session "
        "(not backfillable, so they are excluded rather than imputed), and "
        "meta-sessions are excluded here as everywhere. Median, not mean: the "
        "distribution is right-skewed",
        "count",
    ),
]

# Session shape: how work is divided into sessions. Read alongside "Sessions per
# week" -- volume alone cannot distinguish more work from the same work split
# across more cold starts, and those have opposite cost implications (each new
# session re-derives context that a continued one already holds).
_TIER_SHAPE = [
    (
        "turns_per_session_p50",
        "Human turns per session (p50)",
        "Turns before a session ends. Low = many cold starts paying context startup.",
        "",
        "count",
    ),
    (
        "single_turn_pct",
        "% single-turn sessions",
        "One-and-done sessions. Each pays full context load for one answer.",
        "",
        "pct",
    ),
]

# ---------------------------------------------------------------------------
# Friction tab — Step 9: prompt-eng / loop-eng / harness-eng regroup (F7)
#
# Research finding F4 confirmed: 3 of 5 original metrics measured productivity
# not friction. The regroup separates true friction (loop-eng) from capability
# signals (prompt-eng) and infrastructure health (harness-eng).
# ---------------------------------------------------------------------------

# Prompt-eng: does reasoning work? Skill compliance renamed from "friction" framing.
_FRICTION_PROMPT_ENG = [
    (
        "execution_skill_compliance_pct",
        "Skill compliance — execution sessions (%)",
        "Execution sessions invoking ≥1 skill. Low = unscaffolded work. "
        "Higher is better (productivity signal, not friction).",
        "Heuristic: intent classifier is v1",
        "pct",
    ),
]

# Loop-eng: does workflow repeat? The true-friction group.
_FRICTION_LOOP_ENG = [
    (
        "interruptions_p50",
        "User interruptions per session (p50)",
        "Fast follow-up turns (<5s) — agent went off-track and was corrected. "
        "Direct friction signal.",
        "Tool results excluded from turn count",
        "count",
    ),
    (
        "friction_labels_total",
        "Explicit friction labels (FRICTION:)",
        "Count of FRICTION: labels in user messages. User-reported friction only.",
        "User-authored signal",
        "count",
    ),
]

# Harness-eng: does infrastructure hold? Context + error signals.
_FRICTION_HARNESS_ENG = [
    (
        "tool_error_rate",
        "Tool error rate (per 100 calls)",
        "Errors per 100 tool calls. Structural noise level is ~28.7 Bash antipatterns/session "
        "(flat across interventions — endemic, not recoverable by config). "
        "Taxonomy split (code/env/tool/unknown) tracked in tool_errors column.",
        "Normalised so long sessions are not penalised",
        "count",
    ),
    # LIB-57: failure attribution, computed at parse time (errors_code/env/tool/
    # unknown columns) from the workflow-insights step-9 lookup table.
    (
        "errors_code_total",
        "Errors — code",
        "file_not_found, edit_failed, command_failed (retry unknown — parser "
        "carries no retry sequence, so transient/code fold together).",
        "Attribution applied at parse time; backfill requires re-parse",
        "count",
    ),
    (
        "errors_env_total",
        "Errors — env",
        "permission_denied, file_too_large, quota/rate-limit signals.",
        "Attribution applied at parse time; backfill requires re-parse",
        "count",
    ),
    (
        "errors_tool_total",
        "Errors — tool",
        "user_rejected (hook blocks) on any tool.",
        "Attribution applied at parse time; backfill requires re-parse",
        "count",
    ),
    (
        "errors_unknown_total",
        "Errors — unknown",
        "Unclassified error_kind values. A high rate flags a taxonomy gap, not noise to ignore.",
        "Attribution applied at parse time; backfill requires re-parse",
        "count",
    ),
    (
        "bash_antipatterns_p50",
        "Bash antipatterns per session (p50)",
        "Shell used where a dedicated tool (Read/Grep/Glob) exists — wastes "
        "context, slower than the native tool.",
        "",
        "count",
    ),
]

# Rework-cycle placeholder — loop-eng signal not yet captured (F5, Tier 3 deferred)
_REWORK_PLACEHOLDER = (
    '<section class="chart"><h3>Rework cycles</h3>'
    '<p class="note">Not yet captured. Detecting rework requires message-pair '
    "similarity analysis on session JSONL — deferred to Tier 3 (F5, LIB #65). "
    "Current proxy: user interruptions (see above).</p></section>"
)

# Population rates: within-regime diagnostics only. Rendered faceted, never as a
# cross-regime trend - the Apr-Jun corpus samples only compacted sessions.
_RATES = [
    (
        "compaction_pct",
        "Compaction rate",
        "How often sessions compact. Per-regime only — the pre-July logger makes these incomparable across regimes.",
        "Survivorship: see panel frames",
        "pct",
    ),
    (
        "sessions_per_week",
        "Sessions per week",
        "Session volume. More sessions could mean more work or the same work restarted.",
        "Sampling frame differs per regime",
        "count",
    ),
]


def _fmt_value(value: float, unit: str) -> str:
    if unit == "pct":
        return f"{value:.0f}%"
    if unit == "tokens" and abs(value) >= 1000:
        return f"{value / 1000:.0f}k"
    if unit == "cost" and abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if unit == "cost" and abs(value) >= 1000:
        return f"{value / 1000:.0f}k"
    return f"{value:g}"


_MONTH_ABBR = [
    "",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


def _svg_line(
    points: list[Point],
    color: str,
    width: int = 640,
    height: int = 160,
    unit: str = "count",
    experiments: list[Experiment] | None = None,
) -> str:
    """A minimal 2px trend line with y-axis labels and x-axis month ticks.

    `experiments` (LIB-59) draws one dated vertical annotation line per mapped
    ledger experiment that falls within the plotted date range -- see
    `_render_annotations`. Omitted by every caller that has no experiments to
    bind, so charts with no mapping render exactly as before.
    """
    if not points:
        return '<p class="empty">no data</p>'
    pad_left = 48
    pad_bottom = 18
    plot_w = width - pad_left
    plot_h = height - pad_bottom
    values = [p.value for p in points]
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    step = plot_w / max(len(points) - 1, 1)

    def _x(i: int) -> float:
        return pad_left + i * step

    def _y(v: float) -> float:
        return plot_h - ((v - lo) / span) * (plot_h - 20) - 10

    coords = " ".join(f"{_x(i):.1f},{_y(p.value):.1f}" for i, p in enumerate(points))
    dots = "".join(
        f'<circle cx="{_x(i):.1f}" cy="{_y(p.value):.1f}" r="4" '
        f'fill="{color}"><title>{html.escape(p.date)}: {p.value:g} (n={p.n})</title></circle>'
        for i, p in enumerate(points)
    )

    y_labels = (
        f'<text x="{pad_left - 4}" y="{_y(hi):.1f}" text-anchor="end" '
        f'dominant-baseline="middle" class="axis-label">{html.escape(_fmt_value(hi, unit))}</text>'
        f'<text x="{pad_left - 4}" y="{_y(lo):.1f}" text-anchor="end" '
        f'dominant-baseline="middle" class="axis-label">{html.escape(_fmt_value(lo, unit))}</text>'
    )

    x_labels = ""
    if len(points) > 14:
        seen_months: set[str] = set()
        for i, p in enumerate(points):
            month_str = p.date[:7]
            if month_str not in seen_months:
                seen_months.add(month_str)
                month_num = int(p.date[5:7])
                x_labels += (
                    f'<text x="{_x(i):.1f}" y="{height - 2}" text-anchor="middle" '
                    f'class="axis-label">{_MONTH_ABBR[month_num]}</text>'
                )
    else:
        x_labels = (
            f'<text x="{_x(0):.1f}" y="{height - 2}" text-anchor="start" '
            f'class="axis-label">{html.escape(points[0].date[5:])}</text>'
            f'<text x="{_x(len(points) - 1):.1f}" y="{height - 2}" text-anchor="end" '
            f'class="axis-label">{html.escape(points[-1].date[5:])}</text>'
        )

    annotations = _render_annotations(points, experiments, _x, plot_h) if experiments else ""

    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" preserveAspectRatio="none">'
        f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linejoin="round" stroke-linecap="round"/>{dots}{annotations}{y_labels}{x_labels}'
        f"</svg>"
    )


# Neutral annotation colour, distinct from every _CSS --chart-N line colour in
# both themes -- see LIB-59 issue comment (2026-08-01): the ledger's Status
# column no longer leads with a stable `hypothesis`/`FRICTION` vocabulary (all
# 32 rows now lead with `hypothesis`), so colour-by-status would render every
# annotation identically and carry zero information. One neutral colour for
# all annotations; the hover tooltip carries the full status text instead.
_ANNOTATION_COLOR = "#8a8a86"


def _render_annotations(
    points: list[Point],
    experiments: list[Experiment],
    x_of: Callable[[int], float],
    plot_h: float,
) -> str:
    """One dated vertical line per experiment that falls inside `points`' date range.

    `x_of` is `_svg_line`'s own index->x closure; the date is located by linear
    interpolation between the two bracketing points (or snapped to an exact
    match) so an annotation lines up with the same x-scale as the trend line
    it sits behind. Experiments outside the series' first/last date render
    nothing -- there is no x-coordinate for them on this chart.
    """
    if not points:
        return ""
    first, last = points[0].date, points[-1].date
    marks = ""
    for exp in experiments:
        if not (first <= exp.date <= last):
            continue
        x = _annotation_x(points, exp.date, x_of)
        if x is None:
            continue
        title = html.escape(f"{exp.name} — {exp.metric} — {exp.status}")
        marks += (
            f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{plot_h:.1f}" '
            f'stroke="{_ANNOTATION_COLOR}" stroke-width="1.5" stroke-dasharray="3,2" '
            f'class="annotation-line"><title>{title}</title></line>'
        )
    return marks


def _annotation_x(
    points: list[Point], target_date: str, x_of: Callable[[int], float]
) -> float | None:
    """x-coordinate for `target_date` on `points`' scale, or None if unplaceable."""
    for i, p in enumerate(points):
        if p.date == target_date:
            return x_of(i)
    # Interpolate between the bracketing points sharing the same index scale
    # `_svg_line` uses (index-based, not calendar-day-based) -- points are not
    # evenly spaced in time, so an annotation between two plotted dates lands
    # at the midpoint of their index positions, which is close enough for a
    # marker whose job is "roughly here", not exact date arithmetic.
    for i in range(len(points) - 1):
        if points[i].date < target_date < points[i + 1].date:
            return (x_of(i) + x_of(i + 1)) / 2
    return None


def _table_view(points: list[Point]) -> str:
    """The relief rule: three light-mode slots sit below 3:1 on the light surface,
    and the dark palette's worst adjacent CVD pair lands in the 6-8 floor band.
    Both are legal only with secondary encoding, so every chart ships a readable
    table alongside it - identity and value are never carried by hue alone.
    """
    rows = "".join(
        f"<tr><td>{html.escape(p.date)}</td><td>{p.value:g}</td>"
        f"<td>{html.escape(p.regime)}</td><td>{p.n}</td></tr>"
        for p in points
    )
    return (
        '<details class="table-view"><summary>Table view</summary>'
        "<table><thead><tr><th>date</th><th>value</th><th>regime</th><th>n</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></details>"
    )


def _span_days(points: list[Point]) -> int:
    """Calendar days covered by a panel's points."""
    first = _date.fromisoformat(points[0].date)
    last = _date.fromisoformat(points[-1].date)
    return (last - first).days


# Below this many points a line is unreadable — one or two points drew a ~2px
# sliver that looked like a rendering bug rather than a sparse regime.
_MIN_LINE_POINTS = 3


def _saturation_warning(panel: Panel) -> str:
    """Flag a rate panel pinned at either rail — that is the logger, not the workflow.

    Both rails are artifacts here, and both are structural (verified 2026-07-19):
    every `note-hook` day is exactly 100% because the hook only fired on
    compaction, and every `migrated-jsonl` day is exactly 0% because migrated
    notes never recorded compaction at all. Unflagged, the pair reads as a 0->100%
    improvement across the boundary when nothing about the work changed.
    """
    for rail, label in ((100.0, "100%"), (0.0, "0%")):
        pinned = [p for p in panel.points if p.value == rail]
        if len(pinned) >= _MIN_LINE_POINTS and len(pinned) >= len(panel.points) / 2:
            return (
                f'<p class="saturated">⚠ {len(pinned)} of {len(panel.points)} points sit at '
                f"{label} — at this rail the metric measures the logging trigger, "
                f"not behaviour.</p>"
            )
    return ""


def _panel_body(panel: Panel, color: str, span: int, widest: int, unit: str = "count") -> str:
    """A line when there is enough to plot, otherwise the values as text."""
    if len(panel.points) < _MIN_LINE_POINTS:
        values = ", ".join(f"{p.value:.0f}" for p in panel.points)
        label = "value" if len(panel.points) == 1 else "values"
        return (
            f'<p class="sparse"><strong>{html.escape(values)}</strong>'
            f'<span class="sparse-label"> ({len(panel.points)} {label} — '
            f"too few points to plot)</span></p>"
        )
    width = max(140, round(300 * span / widest))
    return _svg_line(panel.points, color, width=width, unit=unit)


def _population_line(series: Series) -> str:
    """The rendered n: how many rows the plotted values were computed from.

    GUA-120's DoD requirement, and the fix for the defect that issue names --
    a tile computed over the rows that happen to carry a sparse column renders
    identically to one computed over the whole corpus. Summing Point.n is
    correct because buckets partition the fenced rows: each row lands in exactly
    one (period, regime) bucket, and a bucket whose value is None is dropped
    from `points`, so the total counts contributing rows only.
    """
    total = sum(p.n for p in series.points)
    frame = _POPULATION_FRAME.get(series.metric, "sessions")
    return f'<p class="population">n = {total:,} {html.escape(frame)}</p>'


def _render_series(
    series: Series,
    color: str,
    title: str,
    note: str,
    provenance: str = "",
    unit: str = "count",
    experiments: list[Experiment] | None = None,
) -> str:
    """Faceted panels for rate metrics; one banded line for properties.

    `experiments` (LIB-59) is the full parsed ledger list; only rows whose
    ledger signal maps to `series.metric` (see `LEDGER_METRIC_MAPPING`) draw an
    annotation, and only on the continuous-line branch -- faceted rate metrics
    have no single x-scale to annotate against.
    """
    prov = ""
    if provenance:
        prov = (
            f'<details class="provenance"><summary>Technical note</summary>'
            f"<p>{html.escape(provenance)}</p></details>"
        )
    header = f"<h3>{html.escape(title)}</h3><p class='note'>{html.escape(note)}</p>{prov}"

    if series.faceted:
        drawn = [p for p in series.panels if p.points]
        spans = {p.regime: max(_span_days(p.points), 1) for p in drawn}
        widest = max(spans.values(), default=1)
        panels = "".join(
            f'<div class="panel" style="flex:{spans[panel.regime]} 1 0">'
            f"<h4>{html.escape(panel.regime)}</h4>"
            f'<p class="frame">{html.escape(panel.sampling_frame)}</p>'
            f"{_saturation_warning(panel)}"
            f"{_panel_body(panel, color, spans[panel.regime], widest, unit)}"
            f'<p class="range">{html.escape(panel.points[0].date)} - '
            f"{html.escape(panel.points[-1].date)}</p></div>"
            for panel in drawn
        )
        return (
            f'<section class="chart faceted">{header}'
            f'<p class="rule">Population rate - separate panels per regime; '
            f"no line crosses a regime boundary.</p>"
            f'<div class="panels">{panels}</div>'
            f"{_table_view([p for panel in series.panels for p in panel.points])}</section>"
        )

    if not series.points:
        return f'<section class="chart">{header}<p class="empty">no data</p></section>'

    bands = "".join(
        f'<li><span class="swatch"></span>{html.escape(regime)}: '
        f"{html.escape(start)} - {html.escape(end)}</li>"
        for regime, start, end in series.regime_bands
    )

    mapped_experiments = _annotations_for_metric(series.metric, experiments or [])

    # Pre-render one SVG per surface (including "all") as hidden divs.
    # The JS surface selector simply shows/hides these divs -- no SVG re-draw
    # in the browser, no framework, no build step. The "all" div is visible by
    # default; selecting a specific surface shows only its div.
    svg_all = _svg_line(series.points, color, unit=unit, experiments=mapped_experiments)
    surface_svgs = f'<div class="surf-view" data-surface="all">{svg_all}</div>'
    for surf, pts in series.surface_points.items():
        surf_svg = _svg_line(pts, color, unit=unit)
        surface_svgs += (
            f'<div class="surf-view" data-surface="{html.escape(surf)}" '
            f'style="display:none">{surf_svg}</div>'
        )

    return (
        f'<section class="chart" data-metric="{html.escape(series.metric)}">{header}'
        f"{surface_svgs}"
        f'<p class="range">{html.escape(series.points[0].date)} - '
        f"{html.escape(series.points[-1].date)}</p>"
        f"{_population_line(series)}"
        f'<ul class="bands">{bands}</ul>'
        f"{_table_view(series.points)}</section>"
    )


def _subagent_totals(
    store: Path,
    since: str | None = None,
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]], dict[str, int]]:
    """Sum the stored per-parent subagent breakdowns into (by_agent, by_model, spawn_counts).

    Work sessions only, matching every other panel. Rows with a NULL column are
    parents that spawned no subagent -- skipped, not counted as zero.
    spawn_counts aggregates agent type counts from parent Agent tool calls.
    Pass `since` (YYYY-MM-DD) to restrict to sessions on/after that date -- used to
    measure unattributed share on a recent window, since pre-CLI-2.1.201 transcripts
    permanently lack attribution and would otherwise dominate an all-time cumulative
    view regardless of how many new named agents ship.
    """
    by_agent: dict[str, dict[str, float]] = {}
    by_model: dict[str, dict[str, float]] = {}
    spawn_counts: dict[str, int] = {}
    for row in _work_sessions(read_all(store)):
        if since and row.get("date", "") < since:
            continue
        raw = row.get("subagent_costs")
        if raw:
            try:
                payload = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                payload = {}
            for group, target in (("by_agent", by_agent), ("by_model", by_model)):
                for name, stats in (payload.get(group) or {}).items():
                    slot = target.setdefault(name, {"cost": 0.0, "output_tokens": 0.0, "n": 0.0})
                    slot["cost"] += stats.get("cost", 0.0)
                    slot["output_tokens"] += stats.get("output_tokens", 0)
                    slot["n"] += stats.get("n", 0)
        raw_spawns = row.get("agent_spawns")
        if raw_spawns:
            try:
                spawns = json.loads(raw_spawns)
            except (TypeError, json.JSONDecodeError):
                spawns = []
            for spawn in spawns:
                agent_type = spawn.get("type", "general-purpose")
                spawn_counts[agent_type] = spawn_counts.get(agent_type, 0) + 1
    return by_agent, by_model, spawn_counts


def _share_rows(totals: dict[str, dict[str, float]], label: str) -> str:
    """A cost-ranked breakdown table. Share is of subagent spend, not session spend."""
    if not totals:
        return '<p class="empty">no data</p>'
    grand = sum(s["cost"] for s in totals.values()) or 1.0
    rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{stats['cost']:,.0f}</td>"
        f"<td>{stats['cost'] / grand * 100:.0f}%</td>"
        f"<td>{stats['output_tokens']:,.0f}</td><td>{stats['n']:.0f}</td></tr>"
        for name, stats in sorted(totals.items(), key=lambda kv: -kv[1]["cost"])
    )
    return (
        f"<table><thead><tr><th>{html.escape(label)}</th><th>cost units</th>"
        f"<th>share</th><th>output tokens</th><th>transcripts</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _spawn_table(spawn_counts: dict[str, int]) -> str:
    """Spawned agents by type — from parent Agent tool calls."""
    if not spawn_counts:
        return ""
    total = sum(spawn_counts.values()) or 1
    rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{count}</td><td>{count / total * 100:.0f}%</td></tr>"
        for name, count in sorted(spawn_counts.items(), key=lambda kv: -kv[1])
    )
    return (
        f"<h4>Spawned agents by type</h4>"
        f'<p class="note">From parent sessions\' Agent tool calls.</p>'
        f"<table><thead><tr><th>agent type</th><th>spawns</th>"
        f"<th>share</th></tr></thead><tbody>{rows}</tbody></table>"
    )


# GUA-137: rolling windows for the subagent attribution card. Each window is
# computed server-side and all four are emitted; the toggle only changes which
# is visible, so switching never re-reads the store.
SUBAGENT_WINDOWS: list[tuple[str, str, int | None]] = [
    ("7d", "7 days", 7),
    ("30d", "30 days", 30),
    ("6mo", "6 months", 182),
    ("1y", "1 year", 365),
    ("all", "All time", None),
]


def _window_cutoff(store: Path, days: int | None) -> str | None:
    """ISO cutoff `days` back from the newest row, or None for all-time.

    Anchored to the newest observation rather than today: the store is refreshed
    by a batch job, so anchoring to wall-clock would silently empty the 7-day
    window whenever the job has not run yet.
    """
    if days is None:
        return None
    rows = _work_sessions(read_all(store))
    newest = max((str(r["date"]) for r in rows), default="")
    if not newest:
        return None
    return (_date.fromisoformat(newest) - timedelta(days=days)).isoformat()


def render_subagent_windows_card(store: Path) -> str:
    """Subagent attribution with a rolling-window toggle (7d/30d/6mo/1y/all).

    Replaces the hardcoded "84% unattributed" prose: the share is computed per
    window, so the number cannot go stale, and a reader can see whether recent
    work is better attributed than the all-time figure suggests.
    """
    panels, buttons = [], []
    for i, (key, label, days) in enumerate(SUBAGENT_WINDOWS):
        cutoff = _window_cutoff(store, days)
        by_agent, by_model, spawn_counts = _subagent_totals(store, since=cutoff)
        grand = sum(s["cost"] for s in by_agent.values())
        unattr = by_agent.get(UNATTRIBUTED_AGENT, {}).get("cost", 0.0)
        active = " active" if i == 0 else ""
        hidden = "" if i == 0 else ' style="display:none"'

        if not grand:
            body = (
                '<p class="empty">No subagent spend recorded in this window.</p>'
                if cutoff
                else '<p class="empty">No subagent spend recorded.</p>'
            )
        else:
            pct = unattr / grand * 100
            tone = "bad" if pct >= 60 else ("warn" if pct >= 25 else "good")
            body = (
                f'<div class="stat-row">'
                f'<div class="stat"><span class="value">{grand / 1_000_000:,.1f}M</span>'
                f'<span class="label">subagent cost</span></div>'
                f'<div class="stat"><span class="value" style="color:var(--{tone})">'
                f"{pct:.0f}%</span>"
                f'<span class="label">unattributed</span></div>'
                f'<div class="stat"><span class="value">{sum(spawn_counts.values()):,}</span>'
                f'<span class="label">agents spawned</span></div></div>'
                f'<div class="overflow-x">{_share_rows(by_agent, "agent")}</div>'
                f'<div class="overflow-x">{_share_rows(by_model, "model")}</div>'
            )

        panels.append(f'<div class="win-panel" data-win="{key}"{hidden}>{body}</div>')
        buttons.append(
            f'<button type="button" class="win-btn{active}" data-win="{key}">{label}</button>'
        )

    return (
        '<div class="card">\n'
        '      <div class="card-title">Subagent attribution</div>\n'
        '      <p class="card-note">Cost of subagent transcripts, charged to the parent '
        "session that spawned them. Only CLI "
        f"{SUBAGENT_ATTRIBUTION_CLI}+ transcripts carry an agent name, so "
        "<em>unattributed</em> is a coverage measure, not an agent.</p>\n"
        f'      <div class="win-toggle" role="group" aria-label="Time window">'
        f"{''.join(buttons)}</div>\n"
        f"      {''.join(panels)}\n"
        "    </div>"
    )


def _render_subagents(store: Path) -> str:
    """Subagent spend split by agent type and by model.

    Rendered as tables rather than a trend line: this is a categorical breakdown
    of a single window, and only 2.1.201+ transcripts carry an agent name, so a
    time series would show attribution coverage arriving rather than any change
    in how subagents are used.
    """
    by_agent, by_model, spawn_counts = _subagent_totals(store)
    unattributed = by_agent.get(UNATTRIBUTED_AGENT, {}).get("cost", 0.0)
    grand = sum(s["cost"] for s in by_agent.values())
    # Recent-window figure: CLI 2.1.201 rollout date is the natural cut -- anything
    # before it structurally cannot carry attribution.
    recent_by_agent, _, _ = _subagent_totals(store, since=SUBAGENT_ATTRIBUTION_SINCE)
    recent_unattributed = recent_by_agent.get(UNATTRIBUTED_AGENT, {}).get("cost", 0.0)
    recent_grand = sum(s["cost"] for s in recent_by_agent.values())
    caveat = ""
    if unattributed and grand:
        caveat = (
            f'<p class="saturated">&#9888; {unattributed / grand * 100:.0f}% of subagent cost '
            f"predates CLI {SUBAGENT_ATTRIBUTION_CLI} and carries no agent name. "
            f"Per-agent shares below are shares of all subagent spend, so the named "
            f"rows understate each agent's true share of attributable work.</p>"
        )
        if recent_grand:
            caveat += (
                f'<p class="note">Since {SUBAGENT_ATTRIBUTION_SINCE}: '
                f"{recent_unattributed / recent_grand * 100:.0f}% unattributed "
                f"(recent-window figure -- the acceptance metric for GUA-45).</p>"
            )
    total_spawns = sum(spawn_counts.values())
    attributed_n = sum(s["n"] for s in by_agent.values())
    coverage_caveat = ""
    if total_spawns and attributed_n and total_spawns > attributed_n * 1.5:
        coverage_caveat = (
            f'<p class="saturated">⚠ {total_spawns} agents spawned but only '
            f"{attributed_n:.0f} cost-attributed — coverage gap.</p>"
        )
    return (
        f'<section class="chart"><h3>Subagent attribution</h3>'
        f'<p class="note">Cost and tokens of subagent transcripts, charged to the '
        f"parent session that spawned them. Work sessions only.</p>"
        f"{caveat}{coverage_caveat}"
        f'<div class="table-view">{_spawn_table(spawn_counts)}</div>'
        f'<div class="table-view">{_share_rows(by_agent, "agent")}</div>'
        f'<div class="table-view">{_share_rows(by_model, "model")}</div></section>'
    )


def build_skill_economics(store: Path, since: str | None = None) -> dict[str, dict[str, float]]:
    """Aggregate per-skill invocation count and cost from stored skill_costs JSON.

    Returns {skill_name: {"cost": float, "n": int}} sorted by cost descending.
    Work sessions only (meta-sessions excluded). July-forward only — skill_costs
    is null in the note era. `since` is an inclusive ISO date floor; None means
    the whole store.
    """
    totals: dict[str, dict[str, float]] = {}
    for row in _work_sessions(read_all(store)):
        raw = row.get("skill_costs")
        if not raw:
            continue
        if since and str(row.get("date") or "") < since:
            continue
        try:
            costs: dict[str, float] = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        for skill, cost in costs.items():
            entry = totals.setdefault(skill, {"cost": 0.0, "n": 0})
            entry["cost"] += float(cost)
            entry["n"] += 1
    return dict(sorted(totals.items(), key=lambda kv: -kv[1]["cost"]))


def build_skill_daily(store: Path) -> dict[str, list[Point]]:
    """Per-skill daily cost/session series, for the trend_7d component.

    `build_series` is whole-store by construction, so a per-skill breakdown
    needs its own bucketing. Value is mean cost per invocation on that day —
    the same quantity the table's cost/session column ranks, so the sparkline
    and the number next to it describe one metric.

    Days a skill was not invoked are absent, not zero (GUA-137 metric fence).
    """
    by_skill: dict[str, dict[str, list[float]]] = {}
    for row in _work_sessions(read_all(store)):
        raw = row.get("skill_costs")
        if not raw:
            continue
        try:
            costs: dict[str, float] = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        date = str(row.get("date") or "")
        if not date:
            continue
        for skill, cost in costs.items():
            by_skill.setdefault(skill, {}).setdefault(date, []).append(float(cost))

    series: dict[str, list[Point]] = {}
    for skill, by_date in by_skill.items():
        series[skill] = [
            Point(date=date, value=sum(vals) / len(vals), regime="", n=len(vals))
            for date, vals in sorted(by_date.items())
        ]
    return series


def _render_skill_economics(store: Path) -> str:
    """Per-skill invocation count and cost table.

    Parallel to the existing model/agent-type breakdown tables. Marker-owned
    region in the aggregate dashboard; not patched into context-dashboard.html
    (that is the review-card pattern, not needed here).
    """
    totals = build_skill_economics(store)
    daily = build_skill_daily(store)
    if not totals:
        return (
            '<section class="chart"><h3>Skill economics</h3>'
            '<p class="note">No skill cost data yet. Skill invocations are attributed '
            "from JSONL era sessions (July+).</p></section>"
        )
    grand = sum(e["cost"] for e in totals.values()) or 1.0
    sessions = sum(int(e["n"]) for e in totals.values())
    rows = "".join(
        f"<tr><td>{html.escape(skill)}</td>"
        f"<td>{stats['cost']:,.0f}</td>"
        f"<td>{stats['cost'] / grand * 100:.0f}%</td>"
        f"<td>{int(stats['n'])}</td>"
        f"<td>{stats['cost'] / stats['n']:,.0f}</td>"
        f'<td class="trend-cell">{_sparkline_svg(daily.get(skill, [])[-7:], unit="cost")}</td>'
        "</tr>"
        for skill, stats in totals.items()
        if stats["n"]
    )
    return (
        '<section class="chart"><h3>Skill economics</h3>'
        '<p class="note">Per-skill cost and session count. Cost attributed from JSONL '
        "assistant output between a slash invocation and the next human turn. "
        "Work sessions only; July-forward.</p>"
        # GUA-120: cost/session is the only yield proxy the stored data supports.
        # skill_costs carries cost and invocation count, not an outcome, so a
        # cheap skill and an effective one are indistinguishable here -- said
        # plainly rather than letting the column imply a value judgement.
        '<p class="note">Cost/session ranks spend per invocation, not value returned: '
        "the store carries no outcome per skill, so a high number means expensive, "
        "not wasteful.</p>"
        f'<p class="population">n = {sessions:,} skill invocations</p>'
        '<div class="table-view"><table>'
        "<thead><tr><th>Skill</th><th>cost units</th><th>share</th><th>sessions</th>"
        "<th>cost/session</th><th>7-day trend</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div></section>"
    )


def _render_funnel(funnel: Funnel | None) -> str:
    if funnel is None or funnel.entries_in is None:
        return (
            '<section class="chart"><h3>Promotion funnel</h3>'
            '<p class="note">No logged synthesis event. growth.md drains on /dream, so an '
            "empty buffer is not evidence of zero promotions - the counts must be emitted "
            "at synthesis time.</p></section>"
        )
    stages = [
        ("entries in", funnel.entries_in),
        ("to sounding", funnel.to_sounding),
        ("to portfolio", funnel.to_portfolio),
        ("flagged for retro", funnel.flagged_retro),
    ]
    tiles = "".join(
        f'<div class="tile"><span class="value">{v if v is not None else "-"}</span>'
        f'<span class="label">{html.escape(label)}</span></div>'
        for label, v in stages
    )
    return (
        f'<section class="chart"><h3>Promotion funnel</h3>'
        f'<p class="note">Last synthesis {html.escape(funnel.last_synthesis or "unknown")} - '
        f"counts read from the logged event, not the drained buffer "
        f"(buffer now holds {funnel.entries_since}).</p>"
        f'<div class="tiles">{tiles}</div></section>'
    )


_STATUS_ORDER = {
    "confirmed": 0,
    "verified": 0,
    "partial-verified": 0,
    "fixed-pending-commit": 0,
    "failed": 1,
    "trending": 2,
    "hypothesis": 3,
    "applied": 3,
    "fixed": 3,
    "inconclusive": 4,
    "superseded": 5,
    "dropped": 5,
    "duplicate": 5,
}
_STATUS_CLASS = {
    "confirmed": "exp-confirmed",
    "verified": "exp-confirmed",
    "partial-verified": "exp-confirmed",
    "fixed-pending-commit": "exp-confirmed",
    "failed": "exp-failed",
}

# ---------------------------------------------------------------------------
# Ledger parsing (Step 7)
# ---------------------------------------------------------------------------

_LEDGER_ROW = re.compile(
    r"^\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|"
)
_LEDGER_LOG_ROW = re.compile(
    r"^\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|"
)
_HEADER_CELL = re.compile(r"^-+$")


def parse_ledger(ledger_path: Path, log_path: Path | None = None) -> list[Experiment]:
    """Parse tooling-ledger.md (and optionally tooling-ledger-log.md) into Experiment rows.

    Active ledger schema: | Date | Change | Area | Metric | Status |
    Log ledger schema:    | Date | Change | Area | Verdict | Evidence |
    Both are 5-column tables. Rows with rollup/batch markers in the date cell are
    skipped (not parseable as individual experiments). Malformed rows degrade to
    'skipped N rows' logged at WARNING — never crash the dashboard build.

    Returns the list deduplicated by (date, name) — the log may contain superseded
    entries that are re-archived from the active ledger.
    """
    experiments: list[Experiment] = []
    skipped = 0

    def _parse_5col_table(text: str, is_log: bool) -> None:
        nonlocal skipped
        for line in text.splitlines():
            m = _LEDGER_ROW.match(line)
            if not m:
                continue
            cells = [m.group(i).strip() for i in range(1, 6)]
            # 5th cell is Status in the active ledger but Evidence in the log —
            # named neutrally because its meaning depends on `is_log` below.
            date_cell, change_cell, _area_cell, metric_cell, evidence_or_status_cell = cells
            # Skip header and separator rows
            if _HEADER_CELL.match(date_cell) or date_cell.lower() in ("date", "---"):
                continue
            if _HEADER_CELL.match(evidence_or_status_cell) or evidence_or_status_cell.lower() in (
                "status",
                "verdict",
                "---",
            ):
                continue
            # Skip rollup/batch rows (not individual experiments)
            if any(kw in date_cell.lower() for kw in ("rollup", "batch", "2026-07 (rollup)")):
                skipped += 1
                continue
            # Guard the cell that actually carries the verdict for this file:
            # metric_cell for the log, the 5th cell for the active ledger.
            verdict_cell = metric_cell if is_log else evidence_or_status_cell
            if not change_cell or not verdict_cell:
                skipped += 1
                continue
            # The two files do NOT share a positional layout:
            #   active: | Date | Change | Area | Metric  | Status   |
            #   log:    | Date | Change | Area | Verdict | Evidence |
            # So for the log the verdict sits in the 4th cell and free-text
            # evidence in the 5th. Reading the 5th as status (the pre-GUA-137
            # behaviour) fed evidence prose into _status_key, which is what
            # produced 40+ "statuses" like `0`, `R3` and `.venv\` and hid 43
            # already-closed verdicts one column over.
            if is_log:
                effective_status = metric_cell
                effective_metric = evidence_or_status_cell.strip("`") or "—"
            else:
                effective_status = evidence_or_status_cell
                effective_metric = metric_cell.strip("`") or "—"
            experiments.append(
                Experiment(
                    name=change_cell,
                    metric=effective_metric,
                    status=effective_status,
                    date=date_cell,
                )
            )

    if not ledger_path.exists():
        log.warning("dashboard.ledger_missing", path=str(ledger_path))
        return []

    try:
        _parse_5col_table(ledger_path.read_text(encoding="utf-8", errors="replace"), is_log=False)
    except Exception as exc:
        log.warning("dashboard.ledger_parse_error", path=str(ledger_path), error=str(exc))

    if log_path and log_path.exists():
        try:
            _parse_5col_table(log_path.read_text(encoding="utf-8", errors="replace"), is_log=True)
        except Exception as exc:
            log.warning("dashboard.ledger_log_parse_error", path=str(log_path), error=str(exc))

    if skipped:
        log.warning("dashboard.ledger_rows_skipped", skipped=skipped)

    # Dedup by (date, name) keeping last occurrence (log entries supersede earlier active rows).
    seen: dict[tuple[str, str], int] = {}
    for i, exp in enumerate(experiments):
        seen[(exp.date, exp.name)] = i
    return [experiments[i] for i in sorted(seen.values())]


def _status_key(status: str) -> str:
    """Normalise a ledger status/verdict cell to a comparable vocabulary key.

    Lowercased and stripped of markdown emphasis and trailing punctuation, so
    `**VERIFIED**`, `Confirmed present at ...` and `verified` all collapse to
    `verified`/`confirmed`. Every downstream lookup (_STATUS_ORDER, _BADGE,
    _STATUS_CLASS, _verdict_of) is keyed lowercase; before GUA-137 this returned
    the raw first token, so capitalised cells silently missed every one of them.
    """
    parts = status.split()
    if not parts:
        return ""
    return parts[0].strip("*`_,.:;()[]").lower()


# Closed verdict vocabulary (GUA-137). RESOLVED_* are the terminal states that
# count toward the graduation rate; OPEN_STATUSES are live experiments awaiting a
# verdict, and EXCLUDED_STATUSES are rows retired without ever being tested, which
# are neither a pass nor a failure and so leave the ratio entirely.
# `partial-verified` and `fixed-pending-commit` are deliberate ledger verdicts whose
# rows say "Graduating" in their own evidence — they are graduations with a caveat,
# not open experiments, so they count as confirmed rather than diluting the backlog.
CONFIRMED_STATUSES = frozenset(
    {"confirmed", "verified", "partial-verified", "fixed-pending-commit"}
)
FAILED_STATUSES = frozenset({"failed"})
INCONCLUSIVE_STATUSES = frozenset({"inconclusive"})
OPEN_STATUSES = frozenset({"hypothesis", "trending", "applied", "fixed"})
EXCLUDED_STATUSES = frozenset({"superseded", "dropped", "duplicate"})
RESOLVED_STATUSES = CONFIRMED_STATUSES | FAILED_STATUSES | INCONCLUSIVE_STATUSES


@dataclass(frozen=True)
class GraduationRate:
    """Graduation rate over *resolved* experiments, plus the open backlog.

    Denominator is `resolved` (confirmed + failed + inconclusive), not the whole
    ledger: an untested hypothesis has not failed, it simply has not been scored,
    and diluting the ratio with a growing pile of them makes a healthy loop look
    broken. `open_count` is therefore reported alongside rather than folded in —
    it is the retro signal ("we are accruing hypotheses faster than we test
    them"), which is a different question from "does what we test hold up".

    `unknown` counts rows whose status matched no known vocabulary term; a
    non-zero value means the ledger drifted and the vocabulary needs extending,
    so it is surfaced rather than silently bucketed.
    """

    confirmed: int = 0
    failed: int = 0
    inconclusive: int = 0
    open_count: int = 0
    excluded: int = 0
    unknown: int = 0
    unknown_samples: tuple[str, ...] = ()

    @property
    def resolved(self) -> int:
        """Experiments with a terminal verdict — the graduation-rate denominator."""
        return self.confirmed + self.failed + self.inconclusive

    @property
    def rate_pct(self) -> float | None:
        """Percent of resolved experiments that graduated. None when nothing resolved."""
        if not self.resolved:
            return None
        return self.confirmed / self.resolved * 100

    @property
    def total(self) -> int:
        return self.resolved + self.open_count + self.excluded + self.unknown


def _grad_rate_text(grad: GraduationRate) -> str:
    """Human-readable graduation rate, explicit about the resolved denominator."""
    if grad.rate_pct is None:
        return "no resolved experiments yet"
    return f"{grad.rate_pct:.0f}% graduation rate ({grad.confirmed}/{grad.resolved} resolved)"


def compute_graduation(experiments: list[Experiment]) -> GraduationRate:
    """Tally ledger rows into the closed verdict vocabulary (GUA-137)."""
    confirmed = failed = inconclusive = open_count = excluded = unknown = 0
    unknown_samples: list[str] = []
    for exp in experiments:
        key = _status_key(exp.status)
        if key in CONFIRMED_STATUSES:
            confirmed += 1
        elif key in FAILED_STATUSES:
            failed += 1
        elif key in INCONCLUSIVE_STATUSES:
            inconclusive += 1
        elif key in OPEN_STATUSES:
            open_count += 1
        elif key in EXCLUDED_STATUSES:
            excluded += 1
        else:
            unknown += 1
            if len(unknown_samples) < 5 and key:
                unknown_samples.append(key)
    if unknown:
        log.warning(
            "dashboard.ledger_unknown_status",
            count=unknown,
            samples=unknown_samples,
        )
    return GraduationRate(
        confirmed=confirmed,
        failed=failed,
        inconclusive=inconclusive,
        open_count=open_count,
        excluded=excluded,
        unknown=unknown,
        unknown_samples=tuple(unknown_samples),
    )


# ---------------------------------------------------------------------------
# Regime-band annotations (LIB-59) — bind ledger experiments to friction charts
# ---------------------------------------------------------------------------
#
# MVP scope: exactly one verified mapping. The ledger's ~32 experiments span
# four metric types (absence/presence/ratio/count-drop); most name process or
# git/GitHub events the factstore cannot observe as a chart timeseries at all
# (see verdicts.py module docstring). Building a general mapping engine for
# rows that have nothing to point at is out of scope — this is a closed
# registry, extended only when a new ledger signal has a real chart to land
# on. Keyed by the ledger signal slug (the text after `<type>:`, e.g.
# "execution-sessions-with-skills"), not the raw metric cell, so ledger
# comparator/threshold prose can vary without breaking the mapping.
LEDGER_METRIC_MAPPING: dict[str, str] = {
    "execution-sessions-with-skills": "execution_skill_compliance_pct",
}


def _experiment_signals(experiment: Experiment) -> list[str]:
    """Signal slugs named by an experiment's ledger metric cell (0, 1, or many)."""
    return [clause.signal.strip().lower() for clause in parse_metric(experiment.metric)]


def warn_unmapped_experiments(experiments: list[Experiment]) -> list[str]:
    """Build-time check: which parsed experiments have no annotation mapping.

    Returns the list of unmapped signal slugs (deduplicated, order preserved)
    and logs one WARNING per slug so a newly added ledger experiment surfaces
    instead of silently never appearing as an annotation. This is a warning,
    not a failure — most ledger rows (absence/presence meta-signals) are
    legitimately unchartable, so an unmapped signal is expected, not broken.
    """
    seen: dict[str, None] = {}
    for exp in experiments:
        for signal in _experiment_signals(exp):
            if signal and signal not in LEDGER_METRIC_MAPPING:
                seen.setdefault(signal, None)
    for signal in seen:
        log.warning("dashboard.ledger_signal_unmapped", signal=signal)
    return list(seen)


def _annotations_for_metric(metric: str, experiments: list[Experiment]) -> list[Experiment]:
    """Experiments whose ledger signal maps to `metric`, for annotation rendering."""
    return [
        exp
        for exp in experiments
        if any(LEDGER_METRIC_MAPPING.get(signal) == metric for signal in _experiment_signals(exp))
    ]


def parse_findings(path: Path) -> list[dict]:
    """Read review-findings JSONL, parse each line, return list of finding dicts.

    Malformed lines are skipped with a warning so a single bad write never
    breaks the dashboard render.
    """
    findings: list[dict] = []
    if not path.exists():
        return findings
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            findings.append(json.loads(line))
        except json.JSONDecodeError:
            log.warning("dashboard.findings_parse_error", line=i, path=str(path))
    return findings


# Falling is rendered in the *good* colour: friction going down is the outcome the whole
# report exists to produce, and colouring it like a warning would misread a fix as a
# problem. Flat renders nothing -- a badge on every row is a badge that says nothing.
_DIRECTION_STYLE: dict[str, str | None] = {
    DIRECTION_RISING: "--bad",
    DIRECTION_FALLING: "--good",
    DIRECTION_FLAT: None,
}


def _direction_badge(direction: str) -> str:
    """Inline trend badge for a recurrence row. Empty when flat or unrecognized."""
    color = _DIRECTION_STYLE.get(direction)
    if color is None:
        return ""
    return (
        f' <span style="font-size:10px;font-weight:600;color:var({color});'
        f"border:1px solid var({color});border-radius:3px;padding:0 4px;"
        f'vertical-align:middle">{html.escape(direction)}</span>'
    )


# Sparkline geometry: sized to sit inside a table cell without changing row
# height. Kept local rather than reusing `_svg_line`, which renders a full
# `Point` series with axes and is the wrong altitude for a cell.
_SPARK_BAR_W = 6
_SPARK_GAP = 2
_SPARK_H = 18
_SPARK_MAX_BUCKETS = 12


def _period_sparkline(period_counts: dict[str, int]) -> str:
    """Bar sparkline over the last `_SPARK_MAX_BUCKETS` periods of a signature.

    Bars are scaled to the group's own maximum, so the shape shows this
    signature's trend rather than its size relative to other signatures --
    the table's Count column already carries magnitude.
    """
    if not period_counts:
        return '<span style="color:var(--text-3);font-size:11px">—</span>'

    keys = sorted(period_counts)[-_SPARK_MAX_BUCKETS:]
    values = [period_counts[k] for k in keys]
    peak = max(values)
    width = len(keys) * (_SPARK_BAR_W + _SPARK_GAP)

    bars = "".join(
        f'<rect x="{i * (_SPARK_BAR_W + _SPARK_GAP)}" '
        f'y="{_SPARK_H - height}" width="{_SPARK_BAR_W}" height="{height}" '
        f'fill="var(--s1)"><title>{html.escape(key)}: {value}</title></rect>'
        for i, (key, value) in enumerate(zip(keys, values))
        for height in (max(1, round(_SPARK_H * value / peak)) if peak else 1,)
    )
    return (
        f'<svg width="{width}" height="{_SPARK_H}" viewBox="0 0 {width} {_SPARK_H}" '
        f'role="img" aria-label="{len(keys)} periods, peak {peak}">{bars}</svg>'
    )


def _render_review_findings(findings: list[dict] | None) -> str:
    """Render the Code Review Findings subtab section.

    Five panels: severity distribution over time, findings by source, recurring
    friction (named signature groups, GUA-100), top categories (reporter-native
    tag distribution -- kept as a separate view, not a recurrence signal), and
    per-repo finding density. Renders an empty-state placeholder when no
    findings exist yet.
    """
    if not findings:
        return (
            '<section class="chart"><h3>Code Review Findings</h3>'
            '<p class="note">No review findings yet. Run <code>/code-review</code> '
            "or <code>/workflow-review</code> to populate.</p>"
            "<p>Each run appends structured findings (akira-scan + SANYI) to "
            "<code>guacamayo/.claude/docs/review-findings.jsonl</code>. "
            "Cartographer reads this file on every <code>--facts</code> run.</p>"
            "</section>"
        )

    # Severity distribution table
    impact_order = {"blocker": 0, "important": 1, "question": 2, "suggestion": 3, "nit": 4}
    impact_counts: dict[str, int] = {}
    for f in findings:
        impact = f.get("merge_impact", "unknown")
        impact_counts[impact] = impact_counts.get(impact, 0) + 1
    impact_rows = "".join(
        f"<tr><td>{html.escape(impact)}</td><td>{count}</td></tr>"
        for impact, count in sorted(
            impact_counts.items(), key=lambda kv: impact_order.get(kv[0], 9)
        )
    )
    severity_table = (
        "<h4>By severity</h4>"
        '<div class="table-view"><table>'
        "<thead><tr><th>Severity</th><th>Count</th></tr></thead>"
        f"<tbody>{impact_rows}</tbody></table></div>"
    )

    # Source breakdown (akira-scan vs SANYI vs other)
    source_counts: dict[str, int] = {}
    for f in findings:
        src = f.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1
    source_rows = "".join(
        f"<tr><td>{html.escape(src)}</td><td>{count}</td></tr>"
        for src, count in sorted(source_counts.items(), key=lambda kv: -kv[1])
    )
    source_table = (
        "<h4>By source</h4>"
        '<div class="table-view"><table>'
        "<thead><tr><th>Source</th><th>Count</th></tr></thead>"
        f"<tbody>{source_rows}</tbody></table></div>"
    )

    # Recurring friction (GUA-100) -- named signature groups, not the reporter-
    # native category tag below. See telemetry/recurrence.py for the grouping
    # rationale (multi-match "all matches", unmatched -> category/repo fallback).
    # A group reaches this table if it is promotable (lifetime count) OR trending
    # (rising or falling) -- the `or` lives here at the call site, not inside
    # RecurrenceGroup, so the two signals stay separately inspectable (GUA-104b
    # Open Question 3). compute_recurrence already sorts rising groups first.
    # Falling groups are included deliberately (GUA-109): a friction that is being
    # fixed is reportable evidence, and dropping it would make the table show only
    # bad news.
    recurrence_html = ""
    recurring_groups = [
        g for g in compute_recurrence(findings) if g.promotable or g.direction != DIRECTION_FLAT
    ]
    if recurring_groups:
        recurrence_rows = "".join(
            f"<tr><td>{html.escape(g.pattern_key)}"
            f"{_direction_badge(g.direction)}</td><td>{g.count}</td>"
            f"<td>{_period_sparkline(g.period_counts)}</td>"
            f"<td>{html.escape(', '.join(g.repos))}</td>"
            f"<td>{html.escape(g.first_seen)} → {html.escape(g.last_seen)}</td></tr>"
            for g in recurring_groups
        )
        recurrence_html = (
            "<h4>Recurring friction</h4>"
            '<p class="note">A <span style="color:var(--bad);font-weight:600">rising</span> '
            "badge means the most recent complete week exceeded 1.5&times; the mean of the "
            "three weeks before it; "
            '<span style="color:var(--good);font-weight:600">falling</span> means it dropped '
            "below that mean by the same factor, from a base of at least three. Partial "
            "trailing weeks are excluded and unbadged rows are flat. Rising groups sort "
            "first &mdash; a pattern getting worse is more actionable than one that has "
            "been bad for a long time. Weeks are keyed on each finding's occurrence date "
            "(when the code was last touched), not on the day its review ran.</p>"
            '<div class="table-view"><table>'
            "<thead><tr><th>Pattern</th><th>Count</th><th>By week</th><th>Repos</th>"
            "<th>First → last seen</th></tr></thead>"
            f"<tbody>{recurrence_rows}</tbody></table></div>"
        )

    # Top recurring categories
    category_counts: dict[str, int] = {}
    for f in findings:
        cat = f.get("category")
        if cat:
            category_counts[cat] = category_counts.get(cat, 0) + 1
    category_html = ""
    if category_counts:
        cat_rows = "".join(
            f"<tr><td>{html.escape(cat)}</td><td>{count}</td></tr>"
            for cat, count in sorted(category_counts.items(), key=lambda kv: -kv[1])[:10]
        )
        category_html = (
            "<h4>Top categories</h4>"
            '<div class="table-view"><table>'
            "<thead><tr><th>Category</th><th>Count</th></tr></thead>"
            f"<tbody>{cat_rows}</tbody></table></div>"
        )

    # Per-repo finding density
    repo_counts: dict[str, int] = {}
    for f in findings:
        repo = f.get("repo", "unknown")
        repo_counts[repo] = repo_counts.get(repo, 0) + 1
    repo_rows = "".join(
        f"<tr><td>{html.escape(repo)}</td><td>{count}</td></tr>"
        for repo, count in sorted(repo_counts.items(), key=lambda kv: -kv[1])
    )
    repo_table = (
        "<h4>By repo</h4>"
        '<div class="table-view"><table>'
        "<thead><tr><th>Repo</th><th>Findings</th></tr></thead>"
        f"<tbody>{repo_rows}</tbody></table></div>"
    )

    total = len(findings)
    blockers = sum(1 for f in findings if f.get("merge_impact") == "blocker")
    return (
        f'<section class="chart"><h3>Code Review Findings</h3>'
        f'<p class="note">{total} findings total, {blockers} blockers. '
        f"Source: akira-scan + SANYI, persisted per review run.</p>"
        f"{severity_table}{source_table}{recurrence_html}{category_html}{repo_table}"
        f"</section>"
    )


# ---------------------------------------------------------------------------
# Marker-owned region helpers (canonical guacamayo dashboard patching)
#
# Every auto-refreshed card in context-dashboard.html is bounded by a pair of
# HTML comments:
#   <!-- REGION-NAME:START (regenerated by cartographer --facts; do not hand-edit) -->
#   ... rendered content ...
#   <!-- REGION-NAME:END -->
#
# _patch_marker_region is the shared swap logic.  Each card has its own pair of
# marker constants and a thin patch_* wrapper so callers stay readable.
# ---------------------------------------------------------------------------


def _patch_marker_region(dashboard: Path, start_marker: str, end_marker: str, content: str) -> bool:
    """Replace the content between start/end markers with `content`, in place.

    Returns False (without writing) when the file or either marker is absent.
    The start comment itself is preserved verbatim; only the region body changes.
    """
    if not dashboard.exists():
        log.warning("dashboard.patch_missing_file", path=str(dashboard), marker=start_marker)
        return False
    text = dashboard.read_text(encoding="utf-8")
    start = text.find(start_marker)
    open_end = text.find("-->", start) if start != -1 else -1
    end = text.find(end_marker, open_end + 3) if open_end != -1 else -1
    if end == -1:
        log.warning(
            "dashboard.patch_missing_markers",
            path=str(dashboard),
            start=start_marker,
            end=end_marker,
        )
        return False
    patched = text[: open_end + 3] + "\n    " + content + "\n    " + text[end:]
    dashboard.write_text(patched, encoding="utf-8")
    return True


REVIEW_CARD_START = "<!-- REVIEW-FINDINGS:START"
REVIEW_CARD_END = "<!-- REVIEW-FINDINGS:END -->"

# ---------------------------------------------------------------------------
# Additional marker-owned regions (Step 4-9 cards)
# ---------------------------------------------------------------------------

INPUT_TOKENS_CARD_START = "<!-- INPUT-TOKENS:START"
INPUT_TOKENS_CARD_END = "<!-- INPUT-TOKENS:END -->"

SKILL_ECONOMICS_CARD_START = "<!-- SKILL-ECONOMICS:START"
SKILL_ECONOMICS_CARD_END = "<!-- SKILL-ECONOMICS:END -->"

TOOL_TRENDS_CARD_START = "<!-- TOOL-TRENDS:START"
TOOL_TRENDS_CARD_END = "<!-- TOOL-TRENDS:END -->"

FRICTION_REGROUP_CARD_START = "<!-- FRICTION-REGROUP:START"
FRICTION_REGROUP_CARD_END = "<!-- FRICTION-REGROUP:END -->"

FAILURE_KINDS_CARD_START = "<!-- FAILURE-KINDS:START"
FAILURE_KINDS_CARD_END = "<!-- FAILURE-KINDS:END -->"

# Display groups for the failure-kind card. The categories are the canonical
# ones from factstore.classify_error_kind -- this table only supplies the
# labelling, so the card can never disagree with the errors_code/env/tool/
# unknown series on Loop Health.
_FAILURE_KIND_GROUPS: tuple[tuple[str, str, str, str], ...] = (
    (
        "Code-side",
        "The call was wrong. Lower is better.",
        "var(--bad)",
        ERROR_CATEGORY_CODE,
    ),
    (
        "Harness-side",
        "A guard or the user stopped it. Working as designed.",
        "var(--good)",
        ERROR_CATEGORY_TOOL,
    ),
    (
        "Environment",
        "Reality pushed back. Not usually actionable.",
        "var(--text-2)",
        ERROR_CATEGORY_ENV,
    ),
    (
        "Unclassified",
        "No category yet — widen the lookup table.",
        "var(--warn)",
        ERROR_CATEGORY_UNKNOWN,
    ),
)

EXPERIMENTS_CARD_START = "<!-- EXPERIMENTS-LIFECYCLE:START"
EXPERIMENTS_CARD_END = "<!-- EXPERIMENTS-LIFECYCLE:END -->"

HOOK_ACTIVITY_CARD_START = "<!-- HOOK-ACTIVITY:START"
HOOK_ACTIVITY_CARD_END = "<!-- HOOK-ACTIVITY:END -->"

_SEVERITY_ORDER = {"blocker": 0, "important": 1, "question": 2, "suggestion": 3, "nit": 4}
_SEVERITY_COLOR = {"blocker": "var(--bad)", "important": "var(--warn)", "nit": "var(--text-3)"}
_REVIEW_ROW_CAP = 20


def _sev_style(sev: str) -> str:
    color = _SEVERITY_COLOR.get(sev)
    return f' style="color:{color}"' if color else ""


def _review_row(f: dict) -> str:
    where = f"{f.get('repo', '?')} {f.get('issue', '')}".strip()
    title = html.escape(f.get("title", "?"))
    file, line = f.get("file", ""), f.get("line", 0)
    if file and file != "n/a":
        loc = html.escape(file.rsplit("/", 1)[-1] + (f":{line}" if line else ""))
        title += f' <span style="color:var(--text-3)">({loc})</span>'
    sev = f.get("severity", "unknown")
    return (
        f"<tr><td>{html.escape(where)}</td><td>{title}</td>"
        f"<td>{html.escape(f.get('category', ''))}</td>"
        f"<td{_sev_style(sev)}>{html.escape(sev)}</td></tr>"
    )


def render_review_card(findings: list[dict]) -> str:
    """Render the review-findings card for the canonical guacamayo dashboard.

    Targets context-dashboard.html's hand-maintained idiom (card / card-note /
    stat-row / repo-table), unlike ``_render_review_findings`` which renders this
    repo's aggregate-dashboard chart idiom. Keyed to the review-findings.jsonl
    schema: date, repo, issue, file, line, category, severity, title.

    Step 8: findings are grouped by repo, time-descending within each repo.
    Severity is a sort key within each repo group (not the primary grouping).
    The `source` field is consumed when present (F8 full-schema rows) and
    degraded gracefully for older rows without it.
    """
    if not findings:
        return (
            '<div class="card">\n'
            '      <div class="card-title">Review findings</div>\n'
            '      <p class="card-note">No review findings yet. Run <code>/code-review</code> '
            "or <code>/workflow-review</code> to populate.</p>\n"
            "    </div>"
        )

    sev_counts: dict[str, int] = {}
    for f in findings:
        sev = f.get("severity", "unknown")
        sev_counts[sev] = sev_counts.get(sev, 0) + 1
    stats = "".join(
        f'<div class="stat"><span class="value"{_sev_style(sev)}>{count}</span>'
        f'<span class="label">{html.escape(sev)}</span></div>'
        for sev, count in sorted(sev_counts.items(), key=lambda kv: _SEVERITY_ORDER.get(kv[0], 9))
    )

    # Step 8: group by repo, sort repos by most-recent finding date descending,
    # then within each repo sort by (severity, date descending).
    by_repo: dict[str, list[dict]] = {}
    for f in findings:
        by_repo.setdefault(f.get("repo", "unknown"), []).append(f)
    repo_order = sorted(
        by_repo,
        key=lambda r: max((f.get("date", "") for f in by_repo[r]), default=""),
        reverse=True,
    )

    rows_rendered = 0
    repo_sections = []
    for repo in repo_order:
        repo_findings = sorted(
            by_repo[repo],
            key=lambda f: (
                _SEVERITY_ORDER.get(f.get("severity", ""), 9),
                -(f.get("date") or "").__len__(),
            ),
        )
        # Sort time-descending within same severity
        repo_findings = sorted(
            by_repo[repo],
            key=lambda f: (_SEVERITY_ORDER.get(f.get("severity", ""), 9), f.get("date", "")),
        )
        repo_rows = ""
        for f in repo_findings:
            if rows_rendered >= _REVIEW_ROW_CAP:
                break
            repo_rows += _review_row(f)
            rows_rendered += 1
        if repo_rows:
            source_tag = ""
            # Consume `source` field (F8) when present on any finding in this repo
            sources = {f.get("source") for f in repo_findings if f.get("source")}
            if sources:
                source_tag = (
                    f' <span style="font-size:10px;color:var(--text-3)">'
                    f"[{html.escape(', '.join(sorted(sources)))}]</span>"
                )
            repo_sections.append(
                f'<tr><td colspan="4" style="padding-top:10px;font-weight:600;'
                f'font-size:12px;color:var(--text-secondary)">'
                f"{html.escape(repo)}{source_tag}</td></tr>"
                f"{repo_rows}"
            )

    dates = sorted(f.get("date", "") for f in findings if f.get("date"))
    latest = dates[-1] if dates else "?"
    targets = {(f.get("repo", "?"), f.get("issue", "?")) for f in findings}
    note = (
        f"{len(findings)} findings across {len(targets)} review targets, "
        f"{len(by_repo)} repos. Latest run: {html.escape(latest)}."
    )

    cap_note = ""
    if len(findings) > _REVIEW_ROW_CAP:
        cap_note = (
            '\n      <p style="font-size:11px;color:var(--text-3);margin-top:8px;font-style:italic">'
            f"Showing {_REVIEW_ROW_CAP} of {len(findings)} by severity; "
            "full list in review-findings.jsonl.</p>"
        )

    return (
        '<div class="card">\n'
        '      <div class="card-title">Review findings</div>\n'
        f'      <p class="card-note">{note}</p>\n'
        f'      <div class="stat-row" style="margin-bottom:16px">{stats}</div>\n'
        '      <div class="overflow-x">\n'
        '      <table class="repo-table">\n'
        "        <thead><tr><th>Repo / issue</th><th>Finding</th><th>Category</th><th>Severity</th></tr></thead>\n"
        f"        <tbody>{''.join(repo_sections)}</tbody>\n"
        "      </table>\n"
        f"      </div>{cap_note}\n"
        "    </div>"
    )


def patch_review_findings(dashboard: Path, findings: list[dict]) -> bool:
    """Regenerate the review card between REVIEW-FINDINGS markers, in place.

    The canonical dashboard is hand-maintained; only the marked region is
    cartographer-owned. Returns False without writing when the file or either
    marker is missing, so a moved marker never silently truncates the page.
    """
    if not dashboard.exists():
        log.warning("dashboard.review_patch_missing_file", path=str(dashboard))
        return False
    text = dashboard.read_text(encoding="utf-8")
    start = text.find(REVIEW_CARD_START)
    open_end = text.find("-->", start) if start != -1 else -1
    end = text.find(REVIEW_CARD_END, open_end + 3) if open_end != -1 else -1
    if end == -1:
        log.warning("dashboard.review_patch_missing_markers", path=str(dashboard))
        return False
    patched = text[: open_end + 3] + "\n    " + render_review_card(findings) + "\n    " + text[end:]
    dashboard.write_text(patched, encoding="utf-8")
    return True


def render_input_tokens_card(store: Path) -> str:
    """Render the input-tokens card for the canonical guacamayo dashboard.

    Two metrics: p50 per-session and daily total. Shows how much context is
    being carried in and how that tracks with cost. July-forward only.
    """
    series_p50 = build_series("input_tokens_p50", store)
    series_sum = build_series("input_tokens_sum", store)
    if not series_p50.points and not series_sum.points:
        return (
            '<div class="card">\n'
            '      <div class="card-title">Input tokens</div>\n'
            '      <p class="card-note">No data yet. July-forward only.</p>\n'
            "    </div>"
        )
    latest_p50 = series_p50.points[-1].value if series_p50.points else 0
    latest_sum = series_sum.points[-1].value if series_sum.points else 0
    svg_p50 = _svg_line(series_p50.points, "var(--s1)", unit="tokens") if series_p50.points else ""
    svg_sum = _svg_line(series_sum.points, "var(--s2)", unit="tokens") if series_sum.points else ""
    return (
        '<div class="card">\n'
        '      <div class="card-title">Input tokens</div>\n'
        '      <p class="card-note">How much context is carried into each session. '
        "p50 = median per session; daily total tracks with daily cost. "
        '<span class="direction good">&darr; Lower input volume = cheaper sessions.</span></p>\n'
        '      <div class="card-row">\n'
        '        <div class="card">\n'
        '          <div class="card-title">Input tokens per session (p50)</div>\n'
        '          <div class="stat-row">'
        f'<div class="stat"><span class="value">{_fmt_value(latest_p50, "tokens")}</span>'
        '<span class="label">p50 today</span></div></div>\n'
        f"          {svg_p50}\n"
        "        </div>\n"
        '        <div class="card">\n'
        '          <div class="card-title">Input tokens total (daily)</div>\n'
        '          <div class="stat-row">'
        f'<div class="stat"><span class="value">{_fmt_value(latest_sum, "tokens")}</span>'
        '<span class="label">today</span></div></div>\n'
        f"          {svg_sum}\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>"
    )


def patch_input_tokens_card(dashboard: Path, store: Path) -> bool:
    """Regenerate the input-tokens card between INPUT-TOKENS markers, in place."""
    return _patch_marker_region(
        dashboard, INPUT_TOKENS_CARD_START, INPUT_TOKENS_CARD_END, render_input_tokens_card(store)
    )


_AGENT_TYPES = frozenset(
    {
        "general-purpose",
        "Explore",
        "Plan",
        "correctness",
        "intent",
        "architecture",
        "safety",
        "testing",
        "silent-failure",
        "performance",
        "wander",
        "runtime",
        "safeguards",
        "leakage",
        "contracts",
        "plan-research-scout",
        "agent-creator",
        "claude-code-guide",
        "akira-scan",
        "akira-wander",
        "fog-advisor",
        "review",
    }
)

_SKILL_REPO: dict[str, str] = {
    "meta-wake": "guacamayo",
    "meta-grow": "guacamayo",
    "meta-dream": "guacamayo",
    "meta-insights": "guacamayo",
    "meta-retro": "guacamayo",
    "workflow-research": "guacamayo",
    "workflow-plan": "guacamayo",
    "workflow-refine": "guacamayo",
    "workflow-execute": "guacamayo",
    "workflow-review": "guacamayo",
    "code-review": "global",
    "code-debug": "global",
    "code-refactor": "global",
    "docs-check": "guacamayo",
    "new-agent": "guacamayo",
    "skill-creator": "guacamayo",
    "proto-refine": "galactus",
    "proto-plan": "galactus",
    "proto-execute": "galactus",
    "interview-drill": "sisyphus",
}

# Pre-rename aliases. The meta-* family was invoked bare (/wake, /grow) before the
# 2026-07-18 v3 consolidation; the trend lines are continuous across the rename, so
# the old name folds into the new one rather than splitting the series.
_SKILL_ALIASES: dict[str, str] = {
    "wake": "meta-wake",
    "grow": "meta-grow",
    "dream": "meta-dream",
    "retro": "meta-retro",
    "insights": "meta-insights",
    "workflow-retro": "meta-retro",
    "workflow-insights": "meta-insights",
}

# Domain groups by name prefix. Order is display order. Proto (galactus) was
# dropped 2026-08-19 — its single skill has n=1 and so no trend line to plot.
_SKILL_DOMAINS: tuple[tuple[str, str, str], ...] = (
    ("workflow-", "Workflow", "guacamayo"),
    ("meta-", "Meta", "guacamayo"),
)


def _canonical_skill(name: str) -> str:
    """Map a pre-rename skill name onto its current name."""
    return _SKILL_ALIASES.get(name, name)


def _skill_domain(name: str) -> str | None:
    """Return the domain label for a skill name, or None if it belongs to Other."""
    for prefix, label, _repo in _SKILL_DOMAINS:
        if name.startswith(prefix):
            return label
    return None


def _merge_skill_aliases(
    items: dict[str, dict[str, float]],
) -> dict[str, dict[str, float]]:
    """Fold pre-rename names into their current name, summing cost and count."""
    merged: dict[str, dict[str, float]] = {}
    for name, stats in items.items():
        entry = merged.setdefault(_canonical_skill(name), {"cost": 0.0, "n": 0})
        entry["cost"] += stats["cost"]
        entry["n"] += stats["n"]
    return dict(sorted(merged.items(), key=lambda kv: -kv[1]["cost"]))


def _merge_daily_aliases(daily: dict[str, list[Point]]) -> dict[str, list[Point]]:
    """Concatenate the daily series of aliased names under the current name.

    Same-day points from two names are averaged, matching build_skill_daily's
    mean-cost-per-invocation semantics.
    """
    by_name: dict[str, dict[str, list[Point]]] = {}
    for name, points in daily.items():
        target = by_name.setdefault(_canonical_skill(name), {})
        for point in points:
            target.setdefault(point.date, []).append(point)

    merged: dict[str, list[Point]] = {}
    for name, by_date in by_name.items():
        merged[name] = [
            points[0]
            if len(points) == 1
            else Point(
                date=date,
                value=sum(p.value * p.n for p in points) / max(sum(p.n for p in points), 1),
                regime="",
                n=sum(p.n for p in points),
            )
            for date, points in sorted(by_date.items())
        ]
    return merged


def _skill_table(
    items: dict[str, dict[str, float]],
    grand: float,
    daily: dict[str, list[Point]],
    show_repo: bool = False,
) -> str:
    """Render a skill/agent economics table with optional repo column."""
    header = (
        "<th>Name</th><th>Repo</th><th>Cost</th><th>Share</th><th>Sessions</th><th>7d</th>"
        if show_repo
        else "<th>Name</th><th>Cost</th><th>Share</th><th>Sessions</th><th>7d</th>"
    )
    rows = ""
    for name, stats in items.items():
        repo_col = (
            f'<td style="color:var(--text-3);font-size:11px">{html.escape(_SKILL_REPO.get(name, ""))}</td>'
            if show_repo
            else ""
        )
        rows += (
            f"<tr><td><code>{html.escape(name)}</code></td>"
            f"{repo_col}"
            f"<td>{stats['cost'] / 1_000_000:,.1f}M</td>"
            f"<td>{stats['cost'] / grand * 100:.0f}%</td>"
            f"<td>{int(stats['n'])}</td>"
            f'<td class="trend-cell">{_sparkline_svg(daily.get(name, [])[-7:], unit="cost")}</td>'
            "</tr>"
        )
    return (
        '<div class="table-view">'
        f"<table><thead><tr>{header}</tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def _skill_economics_tables(store: Path, since: str | None) -> str:
    """The skill/agent economics tables for one window, or an empty-state note."""
    totals = build_skill_economics(store, since=since)
    if not totals:
        return '<p class="empty">No skill cost data in this window.</p>'
    grand = sum(e["cost"] for e in totals.values()) or 1.0
    daily = build_skill_daily(store)

    skills = _merge_skill_aliases({k: v for k, v in totals.items() if k not in _AGENT_TYPES})
    agents = {k: v for k, v in totals.items() if k in _AGENT_TYPES}
    daily = _merge_daily_aliases(daily)

    agent_cost = sum(s["cost"] for s in agents.values())

    parts = []

    # Only domains with a real trend line are shown. Proto (one skill, n=1) and the
    # Other catch-all were dropped 2026-08-19: every row in them is "no trend (n=1)",
    # so the sparkline column was empty and the tables carried no signal.
    grouped: dict[str, dict[str, dict[str, float]]] = {
        label: {} for _prefix, label, _repo in _SKILL_DOMAINS
    }
    for name, stats in skills.items():
        domain = _skill_domain(name)
        if domain in grouped:
            grouped[domain][name] = stats

    for _prefix, label, repo in _SKILL_DOMAINS:
        items = grouped[label]
        if not items:
            continue
        cost = sum(s["cost"] for s in items.values())
        parts.append(
            f'<h4 style="font-size:13px;font-weight:600;margin:16px 0 8px">'
            f"{label} "
            f'<span style="font-weight:400;color:var(--text-3);font-size:12px">'
            f"{html.escape(repo)} \u00b7 {_fmt_value(cost, 'cost')} "
            f"\u00b7 {cost / grand * 100:.0f}% of spend"
            f"</span></h4>" + _skill_table(items, grand, daily)
        )

    if agents:
        parts.append(
            f'<h4 style="font-size:13px;font-weight:600;margin:20px 0 8px">'
            f"Agents "
            f'<span style="font-weight:400;color:var(--text-3);font-size:12px">'
            f"{_fmt_value(agent_cost, 'cost')} \u00b7 {agent_cost / grand * 100:.0f}% of spend"
            f"</span></h4>" + _skill_table(agents, grand, daily)
        )

    return "\n".join(parts)


def render_skill_economics_card(store: Path) -> str:
    """Skill economics, windowed 7d/30d/90d/all like the KPI regions.

    Every window is rendered server-side and toggled client-side, so switching
    never re-reads the store. The 7d sparkline column is deliberately NOT
    windowed — it is a fixed-length recency trend, and rescaling it per window
    would make the same skill's trend mean four different things.
    """
    all_rows = _work_sessions(read_all(store))
    if not all_rows:
        return (
            '<div class="card">\n'
            '      <div class="card-title">Skill &amp; agent economics</div>\n'
            '      <p class="card-note">No cost data yet (July+ sessions only).</p>\n'
            "    </div>"
        )

    newest = max(str(r["date"]) for r in all_rows)
    panels, buttons = [], []
    for key, label, days in INSIGHTS_WINDOWS:
        cutoff = (_date.fromisoformat(newest) - timedelta(days=days)).isoformat() if days else None
        is_default = key == _INSIGHTS_DEFAULT_WINDOW
        buttons.append(
            f'<button type="button" class="win-btn{" active" if is_default else ""}" '
            f'data-win="{key}">{label}</button>'
        )
        hidden = "" if is_default else ' style="display:none"'
        panels.append(
            f'<div class="win-panel" data-win="{key}"{hidden}>'
            f"{_skill_economics_tables(store, cutoff)}</div>"
        )

    return (
        '<div class="card">\n'
        '      <div class="card-title">Skill &amp; agent economics</div>\n'
        '      <p class="card-note">Cost attributed from JSONL output between '
        "a slash invocation and the next human turn. Work sessions only; July-forward. "
        "Share is of spend within the selected window; the 7d column is a fixed "
        "recency trend and does not rewindow.</p>\n"
        '      <div class="win-toggle" role="group" aria-label="Time window">'
        f"{''.join(buttons)}</div>\n" + "".join(panels) + "\n    </div>"
    )


def patch_skill_economics_card(dashboard: Path, store: Path) -> bool:
    """Regenerate the skill economics card between SKILL-ECONOMICS markers, in place."""
    return _patch_marker_region(
        dashboard,
        SKILL_ECONOMICS_CARD_START,
        SKILL_ECONOMICS_CARD_END,
        render_skill_economics_card(store),
    )


def render_tool_trends_card(store: Path) -> str:
    """Render the tool-trends card for the canonical guacamayo dashboard."""
    ordered, series = build_tool_trends(store)
    if not series:
        return (
            '<div class="card">\n'
            '      <div class="card-title">Tool call trends</div>\n'
            '      <p class="card-note">No tool-count data yet. July-forward only.</p>\n'
            "    </div>"
        )
    # Ranked bars, not sparklines. Six daily lines answered "is Bash drifting?" — a
    # question the flat volume already answers better — while burying the comparison
    # that actually reads at a glance: Bash dwarfs everything else. Totals, ranked.
    colors = [
        "var(--ac-rose)",
        "var(--ac-violet)",
        "var(--ac-teal)",
        "var(--ac-blue)",
        "var(--ac-orange)",
        "var(--text-3)",
    ]
    totals = {tool: sum(p.value for p in series[tool]) for tool in ordered if tool in series}
    ranked = sorted(totals.items(), key=lambda kv: -kv[1])
    peak = ranked[0][1] or 1
    grand = sum(totals.values()) or 1
    bars = "".join(
        _hbar(
            tool,
            f"{count:,.0f} · {count / grand * 100:.0f}%",
            count / peak * 100,
            colors[min(i, len(colors) - 1)],
        )
        for i, (tool, count) in enumerate(ranked)
    )
    # Paired with the error breakdown: volume and failure are the same question asked
    # twice — which tools are worked hardest, and which of those calls come back wrong.
    # Both are July-forward store-wide, so the two halves share one frame.
    july_rows = [
        r for r in _work_sessions(read_all(store)) if str(r.get("date") or "") >= JULY_BOUNDARY
    ]
    return (
        '<div class="card-row">\n'
        '      <div class="card" style="flex:1">\n'
        '      <div class="card-title">Tool calls by volume</div>\n'
        '      <p class="card-note">Total calls for the top 5 tools, plus an '
        "'other' bucket. July-forward only. Bash volume is structural "
        "(28.7/session median) &mdash; track for antipattern changes, not absolute "
        "reduction.</p>\n"
        f'      <div class="hbars">{bars}</div>\n'
        f'      <p class="dist-note">{grand:,.0f} calls across {len(ranked)} buckets</p>\n'
        "      </div>\n"
        f"      {_error_breakdown_card(july_rows)}\n"
        "    </div>"
    )


def build_failure_kinds(store: Path) -> tuple[dict[str, int], int, int, int]:
    """Tally tool failures by kind, July-forward.

    `tool_errors` is keyed by failure kind (``command_failed``,
    ``read_before_write``, ...), while `tool_counts` is keyed by tool name, so
    the two cannot be joined -- there is no per-tool error rate to compute here.
    The call total is returned alongside so the card can normalise, matching the
    `tool_error_rate` metric's errors-per-100-calls framing.

    Returns (kind -> count, total_errors, total_calls, session_count).
    """
    rows = [r for r in _work_sessions(read_all(store)) if str(r.get("date") or "") >= JULY_BOUNDARY]
    kinds: dict[str, int] = {}
    calls = 0
    scored = 0
    for row in rows:
        raw = row.get("tool_errors")
        if not raw:
            continue
        try:
            parsed: dict[str, int] = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        scored += 1
        for kind, n in parsed.items():
            kinds[kind] = kinds.get(kind, 0) + int(n)
        calls += _tool_call_total(row)
    return kinds, sum(kinds.values()), calls, scored


def render_failure_kinds_card(store: Path) -> str:
    """Render the failure-kind card, grouped for comparison.

    Follows the three-column shape of the friction regroup card: each group is a
    sub-card so the buckets read side by side rather than as one long ranked
    list. The split is by *who* the failure implicates -- a guard firing is the
    system working, a malformed call is not.
    """
    kinds, total, calls, scored = build_failure_kinds(store)
    if not kinds:
        return (
            '<div class="card">\n'
            '      <div class="card-title">Tool failures by kind</div>\n'
            '      <p class="card-note">No tool-error data yet. July-forward only.</p>\n'
            "    </div>"
        )

    grouped: dict[str, dict[str, int]] = {}
    for kind, n in kinds.items():
        grouped.setdefault(classify_error_kind(kind), {})[kind] = n

    def _group(title: str, note: str, color: str, category: str) -> str:
        rows = sorted(grouped.get(category, {}).items(), key=lambda kv: -kv[1])
        subtotal = sum(n for _k, n in rows)
        share = f"{subtotal / total * 100:.0f}%" if total else "&mdash;"
        lines = (
            "".join(
                f'<div style="display:flex;justify-content:space-between;'
                f'font-size:12px;margin-bottom:4px">'
                f"<span>{html.escape(k.replace('_', ' '))}</span>"
                f'<span style="font-weight:600">{n}</span></div>'
                for k, n in rows
                if n
            )
            or '<p class="card-note">None recorded.</p>'
        )
        return (
            '<div class="card" style="flex:1">\n'
            f'          <div class="card-title">{title}</div>\n'
            f'          <p class="card-note" style="color:{color}">{note}</p>\n'
            f'          <div class="stat-row"><div class="stat">'
            f'<span class="value" style="color:{color}">{subtotal}</span>'
            f'<span class="label">{share} of failures</span></div></div>\n'
            f"          {lines}\n"
            "        </div>"
        )

    rate = f"{100 * total / calls:.2f}" if calls else "&mdash;"
    groups = "\n        ".join(
        _group(title, note, color, category)
        for title, note, color, category in _FAILURE_KIND_GROUPS
    )
    return (
        '<div class="card">\n'
        '      <div class="card-title">Tool failures by kind</div>\n'
        f'      <p class="card-note">{total} failures across {scored} sessions since '
        f"{JULY_BOUNDARY} &mdash; <strong>{rate} per 100 calls</strong>. Grouped by what "
        "the failure implicates: a guard firing is the harness working, a malformed call "
        "is not. Errors are keyed by failure kind, not by tool, so this is not a per-tool "
        "error rate.</p>\n"
        '      <div class="card-row">\n'
        f"        {groups}\n"
        "      </div>\n"
        "    </div>"
    )


def patch_failure_kinds_card(dashboard: Path, store: Path) -> bool:
    """Regenerate the failure-kinds card between FAILURE-KINDS markers, in place."""
    return _patch_marker_region(
        dashboard,
        FAILURE_KINDS_CARD_START,
        FAILURE_KINDS_CARD_END,
        render_failure_kinds_card(store),
    )


def render_failure_kinds_region(store: Path) -> str:
    """Return the injectable HTML for the FAILURE-KINDS marker region."""
    return render_failure_kinds_card(store)


def patch_tool_trends_card(dashboard: Path, store: Path) -> bool:
    """Regenerate the tool-trends card between TOOL-TRENDS markers, in place."""
    return _patch_marker_region(
        dashboard, TOOL_TRENDS_CARD_START, TOOL_TRENDS_CARD_END, render_tool_trends_card(store)
    )


def render_friction_regroup_card(store: Path) -> str:
    """Render the friction three-group regroup card for the canonical guacamayo dashboard.

    Step 9: prompt-eng / loop-eng / harness-eng grouping. Each metric becomes a
    compact inline stat with sparkline, so all three groups fit without scrolling.
    """

    def _inline_metric(metric: str, title: str, unit: str, label_hint: str) -> str:
        series = build_series(metric, store)
        if not series.points:
            return (
                f'<div style="margin-bottom:8px">'
                f'<span style="font-size:12px;font-weight:600">{html.escape(title)}</span> '
                f'<span style="color:var(--text-3);font-size:11px">no data</span></div>'
            )
        latest = series.points[-1]
        svg = _svg_line(series.points, "var(--s1)", height=60, unit=unit)
        # GUA-137: the shared 7-day component sits beside the headline number as
        # a trailing-window read. The 60px chart below it covers the full window,
        # so this is a different span of the same metric, not a second copy.
        spark = _sparkline_svg(series.points[-7:], unit=unit)
        return (
            f'<div style="margin-bottom:12px">'
            f'<div style="font-size:12px;font-weight:600;margin-bottom:2px">{html.escape(title)}</div>'
            f'<span style="font-size:18px;font-weight:600">{html.escape(_fmt_value(latest.value, unit))}</span>'
            f'<span style="color:var(--text-3);font-size:11px;margin-left:6px">{html.escape(label_hint)}</span>'
            f'<span class="trend-cell" style="margin-left:6px">{spark}</span>'
            f"{svg}</div>"
        )

    def _hint(note: str, limit: int = 40) -> str:
        if len(note) <= limit:
            return note
        cut = note[:limit].rsplit(" ", 1)[0].rstrip()
        return f"{cut}…" if cut else f"{note[:limit]}…"

    prompt_eng = "".join(
        _inline_metric(metric, title, unit, _hint(note))
        for metric, title, note, _prov, unit in _FRICTION_PROMPT_ENG
    )
    loop_eng = "".join(
        _inline_metric(metric, title, unit, _hint(note))
        for metric, title, note, _prov, unit in _FRICTION_LOOP_ENG
    )
    harness_eng = "".join(
        _inline_metric(metric, title, unit, _hint(note))
        for metric, title, note, _prov, unit in _FRICTION_HARNESS_ENG
    )
    return (
        '<div class="card">\n'
        '      <div class="card-title">Friction &amp; Quality (regrouped)</div>\n'
        '      <p class="card-note">Metrics regrouped by engineering layer: '
        "<strong>Prompt-eng</strong> (capability signals, higher = better), "
        "<strong>Loop-eng</strong> (true friction, lower = better), "
        "<strong>Harness-eng</strong> (infrastructure health).</p>\n"
        '      <div class="card-row">\n'
        '        <div class="card" style="flex:1">\n'
        '          <div class="card-title">Prompt-eng</div>\n'
        '          <p class="card-note" style="color:var(--good)">Does reasoning work? '
        "Higher is better.</p>\n"
        f"          {prompt_eng}\n"
        "        </div>\n"
        '        <div class="card" style="flex:1">\n'
        '          <div class="card-title">Loop-eng</div>\n'
        '          <p class="card-note" style="color:var(--bad)">Does workflow repeat? '
        "Lower is better.</p>\n"
        f"          {loop_eng}\n"
        f'          <p style="font-size:11px;color:var(--text-3)">Rework cycles: '
        f"Not yet captured (message-pair analysis, Tier 3).</p>\n"
        "        </div>\n"
        '        <div class="card" style="flex:1">\n'
        '          <div class="card-title">Harness-eng</div>\n'
        '          <p class="card-note">Does infrastructure hold?</p>\n'
        f"          {harness_eng}\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>"
    )


def patch_friction_regroup_card(dashboard: Path, store: Path) -> bool:
    """Regenerate the friction regroup card between FRICTION-REGROUP markers, in place."""
    return _patch_marker_region(
        dashboard,
        FRICTION_REGROUP_CARD_START,
        FRICTION_REGROUP_CARD_END,
        render_friction_regroup_card(store),
    )


def render_experiments_card(
    experiments: list[Experiment] | None,
    ledger_path: Path | None = None,
    ledger_log_path: Path | None = None,
) -> str:
    """Render the experiments lifecycle card for the canonical guacamayo dashboard.

    Reads from ledger when provided (Step 7). Falls back to the passed experiments
    list for backward compatibility. Renders verdict counts + top-10 table matching
    the hand-maintained card idiom.
    """
    if ledger_path is not None and experiments is None:
        experiments = parse_ledger(ledger_path, ledger_log_path)
    if not experiments:
        return (
            '<div class="card">\n'
            '      <div class="card-title">Experiment verdicts</div>\n'
            '      <p class="card-note">No experiments tracked. Add hypothesis rows to the '
            "tooling ledger.</p>\n"
            "    </div>"
        )
    grad = compute_graduation(experiments)
    confirmed, failed = grad.confirmed, grad.failed
    pending = grad.open_count

    _BADGE = {
        "confirmed": ("confirmed", "var(--good)"),
        "verified": ("confirmed", "var(--good)"),
        "partial-verified": ("partial", "var(--good)"),
        "fixed-pending-commit": ("fixed", "var(--good)"),
        "failed": ("failed", "var(--bad)"),
        "inconclusive": ("inconclusive", "var(--warn)"),
        "hypothesis": ("open", "var(--text-3)"),
        "trending": ("trending", "var(--text-3)"),
        "applied": ("applied", "var(--text-3)"),
        "fixed": ("fixed", "var(--text-3)"),
        "superseded": ("superseded", "var(--text-3)"),
        "dropped": ("dropped", "var(--text-3)"),
        "duplicate": ("duplicate", "var(--text-3)"),
    }

    def _badge(status: str) -> str:
        key = _status_key(status)
        label, color = _BADGE.get(key, (status[:10], "var(--text-3)"))
        return f'<span class="badge" style="color:{color}">{html.escape(label)}</span>'

    top = sorted(
        experiments,
        key=lambda e: (_STATUS_ORDER.get(_status_key(e.status), 9), e.date),
    )[:10]
    rows = "".join(
        f"<tr>"
        f'<td title="{html.escape(e.name)}">{html.escape(e.name[:50])}</td>'
        f'<td style="font-family:\'DM Mono\',monospace;font-size:11px" title="{html.escape(e.metric)}">{html.escape(e.metric[:30])}</td>'
        f"<td>{_badge(e.status)}</td>"
        f"<td>{html.escape(e.date)}</td>"
        f"</tr>"
        for e in top
    )
    cap = ""
    if len(experiments) > 10:
        cap = (
            f'\n      <p style="font-size:11px;color:var(--text-3);margin-top:8px;font-style:italic">'
            f"Showing top 10 of {len(experiments)}. Full list in tooling-ledger.md.</p>"
        )
    return (
        '<div class="card">\n'
        '      <div class="card-title">Experiment verdicts</div>\n'
        f'      <p class="card-note">{confirmed} confirmed, {failed} failed, '
        f"{grad.inconclusive} inconclusive &mdash; {_grad_rate_text(grad)}. "
        f"{pending} still open (untested hypotheses, excluded from the rate).</p>\n"
        '      <div class="stat-row" style="margin-bottom:16px">\n'
        f'        <div class="stat"><span class="value" style="color:var(--good)">{confirmed}</span>'
        '<span class="label">confirmed</span></div>\n'
        f'        <div class="stat"><span class="value" style="color:var(--bad)">{failed}</span>'
        '<span class="label">failed</span></div>\n'
        f'        <div class="stat"><span class="value" style="color:var(--text-3)">{pending}</span>'
        '<span class="label">pending</span></div>\n'
        "      </div>\n"
        '      <div class="overflow-x">\n'
        '      <table class="exp-table">\n'
        "        <thead><tr><th>Change</th><th>Metric</th><th>Status</th><th>Date</th></tr></thead>\n"
        f"        <tbody>{rows}</tbody>\n"
        f"      </table>\n"
        f"      </div>{cap}\n"
        "    </div>"
    )


def patch_experiments_card(
    dashboard: Path,
    experiments: list[Experiment] | None = None,
    ledger_path: Path | None = None,
    ledger_log_path: Path | None = None,
) -> bool:
    """Regenerate the experiments card between EXPERIMENTS-LIFECYCLE markers, in place."""
    content = render_experiments_card(experiments, ledger_path, ledger_log_path)
    return _patch_marker_region(dashboard, EXPERIMENTS_CARD_START, EXPERIMENTS_CARD_END, content)


# ---------------------------------------------------------------------------
# Hook activity (guard-hook fires from ~/.claude/hooks/lib.sh logging)
# ---------------------------------------------------------------------------
#
# Two logs, written by two different lib.sh helpers:
#   .hook-log.jsonl      -- log_event, carries exit_code (2 = block, 0 = warn)
#   .hook-pass-log.jsonl -- log_pass, no exit_code, silent OKs, capped by tail
#
# Both are written by shell `printf` with only `tr '"\\' '..'` sanitising the
# context field, so a logged multi-line command embeds real newlines and splits
# one record across several physical lines.  `strict=False` does NOT rescue those
# (it relaxes control chars *within* a string, not a string cut in half by
# splitlines), so the reader below also stitches continuation fragments back
# together before parsing.  strict=False is still passed for the raw-control-char
# case the sanitiser likewise misses (e.g. a literal tab in a command).

# Every hook that sources lib.sh -- used to report which guards have never fired.
KNOWN_HOOKS = (
    "branch_guard",
    "ci_drift_warn",
    "destructive_cmd_guard",
    "docs_drift_warn",
    "docs_hygiene",
    "function_complexity_warning",
    "issue_label_sync",
    "memory_duplication_guard",
    "memory_route_guard",
    "pip_guard",
    "review-verdict-gate",
    "risky_git_guard",
    "secrets_scan",
    "task_complete_check",
)

# Hooks wired to call log_pass; pass counts for anything else are absent, not zero.
PASS_LOGGING_HOOKS = ("risky_git_guard", "branch_guard")


def parse_hook_log(path: Path) -> list[dict]:
    """Read a hook JSONL log, tolerating records broken across physical lines.

    Records are emitted by shell printf, so an unescaped newline inside the
    `context` field splits one JSON object over several lines. Lines are
    re-joined until they parse (or the record is abandoned), and parsing uses
    strict=False so raw control characters inside strings are accepted.

    Malformed records are skipped with a warning -- one bad write never breaks
    the dashboard render. Returns [] when the file is absent.
    """
    events: list[dict] = []
    if not path.exists():
        return events
    buf = ""
    buf_start = 0
    for i, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if not buf:
            if not raw.strip():
                continue
            buf, buf_start = raw, i
        else:
            # Continuation of a record whose context field contained a newline.
            buf += "\n" + raw
        try:
            obj = json.loads(buf, strict=False)
        except json.JSONDecodeError:
            # A truncating `tail` can orphan a fragment with no opening brace;
            # give up on it rather than swallowing every following line.
            if not buf.lstrip().startswith("{"):
                log.warning("dashboard.hook_log_parse_error", line=buf_start, path=str(path))
                buf = ""
            continue
        if isinstance(obj, dict):
            events.append(obj)
        buf = ""
    if buf:
        log.warning("dashboard.hook_log_truncated_record", line=buf_start, path=str(path))
    return events


@dataclass
class HookActivity:
    """Per-hook block/warn/pass counts plus the roll-ups the card header needs."""

    rows: list[dict] = field(default_factory=list)
    blocks: int = 0
    warns: int = 0
    passes: int = 0
    seen: int = 0
    known: int = len(KNOWN_HOOKS)
    silent: list[str] = field(default_factory=list)
    since: str = ""


def build_hook_activity(event_log: Path, pass_log: Path) -> HookActivity:
    """Aggregate block/warn/pass counts per hook from the two lib.sh logs.

    Blocks are exit_code 2, warns are exit 0 with a message. Passes come from the
    separate pass log, which only a couple of hooks write and which lib.sh caps --
    so pass counts are floor values, and hooks that never call log_pass get None
    (rendered as an em dash) rather than a misleading 0.
    """
    stats: dict[str, dict[str, int]] = {}
    timestamps: list[str] = []

    for ev in parse_hook_log(event_log):
        hook = ev.get("hook")
        if not hook:
            continue
        entry = stats.setdefault(hook, {"blocks": 0, "warns": 0, "passes": 0})
        if ev.get("exit_code") == 2:
            entry["blocks"] += 1
        else:
            entry["warns"] += 1
        if ts := ev.get("ts"):
            timestamps.append(ts)

    for ev in parse_hook_log(pass_log):
        hook = ev.get("hook")
        if not hook:
            continue
        stats.setdefault(hook, {"blocks": 0, "warns": 0, "passes": 0})["passes"] += 1
        if ts := ev.get("ts"):
            timestamps.append(ts)

    rows = [
        {
            "hook": hook,
            "blocks": s["blocks"],
            "warns": s["warns"],
            # None (not 0) for hooks that never call log_pass -- absence of data.
            "passes": s["passes"] if hook in PASS_LOGGING_HOOKS else None,
        }
        for hook, s in stats.items()
    ]
    rows.sort(key=lambda r: (-r["blocks"], -r["warns"], r["hook"]))

    return HookActivity(
        rows=rows,
        blocks=sum(r["blocks"] for r in rows),
        warns=sum(r["warns"] for r in rows),
        passes=sum(s["passes"] for s in stats.values()),
        seen=len(rows),
        silent=sorted(h for h in KNOWN_HOOKS if h not in stats),
        since=min(timestamps, default="")[:10],
    )


def render_hook_activity_card(event_log: Path, pass_log: Path) -> str:
    """Render the hook-activity card for the canonical guacamayo dashboard."""
    act = build_hook_activity(event_log, pass_log)
    if not act.rows:
        return (
            '<div class="card">\n'
            '      <div class="card-title">Hook activity</div>\n'
            '      <p class="card-note">No hook fires logged yet. Guard hooks log to '
            "<code>.sounding/telemetry/.hook-log.jsonl</code> via <code>lib.sh</code>.</p>\n"
            "    </div>"
        )

    def _cell(value: int | None, color: str) -> str:
        if value is None:
            return "<td>&mdash;</td>"
        style = f' style="color:{color}"' if value else ""
        return f"<td{style}>{value}</td>"

    rows = "".join(
        f"<tr><td>{html.escape(r['hook'])}</td>"
        f"{_cell(r['blocks'], 'var(--bad)')}"
        f"{_cell(r['warns'], 'var(--warn)')}"
        f"{_cell(r['passes'], 'var(--good)')}</tr>"
        for r in act.rows
    )
    since = f" (since {act.since})" if act.since else ""
    silent = ""
    if act.silent:
        silent = (
            '\n      <p style="font-size:11px;color:var(--text-3);margin-top:8px;'
            'font-style:italic">Silent since logging began: '
            f"{html.escape(', '.join(act.silent))}. Pass-logging (log_pass) is only wired into "
            f"{html.escape(' + '.join(PASS_LOGGING_HOOKS))}, and the pass log is capped &mdash; "
            "pass counts are floor values, not totals.</p>"
        )
    return (
        '<div class="card">\n'
        f'      <div class="card-title">Hook activity{html.escape(since)}</div>\n'
        '      <p class="card-note">Guard-hook fires from <code>lib.sh</code> logging. '
        "<strong>Blocks</strong> = exit 2 (action denied), <strong>warns</strong> = exit 0 "
        "with a message, <strong>passes</strong> = silent OK (logged by opted-in hooks only).</p>\n"
        '      <div class="stat-row">\n'
        f'        <div class="stat"><span class="value" style="color:var(--bad)">{act.blocks}</span>'
        '<span class="label">blocks</span></div>\n'
        f'        <div class="stat"><span class="value" style="color:var(--warn)">{act.warns}</span>'
        '<span class="label">warns</span></div>\n'
        f'        <div class="stat"><span class="value" style="color:var(--good)">{act.passes}</span>'
        '<span class="label">passes logged</span></div>\n'
        f'        <div class="stat"><span class="value">{act.seen} / {act.known}</span>'
        '<span class="label">hooks seen firing</span></div>\n'
        "      </div>\n"
        '      <div class="overflow-x">\n'
        '      <table class="repo-table">\n'
        "        <thead><tr><th>Hook</th><th>Blocks</th><th>Warns</th><th>Passes</th></tr></thead>\n"
        f"        <tbody>{rows}</tbody>\n"
        "      </table>\n"
        f"      </div>{silent}\n"
        "    </div>"
    )


def patch_hook_activity_card(dashboard: Path, event_log: Path, pass_log: Path) -> bool:
    """Regenerate the hook-activity card between HOOK-ACTIVITY markers, in place."""
    return _patch_marker_region(
        dashboard,
        HOOK_ACTIVITY_CARD_START,
        HOOK_ACTIVITY_CARD_END,
        render_hook_activity_card(event_log, pass_log),
    )


def _experiment_trend(experiment: Experiment, store: Path | None) -> str:
    """7-day sparkline for an experiment whose ledger metric has store backing.

    Most ledger rows name absence/presence meta-signals that no series can
    chart (see `warn_unmapped_experiments`), so the common case is deliberately
    empty — an unchartable hypothesis renders no trend rather than a
    placeholder line implying data exists.
    """
    if store is None:
        return ""
    for signal in _experiment_signals(experiment):
        metric = LEDGER_METRIC_MAPPING.get(signal)
        if metric:
            return trend_7d(metric, store)
    return ""


_GRAD_ROW = re.compile(r"^\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|", re.MULTILINE)
_RETRO_HEAD = re.compile(r"^## (R\d+)\b.*$", re.MULTILINE)


def render_loop_closure_card(log_path: Path) -> str:
    """Graduation throughput from the append-only tooling-ledger archive.

    The active ledger says what is being tried; this says what actually landed.
    A verdict alone does not close the loop — graduating the row out of the
    active ledger does, so this counts the archive rather than the verdicts.
    """
    if not log_path.exists():
        return ""
    text = log_path.read_text(encoding="utf-8", errors="replace")

    verdicts: Counter[str] = Counter()
    for _date_cell, _change, _area, verdict_cell, _evidence in _GRAD_ROW.findall(text):
        word = (
            re.sub(r"[^a-z/]", "", verdict_cell.strip().lower().split()[0])
            if verdict_cell.strip()
            else ""
        )
        if not word or word.startswith(("verdict", "---")):
            continue
        if "verified" in word and "failed" in word:  # "verified/failed" rollup cell
            verdicts["rollup"] += 1
        elif word.startswith(("verified", "confirmed")):
            verdicts["verified"] += 1
        elif word.startswith("failed"):
            verdicts["failed"] += 1
        elif word.startswith("superseded"):
            verdicts["superseded"] += 1
        else:
            verdicts["inconclusive"] += 1

    graduated = sum(verdicts.values())
    if not graduated:
        return ""
    rounds = len(_RETRO_HEAD.findall(text))
    called = verdicts["verified"] + verdicts["failed"]
    hit_rate = verdicts["verified"] / called * 100 if called else 0.0

    return (
        '<div class="card"><div class="card-title">Loop closure</div>'
        '<p class="card-note">Experiments graduated out of the active ledger into '
        "<code>tooling-ledger-log.md</code>. This is the loop actually closing — a "
        "verdict is a measurement, graduation is a decision.</p>"
        f'<div class="stat-row">'
        f'<div class="stat"><span class="value">{graduated}</span>'
        f'<span class="label">graduated</span></div>'
        f'<div class="stat"><span class="value" style="color:var(--good)">'
        f'{verdicts["verified"]}</span><span class="label">verified</span></div>'
        f'<div class="stat"><span class="value" style="color:var(--bad)">'
        f'{verdicts["failed"]}</span><span class="label">failed</span></div>'
        f'<div class="stat"><span class="value">{hit_rate:.0f}%</span>'
        f'<span class="label">hit rate (of called)</span></div>'
        f'<div class="stat"><span class="value">{rounds}</span>'
        f'<span class="label">retro rounds</span></div>'
        f'<div class="stat"><span class="value">{graduated / rounds:.1f}</span>'
        f'<span class="label">per round</span></div></div>'
        '<p style="font-size:11px;color:var(--text-3);margin-top:8px;font-style:italic">'
        "A failed experiment still closes the loop — it is a question answered. "
        "Hit rate counts only verified/failed; inconclusive and superseded rows are "
        "excluded from the denominator.</p></div>"
    )


def render_proposal_sightings_card(sightings_path: Path | None = None) -> str:
    """Delegate to telemetry.sightings — kept here so dashboard.py is the one-stop render import."""
    from telemetry.sightings import render_proposal_sightings_card as _render

    return _render(sightings_path)


_VERDICT_BADGE = {
    "confirmed": "exp-confirmed",
    "trending": "exp-trending",
    "failed": "exp-failed",
    "inconclusive": "exp-pending",
    "unscored": "exp-other",
}

# A due date in a ledger status: "due 08-17" or "due 2026-09-15". The year is
# frequently omitted, so it is inferred from the experiment's own date.
_DUE_RE = re.compile(r"due\s+(?:(\d{4})-)?(\d{1,2})-(\d{1,2})", re.IGNORECASE)


def _latest_verdicts(store: Path | None) -> dict[str, dict[str, Any]]:
    """Newest verdict row per experiment name, keyed for the ledger join.

    `experiment_verdicts` is append-only — one row per experiment per insights
    run — so the current call is the row with the greatest `run_at`.
    """
    if store is None:
        return {}
    latest: dict[str, dict[str, Any]] = {}
    for row in read_verdicts(store):
        name = str(row.get("experiment") or "")
        run_at = str(row.get("run_at") or "")
        if not name:
            continue
        prev = latest.get(name)
        if prev is None or run_at >= str(prev.get("run_at") or ""):
            latest[name] = row
    return latest


def _experiment_due(experiment: Experiment) -> str | None:
    """The due date named in a ledger status, as an ISO date, or None."""
    m = _DUE_RE.search(experiment.status)
    if not m:
        return None
    year, month, day = m.groups()
    if year is None:
        # Infer from the row's own date; a due month before the start month
        # means the deadline rolled into the following year.
        base = experiment.date[:4]
        if not base.isdigit():
            return None
        year = base
        if experiment.date[5:7].isdigit() and int(month) < int(experiment.date[5:7]):
            year = str(int(base) + 1)
    try:
        return _date(int(year), int(month), int(day)).isoformat()
    except ValueError:
        return None


def _render_experiments(experiments: list[Experiment] | None, store: Path | None = None) -> str:
    if not experiments:
        return (
            '<section class="chart"><h3>Experiments</h3>'
            '<p class="note">No experiments tracked. Add hypothesis rows to the '
            "tooling ledger.</p></section>"
        )
    # The ledger's Status: text is hand-written and rarely updated after the row
    # is added, so reading it alone reported "107 pending" while the scorer held
    # 1,395 verdict rows. The scored verdict wins where it exists; the ledger
    # status is the fallback for rows the scorer never reached.
    latest = _latest_verdicts(store)
    # Overdue is judged against the newest observation, not the wall clock: the
    # store is refreshed in batches, so anchoring to the data keeps a render
    # reproducible and stops a stale store from inventing overdue rows.
    today = max(
        (str(r.get("run_at") or "")[:10] for r in latest.values()),
        default=max((e.date for e in experiments), default=""),
    )

    def _verdict_of(e: Experiment) -> str:
        row = latest.get(e.name)
        if row:
            return str(row.get("verdict") or "inconclusive")
        key = _status_key(e.status)
        if key in CONFIRMED_STATUSES:
            return "confirmed"
        if key in FAILED_STATUSES:
            return "failed"
        if key in INCONCLUSIVE_STATUSES:
            return "inconclusive"
        return "unscored"

    tally = Counter(_verdict_of(e) for e in experiments)
    scored = len(experiments) - tally["unscored"]
    decisive = tally["confirmed"] + tally["failed"]
    inconclusive_share = tally["inconclusive"] / scored * 100 if scored else 0.0

    order = {"failed": 0, "trending": 1, "confirmed": 2, "inconclusive": 3, "unscored": 4}
    grouped = sorted(experiments, key=lambda e: (order.get(_verdict_of(e), 9), e.name))

    rows = ""
    overdue_n = 0
    for e in grouped:
        verdict = _verdict_of(e)
        due = _experiment_due(e)
        # Only an undecided experiment can be overdue — a called one is done.
        overdue = bool(due and due < today and verdict in ("inconclusive", "unscored"))
        overdue_n += overdue
        due_cell = (
            f'<span style="color:var(--bad);font-weight:600">{html.escape(due)}</span>'
            if overdue
            else html.escape(due or "—")
        )
        row = latest.get(e.name)
        evidence = str(row.get("evidence") or "") if row else ""
        title_attr = (
            f' title="{html.escape(_truncate(evidence, 200), quote=True)}"' if evidence else ""
        )
        rows += (
            f"<tr><td>{html.escape(e.name)}</td><td>{html.escape(e.metric)}</td>"
            f'<td><span class="exp-badge {_VERDICT_BADGE.get(verdict, "exp-other")}"'
            f"{title_attr}>"
            f"{html.escape(verdict)}</span></td>"
            f"<td>{html.escape(e.date)}</td><td>{due_cell}</td>"
            f'<td class="trend-cell">{_experiment_trend(e, store)}</td></tr>'
        )

    kpis = (
        f'<div class="stat-row" style="margin-bottom:12px">'
        f'<div class="stat"><span class="value" style="color:var(--good)">{tally["confirmed"]}</span>'
        f'<span class="label">confirmed</span></div>'
        f'<div class="stat"><span class="value" style="color:var(--bad)">{tally["failed"]}</span>'
        f'<span class="label">failed</span></div>'
        f'<div class="stat"><span class="value" style="color:var(--s3)">{tally["trending"]}</span>'
        f'<span class="label">trending</span></div>'
        f'<div class="stat"><span class="value" style="color:var(--warn)">'
        f"{inconclusive_share:.0f}%</span>"
        f'<span class="label">inconclusive of scored</span></div>'
        f'<div class="stat"><span class="value">{tally["unscored"]}</span>'
        f'<span class="label">never scored</span></div>'
        f'<div class="stat"><span class="value" style="color:var(--bad)">{overdue_n}</span>'
        f'<span class="label">overdue</span></div></div>'
    )

    diagnosis = (
        f"{decisive} of {len(experiments)} experiments reached a decisive call. "
        f"The bottleneck is measurability, not outcome: {inconclusive_share:.0f}% of "
        f"scored experiments came back <em>inconclusive</em>, and {tally['unscored']} "
        f"carry no scorable metric at all. An unfalsifiable hypothesis cannot close "
        f"the loop."
    )

    return (
        f'<section class="chart"><h3>Experiments</h3>'
        f"{kpis}"
        f'<p class="note">{diagnosis}</p>'
        f'<div class="table-view"><table>'
        f"<thead><tr><th>Change</th><th>Metric</th><th>Verdict</th><th>Opened</th>"
        f"<th>Due</th><th>7-day trend</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
        f'<p class="frame">Verdict is the scorer\'s latest call from '
        f"<code>experiment_verdicts</code> where the ledger name joins "
        f"({len(latest)} scored experiments); otherwise the ledger's own status. "
        f"Hover a badge for the scoring evidence.</p></section>"
    )


# ---------------------------------------------------------------------------
# Verdict trajectories (LIB-58) — deterministic verdict history per experiment
# ---------------------------------------------------------------------------
#
# `experiment_verdicts` is append-only: every insights run that scores an
# experiment's metric adds a row, so the same experiment accumulates one
# verdict per run over time. That history is the trajectory this section
# renders — hypothesis date, then the ordered sequence of (run_at, verdict)
# observations — so a reader can see an experiment move from `inconclusive`
# to `trending` to `confirmed` across runs, rather than only its latest call.

# Caps on what one trajectory row renders. Without them the region injected
# 302KB into context-dashboard.html (GUA-137) — 66 experiments' entire scored
# history, each step carrying its full evidence string in a title attribute.
_TRAJECTORY_MAX_STEPS = 12
_TRAJECTORY_EVIDENCE_CHARS = 160


def _truncate(text: str, limit: int) -> str:
    """`text` clipped to `limit` chars on a word boundary, with an ellipsis."""
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip()
    return f"{cut or text[:limit]}…"


_TRAJECTORY_BADGE_CLASS = {
    "confirmed": "exp-confirmed",
    "trending": "exp-trending",
    "inconclusive": "exp-pending",
    "failed": "exp-failed",
}


def _render_verdict_trajectories(verdict_rows: list[dict[str, Any]] | None) -> str:
    """Render one trajectory (date -> ordered verdict sequence) per experiment.

    `verdict_rows` is the shape returned by `factstore.read_verdicts()`: dicts
    with `experiment`, `date`, `metric`, `verdict`, `evidence`, `run_at`. Rows
    are grouped by experiment name and sorted by `run_at` within each group,
    oldest first, so the sequence reads left-to-right as it happened.
    """
    if not verdict_rows:
        return (
            '<section class="chart"><h3>Verdict trajectories</h3>'
            '<p class="note">No scored verdicts yet. Verdicts accumulate one row '
            "per insights run against the tooling ledger.</p></section>"
        )

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in verdict_rows:
        grouped.setdefault(row["experiment"], []).append(row)

    def _steps(runs: list[dict[str, Any]]) -> str:
        """The trailing `_TRAJECTORY_MAX_STEPS` runs, with an elision marker.

        GUA-137: uncapped, this rendered 302KB into the page — every run's full
        evidence string inlined as a title attribute. The recent steps are what
        a trajectory is read for; the elision marker keeps the truncation
        visible rather than silently showing a shorter history than exists.
        """
        ordered = sorted(runs, key=lambda r: r.get("run_at") or "")
        shown = ordered[-_TRAJECTORY_MAX_STEPS:]
        steps = '<span class="verdict-arrow">&rarr;</span>'.join(
            f'<span class="verdict-step {_TRAJECTORY_BADGE_CLASS.get(r["verdict"], "exp-other")}" '
            f'title="{html.escape(r.get("run_at", ""))}: '
            f'{html.escape(_truncate(r.get("evidence", ""), _TRAJECTORY_EVIDENCE_CHARS))}">'
            f"{html.escape(r['verdict'])}</span>"
            for r in shown
        )
        if len(ordered) > len(shown):
            elided = len(ordered) - len(shown)
            steps = (
                f'<span class="verdict-elided" title="{elided} earlier run(s) not shown">'
                f"+{elided}&hellip;</span>"
                '<span class="verdict-arrow">&rarr;</span>' + steps
            )
        return steps

    rows_html = "".join(
        f"<tr><td>{html.escape(name)}</td>"
        f"<td>{html.escape(runs[0].get('date', ''))}</td>"
        f'<td class="verdict-trajectory">{_steps(runs)}</td></tr>'
        for name, runs in sorted(grouped.items(), key=lambda kv: kv[1][0].get("date", ""))
    )
    return (
        '<section class="chart"><h3>Verdict trajectories</h3>'
        f'<p class="note">{len(grouped)} experiment(s) with scored history — '
        "each step is one insights run, oldest to newest.</p>"
        '<div class="table-view"><table>'
        "<thead><tr><th>Experiment</th><th>Hypothesis date</th><th>Verdict sequence</th></tr></thead>"
        f"<tbody>{rows_html}</tbody></table></div></section>"
    )


_CSS = """
.viz-root{color-scheme:light;--surface-1:#fcfcfb;--page:#f9f9f7;--text-primary:#0b0b0b;
--text-secondary:#52514e;--muted:#898781;--baseline:#c3c2b7;--border:rgba(11,11,11,.10);
--warn:#9a5b00;
--chart-1:#2a78d6;--chart-2:#008300;--chart-3:#e87ba4;--chart-4:#eda100;
font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--page);
color:var(--text-primary);padding:24px;}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])) .viz-root{
color-scheme:dark;--surface-1:#1a1a19;--page:#0d0d0d;--text-primary:#fff;
--text-secondary:#c3c2b7;--muted:#898781;--baseline:#383835;--border:rgba(255,255,255,.10);
--warn:#f0a94c;
--chart-1:#3987e5;--chart-2:#008300;--chart-3:#d55181;--chart-4:#c98500;}}
:root[data-theme="dark"] .viz-root{color-scheme:dark;--surface-1:#1a1a19;--page:#0d0d0d;
--text-primary:#fff;--text-secondary:#c3c2b7;--baseline:#383835;--border:rgba(255,255,255,.10);
--warn:#f0a94c;
--chart-1:#3987e5;--chart-2:#008300;--chart-3:#d55181;--chart-4:#c98500;}
.dash-nav{position:sticky;top:0;z-index:10;background:var(--page);display:flex;gap:8px;
padding:8px 0 12px;border-bottom:1px solid var(--border);margin-bottom:16px;flex-wrap:wrap;}
.dash-nav a{font-size:13px;padding:4px 12px;border-radius:16px;text-decoration:none;
color:var(--text-secondary);background:var(--surface-1);border:1px solid var(--border);
transition:background .15s,color .15s;}
.dash-nav a:hover{color:var(--text-primary);background:var(--baseline);}
.viz-root section{scroll-margin-top:48px;}
.viz-root section>h2{font-size:17px;margin:24px 0 4px;border-left:3px solid var(--baseline);padding-left:12px;}
.viz-root h1{font-size:20px;margin:0 0 4px;}
.viz-root .sub{color:var(--text-secondary);margin:0 0 24px;font-size:13px;}
.chart{background:var(--surface-1);border:1px solid var(--border);border-radius:8px;
padding:16px;margin-bottom:16px;overflow-x:auto;}
.chart h3{font-size:15px;margin:0 0 2px;}
.chart h4{font-size:13px;margin:0 0 2px;}
.note,.frame,.range,.rule{color:var(--text-secondary);font-size:12px;margin:0 0 8px;}
.frame{color:var(--muted);font-style:italic;}
/* GUA-120: the population a tile was computed from. Deliberately not .note --
   a muted footnote is how a sparse-column metric passes for a corpus-wide one. */
.population{color:var(--text-primary);font-size:12px;font-weight:600;margin:0 0 8px;
font-variant-numeric:tabular-nums;}
.rule{border-left:2px solid var(--baseline);padding-left:8px;}
.panels{display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start;}
/* flex-grow is set inline, proportional to each regime's span in days, so panel
   width reflects duration. min-width keeps a short regime legible. */
.panel{min-width:140px;}
.saturated{color:var(--warn);font-size:12px;margin:0 0 6px;font-weight:600;}
.sparse{margin:12px 0;font-size:20px;}
.sparse-label{font-size:12px;color:var(--text-secondary);font-weight:400;}
svg{width:100%;height:160px;display:block;}
.axis-label{font-size:10px;fill:var(--text-secondary);font-family:system-ui,sans-serif;}
.bands{list-style:none;padding:0;margin:8px 0 0;font-size:12px;color:var(--text-secondary);
display:flex;gap:16px;flex-wrap:wrap;}
.tiles{display:flex;gap:24px;flex-wrap:wrap;}
.tile{display:flex;flex-direction:column;}
.tile .value{font-size:32px;font-weight:600;}
.tile .label{font-size:12px;color:var(--text-secondary);}
.boundary{border-left:3px solid var(--baseline);padding-left:12px;margin:24px 0 12px;}
.empty{color:var(--muted);font-size:12px;}
.exp-badge{font-size:11px;padding:2px 8px;border-radius:10px;font-weight:600;}
.exp-confirmed{background:rgba(0,131,0,.15);color:#008300;}
.exp-failed{background:rgba(220,50,50,.12);color:#c03030;}
.exp-trending{background:rgba(237,161,0,.15);color:#9a6a00;}
.exp-pending{background:var(--border);color:var(--text-secondary);}
.exp-other{background:var(--border);color:var(--text-secondary);}
.verdict-trajectory{white-space:nowrap;}
.verdict-step{font-size:11px;padding:2px 8px;border-radius:10px;font-weight:600;}
.verdict-arrow{color:var(--muted);margin:0 4px;}
.provenance{font-size:11px;color:var(--muted);margin:0 0 6px;}
.provenance summary{cursor:pointer;}
.provenance p{margin:4px 0 0;}
.table-view{margin-top:12px;font-size:12px;color:var(--text-secondary);}
.table-view summary{cursor:pointer;color:var(--text-secondary);}
.table-view table{border-collapse:collapse;margin-top:8px;font-variant-numeric:tabular-nums;}
.table-view th,.table-view td{text-align:left;padding:2px 12px 2px 0;
border-bottom:1px solid var(--border);}
.surf-filter{display:flex;align-items:center;gap:8px;}
.surf-filter label{font-size:12px;color:var(--text-secondary);}
.surf-filter select{font-size:12px;padding:3px 8px;border-radius:12px;
border:1px solid var(--border);background:var(--surface-1);color:var(--text-primary);
cursor:pointer;}
.period-filter{display:flex;align-items:center;gap:4px;margin-left:auto;}
.period-filter label{font-size:12px;color:var(--text-secondary);margin-right:4px;}
.period-btn{font-size:12px;padding:3px 10px;border-radius:12px;
border:1px solid var(--border);background:var(--surface-1);color:var(--text-secondary);
cursor:pointer;}
.period-btn.active{background:var(--text-primary);color:var(--surface-1);
border-color:var(--text-primary);}
"""


# Provenance ledger: signal -> (source, earliest honest date, status). Rendered so
# a reader can tell "flat line" from "never recorded", and so the next person to
# add a metric knows what is already collected before instrumenting again.
_COVERAGE = [
    ("Cost, tokens, cache", "JSONL usage + migrated notes", "2026-04-10", "complete"),
    ("Compaction flag", "note hook, then JSONL", "2026-04-10", "regime-bound - see rates"),
    ("Max context", "JSONL per-request", JULY_BOUNDARY, "no pre-July data, not imputed"),
    ("Skill + model attribution", "JSONL tool_use blocks", JULY_BOUNDARY, "no pre-July data"),
    ("Tool errors, interruptions", "JSONL tool_result is_error", JULY_BOUNDARY, "backfilled"),
    (
        "Human turns per session",
        "JSONL user records, tool_results excluded",
        JULY_BOUNDARY,
        "backfilled",
    ),
    ("Plan-doc outcome", "not collected", "-", "blocked - no ABANDONED label exists; see note"),
    (
        "Commits + churn",
        "git log across ~/workspace",
        "2026-04-03",
        "repo activity, not per-session",
    ),
    ("PRs opened/merged", "gh pr list", "2026-04-03", "repo activity; 94% dependabot"),
    ("Issues resolved", "not collected", "-", "no data - 0 GitHub issues, 0 LIN- refs in commits"),
    (
        "Subagent attribution",
        "JSONL subagent transcripts",
        JULY_BOUNDARY,
        f"per-model complete; agent names only from CLI {SUBAGENT_ATTRIBUTION_CLI}",
    ),
    (
        "Context fixed overhead",
        "manual JSONL sample, first-turn cache write",
        "2026-07-28",
        "one-time - GUA-44, see research doc; ~15-23k tokens/session, not tracked live",
    ),
    (
        "Failure attribution (code/env/tool/unknown)",
        "JSONL tool_errors, classified at parse time (LIB-57)",
        JULY_BOUNDARY,
        "backfill requires re-parse - raw error text discarded after error_kind reduction",
    ),
    (
        "Bash antipatterns",
        "JSONL Bash tool_use commands",
        JULY_BOUNDARY,
        "backfilled",
    ),
]

# Signals deliberately not collected, with the reason. Kept visible so the same
# proposal is not re-litigated from scratch each time.
_NOT_COLLECTED = (
    "Plan-doc Status transitions (EXECUTED vs ABANDONED) would be the natural "
    "outcome metric, and it is not built for two reasons measured 2026-07-20. "
    "First, .claude/docs/ is git-ignored by policy, so a doc has current state but "
    "no history - nothing recovers the past, only forward snapshots would work. "
    "Second, and decisive: across 61 plan docs, 37 carry a Status line and ZERO "
    "say ABANDONED (EXECUTED 26, COMPLETE 5, SUPERSEDED 2, IN PROGRESS 1). An "
    "abandoned plan is silently dropped, never marked - so the ratio would read "
    "~100% success by construction and measure labelling discipline, not outcomes. "
    "The vocabulary is also unnormalised (EXECUTED vs COMPLETE vs RESEARCH "
    "COMPLETE) and only 29 of 61 filenames are date-prefixed, so a time series "
    "would cover under half the corpus. Fixing the metric means fixing the "
    "convention first, not adding a panel."
)


def weekly_cost_by_repo(store: Path) -> tuple[dict[str, dict[str, float]], float, float]:
    """Weekly cost_units per repo, July-forward only.

    Cost is split across the repos a session actually worked in, weighted by how
    many records ran under each `cwd` (`session_repos`). A session that spent 90%
    of its records in one repo contributes 90% of its cost there -- 22% of
    sessions touch more than one repo, so assigning the whole session to a single
    winner would misattribute real spend.

    July-forward only (JULY_ONLY_METRICS): `session_repos` is derived from JSONL
    `cwd` records, which the note era never captured. A pre-July point would plot
    the absence of transcripts, not a quiet week.

    Returns (weekly, attributed_cost, total_cost). The two totals are what the
    panel needs to state its own coverage rather than implying it is complete.
    """
    weekly: dict[str, dict[str, float]] = {}
    attributed = 0.0
    total = 0.0
    for row in _work_sessions(read_all(store)):
        day = str(row.get("date") or "")
        if day < JULY_BOUNDARY:
            continue
        cost = float(row.get("cost_units") or 0.0)
        total += cost
        try:
            repos: dict[str, int] = json.loads(row.get("session_repos") or "{}")
        except (json.JSONDecodeError, TypeError):
            repos = {}
        if not repos:
            continue
        attributed += cost
        records = sum(repos.values())
        week = _iso_week(day)
        for repo, count in repos.items():
            bucket = weekly.setdefault(repo, {})
            bucket[week] = bucket.get(week, 0.0) + cost * count / records
    return weekly, attributed, total


def weekly_commits_by_repo(store: Path) -> dict[str, dict[str, float]]:
    """Weekly human (non-bot) commits per repo, July-forward only.

    Same window as `weekly_cost_by_repo` so the two panels sit on one x-axis.
    Bot commits are excluded, not pooled -- see gitstore.ATTRIBUTION.
    """
    weekly: dict[str, dict[str, float]] = {}
    for row in read_git_activity(store):
        day = str(row.get("date") or "")
        if day < JULY_BOUNDARY:
            continue
        human = int(row.get("commits") or 0) - int(row.get("commits_bot") or 0)
        if human <= 0:
            continue
        bucket = weekly.setdefault(str(row["repo"]), {})
        week = _iso_week(day)
        bucket[week] = bucket.get(week, 0.0) + human
    return weekly


def _render_repo_economics(store: Path) -> str:
    """Cost and commits per repo, side by side -- deliberately NOT divided.

    The ratio these two panels invite is exactly the number this dashboard must
    not print. Ramsey commits, always (gitstore.ATTRIBUTION): there is no
    commit -> session join, so cost-per-commit would read as "Claude cost X per
    commit" when the commits are Ramsey's and the trailer is absent from 400 of
    406 of them. Rendering both series unjoined lets a reader see effort next to
    outcome without the panel asserting a causal link the data cannot support.
    """
    cost_weekly, attributed, total = weekly_cost_by_repo(store)
    commit_weekly = weekly_commits_by_repo(store)
    if not cost_weekly and not commit_weekly:
        return ""

    repos = sorted(
        set(cost_weekly) | set(commit_weekly),
        key=lambda r: -sum(cost_weekly.get(r, {}).values()),
    )
    unattributed = total - attributed
    share = (unattributed / total * 100) if total else 0.0

    rows = []
    for repo in repos:
        cost = sum(cost_weekly.get(repo, {}).values())
        commits = int(sum(commit_weekly.get(repo, {}).values()))
        rows.append(
            f"<tr><td>{html.escape(repo)}</td>"
            f"<td>{cost / 1_000_000:,.1f}M</td><td>{commits}</td></tr>"
        )
    table = (
        f'<div class="table-view"><table>'
        f"<tr><th>Repo</th><th>Session cost (July+)</th><th>Human commits</th></tr>"
        f"{''.join(rows)}</table></div>"
    )
    return (
        f'<div class="boundary"><h2>Repo effort and outcome</h2>'
        f'<p class="sub">Session cost and landed commits per repo, side by side and '
        f"<strong>deliberately not divided</strong>. There is no commit -&gt; session "
        f"join: Ramsey commits, always, so a cost-per-commit ratio would read as "
        f"Claude-authored output when the commits are his. Read these as two "
        f"independent series over the same weeks.</p></div>"
        f'<div class="chart"><h3>Since {html.escape(JULY_BOUNDARY)}</h3>{table}'
        f'<p class="frame">Cost is split across the repos a session worked in, '
        f"weighted by records under each cwd; 22% of sessions touch more than one. "
        f"{unattributed / 1_000_000:,.1f}M cost units ({share:.0f}%) ran entirely at "
        f"the workspace root and name no repo - excluded here rather than assigned to "
        f"one. A repo with cost and zero commits means spend without landed work, not "
        f"a missing join.</p></div>"
    )


def _render_repo_activity(store: Path) -> str:
    """Repo-activity tiles: commits, churn, PR flow.

    Deliberately tiles and not a trend line. These are NOT per-session metrics and
    do not join to a session, so plotting them beside cost/context would invite the
    inference the caveat exists to block (see gitstore.ATTRIBUTION).
    """
    activity = read_git_activity(store)
    prs = read_prs(store)
    if not activity and not prs:
        return ""

    commits = sum(r["commits"] for r in activity)
    bot = sum(r["commits_bot"] for r in activity)
    trailer = sum(r["commits_claude_trailer"] for r in activity)
    human = commits - bot
    insertions = sum(r["insertions"] for r in activity)
    deletions = sum(r["deletions"] for r in activity)
    repos = len({r["repo"] for r in activity})
    human_prs = [p for p in prs if not p["is_bot"]]
    merged = sum(p["merged"] for p in human_prs)

    tiles = [
        (f"{human:,}", "human commits"),
        (f"{bot:,}", "bot commits"),
        (f"+{insertions:,}", "lines added (source only)"),
        (f"-{deletions:,}", "lines removed"),
        (f"{len(human_prs)}", "human PRs"),
        (f"{merged}", "PRs merged"),
        (f"{repos}", "active repos"),
    ]
    tile_html = "".join(
        f'<div class="tile"><span class="value">{html.escape(v)}</span>'
        f'<span class="label">{html.escape(label)}</span></div>'
        for v, label in tiles
    )
    return (
        f'<div class="boundary"><h2>Repo activity</h2>'
        f'<p class="sub">What landed in the repos. NOT a Claude-productivity metric '
        f"and not joinable to a session - Ramsey commits, always, so only "
        f"{trailer} of {commits:,} commits carry a Co-Authored-By trailer and its "
        f"absence means nothing. Read these as workspace throughput.</p></div>"
        f'<div class="chart"><h3>Totals since 2026-04-01</h3>'
        f'<div class="tiles">{tile_html}</div>'
        f'<p class="frame">Churn counts source files only - PDFs, notebooks, '
        f"lockfiles, vendored course material and bundled plugin JS are excluded. "
        f"Unfiltered, those were 50% of all insertions and one 70k-line PDF was the "
        f"single largest contributor.</p></div>"
    )


def _render_coverage() -> str:
    """The provenance ledger -- what is measured, since when, and what never was."""
    rows = "".join(
        f"<tr><td>{html.escape(signal)}</td><td>{html.escape(source)}</td>"
        f"<td>{html.escape(since)}</td><td>{html.escape(status)}</td></tr>"
        for signal, source, since, status in _COVERAGE
    )
    return (
        f'<div class="boundary"><h2>Signal coverage</h2>'
        f'<p class="sub">Where each number comes from and the earliest date it is '
        f"honest. A metric absent here is not being measured.</p></div>"
        f'<div class="chart"><div class="table-view"><table>'
        f"<tr><th>Signal</th><th>Source</th><th>Since</th><th>Status</th></tr>"
        f"{rows}</table></div>"
        f'<p class="frame">{html.escape(_NOT_COLLECTED)}</p></div>'
    )


def render_dashboard(
    store: Path,
    funnel: Funnel | None = None,
    experiments: list[Experiment] | None = None,
    review_findings: list[dict] | None = None,
    ledger_path: Path | None = None,
    ledger_log_path: Path | None = None,
    verdict_store: Path | None = None,
) -> str:
    """Render the full dashboard to a self-contained HTML string.

    `ledger_path` and `ledger_log_path` are optional; when provided, the
    experiments section reads live from the tooling ledger (Step 7). When not
    provided, `experiments` is used directly (backward-compatible).

    `verdict_store` is optional (LIB-58); when provided, the progress section
    also renders per-experiment verdict trajectories read from the
    `experiment_verdicts` table. Omitted entirely when not given, so callers
    that never scored verdicts see no change to the rendered page.
    """
    if ledger_path is not None and experiments is None:
        experiments = parse_ledger(ledger_path, ledger_log_path)
    if experiments:
        warn_unmapped_experiments(experiments)
    verdict_rows = read_verdicts(verdict_store) if verdict_store is not None else None

    def _chart_var(i: int) -> str:
        return f"var(--chart-{(i % 4) + 1})"

    def _tier(
        specs: Sequence[tuple[str, str, str, str, str]],
        exps: list[Experiment] | None = None,
    ) -> str:
        """Render a tier at all three periods into period-tagged wrappers.

        Aggregation stays in Python — the browser only shows and hides. The
        alternative (ship rows, bucket in JS) is a second implementation of
        `_period_key` that would drift from this one.
        """

        def _view(i: int, spec: tuple[str, str, str, str, str], period: str) -> str:
            metric, title, note, prov, unit = spec
            hidden = "" if period == _DEFAULT_PERIOD else ' style="display:none"'
            body = _render_series(
                build_series(metric, store, period),
                _chart_var(i),
                title,
                note,
                prov,
                unit,
                exps,
            )
            return f'<div class="period-view" data-period="{period}"{hidden}>{body}</div>'

        return "".join(_view(i, spec, period) for i, spec in enumerate(specs) for period in PERIODS)

    tier1 = _tier(_TIER1)
    tier2 = _tier(_TIER2)
    work = _tier(_TIER_WORK)
    shape = _tier(_TIER_SHAPE)
    # Step 9: friction tab regroup — three groups instead of flat _TIER3 list.
    # LIB-59: this is the one tier with a mapped ledger experiment
    # (execution_skill_compliance_pct), so it is the only call site that passes
    # `experiments` through for annotation rendering.
    friction_prompt = _tier(_FRICTION_PROMPT_ENG, experiments)
    friction_loop = _tier(_FRICTION_LOOP_ENG)
    friction_harness = _tier(_FRICTION_HARNESS_ENG)
    tier3 = (
        f'<div class="boundary"><h2 style="font-size:14px;margin:0 0 4px">Prompt-eng</h2>'
        f'<p class="sub" style="margin:0 0 12px">Does reasoning work? '
        f"Capability signals — higher is better.</p></div>"
        f"{friction_prompt}"
        f'<div class="boundary"><h2 style="font-size:14px;margin:0 0 4px">Loop-eng</h2>'
        f'<p class="sub" style="margin:0 0 12px">Does workflow repeat? '
        f"True friction signals — lower is better.</p></div>"
        f"{friction_loop}{_REWORK_PLACEHOLDER}"
        f'<div class="boundary"><h2 style="font-size:14px;margin:0 0 4px">Harness-eng</h2>'
        f'<p class="sub" style="margin:0 0 12px">Does infrastructure hold? '
        f"Error and context signals.</p></div>"
        f"{friction_harness}"
    )
    rates = _tier(_RATES)
    # Build surface selector: "All" + one option per distinct observed surface.
    surfaces = _distinct_surfaces(store)
    surf_options = '<option value="all">All surfaces</option>' + "".join(
        f'<option value="{html.escape(s)}">{html.escape(s)}</option>' for s in surfaces
    )
    surf_selector = (
        f'<div class="surf-filter">'
        f'<label for="surf-sel">Surface:</label>'
        f'<select id="surf-sel">{surf_options}</select>'
        f"</div>"
    )

    period_buttons = "".join(
        f'<button type="button" class="period-btn'
        f'{" active" if period == _DEFAULT_PERIOD else ""}" '
        f'data-period="{period}">{period.capitalize()}</button>'
        for period in PERIODS
    )
    period_selector = f'<div class="period-filter"><label>Period:</label>{period_buttons}</div>'

    nav = (
        '<nav class="dash-nav">'
        '<a href="#cost">Cost &amp; Efficiency</a>'
        '<a href="#context">Context Health</a>'
        '<a href="#friction">Friction &amp; Quality</a>'
        '<a href="#review">Code Review</a>'
        '<a href="#progress">Experiments &amp; Progress</a>'
        f"{period_selector}"
        f"{surf_selector}"
        "</nav>"
    )

    surf_js = (
        "<script>(function(){"
        'var sel=document.getElementById("surf-sel");'
        "if(!sel)return;"
        "function apply(v){"
        'document.querySelectorAll(".chart[data-metric]").forEach(function(chart){'
        'var views=chart.querySelectorAll(".surf-view");'
        "var found=false;"
        "views.forEach(function(d){"
        'var match=(d.dataset.surface===v)||(v==="all"&&d.dataset.surface==="all");'
        'd.style.display=match?"":"none";'
        "if(match)found=true;"
        "});"
        "if(!found){var a=chart.querySelector('.surf-view[data-surface=\"all\"]');"
        'if(a)a.style.display="";}'
        "});"
        "}"
        'sel.addEventListener("change",function(){apply(sel.value);});'
        'apply("all");'
        "})();</script>"
    )

    # Period toggle. Every panel is already rendered at all three periods as
    # sibling .period-view wrappers; this only flips display. Vanilla JS with no
    # CDN — a remote <script> is a blank panel on a file:// open.
    period_js = (
        "<script>(function(){"
        'var btns=document.querySelectorAll(".period-btn");'
        "if(!btns.length)return;"
        "function apply(p){"
        'document.querySelectorAll(".period-view").forEach(function(d){'
        'd.style.display=(d.dataset.period===p)?"":"none";'
        "});"
        "btns.forEach(function(b){"
        'b.classList.toggle("active",b.dataset.period===p);'
        "});"
        "}"
        "btns.forEach(function(b){"
        'b.addEventListener("click",function(){apply(b.dataset.period);});'
        "});"
        f'apply("{_DEFAULT_PERIOD}");'
        "})();</script>"
    )

    sec_cost = (
        f'<section id="cost"><h2>Cost &amp; Efficiency</h2>'
        f'<p class="sub">Am I spending well?</p>'
        f"{tier1}{_render_tool_trends(store)}"
        f'<div class="boundary"><h2 style="font-size:14px;margin:0 0 4px">Work economics</h2>'
        f'<p class="sub" style="margin:0 0 12px">What does a unit of work cost, and what '
        f"kind of work was it? Each tile states the population it was computed from.</p></div>"
        f"{work}</section>"
    )

    sec_context = (
        f'<section id="context"><h2>Context Health</h2>'
        f'<p class="sub">Is context under control? Telemetry begins {JULY_BOUNDARY} '
        f"— these metrics have no pre-boundary data.</p>"
        f"{tier2}{rates}{shape}</section>"
    )

    sec_friction = (
        f'<section id="friction"><h2>Friction &amp; Quality</h2>'
        f'<p class="sub">Where does work break? Stored from {FRICTION_STORED}, '
        f"backfilled to {JULY_BOUNDARY}.</p>"
        f"{tier3}{_render_subagents(store)}{_render_skill_economics(store)}</section>"
    )

    sec_review = (
        f'<section id="review"><h2>Code Review Findings</h2>'
        f'<p class="sub">Structured findings from akira-scan and SANYI, '
        f"persisted per review run.</p>"
        f"{_render_review_findings(review_findings)}</section>"
    )

    sec_progress = (
        f'<section id="progress"><h2>Experiments &amp; Progress</h2>'
        f'<p class="sub">Are my changes working?</p>'
        f"{_render_experiments(experiments, store)}"
        f"{_render_verdict_trajectories(verdict_rows)}"
        f"{_render_funnel(funnel)}"
        f"{_render_repo_activity(store)}"
        f"{_render_repo_economics(store)}"
        f"{_render_coverage()}</section>"
    )

    return (
        # Without this, a file:// open leaves the browser guessing the encoding
        # and every em-dash, arrow and ellipsis in the page renders as mojibake.
        # The rendered fragment carries no <head>, so the declaration has to
        # lead the output to fall inside the first 1024 bytes the parser scans.
        f'<meta charset="utf-8">'
        f"<style>{_CSS}</style>"
        f'<div class="viz-root"><h1>Context engineering dashboard</h1>'
        f'<p class="sub">Work sessions only, faceted by instrumentation regime. '
        f"Rates are never pooled across regimes.</p>"
        f'<p class="sub">Vertical markers on a chart pin a dated tooling-ledger '
        f"experiment to that metric (hover for name, metric, and status); "
        f"<code>absence:</code>-type experiments are meta-signals with no "
        f"timeseries to land on and are deliberately not rendered.</p>"
        f"{nav}{sec_cost}{sec_context}{sec_friction}{sec_review}{sec_progress}"
        f"{surf_js}{period_js}</div>"
    )


def write_dashboard(
    store: Path,
    out: Path,
    growth_md: Path | None = None,
    experiments: list[Experiment] | None = None,
    review_findings: list[dict] | None = None,
    ledger_path: Path | None = None,
    ledger_log_path: Path | None = None,
    verdict_store: Path | None = None,
) -> Path:
    """Render and write the dashboard, returning the output path."""
    funnel = funnel_counts(growth_md) if growth_md else None
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        render_dashboard(
            store,
            funnel,
            experiments,
            review_findings,
            ledger_path,
            ledger_log_path,
            verdict_store,
        ),
        encoding="utf-8",
    )
    log.info("dashboard.written", out=str(out), store=str(store))
    return out


# ---------------------------------------------------------------------------
# Region injection — context-dashboard.html marker pairs
# ---------------------------------------------------------------------------

# Marker pattern: <!-- NAME:START ... --> ... <!-- NAME:END -->
_MARKER_END_TMPL = "<!-- {name}:END -->"


def inject_regions(html_path: Path, regions: dict[str, str]) -> Path:
    """Replace content between START/END marker pairs in *html_path*.

    Only the bytes between each matched pair are replaced; everything else —
    including the marker comments themselves — is left untouched.  The result
    is built entirely in memory and written once, so a mid-run failure leaves
    the original file intact.

    Args:
        html_path: Target HTML file (read + written in place).
        regions: Mapping of region-name → replacement HTML.  Names not present
            in the file are skipped with a warning; names present in the file
            but absent from *regions* are left untouched.

    Returns:
        The path that was written.

    Raises:
        FileNotFoundError: If *html_path* does not exist.
    """
    # Guard: never write to the deprecated path. Checked before any read so the
    # refusal is unconditional rather than dependent on the file being readable.
    if html_path.name == "dashboard.html" and ".sounding" in str(html_path):
        raise ValueError(
            f"Refusing to write to deprecated path {html_path}. "
            "The shared artifact is context-dashboard.html."
        )

    if not html_path.exists():
        raise FileNotFoundError(f"context-dashboard not found: {html_path}")

    result = html_path.read_text(encoding="utf-8")
    for name, replacement in regions.items():
        start_tag = f"<!-- {name}:START"
        end_tag = _MARKER_END_TMPL.format(name=name)

        start_idx = result.find(start_tag)
        if start_idx == -1:
            log.warning("inject_regions.missing_start", region=name, path=str(html_path))
            continue

        # Find the end of the START comment (the closing ">")
        start_comment_end = result.index("-->", start_idx) + len("-->")

        end_idx = result.find(end_tag, start_comment_end)
        if end_idx == -1:
            # Fail soft: a half-marked region is skipped, not fatal. Raising here
            # would let one malformed pair block every other region's refresh.
            log.warning("inject_regions.missing_end", region=name, path=str(html_path))
            continue

        # Replace only the content BETWEEN the two markers.
        # Preserve a single newline on each side so markers stay on their own lines.
        before = result[:start_comment_end]
        after = result[end_idx:]
        result = before + "\n" + replacement + "\n" + after

    html_path.write_text(result, encoding="utf-8")
    log.info("inject_regions.written", path=str(html_path), regions=list(regions))
    return html_path


def render_review_findings_region(findings: list[dict] | None) -> str:
    """Return the injectable HTML for the REVIEW-FINDINGS marker region."""
    return _render_review_findings(findings)


def render_experiments_region(
    experiments: list[Experiment] | None, store: Path | None = None
) -> str:
    """Return the injectable HTML for the EXPERIMENTS-LIFECYCLE marker region."""
    return _render_experiments(experiments, store)


def render_verdict_trajectories_region(verdict_rows: list[dict[str, Any]] | None) -> str:
    """Return the injectable HTML for a VERDICT-TRAJECTORIES marker region.

    Not wired into any marker set yet — no VERDICT-TRAJECTORIES comment pair
    exists in context-dashboard.html today. Exposed so a future region-
    injection wire-up (in __main__.py, alongside EXPERIMENTS-LIFECYCLE) can
    reuse this rather than re-deriving the render.
    """
    return _render_verdict_trajectories(verdict_rows)


# ---------------------------------------------------------------------------
# Skill eval results (GUA #47 / LIB #64) — eval-results.jsonl aggregation
# ---------------------------------------------------------------------------


def parse_eval_results(path: Path) -> list[dict]:
    """Read eval-results.jsonl, parse each line, return list of result dicts.

    Schema: date, repo, skill, eval_id, status, score, notes.
    Malformed lines are skipped with a warning — a single bad write must not
    break the dashboard render.
    """
    results: list[dict] = []
    if not path.exists():
        return results
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            log.warning("dashboard.eval_results_parse_error", line=i, path=str(path))
    return results


def _render_eval_results(results: list[dict] | None) -> str:
    """Render the SKILL-EVALS marker region from eval-results.jsonl rows.

    Three tables:
      1. Summary by repo — pass / fail / skip counts per repo.
      2. Summary by skill — pass / fail / skip counts per skill (across repos).
      3. Run dates present in the data (time dimension).

    All counts are aggregated from whatever dates exist; the trend across
    multiple dates cannot be verified until >=2 distinct run dates exist
    (first additional run expected 2026-08-03).
    """
    if not results:
        return (
            '<div class="card">\n'
            '      <div class="card-title">Skill evals</div>\n'
            '      <p class="card-note">No eval results yet. Run '
            "<code>guacamayo/scripts/eval-runner.sh</code> to populate "
            "<code>.sounding/eval-results.jsonl</code>.</p>\n"
            "    </div>"
        )

    # Aggregate by repo
    repo_stats: dict[str, dict[str, int]] = {}
    for r in results:
        repo = r.get("repo", "unknown")
        status = r.get("status", "unknown")
        repo_stats.setdefault(repo, {"pass": 0, "fail": 0, "skip": 0})
        if status in repo_stats[repo]:
            repo_stats[repo][status] += 1
        else:
            repo_stats[repo].setdefault(status, 0)
            repo_stats[repo][status] += 1

    # Aggregate by skill (repo/skill pair → then roll up to skill name)
    skill_stats: dict[str, dict[str, int]] = {}
    for r in results:
        skill = r.get("skill", "unknown")
        status = r.get("status", "unknown")
        skill_stats.setdefault(skill, {"pass": 0, "fail": 0, "skip": 0})
        if status in skill_stats[skill]:
            skill_stats[skill][status] += 1
        else:
            skill_stats[skill].setdefault(status, 0)
            skill_stats[skill][status] += 1

    # Run dates (time dimension)
    run_dates = sorted({r.get("date", "")[:10] for r in results if r.get("date")})

    total = len(results)
    total_pass = sum(r.get("status") == "pass" for r in results)
    total_fail = sum(r.get("status") == "fail" for r in results)
    total_skip = sum(r.get("status") == "skip" for r in results)

    # Repo table rows — sorted by repo name
    repo_rows = "".join(
        f"<tr>"
        f"<td>{html.escape(repo)}</td>"
        f"<td style='color:var(--success,#2a7d4f)'>{stats.get('pass', 0)}</td>"
        f"<td style='color:var(--danger,#c0392b)'>{stats.get('fail', 0)}</td>"
        f"<td style='color:var(--text-3)'>{stats.get('skip', 0)}</td>"
        f"</tr>"
        for repo, stats in sorted(repo_stats.items())
    )
    repo_table = (
        "<h4>By repo</h4>"
        '<div class="table-view"><table>'
        "<thead><tr><th>Repo</th><th>Pass</th><th>Fail</th><th>Skip</th></tr></thead>"
        f"<tbody>{repo_rows}</tbody></table></div>"
    )

    # Skill table rows — sorted by fail desc, then pass desc
    def _skill_sort_key(kv: tuple[str, dict[str, int]]) -> tuple[int, int, str]:
        _, s = kv
        return (-s.get("fail", 0), -s.get("pass", 0), kv[0])

    skill_rows = "".join(
        f"<tr>"
        f"<td>{html.escape(skill)}</td>"
        f"<td style='color:var(--success,#2a7d4f)'>{stats.get('pass', 0)}</td>"
        f"<td style='color:var(--danger,#c0392b)'>{stats.get('fail', 0)}</td>"
        f"<td style='color:var(--text-3)'>{stats.get('skip', 0)}</td>"
        f"</tr>"
        for skill, stats in sorted(skill_stats.items(), key=_skill_sort_key)
    )
    skill_table = (
        "<h4>By skill</h4>"
        '<div class="table-view"><table>'
        "<thead><tr><th>Skill</th><th>Pass</th><th>Fail</th><th>Skip</th></tr></thead>"
        f"<tbody>{skill_rows}</tbody></table></div>"
    )

    # Time dimension — dates present in data
    dates_note = (
        f"Run dates: {html.escape(', '.join(run_dates))}. "
        f"Trend across multiple dates requires &ge;2 distinct run dates "
        f"(next expected 2026-08-03)."
        if len(run_dates) < 2
        else f"Run dates ({len(run_dates)}): {html.escape(', '.join(run_dates))}."
    )

    return (
        '<div class="card">\n'
        '      <div class="card-title">Skill evals</div>\n'
        f'      <p class="card-note">{total} cases: {total_pass} pass, '
        f"{total_fail} fail, {total_skip} skip. "
        f"Source: <code>guacamayo/.sounding/eval-results.jsonl</code> "
        f"(written by <code>scripts/eval-runner.sh</code>).</p>\n"
        f"      {repo_table}\n"
        f"      {skill_table}\n"
        f'      <p style="font-size:11px;color:var(--text-3);margin-top:8px">'
        f"{dates_note}</p>\n"
        "    </div>"
    )


def render_eval_results_region(results: list[dict] | None) -> str:
    """Return the injectable HTML for the SKILL-EVALS marker region."""
    return _render_eval_results(results)


# ---------------------------------------------------------------------------
# Workflow loop (LIB #91) — plan-doc Status vs. issue workflow label
# ---------------------------------------------------------------------------


def _render_loop(docs: list[PlanDoc] | None, issues: list[dict[str, Any]] | None) -> str:
    """Render the LOOP marker region: where work sits, and where the two records disagree.

    Two distributions are shown side by side rather than merged, because they are not
    two views of one number: most plan docs carry no issue reference at all (35 of 126
    have an `Issue:` line, measured 2026-08-02). Merging them would imply a join that
    does not exist. Coverage is stated instead, so a small drift count reads as "few
    disagreements among the joinable ones", not "the loop is healthy".
    """
    docs = docs or []
    issues = issues or []
    if not docs and not issues:
        return (
            '<div class="card">\n'
            '      <div class="card-title">Workflow loop</div>\n'
            '      <p class="card-note">No plan docs or issues collected. '
            "Plan docs are read from <code>~/workspace/*/.claude/docs/plans/</code>; "
            "issues need <code>gh</code> on PATH.</p>\n"
            "    </div>"
        )

    statuses = status_counts(docs)
    labels = label_counts(issues)
    drifts = detect_drift(docs, issues)
    bad = non_conforming(docs)
    joinable = sum(1 for d in docs if d.issue is not None)

    status_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{count}</td></tr>" for name, count in statuses.items()
    )
    status_table = (
        "<h4>Plan docs by Status</h4>"
        '<div class="table-view"><table>'
        "<thead><tr><th>Status</th><th>Docs</th></tr></thead>"
        f"<tbody>{status_rows}</tbody></table></div>"
    )

    label_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{count}</td></tr>" for name, count in labels.items()
    )
    label_table = (
        "<h4>Open issues by workflow label</h4>"
        '<div class="table-view"><table>'
        "<thead><tr><th>Label</th><th>Issues</th></tr></thead>"
        f"<tbody>{label_rows}</tbody></table></div>"
    )

    if drifts:
        drift_rows = "".join(
            f"<tr>"
            f"<td>{html.escape(d.repo)}</td>"
            f"<td>#{d.issue}</td>"
            f"<td>{html.escape(d.status)}</td>"
            f"<td>{html.escape(d.label)}</td>"
            f"<td>{html.escape(d.reason)}</td>"
            f"</tr>"
            for d in sorted(drifts, key=lambda x: (x.repo, x.issue))
        )
        drift_table = (
            f"<h4>Drift ({len(drifts)})</h4>"
            '<div class="table-view"><table>'
            "<thead><tr><th>Repo</th><th>Issue</th><th>Plan Status</th>"
            "<th>Issue label</th><th>Disagreement</th></tr></thead>"
            f"<tbody>{drift_rows}</tbody></table></div>"
        )
    else:
        drift_table = (
            "<h4>Drift (0)</h4>"
            '<p class="card-note">No plan/issue disagreements among the joinable docs.</p>'
        )

    if bad:
        bad_rows = "".join(
            f"<tr><td>{html.escape(d.repo)}</td>"
            f"<td>{html.escape(Path(d.path).name)}</td>"
            f"<td>{html.escape(d.problem)}</td></tr>"
            for d in sorted(bad, key=lambda x: (x.repo, x.path))
        )
        bad_table = (
            f"<h4>Non-conforming Status ({len(bad)})</h4>"
            '<div class="table-view"><table>'
            "<thead><tr><th>Repo</th><th>Doc</th><th>Why the hook would reject it</th></tr></thead>"
            f"<tbody>{bad_rows}</tbody></table></div>"
        )
    else:
        bad_table = ""

    return (
        '<div class="card">\n'
        '      <div class="card-title">Workflow loop</div>\n'
        f'      <p class="card-note">{len(docs)} plan docs, {joinable} carrying an issue '
        f"reference ({joinable * 100 // len(docs) if docs else 0}% joinable); "
        f"{len(issues)} issues collected. Drift is only detectable on the joinable "
        f"subset — the rest are unreported, not clean.</p>\n"
        f"      {status_table}\n"
        f"      {label_table}\n"
        f"      {drift_table}\n"
        f"      {bad_table}\n"
        "    </div>"
    )


def render_loop_region(docs: list[PlanDoc] | None, issues: list[dict[str, Any]] | None) -> str:
    """Return the injectable HTML for the LOOP marker region."""
    return _render_loop(docs, issues)


# ---------------------------------------------------------------------------
# Automated actions tile (GUA-119, Step 8)
# ---------------------------------------------------------------------------


def parse_actions_log(path: Path) -> list[dict[str, Any]]:
    """Read actions.jsonl, parse each line, return list of record dicts.

    Schema per record: {ts, action, outcome, reason, evidence, ...}.
    Outcomes emitted by actions.py: "acted" | "declined".
    Outcomes emitted by meta-wake (human decisions): "accepted" | "rejected" | "deferred".
    Malformed lines are skipped with a warning — a single bad write must not
    break the dashboard render.
    """
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            log.warning("dashboard.actions_log_parse_error", line=i, path=str(path))
    return records


def _render_automated_actions(records: list[dict[str, Any]] | None) -> str:
    """Render the AUTOMATED-ACTIONS marker region from actions.jsonl rows.

    Per action type: proposed, accepted, rejected, auto-acted, declined counts
    and acceptance rate. Every tile states the row count it was computed from
    (denominator convention — "Metric fences", GUA-119 Step 8).

    Empty/missing log renders "no automated actions" — never a fabricated rate.
    """
    if not records:
        return (
            '<section class="chart"><h3>Automated actions</h3>'
            '<p class="note">No automated actions yet. The actions log is written '
            "by the board tick (auto-mutations + retro spawns) and by "
            "<code>/meta-wake</code> (accept/reject decisions). "
            "File: <code>.sounding/telemetry/actions.jsonl</code>.</p>"
            "</section>"
        )

    total = len(records)

    # Per action type: bucket outcomes
    by_type: dict[str, dict[str, int]] = {}
    for rec in records:
        action = rec.get("action", "unknown")
        outcome = rec.get("outcome", "unknown")
        by_type.setdefault(action, {})
        by_type[action][outcome] = by_type[action].get(outcome, 0) + 1

    # Outcome vocabulary — map to display buckets
    # "acted" = auto-mutation ran; "accepted"/"rejected"/"deferred" = human decision;
    # "declined" = guard refused to act.
    _POSITIVE = frozenset({"acted", "accepted"})
    _NEGATIVE = frozenset({"declined", "rejected"})
    _NEUTRAL = frozenset({"deferred"})

    rows_html = ""
    for action_type in sorted(by_type):
        counts = by_type[action_type]
        positive = sum(counts.get(o, 0) for o in _POSITIVE)
        negative = sum(counts.get(o, 0) for o in _NEGATIVE)
        neutral = sum(counts.get(o, 0) for o in _NEUTRAL)
        row_total = sum(counts.values())
        decidable = positive + negative  # excludes deferred
        rate_str = f"{positive * 100 // decidable}%" if decidable else "—"
        rows_html += (
            f"<tr>"
            f"<td>{html.escape(action_type)}</td>"
            f"<td>{positive}</td>"
            f"<td>{negative}</td>"
            f"<td>{neutral}</td>"
            f"<td>{rate_str}</td>"
            f"<td>{row_total}</td>"
            f"</tr>"
        )

    return (
        '<section class="chart"><h3>Automated actions</h3>'
        f'<p class="note">Computed from {total} total records '
        f"in <code>.sounding/telemetry/actions.jsonl</code>. "
        f"Acceptance rate = acted+accepted / (acted+accepted+declined+rejected); "
        f"deferred records excluded from rate denominator.</p>"
        f'<div class="table-view"><table>'
        f"<tr><th>Action type</th><th>Acted / Accepted</th><th>Declined / Rejected</th>"
        f"<th>Deferred</th><th>Acceptance rate</th><th>Total (n)</th></tr>"
        f"{rows_html}"
        f"</table></div>"
        f"</section>"
    )


def render_automated_actions_region(records: list[dict[str, Any]] | None) -> str:
    """Return the injectable HTML for the AUTOMATED-ACTIONS marker region."""
    return _render_automated_actions(records)


# ---------------------------------------------------------------------------
# Insights embedding (GUA-137) — the Overview tab IS the daily insights report
# ---------------------------------------------------------------------------
#
# The report is a standalone document with its own <style>. Embedding it whole
# would let its rules (body{}, h2{}, .tag{}) rewrite the board around it, so the
# body is extracted and every one of its selectors is scoped under a wrapper
# class. Colours stay as the report authored them — it is a guest document with
# its own palette, not a region that should inherit the board's tokens.

_INSIGHTS_SCOPE = "insights-embed"


def _scope_css(css: str, scope: str) -> str:
    """Prefix every selector in `css` with `.scope`, mapping body/html to the wrapper.

    Skips at-rule preludes (@media, @keyframes) — their inner blocks are still
    walked, so a rule nested inside @media gets scoped like any other.
    """
    out: list[str] = []
    i = 0
    while i < len(css):
        brace = css.find("{", i)
        if brace == -1:
            break
        prelude = css[i:brace].strip()

        if prelude.startswith("@"):
            # Nested block (@media/@supports) — scope its interior, copy the prelude.
            if prelude.split()[0] in ("@media", "@supports"):
                close = _matching_brace(css, brace)
                out.append(f"{prelude}{{{_scope_css(css[brace + 1 : close], scope)}}}")
                i = close + 1
                continue
            close = _matching_brace(css, brace)
            out.append(css[i : close + 1])
            i = close + 1
            continue

        close = _matching_brace(css, brace)
        body = css[brace + 1 : close]
        selectors = []
        for sel in prelude.split(","):
            sel = sel.strip()
            if not sel:
                continue
            if sel in ("body", "html", ":root", "html body"):
                selectors.append(f".{scope}")
            else:
                selectors.append(f".{scope} {sel}")
        if selectors:
            out.append(f"{','.join(selectors)}{{{body}}}")
        i = close + 1
    return "".join(out)


def _matching_brace(text: str, open_idx: int) -> int:
    """Index of the `}` matching the `{` at `open_idx`; len(text) if unbalanced."""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(text)


# Which report sections belong to which board tab. The report is one document;
# the board splits it so a reader looking at cost sees cost charts, not a wall.
# Sections not listed stay on the Overview — the default is "leave it where the
# report put it", so a new section added upstream never silently disappears.
INSIGHTS_TAB_SECTIONS: dict[str, tuple[str, ...]] = {
    "cost": ("section-economics",),
    "context": ("section-ce", "section-pe"),
}

# Report sections the board drops outright. Unlike INSIGHTS_TAB_SECTIONS these
# are not re-homed — they are read on the report itself, not the board.
#   section-work  — the projects roster; portfolio.md and the Overview own that.
#   section-usage — the how-you-use-Claude-Code profile; Context Health owns the
#                   same signals as metrics rather than prose.
# The Retro tab keeps only the narrative four: wins, features, patterns, horizon.
INSIGHTS_DROPPED_SECTIONS: tuple[str, ...] = ("section-work", "section-usage")


def _split_report_sections(inner: str) -> tuple[str, dict[str, str]]:
    """Split report HTML into (overview_remainder, {tab: sections_html}).

    Sections are lifted whole, in document order, so each keeps its own header
    and intro text rather than arriving as orphaned charts.
    """
    taken: dict[str, list[str]] = {}
    for tab, section_ids in INSIGHTS_TAB_SECTIONS.items():
        for sid in section_ids:
            m = re.search(rf'<section id="{re.escape(sid)}">.*?</section>', inner, re.DOTALL)
            if not m:
                log.warning("insights.section_missing", section=sid, tab=tab)
                continue
            taken.setdefault(tab, []).append(m.group(0))
            inner = inner.replace(m.group(0), "", 1)
    for sid in INSIGHTS_DROPPED_SECTIONS:
        m = re.search(rf'<section id="{re.escape(sid)}">.*?</section>', inner, re.DOTALL)
        if not m:
            log.warning("insights.section_missing", section=sid, tab="(dropped)")
            continue
        inner = inner.replace(m.group(0), "", 1)
    return inner, {tab: "".join(parts) for tab, parts in taken.items()}


def _drop_div_block(inner: str, class_name: str) -> str:
    """Remove `<div class="{class_name}">…</div>` including nested divs.

    A non-greedy regex stops at the first `</div>`, which for these blocks is an
    inner one — so match the opening tag, then walk to its true partner.
    """
    open_re = re.compile(rf'<div class="{re.escape(class_name)}"[^>]*>')
    while True:
        m = open_re.search(inner)
        if not m:
            return inner
        depth, pos = 1, m.end()
        tag = re.compile(r"<div\b[^>]*>|</div>")
        while depth:
            t = tag.search(inner, pos)
            if not t:  # unbalanced source — leave it rather than truncate
                log.warning("insights.unbalanced_block", block=class_name)
                return inner
            depth += 1 if t.group(0) != "</div>" else -1
            pos = t.end()
        inner = inner[: m.start()] + inner[pos:]


def _strip_report_chrome(inner: str) -> str:
    """Drop the report's standalone framing: header, KPI cards, glance box,
    pull-quote and footer.

    The board supplies its own header and nav, and the KPI numbers live on Cost
    & Efficiency and Context Health. What remains is the narrative sections.
    """
    for pattern in (r"<header[^>]*>.*?</header>", r"<footer[^>]*>.*?</footer>"):
        inner = re.sub(pattern, "", inner, flags=re.DOTALL)
    for block in ("stat-cards", "glance-box", "quote-box"):
        inner = _drop_div_block(inner, block)
    # stat-cards + glance-box share one .container, quote-box has its own; drop
    # any wrapper left holding nothing but whitespace.
    inner = re.sub(r'<div class="container">\s*</div>', "", inner)
    return inner


def render_insights_region(report_path: Path | None, *, today: str | None = None) -> str:
    """Embed the newest insights report as the Overview's content.

    Renders the report's own charts rather than restating its numbers: the
    report is already the daily read, and a second rendering of the same data
    would be one more thing to keep in sync.
    """
    if report_path is None or not report_path.exists():
        return (
            '<div class="card"><div class="card-title">Daily insights</div>'
            '<p class="card-note">No insights report found. Run <code>/meta-insights</code> '
            "to generate one.</p></div>"
        )

    raw = report_path.read_text(encoding="utf-8")

    generated = ""
    m = re.search(r"insights-report-(\d{4}-\d{2}-\d{2})", str(report_path.resolve()))
    if m:
        generated = m.group(1)

    age_note = ""
    if generated and today:
        days = (_date.fromisoformat(today) - _date.fromisoformat(generated)).days
        if days > 1:
            tone = "saturated" if days > 7 else "note"
            age_note = (
                f'<p class="{tone}">Report generated {html.escape(generated)} — '
                f"{days} days old. Run <code>/meta-insights</code> to refresh.</p>"
            )

    styles = "".join(
        _scope_css(m.group(1), _INSIGHTS_SCOPE)
        for m in re.finditer(r"<style[^>]*>(.*?)</style>", raw, re.DOTALL)
    )

    body_m = re.search(r"<body[^>]*>(.*)</body>", raw, re.DOTALL)
    inner = body_m.group(1) if body_m else raw
    # The report's own <script> is dropped: its charts are pure CSS, and an
    # embedded script would run against the board's DOM, not its own.
    inner = re.sub(r"<script[^>]*>.*?</script>", "", inner, flags=re.DOTALL)

    overview_inner, _by_tab = _split_report_sections(inner)
    overview_inner = _strip_report_chrome(overview_inner)

    return (
        f"<style>{styles}</style>"
        f'<div class="card">'
        f'<div class="card-title">Daily insights</div>'
        f'<p class="card-note">The <code>/meta-insights</code> report, rendered inline. '
        f"Token economics moved to Cost &amp; Efficiency; context-engineering and "
        f"prompt-engineering health moved to Context Health. "
        f"Source: <code>{html.escape(report_path.name)}</code>.</p>"
        f"{age_note}"
        f"</div>"
        f'<div class="{_INSIGHTS_SCOPE}">{overview_inner}</div>'
    )


def render_insights_tab_region(
    report_path: Path | None, tab: str, *, today: str | None = None
) -> str:
    """The slice of the insights report belonging to `tab`.

    Styles are emitted with each slice: the tabs are independent marker regions
    and a reader may land on any of them, so each must carry the CSS its own
    charts need rather than depending on the Overview having rendered first.
    """
    if report_path is None or not report_path.exists():
        return (
            f'<p class="empty">No insights report — run <code>/meta-insights</code> '
            f"for {html.escape(tab)} charts.</p>"
        )

    raw = report_path.read_text(encoding="utf-8")
    styles = "".join(
        _scope_css(m.group(1), _INSIGHTS_SCOPE)
        for m in re.finditer(r"<style[^>]*>(.*?)</style>", raw, re.DOTALL)
    )
    body_m = re.search(r"<body[^>]*>(.*)</body>", raw, re.DOTALL)
    inner = body_m.group(1) if body_m else raw
    inner = re.sub(r"<script[^>]*>.*?</script>", "", inner, flags=re.DOTALL)

    _overview, by_tab = _split_report_sections(inner)
    section_html = by_tab.get(tab, "")
    if not section_html:
        return f'<p class="empty">The insights report carries no {html.escape(tab)} section.</p>'

    return f'<style>{styles}</style><div class="{_INSIGHTS_SCOPE}">{section_html}</div>'


# ---------------------------------------------------------------------------
# Retro (GUA-137) — does the improvement loop actually close?
# ---------------------------------------------------------------------------
#
# The three table-only tabs (code review, experiments, workflow loop) answered
# separate questions that are really one question: findings arrive, become
# hypotheses, get scored, and a few graduate. Rendered as tables that chain is
# invisible — 59 experiments with 44 still open reads the same as 59 shipped.
# The funnel makes the drop-off the headline and keeps the tables as detail.

_FUNNEL_STAGES = ("findings", "hypotheses", "scored", "resolved")


def _retro_funnel(
    findings: list[dict[str, Any]] | None,
    experiments: list[Experiment] | None,
    verdict_rows: list[dict[str, Any]] | None,
) -> str:
    """Stage bars for findings → hypotheses → scored → resolved.

    Each bar is scaled to the widest stage, so the shape *is* the attrition.
    A stage with no data renders at zero width with its count stated, never
    omitted — a missing bar would read as a narrower funnel than reality.
    """
    n_findings = len(findings or [])
    exps = experiments or []
    n_hypotheses = len(exps)
    # Scored-but-unknown experiments would make a later stage wider than an
    # earlier one, which a funnel cannot mean. Count only scored rows that
    # correspond to a known hypothesis, and report the orphans separately.
    known = {e.name for e in exps}
    scored_all = {str(r.get("experiment")) for r in (verdict_rows or [])}
    scored = scored_all & known
    orphan_scored = scored_all - known
    n_scored = len(scored)
    resolved = sum(
        1
        for e in exps
        if any(k in e.status.lower() for k in ("verified", "confirmed", "failed", "graduated"))
    )

    stages = [
        ("findings", n_findings, "review findings logged", "var(--s2)"),
        ("hypotheses", n_hypotheses, "ledger rows under test", "var(--s4)"),
        ("scored", n_scored, "experiments with a verdict", "var(--s1)"),
        ("resolved", resolved, "verified, confirmed or failed", "var(--s3)"),
    ]
    peak = max((n for _, n, _, _ in stages), default=0) or 1

    bars = "".join(
        f'<div class="fn-row">'
        f'<div class="fn-head"><span class="fn-name">{html.escape(name)}</span>'
        f'<span class="fn-n">{n:,}</span></div>'
        f'<div class="fn-track"><div class="fn-fill" style="width:{n / peak * 100:.1f}%;'
        f'background:{color}"></div></div>'
        f'<div class="fn-note">{html.escape(note)}</div></div>'
        for name, n, note, color in stages
    )

    # The interesting number is what does NOT make it through.
    open_pct = (n_hypotheses - resolved) / n_hypotheses * 100 if n_hypotheses else 0.0
    verdict = (
        f'<p class="fn-verdict">{n_hypotheses - resolved} of {n_hypotheses} hypotheses '
        f"({open_pct:.0f}%) are still open. A hypothesis that never resolves is not "
        f"evidence of anything — it is a question the loop stopped asking.</p>"
        if n_hypotheses
        else ""
    )
    orphans = (
        f'<p class="fn-orphan">&#9888; {len(orphan_scored)} scored experiment(s) match no '
        f"ledger row — verdicts accumulated against hypotheses that were renamed or "
        f"removed. They are excluded from the funnel above.</p>"
        if orphan_scored
        else ""
    )
    return f'<div class="funnel">{bars}</div>{verdict}{orphans}'


def _verdict_mix(verdict_rows: list[dict[str, Any]] | None) -> str:
    """Latest verdict per experiment, as a proportional bar.

    Latest-per-experiment, not every row: an experiment scored 25 times would
    otherwise outvote one scored twice, and the question is where experiments
    stand now, not how many times the scorer ran.
    """
    if not verdict_rows:
        return '<p class="empty">No scored verdicts yet.</p>'

    latest: dict[str, dict[str, Any]] = {}
    for row in verdict_rows:
        name = str(row.get("experiment"))
        prev = latest.get(name)
        if prev is None or str(row.get("run_at") or "") >= str(prev.get("run_at") or ""):
            latest[name] = row

    counts: dict[str, int] = {}
    for row in latest.values():
        counts[str(row.get("verdict"))] = counts.get(str(row.get("verdict")), 0) + 1

    tone = {
        "confirmed": "var(--good)",
        "trending": "var(--s1)",
        "inconclusive": "var(--text-3)",
        "failed": "var(--bad)",
    }
    total = sum(counts.values()) or 1
    order = sorted(counts.items(), key=lambda kv: -kv[1])

    segs = "".join(
        f'<div class="mix-seg" style="width:{n / total * 100:.1f}%;'
        f'background:{tone.get(v, "var(--s4)")}" '
        f'title="{html.escape(v)}: {n} of {total}"></div>'
        for v, n in order
    )
    legend = "".join(
        f'<span class="mix-key"><i style="background:{tone.get(v, "var(--s4)")}"></i>'
        f"{html.escape(v)} <b>{n}</b></span>"
        for v, n in order
    )
    return (
        f'<div class="mix-bar">{segs}</div><div class="mix-legend">{legend}</div>'
        f'<p class="card-note">Latest verdict per experiment ({total} scored).</p>'
    )


def render_retro_region(
    *,
    findings: list[dict[str, Any]] | None = None,
    experiments: list[Experiment] | None = None,
    verdict_rows: list[dict[str, Any]] | None = None,
    store: Path | None = None,
) -> str:
    """The retro tab: the improvement loop as a funnel, then per-experiment trends."""
    funnel = _retro_funnel(findings, experiments, verdict_rows)
    mix = _verdict_mix(verdict_rows)

    trend_rows = ""
    if experiments:
        scored = {str(r.get("experiment")) for r in (verdict_rows or [])}
        interesting = [e for e in experiments if e.name in scored][:12]
        if interesting:
            trend_rows = "".join(
                f"<tr><td>{html.escape(_truncate(e.name, 70))}</td>"
                f"<td>{html.escape(_truncate(e.status, 60))}</td>"
                f'<td class="trend-cell">{_experiment_trend(e, store)}</td></tr>'
                for e in interesting
            )

    trends = (
        f'<div class="overflow-x"><table class="repo-table">'
        f"<thead><tr><th>Experiment</th><th>Status</th><th>7-day trend</th></tr></thead>"
        f"<tbody>{trend_rows}</tbody></table></div>"
        if trend_rows
        else '<p class="empty">No scored experiments to trend yet.</p>'
    )

    return (
        '<div class="card">\n'
        '      <div class="card-title">Does the loop close?</div>\n'
        '      <p class="card-note">Findings become hypotheses, hypotheses get scored, '
        "a few resolve. The width of each stage is its share of the widest one.</p>\n"
        f"      {funnel}\n"
        "    </div>\n"
        '    <div class="card">\n'
        '      <div class="card-title">Where experiments stand</div>\n'
        f"      {mix}\n"
        "    </div>\n"
        '    <div class="card">\n'
        '      <div class="card-title">Scored experiments — 7-day trend</div>\n'
        '      <p class="card-note">Experiments whose ledger metric has session-data backing. '
        "A blank trend means the metric is a meta-signal nothing can chart.</p>\n"
        f"      {trends}\n"
        "    </div>"
    )


# ---------------------------------------------------------------------------
# Context & orchestration visuals (GUA-137)
# ---------------------------------------------------------------------------
#
# Rebuilt natively from the fact store rather than lifted from an insights
# report. The July-era reports carried these three panels; the current
# LLM-authored report contract dropped them, so embedding an old report would
# freeze them at July numbers. Computed here, they refresh on every --facts run.

_CONTEXT_BUCKETS: tuple[tuple[str, float, float], ...] = (
    ("<50k", 0, 50_000),
    ("50–100k", 50_000, 100_000),
    ("100–150k", 100_000, 150_000),
    (">150k (heavy)", 150_000, float("inf")),
)

_DURATION_BUCKETS: tuple[tuple[str, float, float], ...] = (
    ("<5 min", 0, 5),
    ("5–15 min", 5, 15),
    ("15–45 min", 15, 45),
    ("45–90 min", 45, 90),
    ("90+ min", 90, float("inf")),
)


def _bucket_bars(
    rows: list[dict[str, Any]],
    column: str,
    buckets: tuple[tuple[str, float, float], ...],
    *,
    highlight_last: bool = False,
) -> tuple[str, int]:
    """Horizontal bars over `buckets`, plus the scored row count.

    Rows with a null `column` are excluded and the surviving count is returned
    so the caller can render the frame — a distribution over 319 of 599 rows
    is not a distribution over all sessions, and must not be drawn as one.
    """
    values = [float(r[column]) for r in rows if r.get(column) is not None]
    if not values:
        return '<p class="empty">No data for this metric.</p>', 0

    counts = []
    for label, lo, hi in buckets:
        counts.append((label, sum(1 for v in values if lo <= v < hi)))
    peak = max(n for _, n in counts) or 1

    bars = ""
    for i, (label, n) in enumerate(counts):
        pct = n / len(values) * 100
        is_last = highlight_last and i == len(counts) - 1
        color = "var(--bad)" if is_last and n else "var(--s1)"
        bars += (
            f'<div class="dist-row">'
            f'<div class="dist-label">{html.escape(label)}</div>'
            f'<div class="dist-track"><div class="dist-fill" '
            f'style="width:{n / peak * 100:.1f}%;background:{color}"></div></div>'
            f'<div class="dist-val">{n:,} <span>({pct:.0f}%)</span></div></div>'
        )
    return bars, len(values)


def render_context_orchestration_card(store: Path) -> str:
    """Context-window distribution, cache performance, and subagent orchestration."""
    rows = _work_sessions(read_all(store))

    ctx_bars, ctx_n = _bucket_bars(rows, "max_context", _CONTEXT_BUCKETS, highlight_last=True)
    dur_bars, dur_n = _bucket_bars(rows, "duration_min", _DURATION_BUCKETS)

    # Cache efficiency: reads as a share of all input the model saw.
    reads = sum(float(r.get("cache_read_tokens") or 0) for r in rows)
    writes = sum(float(r.get("cache_write_tokens") or 0) for r in rows)
    fresh = sum(float(r.get("input_tokens") or 0) for r in rows)
    total_in = reads + writes + fresh
    hit = reads / total_in * 100 if total_in else 0.0

    # Subagent orchestration, all-time. The windowed view lives in its own card;
    # this is the shape of parallel work, not its cost trend.
    by_agent, _by_model, spawns = _subagent_totals(store)
    sub_cost = sum(s["cost"] for s in by_agent.values())
    all_cost = sum(float(r.get("cost_units") or 0) for r in rows) or 1.0
    n_transcripts = sum(int(s["n"]) for s in by_agent.values())
    heavy = sum(1 for r in rows if (r.get("max_context") or 0) > 150_000)

    return (
        '<div class="card">\n'
        '      <div class="card-title">Context window &amp; cache</div>\n'
        f'      <p class="card-note">Peak context per session. Above 150k the overflow cannot be '
        f"cached, so each turn costs ~5&times; more. Computed over {ctx_n:,} sessions carrying a "
        f"context reading.</p>\n"
        f'      <div class="dist">{ctx_bars}</div>\n'
        f'      <div class="stat-row" style="margin-top:14px">'
        f'<div class="stat"><span class="value">{hit:.0f}%</span>'
        f'<span class="label">cache hit rate</span></div>'
        f'<div class="stat"><span class="value">{reads / 1e9:,.1f}B</span>'
        f'<span class="label">tokens read from cache</span></div>'
        f'<div class="stat"><span class="value">{heavy:,}</span>'
        f'<span class="label">sessions over 150k</span></div></div>\n'
        "    </div>\n"
        '    <div class="card">\n'
        '      <div class="card-title">Parallelism &amp; subagent orchestration</div>\n'
        '      <p class="card-note">How much work runs in spawned agents rather than the main '
        "loop, and how long sessions run.</p>\n"
        f'      <div class="stat-row">'
        f'<div class="stat"><span class="value">{n_transcripts:,}</span>'
        f'<span class="label">subagent transcripts</span></div>'
        f'<div class="stat"><span class="value">{sub_cost / all_cost * 100:.0f}%</span>'
        f'<span class="label">share of usage</span></div>'
        f'<div class="stat"><span class="value">{sum(spawns.values()):,}</span>'
        f'<span class="label">agents spawned</span></div></div>\n'
        f'      <p class="card-note" style="margin-top:14px">Session duration '
        f"({dur_n:,} sessions timed)</p>\n"
        f'      <div class="dist">{dur_bars}</div>\n'
        "    </div>"
    )


# ---------------------------------------------------------------------------
# Insights KPI panel (GUA-137) — the dashboards/insights-report.html shape
# ---------------------------------------------------------------------------
#
# A different pipeline from librarian's LLM-authored narrative report. That one
# is retrospective prose and belongs on Retro; this is a metrics read: KPIs,
# context/cache distribution, parallelism, response time. Rebuilt from the fact
# store so it refreshes on every --facts run rather than freezing at a snapshot.

_RESPONSE_BUCKETS: tuple[tuple[str, float, float], ...] = (
    ("<1 min", 0, 1),
    ("1–3 min", 1, 3),
    ("3–10 min", 3, 10),
    ("10–30 min", 10, 30),
    ("30+ min", 30, float("inf")),
)


def _kpi(
    label: str,
    value: str,
    sub: str,
    accent: str,
    status: str = "",
    status_tone: str = "",
) -> str:
    """One KPI card. `status` is the optional third line carrying a judgement."""
    status_html = f'<div class="ikpi-status {status_tone}">{status}</div>' if status else ""
    return (
        f'<div class="ikpi {accent}">'
        f'<div class="ikpi-label">{html.escape(label)}</div>'
        f'<div class="ikpi-value">{html.escape(value)}</div>'
        f'<div class="ikpi-sub">{html.escape(sub)}</div>'
        f"{status_html}</div>"
    )


def _fmt_duration(minutes: float) -> str:
    """`2m 42s` / `1h 05m` — the source report's duration idiom."""
    if minutes <= 0:
        return "—"
    if minutes < 60:
        whole = int(minutes)
        secs = round((minutes - whole) * 60)
        if secs == 60:
            whole, secs = whole + 1, 0
        return f"{whole}m {secs:02d}s"
    hours = int(minutes // 60)
    return f"{hours}h {int(minutes - hours * 60):02d}m"


def _hbar(label: str, value: str, pct: float, color: str) -> str:
    """A labelled horizontal bar with the value inside the fill."""
    return (
        f'<div class="hb-row"><div class="hb-label">{html.escape(label)}</div>'
        f'<div class="hb-track"><div class="hb-fill" style="width:{max(pct, 3):.1f}%;'
        f'background:{color}"><span>{html.escape(value)}</span></div></div>'
        f'<div class="hb-val">{html.escape(value)}</div></div>'
    )


def _short_model(name: str) -> str:
    """Trim a model id to its readable tier: claude-haiku-4-5-20251001 -> haiku-4.5."""
    label = name.removeprefix("claude-")
    # Strip a trailing yyyymmdd build stamp; keep the version that precedes it.
    label = re.sub(r"-\d{8}$", "", label)
    # opus-4-6 -> opus-4.6, but leave a bare tier (opus-5) alone.
    return re.sub(r"-(\d+)-(\d+)$", r"-\1.\2", label)


INSIGHTS_WINDOWS: tuple[tuple[str, str, int | None], ...] = (
    ("7d", "7 days", 7),
    ("30d", "30 days", 30),
    ("90d", "90 days", 90),
    ("all", "All time", None),
)
_INSIGHTS_DEFAULT_WINDOW = "30d"

# Cache reads bill at roughly a tenth of fresh input; the saving is that 90%
# discount applied to the share of input that was served from cache.
_CACHE_READ_DISCOUNT = 0.9

_SPAWN_BUCKETS: tuple[tuple[str, float, float], ...] = (
    ("solo", 0, 1),
    ("1 agent", 1, 2),
    ("2–3 agents", 2, 4),
    ("4+ agents", 4, float("inf")),
)


def _spawn_records(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Parsed agent_spawns for a row, or [] when absent or malformed."""
    raw = row.get("agent_spawns")
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _insights_panel(rows: list[dict[str, Any]], store: Path, cutoff: str | None) -> str:
    """One window's worth of the insights read."""
    if not rows:
        return '<p class="empty">No sessions in this window.</p>'

    n = len(rows)
    total_cost = sum(float(r.get("cost_units") or 0) for r in rows)
    dates = {str(r["date"]) for r in rows}
    turns_total = sum(int(r.get("human_turns") or 0) for r in rows)

    durations = [float(r["duration_min"]) for r in rows if r.get("duration_min") is not None]
    med_dur = _percentile(durations, 50) if durations else 0.0
    avg_dur = sum(durations) / len(durations) if durations else 0.0

    reads = sum(float(r.get("cache_read_tokens") or 0) for r in rows)
    writes = sum(float(r.get("cache_write_tokens") or 0) for r in rows)
    fresh = sum(float(r.get("input_tokens") or 0) for r in rows)
    total_in = reads + writes + fresh
    hit = reads / total_in * 100 if total_in else 0.0
    saved = (reads * _CACHE_READ_DISCOUNT) / total_in * 100 if total_in else 0.0

    compacted = sum(1 for r in rows if r.get("compacted"))
    compact_pct = compacted / n * 100 if n else 0.0

    by_agent, _bm, spawns = _subagent_totals(store, since=cutoff)
    sub_n = sum(int(s["n"]) for s in by_agent.values())
    sub_cost = sum(s["cost"] for s in by_agent.values())
    sub_share = sub_cost / total_cost * 100 if total_cost else 0.0
    heavy = sum(1 for r in rows if (r.get("max_context") or 0) > 150_000)
    heavy_cost = sum(
        float(r.get("cost_units") or 0) for r in rows if (r.get("max_context") or 0) > 150_000
    )
    heavy_share = heavy_cost / total_cost * 100 if total_cost else 0.0

    ba_rows = [r for r in rows if r.get("bash_antipatterns") is not None]
    ba_total = sum(int(r["bash_antipatterns"]) for r in ba_rows)
    ba_avg = ba_total / len(ba_rows) if ba_rows else 0.0
    interruptions = sum(int(r.get("user_interruptions") or 0) for r in rows)
    hook_blocks = sum(int(r.get("hook_blocks") or 0) for r in rows)

    # --- headline row: cost and efficiency levers ---------------------------
    headline = "".join(
        [
            _kpi(
                "Total cost units", f"{total_cost / 1e9:,.2f}B", "usage_cost_units", "accent-left"
            ),
            _kpi("Sessions", f"{n:,}", f"{len(dates)} active days", "accent-teal"),
            _kpi(
                "Turns / day",
                f"{turns_total / len(dates):,.0f}" if dates else "—",
                f"{turns_total:,} total",
                "accent-blue",
            ),
            _kpi(
                "Compact rate",
                f"{compact_pct:.0f}%",
                f"{compacted:,} of {n:,} sessions",
                "accent-green",
                "&#10003; Active context management"
                if compact_pct >= 40
                else "&#9888; Low — context runs long",
                "good" if compact_pct >= 40 else "warn",
            ),
        ]
    )

    # --- context + cache ----------------------------------------------------
    ctx_bars, ctx_n = _bucket_bars(rows, "max_context", _CONTEXT_BUCKETS, highlight_last=True)
    heavy_pct = heavy / ctx_n * 100 if ctx_n else 0.0
    ctx_flag = (
        f'<p class="dist-flag bad"><b>{heavy_pct:.0f}%</b> of sessions exceed 150k context '
        f"— high risk of cost degradation</p>"
        if heavy_pct >= 10
        else ""
    )

    # --- subagent concurrency + activity + attribution ----------------------
    spawn_counts = [float(len(_spawn_records(r))) for r in rows]
    conc_bars, _conc_n = _bucket_bars(
        [{"spawns": c} for c in spawn_counts], "spawns", _SPAWN_BUCKETS
    )
    type_counts: dict[str, int] = {}
    for r in rows:
        for rec in _spawn_records(r):
            key = str(rec.get("type") or "unknown")
            type_counts[key] = type_counts.get(key, 0) + 1

    palette = [
        "var(--ac-violet)",
        "var(--ac-teal)",
        "var(--ac-blue)",
        "var(--ac-orange)",
        "var(--ac-rose)",
        "var(--ac-green)",
    ]
    type_total = sum(type_counts.values()) or 1
    type_bars = (
        "".join(
            _hbar(
                name,
                f"{cnt / type_total * 100:.0f}%",
                cnt / max(type_counts.values()) * 100,
                palette[i % len(palette)],
            )
            for i, (name, cnt) in enumerate(sorted(type_counts.items(), key=lambda kv: -kv[1])[:6])
        )
        or '<p class="empty">No agent spawns recorded in this window.</p>'
    )

    attr_bars = ""
    if by_agent:
        top = sorted(by_agent.items(), key=lambda kv: -kv[1]["cost"])[:6]
        peak = top[0][1]["cost"] or 1
        attr_bars = "".join(
            _hbar(
                name,
                f"{st['cost'] / sub_cost * 100:.0f}%" if sub_cost else "0%",
                st["cost"] / peak * 100,
                palette[i % len(palette)],
            )
            for i, (name, st) in enumerate(top)
        )

    out_tokens = [float(r["output_tokens"]) for r in rows if r.get("output_tokens")]
    o50 = _percentile(out_tokens, 50) if out_tokens else 0.0
    o75 = _percentile(out_tokens, 75) if out_tokens else 0.0
    o90 = _percentile(out_tokens, 90) if out_tokens else 0.0
    dur_bars, dur_n = _bucket_bars(rows, "duration_min", _RESPONSE_BUCKETS)

    # --- secondary row: quality signals, below the graphs -------------------
    secondary = "".join(
        [
            _kpi(
                "Bash antipatterns",
                f"{ba_total:,}",
                f"{ba_avg:.1f} per session avg",
                "accent-orange",
                "&#9888; High — needs attention" if ba_avg > 10 else "&#10003; Within range",
                "bad" if ba_avg > 10 else "good",
            ),
            _kpi(
                "Interruptions", f"{interruptions:,}", f"Hook blocks: {hook_blocks:,}", "accent-red"
            ),
            _kpi(
                "Median session",
                _fmt_duration(med_dur),
                f"avg {_fmt_duration(avg_dur)}",
                "accent-violet" if False else "accent-blue",
            ),
            _kpi(
                "Subagent sessions",
                f"{sub_n:,}",
                f"{sub_share:.0f}% of usage · {heavy} heavy",
                "accent-left",
                f"&#9889; {heavy_share:.0f}% usage in heavy sessions",
                "warn" if heavy_share > 40 else "",
            ),
        ]
    )

    return (
        f'<div class="ikpi-grid four">{headline}</div>\n'
        '<div class="card-row">'
        '<div class="card" style="flex:1">'
        '<div class="card-title">Context usage distribution</div>'
        f'<p class="card-note">Peak context per session, over {ctx_n:,} sessions carrying a '
        f"reading. Above 150k the overflow cannot be cached.</p>"
        f'<div class="dist">{ctx_bars}</div>{ctx_flag}</div>'
        '<div class="card" style="flex:1">'
        '<div class="card-title">Cache efficiency</div>'
        f'<div class="mini-stats">'
        f'<div><b style="color:var(--good)">{hit:.0f}%</b><span>Hit rate</span></div>'
        f'<div><b style="color:var(--ac-teal)">{saved:.0f}%</b><span>Cost saved</span></div>'
        f'<div><b style="color:var(--ac-blue)">{reads / 1e9:,.2f}B</b><span>Cache read</span></div>'
        f'<div><b style="color:var(--ac-violet)">{writes / 1e6:,.0f}M</b>'
        f"<span>Cache write</span></div></div>"
        f'<div class="meter"><div class="meter-head"><span>Cache hit rate</span>'
        f'<span class="meter-pct">{hit:.0f}%</span></div><div class="meter-track">'
        f'<div class="meter-fill" style="width:{hit:.1f}%;background:var(--good)"></div></div></div>'
        f'<div class="meter"><div class="meter-head"><span>Cost savings vs uncached</span>'
        f'<span class="meter-pct">{saved:.0f}%</span></div><div class="meter-track">'
        f'<div class="meter-fill" style="width:{saved:.1f}%;background:var(--ac-teal)">'
        f"</div></div></div>"
        f'<p class="dist-note">{reads / max(writes, 1):.1f}&times; more cache reads than writes — '
        f"prefix caching is working across sessions.</p></div></div>\n"
        '<div class="card-row">'
        '<div class="card" style="flex:1">'
        '<div class="card-title">Subagent concurrency</div>'
        '<p class="card-note">Agents spawned per session. Session <em>overlap</em> needs '
        "start/end timestamps the fact store does not capture — this is agents-per-session, "
        "not concurrent sessions.</p>"
        f'<div class="dist">{conc_bars}</div></div>'
        '<div class="card" style="flex:1">'
        '<div class="card-title">Subagent activity</div>'
        f'<div class="mini-stats">'
        f"<div><b>{sub_n:,}</b><span>Transcripts</span></div>"
        f'<div><b style="color:var(--ac-teal)">{sub_share:.0f}%</b><span>Share of usage</span></div>'
        f'<div><b style="color:var(--ac-orange)">{heavy}</b><span>Heavy sessions</span></div>'
        f'<div><b style="color:var(--ac-rose)">{heavy_share:.0f}%</b>'
        f"<span>Heavy usage</span></div></div>"
        f'<p class="card-note" style="margin-top:8px">Agents by type</p>'
        f'<div class="hbars">{type_bars}</div></div></div>\n'
        '<div class="card-row">'
        '<div class="card" style="flex:1">'
        '<div class="card-title">Subagent attribution</div>'
        '<p class="card-note">Share of subagent spend by agent type. <em>unattributed</em> is a '
        "coverage gap, not an agent.</p>"
        f'<div class="hbars">{attr_bars or "<p class='empty'>No subagent spend.</p>"}</div>'
        f'<p class="dist-note">{sub_n:,} transcripts · {sum(spawns.values()):,} agents spawned · '
        f"{sub_share:.0f}% of all usage</p></div>"
        '<div class="card" style="flex:1">'
        '<div class="card-title">Output tokens per session</div>'
        '<p class="card-note">Output bills ~5&times; input — the primary cost lever.</p>'
        f'<div class="mini-stats">'
        f"<div><b>{o50 / 1000:,.0f}k</b><span>Median</span></div>"
        f'<div><b style="color:var(--ac-blue)">{o75 / 1000:,.0f}k</b><span>p75</span></div>'
        f'<div><b style="color:var(--ac-orange)">{o90 / 1000:,.0f}k</b><span>p90</span></div>'
        f"</div></div></div>\n"
        '<div class="card">'
        '<div class="card-title">Session duration</div>'
        f'<p class="card-note">Wall-clock per session, over {dur_n:,} timed sessions. '
        f"Per-request response time needs timestamps the fact store does not capture.</p>"
        f'<div class="dist">{dur_bars}</div></div>\n'
        f'<div class="ikpi-grid four" style="margin-top:12px">{secondary}</div>'
    )


# ---------------------------------------------------------------------------
# Split KPI regions — Session Health + Context Health (GUA-137)
# ---------------------------------------------------------------------------


def _dual_chart_svg(
    p50_points: list[Point],
    p90_points: list[Point],
    color1: str,
    color2: str,
    *,
    width: int = 420,
    height: int = 140,
    unit: str = "count",
    threshold: float | None = None,
    threshold_label: str = "",
) -> str:
    """SVG line chart with p50 + p90 dual series and optional threshold line."""
    all_points = p50_points + p90_points
    if not all_points:
        return '<p class="empty">no data</p>'
    pad_left = 48
    pad_bottom = 18
    plot_w = width - pad_left
    plot_h = height - pad_bottom
    values = [p.value for p in all_points]
    lo, hi = min(values), max(values)
    if threshold is not None:
        lo = min(lo, threshold * 0.95)
        hi = max(hi, threshold * 1.05)
    span = (hi - lo) or 1.0

    def _x(i: int, n: int) -> float:
        return pad_left + i * (plot_w / max(n - 1, 1))

    def _y(v: float) -> float:
        return plot_h - ((v - lo) / span) * (plot_h - 20) - 10

    def _polyline(pts: list[Point], color: str, dashed: bool = False) -> str:
        if not pts:
            return ""
        n = len(pts)
        coords = " ".join(f"{_x(i, n):.1f},{_y(p.value):.1f}" for i, p in enumerate(pts))
        dash = ' stroke-dasharray="4,3"' if dashed else ""
        dots = "".join(
            f'<circle cx="{_x(i, n):.1f}" cy="{_y(p.value):.1f}" r="3" '
            f'fill="{color}" opacity="0.7"><title>{html.escape(p.date)}: '
            f"{_fmt_value(p.value, unit)} (n={p.n})</title></circle>"
            for i, p in enumerate(pts)
        )
        return (
            f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round"{dash}/>{dots}'
        )

    # threshold dashed line
    thresh_svg = ""
    if threshold is not None:
        ty = _y(threshold)
        thresh_svg = (
            f'<line x1="{pad_left}" y1="{ty:.1f}" x2="{width}" y2="{ty:.1f}" '
            f'stroke="var(--text-3)" stroke-width="1" stroke-dasharray="6,4" opacity="0.5"/>'
            f'<text x="{width - 2}" y="{ty - 4:.1f}" text-anchor="end" '
            f'class="axis-label" fill="var(--text-3)" opacity="0.7">'
            f"{html.escape(threshold_label or _fmt_value(threshold, unit))}</text>"
        )

    # grid lines (3 horizontal)
    grid = ""
    for i in range(4):
        gv = lo + span * i / 3
        gy = _y(gv)
        grid += f'<line x1="{pad_left}" y1="{gy:.1f}" x2="{width}" y2="{gy:.1f}" stroke="var(--grid)" stroke-width="1"/>'

    # y-axis labels
    y_labels = (
        f'<text x="{pad_left - 4}" y="{_y(hi):.1f}" text-anchor="end" '
        f'dominant-baseline="middle" class="axis-label">{html.escape(_fmt_value(hi, unit))}</text>'
        f'<text x="{pad_left - 4}" y="{_y(lo):.1f}" text-anchor="end" '
        f'dominant-baseline="middle" class="axis-label">{html.escape(_fmt_value(lo, unit))}</text>'
    )

    # x-axis date labels
    ref = p50_points or p90_points
    x_labels = ""
    if len(ref) > 14:
        seen: set[str] = set()
        for i, p in enumerate(ref):
            m = p.date[:7]
            if m not in seen:
                seen.add(m)
                x_labels += (
                    f'<text x="{_x(i, len(ref)):.1f}" y="{height - 2}" text-anchor="middle" '
                    f'class="axis-label">{_MONTH_ABBR[int(p.date[5:7])]}</text>'
                )
    elif ref:
        x_labels = (
            f'<text x="{_x(0, len(ref)):.1f}" y="{height - 2}" text-anchor="start" '
            f'class="axis-label">{html.escape(ref[0].date[5:])}</text>'
            f'<text x="{_x(len(ref) - 1, len(ref)):.1f}" y="{height - 2}" text-anchor="end" '
            f'class="axis-label">{html.escape(ref[-1].date[5:])}</text>'
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" preserveAspectRatio="none">'
        f"{grid}{thresh_svg}"
        f"{_polyline(p50_points, color1)}"
        f"{_polyline(p90_points, color2, dashed=True)}"
        f"{y_labels}{x_labels}</svg>"
    )


def _cost_efficiency_panel(rows: list[dict[str, Any]], store: Path, cutoff: str | None) -> str:
    """Cost & Efficiency: headline KPIs + the 3x2 token/cost/cache chart grid.

    Split from Session Health (2026-08-19): the six token charts answer "where did
    effort go", which is this tab's question. Session Health keeps the behavioural
    half (profile, parallelism, duration, friction). Workspace totals moved here
    too — what the effort landed against belongs next to the effort. Both panels
    still run through `_windowed_region`, so the window toggle drives them
    independently.
    """
    if not rows:
        return '<p class="empty">No sessions in this window.</p>'

    n = len(rows)
    total_cost = sum(float(r.get("cost_units") or 0) for r in rows)
    dates = {str(r["date"]) for r in rows}
    turns_total = sum(int(r.get("human_turns") or 0) for r in rows)

    headline = "".join(
        [
            _kpi(
                "Total cost units",
                f"{total_cost / 1e9:,.2f}B",
                "usage_cost_units",
                "accent-left",
            ),
            _kpi("Sessions", f"{n:,}", f"{len(dates)} active days", "accent-teal"),
            _kpi(
                "Turns / day",
                f"{turns_total / len(dates):,.0f}" if dates else "\u2014",
                f"{turns_total:,} total",
                "accent-blue",
            ),
        ]
    )

    # Build daily aggregates
    by_day: dict[str, dict[str, list[float]]] = {}
    for r in rows:
        d = str(r["date"])
        day = by_day.setdefault(d, {"cost": [], "cache": [], "out": [], "in": [], "compact": []})
        day["cost"].append(float(r.get("cost_units") or 0))
        inp = float(r.get("input_tokens") or 0) + float(r.get("cache_read_tokens") or 0)
        day["in"].append(inp)
        day["out"].append(float(r.get("output_tokens") or 0))
        reads = float(r.get("cache_read_tokens") or 0)
        writes = float(r.get("cache_write_tokens") or 0)
        fresh = float(r.get("input_tokens") or 0)
        total_in = reads + writes + fresh
        day["cache"].append(reads / total_in * 100 if total_in else 0.0)
        day["compact"].append(1.0 if r.get("compacted") else 0.0)

    sorted_days = sorted(by_day.keys())

    def _pts(key: str, agg: str) -> list[Point]:
        result = []
        for d in sorted_days:
            vals = by_day[d][key]
            if not vals:
                continue
            if agg == "p50":
                v = _percentile(vals, 50)
            elif agg == "p90":
                v = _percentile(vals, 90)
            elif agg == "sum":
                v = sum(vals)
            elif agg == "mean":
                v = sum(vals) / len(vals)
            elif agg == "pct":
                v = sum(vals) / len(vals) * 100  # fraction → %
            else:
                v = sum(vals) / len(vals)
            result.append(Point(date=d, value=v, regime="", n=len(vals)))
        return result

    def _chart(
        title: str,
        note: str,
        p50: list[Point],
        p90: list[Point],
        c1: str,
        c2: str,
        unit: str,
        threshold: float | None = None,
        thresh_label: str = "",
    ) -> str:
        if not p50 and not p90:
            return (
                f'<div class="card" style="flex:1"><div class="card-title">{title}</div>'
                f'<p class="empty">No data</p></div>'
            )
        ref = p50 or p90
        vals = [p.value for p in ref]
        med = _percentile(vals, 50) if vals else 0.0
        tail = _percentile(vals, 90) if vals else 0.0
        # Check threshold breach
        breach = ""
        if threshold is not None and ref:
            last_3 = [p.value for p in ref[-3:]]
            avg_recent = sum(last_3) / len(last_3) if last_3 else 0.0
            if (unit == "pct" and avg_recent < threshold) or (
                unit != "pct" and avg_recent > threshold
            ):
                breach = (
                    f'<p class="dist-flag bad" style="margin-top:6px">'
                    f"Recent average ({_fmt_value(avg_recent, unit)}) "
                    f"{'below' if unit == 'pct' else 'above'} threshold "
                    f"({_fmt_value(threshold, unit)})</p>"
                )
        chart = _dual_chart_svg(
            p50,
            p90,
            c1,
            c2,
            width=420,
            height=140,
            unit=unit,
            threshold=threshold,
            threshold_label=thresh_label,
        )
        return (
            f'<div class="card" style="flex:1"><div class="card-title">{title}</div>'
            f'<p class="card-note">{note}</p>'
            f'<div class="mini-stats" style="margin-bottom:6px">'
            f'<div><b style="color:{c1}">{_fmt_value(med, unit)}</b><span>p50</span></div>'
            f'<div><b style="color:{c2}">{_fmt_value(tail, unit)}</b><span>p90</span></div>'
            f"<div><b>{len(ref)}</b><span>days</span></div></div>"
            f'<div class="chart-wrap" style="height:140px">{chart}</div>'
            f"{breach}</div>"
        )

    return (
        f'<div class="ikpi-grid four" style="grid-template-columns:repeat(3,1fr)">{headline}</div>\n'
        # Row 1: cost + cache
        '<div class="card-row">'
        + _chart(
            "Cost per session",
            "Lower is better. Solid = p50, dashed = p90.",
            _pts("cost", "p50"),
            _pts("cost", "p90"),
            "var(--s1)",
            "var(--s2)",
            "cost",
        )
        + _chart(
            "Cache hit rate",
            "Higher is better. Below 95% = context churn.",
            _pts("cache", "mean"),
            [],
            "var(--good)",
            "var(--good)",
            "pct",
            threshold=95.0,
            thresh_label="95%",
        )
        + "</div>\n"
        # Row 2: output tokens
        '<div class="card-row">'
        + _chart(
            "Output tokens / session",
            "Output bills 5\u00d7 input. Solid = p50, dashed = p90.",
            _pts("out", "p50"),
            _pts("out", "p90"),
            "var(--s2)",
            "var(--s4)",
            "tokens",
        )
        + _chart(
            "Output tokens / day",
            "Daily output volume. Dashed threshold = p90 day (heavy).",
            _pts("out", "sum"),
            [],
            "var(--s2)",
            "var(--s2)",
            "tokens",
            threshold=(
                _percentile(
                    [sum(by_day[d]["out"]) for d in sorted_days if by_day[d]["out"]],
                    90,
                )
                if len(sorted_days) > 2
                else None
            ),
            thresh_label="p90 day",
        )
        + "</div>\n"
        # Row 3: input tokens
        '<div class="card-row">'
        + _chart(
            "Input tokens / session",
            "Fresh input + cache reads. Solid = p50, dashed = p90.",
            _pts("in", "p50"),
            _pts("in", "p90"),
            "var(--s3)",
            "var(--s4)",
            "tokens",
        )
        + _chart(
            "Input tokens / day",
            "Daily intake. Dashed threshold = p90 day.",
            _pts("in", "sum"),
            [],
            "var(--s3)",
            "var(--s3)",
            "tokens",
            threshold=(
                _percentile(
                    [sum(by_day[d]["in"]) for d in sorted_days if by_day[d]["in"]],
                    90,
                )
                if len(sorted_days) > 2
                else None
            ),
            thresh_label="p90 day",
        )
        + "</div>\n"
        + _repo_totals_card(store, cutoff)
        + _repo_effort_card(store, cutoff)
    )


def _session_health_panel(rows: list[dict[str, Any]], store: Path, cutoff: str | None) -> str:
    """Session Health: how sessions *behaved* — shape, parallelism, duration, friction.

    Deliberately excludes the token/cost/cache grid and the workspace totals,
    both of which moved to `_cost_efficiency_panel`. What stays answers "how did
    the session run", not "what did it cost": context distribution, agent
    concurrency, wall-clock duration, and friction signals.

    `store` and `cutoff` are unused here but required by the `_windowed_region`
    panel signature.
    """
    if not rows:
        return '<p class="empty">No sessions in this window.</p>'

    n = len(rows)
    turns_total = sum(int(r.get("human_turns") or 0) for r in rows)
    turn_vals = [float(r["human_turns"]) for r in rows if r.get("human_turns") is not None]
    single_turn = sum(1 for v in turn_vals if v <= 1)

    # Friction signals — moved here from Context Health (2026-08-19). These are
    # properties of how a session ran, not of how context was managed.
    interruptions = sum(int(r.get("user_interruptions") or 0) for r in rows)
    ba_rows = [r for r in rows if r.get("bash_antipatterns") is not None]
    ba_total = sum(int(r["bash_antipatterns"]) for r in ba_rows)
    err_total = sum(int(r.get("tool_error_count") or 0) for r in rows)

    # Four friction boxes directly under the window toggle (2026-08-19): turns,
    # interruptions, tool failures, bash antipatterns. Sessions moved into the
    # turns subtitle rather than taking a box of its own — it is the denominator
    # the other three are read against, not a friction signal.
    headline = "".join(
        [
            _kpi(
                "Turns / session",
                f"{_percentile(turn_vals, 50):,.0f}" if turn_vals else "—",
                f"{turns_total:,} turns over {n:,} sessions · "
                f"{single_turn * 100 // n if n else 0}% single-turn",
                "accent-blue",
            ),
            _kpi(
                "Interruptions",
                f"{interruptions:,}",
                f"{interruptions / n:.2f} per session" if n else "—",
                "accent-left",
            ),
            _kpi(
                "Tool failures",
                f"{err_total:,}",
                f"{err_total / n:.1f} per session" if n else "—",
                "accent-orange",
            ),
            _kpi(
                "Bash antipatterns",
                f"{ba_total:,}" if ba_rows else "—",
                (
                    f"{ba_total / len(ba_rows):.1f} per session · {len(ba_rows):,} of {n:,} scored"
                    if ba_rows
                    else "column absent in this window"
                ),
                "accent-red",
            ),
        ]
    )

    fence = (
        f'<p style="font-size:11px;color:var(--text-3);margin-top:8px;font-style:italic">'
        f"Antipattern counts computed over {len(ba_rows):,} of {n:,} sessions that carry the "
        f"column; tool failures and interruptions over all {n:,}.</p>"
    )

    return (
        f'<div class="ikpi-grid four">{headline}</div>\n'
        f"{fence}"
        '<div style="border-top:1px solid var(--border);margin:28px 0 20px"></div>\n'
        '<h3 style="font-size:15px;font-weight:600;margin-bottom:16px">'
        "Session Profile</h3>\n" + _session_health_viz(rows, n)
    )


def _repo_effort_card(store: Path, cutoff: str | None) -> str:
    """Session cost and landed commits per repo, windowed to the panel's cutoff.

    Was a hand-written static table frozen at "since Jul 15" (2026-08-19); made
    windowed so the Cost & Efficiency toggle drives it like every other panel.

    Cost is split across the repos a session worked in, weighted by records under
    each `cwd` — 22% of sessions touch more than one, so assigning a whole session
    to a single winner would misattribute real spend.

    The cost column is July-forward regardless of the window: `session_repos` is
    derived from JSONL `cwd` records the note era never captured, so a 90d or
    all-time window cannot extend it earlier (JULY_ONLY_METRICS). Commits carry no
    such fence, so the card states the effective cost floor rather than implying
    the two columns cover the same span.

    Deliberately NOT divided: Ramsey commits, always, so a cost-per-commit ratio
    would read as Claude-authored output (see gitstore.ATTRIBUTION).
    """
    floor = max(cutoff or JULY_BOUNDARY, JULY_BOUNDARY)

    cost_by_repo: dict[str, float] = {}
    attributed = 0.0
    total = 0.0
    for row in _work_sessions(read_all(store)):
        day = str(row.get("date") or "")
        if day < floor:
            continue
        cost = float(row.get("cost_units") or 0.0)
        total += cost
        try:
            repos: dict[str, int] = json.loads(row.get("session_repos") or "{}")
        except (json.JSONDecodeError, TypeError):
            repos = {}
        if not repos:
            continue
        attributed += cost
        records = sum(repos.values())
        for repo, count in repos.items():
            cost_by_repo[repo] = cost_by_repo.get(repo, 0.0) + cost * count / records

    commits_by_repo: dict[str, int] = {}
    for row in read_git_activity(store):
        day = str(row.get("date") or "")
        if cutoff is not None and day < cutoff:
            continue
        human = int(row.get("commits") or 0) - int(row.get("commits_bot") or 0)
        if human <= 0:
            continue
        commits_by_repo[str(row["repo"])] = commits_by_repo.get(str(row["repo"]), 0) + human

    if not cost_by_repo and not commits_by_repo:
        return ""

    # Repos with 10 or fewer commits in the window are omitted, matching the
    # static table this replaced: a repo touched once or twice adds a row of
    # noise without changing the effort picture.
    repos = sorted(
        (r for r in set(cost_by_repo) | set(commits_by_repo) if commits_by_repo.get(r, 0) > 10),
        key=lambda r: -cost_by_repo.get(r, 0.0),
    )
    if not repos:
        return ""
    top = max((cost_by_repo.get(r, 0.0) for r in repos), default=0.0)

    rows_html = "".join(
        f"<tr><td>{html.escape(r)}</td>"
        f"<td>{cost_by_repo.get(r, 0.0) / 1e6:,.1f}M</td>"
        f'<td class="bar-cell"><div class="repo-bar" style="width:'
        f'{(cost_by_repo.get(r, 0.0) / top * 100) if top else 0:.0f}%"></div></td>'
        f"<td>{commits_by_repo.get(r, 0)}</td></tr>"
        for r in repos
    )

    unattributed = total - attributed
    share = (unattributed / total * 100) if total else 0.0
    fenced = floor != (cutoff or JULY_BOUNDARY) or cutoff is None or cutoff < JULY_BOUNDARY
    fence_note = (
        f" Cost is July-forward only (from {html.escape(JULY_BOUNDARY)}) — the note era "
        f"captured no <code>cwd</code> records — while commits span the full window, so "
        f"the two columns do not cover the same span."
        if fenced
        else ""
    )

    return (
        '<div class="card">'
        '<div class="card-title">Repo effort &amp; outcome</div>'
        '<p class="card-note">Session cost and landed commits per repo. These are '
        "<strong>deliberately not divided</strong> — Ramsey commits, so a cost-per-commit "
        "ratio would read as Claude-authored output.</p>"
        '<div class="overflow-x"><table class="repo-table">'
        '<thead><tr><th>Repo</th><th>Cost</th><th class="bar-cell"></th><th>Commits</th></tr></thead>'
        f"<tbody>{rows_html}</tbody></table></div>"
        f'<p style="font-size:11px;color:var(--text-3);margin-top:8px;font-style:italic">'
        f"Repos with 10 or fewer commits in this window are omitted. "
        f"Cost split across repos by session cwd records. "
        f"{unattributed / 1e6:,.1f}M cost units ({share:.0f}%) ran at the workspace root and "
        f"name no repo — excluded rather than assigned to one. A repo with cost and zero "
        f"commits means spend without landed work, not a missing join.{fence_note}</p>"
        "</div>"
    )


def _repo_totals_card(store: Path, cutoff: str | None) -> str:
    """Workspace totals (commits, churn, PRs), windowed to the panel's cutoff.

    Rendered once per window panel so the Session Health toggle drives it. Git
    facts are per-day (git_activity) and per-PR (pull_requests), both dated, so
    the same cutoff that filters sessions filters these — no separate anchor.

    NOT a Claude-productivity metric and not joinable to a session: Ramsey
    commits, always, so the Co-Authored-By trailer is absent by policy and its
    absence means nothing (see gitstore.ATTRIBUTION). Read as workspace throughput.
    """
    activity = [r for r in read_git_activity(store) if cutoff is None or str(r["date"]) >= cutoff]
    prs = [
        p for p in read_prs(store) if cutoff is None or str(p.get("created_date") or "") >= cutoff
    ]
    if not activity and not prs:
        return ""

    commits = sum(r["commits"] for r in activity)
    bot = sum(r["commits_bot"] for r in activity)
    insertions = sum(r["insertions"] for r in activity)
    deletions = sum(r["deletions"] for r in activity)
    repos = len({r["repo"] for r in activity})
    human_prs = [p for p in prs if not p["is_bot"]]
    merged = sum(p["merged"] for p in human_prs)

    tiles = [
        (f"{commits - bot:,}", "human commits"),
        (f"{bot:,}", "bot commits"),
        (f"+{insertions:,}", "lines added"),
        (f"-{deletions:,}", "lines removed"),
        (f"{len(human_prs)}", "human PRs"),
        (f"{merged}", "PRs merged"),
        (f"{repos}", "active repos"),
    ]
    tile_html = "".join(
        f'<div class="stat"><span class="value">{html.escape(v)}</span>'
        f'<span class="label">{html.escape(label)}</span></div>'
        for v, label in tiles
    )
    span = "all time" if cutoff is None else f"since {html.escape(cutoff)}"
    return (
        '<div style="border-top:1px solid var(--border);margin:28px 0 20px"></div>\n'
        '<h3 style="font-size:15px;font-weight:600;margin-bottom:16px">Totals</h3>\n'
        '<div class="card">'
        f'<div class="card-title">Workspace totals ({span})</div>'
        '<p class="card-note">What landed in the repos over this window. Not joinable '
        "to a session &mdash; Ramsey commits, always, so read these as workspace "
        "throughput rather than Claude output.</p>"
        f'<div class="stat-row">{tile_html}</div>'
        '<p style="font-size:11px;color:var(--text-3);margin-top:8px;font-style:italic">'
        "Churn counts source files only &mdash; PDFs, notebooks, lockfiles, vendored "
        "course material and bundled plugin JS are excluded. PRs are counted by "
        "creation date.</p>"
        "</div>"
    )


def _session_health_viz(rows: list[dict[str, Any]], n: int) -> str:
    """Context dist, session parallelism, response time — gradient viz cards."""
    # Context usage distribution
    # Vertical columns, mirroring Session Duration (2026-08-19): both are
    # bucketed distributions over the same sessions, so they read as one pair
    # only if they share an orientation.
    ctx_buckets = [
        ("<50k", 0, 50_000, "linear-gradient(180deg,#4ade80,#22d3a0)"),
        ("50\u2013100k", 50_000, 100_000, "linear-gradient(180deg,#6ab8f7,#7c6af7)"),
        ("100\u2013150k", 100_000, 150_000, "linear-gradient(180deg,#fbbf24,#f7936a)"),
        (">150k", 150_000, float("inf"), "linear-gradient(180deg,#f76a8a,#f7406a)"),
    ]
    ctx_counts = []
    for label, lo, hi, grad in ctx_buckets:
        cnt = sum(1 for r in rows if lo <= (r.get("max_context") or 0) < hi)
        ctx_counts.append((label, cnt, grad))
    peak_ctx = max((c for _, c, _ in ctx_counts), default=1) or 1
    ctx_bars = "".join(
        f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px">'
        f'<div style="font-size:10px;color:var(--text-1);font-weight:600">{cnt}</div>'
        f'<div style="width:100%;height:{max(cnt / peak_ctx * 80, 2):.0f}px;'
        f'border-radius:4px 4px 0 0;background:{grad}"></div>'
        f'<div style="font-size:10px;color:var(--text-3)">{html.escape(lbl)}</div>'
        f'<div style="font-size:10px;color:var(--text-2)">{cnt * 100 // n if n else 0}%</div>'
        f"</div>"
        for lbl, cnt, grad in ctx_counts
    )
    heavy = sum(1 for r in rows if (r.get("max_context") or 0) >= 150_000)
    heavy_pct = heavy * 100 / n if n else 0
    ctx_flag = (
        f'<p class="dist-flag bad" style="margin-top:8px"><b>{heavy_pct:.0f}%</b> of sessions '
        f"exceed 150k \u2014 cost degradation risk</p>"
        if heavy_pct >= 15
        else ""
    )

    # Session parallelism
    solo = sum(1 for r in rows if len(_spawn_records(r)) == 0)
    para_23 = sum(1 for r in rows if 1 <= len(_spawn_records(r)) <= 3)
    para_4p = sum(1 for r in rows if len(_spawn_records(r)) >= 4)
    pt = solo + para_23 + para_4p or 1
    para_bar = (
        f'<div class="mix-bar">'
        f'<div class="mix-seg" style="flex:{solo};background:#4ade80">{solo * 100 // pt}%</div>'
        f'<div class="mix-seg" style="flex:{para_23};background:#7c6af7">{para_23 * 100 // pt}%</div>'
        f'<div class="mix-seg" style="flex:{para_4p};background:#f76a8a">{para_4p * 100 // pt}%</div>'
        f"</div>"
        f'<div style="display:flex;gap:14px;margin-top:8px;font-size:11px;color:var(--text-2)">'
        f'<span style="display:flex;align-items:center;gap:4px">'
        f'<span style="width:8px;height:8px;border-radius:50%;background:#4ade80"></span>'
        f"Solo {solo * 100 // pt}%</span>"
        f'<span style="display:flex;align-items:center;gap:4px">'
        f'<span style="width:8px;height:8px;border-radius:50%;background:#7c6af7"></span>'
        f"2\u20133 {para_23 * 100 // pt}%</span>"
        f'<span style="display:flex;align-items:center;gap:4px">'
        f'<span style="width:8px;height:8px;border-radius:50%;background:#f76a8a"></span>'
        f"4+ {para_4p * 100 // pt}%</span></div>"
    )

    # Response time distribution
    dur_buckets = [
        ("<1m", 0, 1, "linear-gradient(180deg,#4ade80,#22d3a0)"),
        ("1\u20133m", 1, 3, "linear-gradient(180deg,#6ab8f7,#56cfb2)"),
        ("3\u201310m", 3, 10, "linear-gradient(180deg,#7c6af7,#6ab8f7)"),
        ("10\u201330m", 10, 30, "linear-gradient(180deg,#fbbf24,#f7936a)"),
        ("30m+", 30, float("inf"), "linear-gradient(180deg,#f76a8a,#c04080)"),
    ]
    dur_rows = [r for r in rows if r.get("duration_min") is not None]
    dur_counts = []
    for label, lo, hi, grad in dur_buckets:
        cnt = sum(1 for r in dur_rows if lo <= float(r["duration_min"]) < hi)
        dur_counts.append((label, cnt, grad))
    dur_peak = max((c for _, c, _ in dur_counts), default=1) or 1
    dur_vals = [float(r["duration_min"]) for r in dur_rows]
    med_dur = _percentile(dur_vals, 50) if dur_vals else 0.0
    avg_dur = sum(dur_vals) / len(dur_vals) if dur_vals else 0.0
    rt_bars = "".join(
        f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px">'
        f'<div style="font-size:10px;color:var(--text-1);font-weight:600">{cnt}</div>'
        f'<div style="width:100%;height:{max(cnt / dur_peak * 80, 2):.0f}px;'
        f'border-radius:4px 4px 0 0;background:{grad}"></div>'
        f'<div style="font-size:10px;color:var(--text-3)">{html.escape(lbl)}</div></div>'
        for lbl, cnt, grad in dur_counts
    )

    # Main-loop model mix — the fourth quadrant. Source is sessions.models, which
    # is populated on every row, so it needs no window fence. Turns, not cost:
    # subagent spend is a different unit and lives on Context Health.
    palette = ("var(--ac-violet)", "var(--ac-teal)", "var(--ac-orange)", "var(--s2)", "var(--s5)")
    models: dict[str, int] = {}
    for r in rows:
        try:
            for model, turns in json.loads(r.get("models") or "{}").items():
                models[model] = models.get(model, 0) + int(turns)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    model_turns = sum(models.values())
    top_models = sorted(models.items(), key=lambda kv: -kv[1])[:5]
    model_bars = (
        "".join(
            _hbar(
                _short_model(name),
                f"{cnt / model_turns * 100:.0f}%",
                cnt / top_models[0][1] * 100,
                palette[i % len(palette)],
            )
            for i, (name, cnt) in enumerate(top_models)
        )
        if model_turns
        else '<p class="empty">No model data in this window.</p>'
    )

    return (
        '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:16px">'
        '<div class="card">'
        '<div class="card-title">Context Window</div>'
        f'<p class="card-note">{n:,} sessions by peak context.</p>'
        f'<div style="display:flex;gap:6px;align-items:flex-end;height:90px;margin-top:12px">'
        f"{ctx_bars}</div>{ctx_flag}</div>"
        '<div class="card">'
        '<div class="card-title">Session Parallelism</div>'
        f'<p class="card-note">{n:,} sessions \u2014 agent concurrency.</p>'
        f'<div style="margin-top:12px">{para_bar}</div></div>'
        '<div class="card">'
        '<div class="card-title">Session Duration</div>'
        f'<p class="card-note">{len(dur_rows):,} timed. '
        f"Median {_fmt_duration(med_dur)}, avg {_fmt_duration(avg_dur)}.</p>"
        f'<div style="display:flex;gap:6px;align-items:flex-end;height:90px;margin-top:12px">'
        f"{rt_bars}</div></div>"
        '<div class="card">'
        '<div class="card-title">Model Usage</div>'
        f'<p class="card-note">Assistant turns by model. Policy: opus-5 is the session '
        f"default; fable is verdict-only.</p>"
        f'<div class="hbars model-usage" style="margin-top:12px">{model_bars}</div>'
        f'<p class="dist-note">{model_turns:,} turns · {len(models)} models</p></div>'
        "</div>"
    )


_ERROR_KIND_COLORS = {
    "command_failed": "var(--ac-rose)",
    "file_not_found": "var(--ac-orange)",
    "read_before_write": "var(--ac-teal)",
    "blocked_by_hook": "var(--ac-violet)",
}


_DISPATCH_TIERS = ("haiku", "sonnet", "fable", "opus")


def _routing_gap_card(rows: list[dict[str, Any]], by_model: dict[str, dict[str, float]]) -> str:
    """What the dispatch asked for vs what the spend says actually ran.

    `agent_spawns[].model` is the tier named on the Agent call; `subagent_costs.
    by_model` is where the money went. They are different units — a dispatch count
    and a cost — so they are shown as two shares of their own totals, never
    subtracted. The gap that matters is a spawn with no model at all: it inherits
    the session model (opus by default), so an unspecified dispatch is a routing
    decision made by omission rather than by policy.
    """
    requested: dict[str, int] = {}
    unspecified = 0
    for row in rows:
        for rec in _spawn_records(row):
            tier = str(rec.get("model") or "")
            if not tier:
                unspecified += 1
                continue
            requested[tier] = requested.get(tier, 0) + 1
    total_spawns = sum(requested.values()) + unspecified

    spend: dict[str, float] = {}
    for name, stats in by_model.items():
        short = _short_model(name)
        tier = next((t for t in _DISPATCH_TIERS if t in short), short)
        spend[tier] = spend.get(tier, 0.0) + stats["cost"]
    total_spend = sum(spend.values())

    if not total_spawns and not total_spend:
        return (
            '<div class="card">'
            '<div class="card-title">Model routing gap</div>'
            '<p class="empty">No dispatch or subagent-spend data in this window.</p></div>'
        )

    tiers = [t for t in _DISPATCH_TIERS if requested.get(t) or spend.get(t)]
    rows_html = "".join(
        f'<div class="hb-row"><div class="hb-label">{tier}</div>'
        f'<div class="hb-track">'
        f'<div class="hb-fill" style="width:{requested.get(tier, 0) / total_spawns * 100 if total_spawns else 0:.0f}%;'
        f'background:var(--ac-teal)"></div></div>'
        f'<div class="hb-val">{requested.get(tier, 0) / total_spawns * 100 if total_spawns else 0:.0f}%</div>'
        f'<div class="hb-track">'
        f'<div class="hb-fill" style="width:{spend.get(tier, 0.0) / total_spend * 100 if total_spend else 0:.0f}%;'
        f'background:var(--ac-rose)"></div></div>'
        f'<div class="hb-val">{spend.get(tier, 0.0) / total_spend * 100 if total_spend else 0:.0f}%</div>'
        f"</div>"
        for tier in tiers
    )

    unspec_share = unspecified / total_spawns * 100 if total_spawns else 0.0
    flag = ""
    if unspec_share > 20:
        flag = (
            f'<p class="dist-note" style="color:var(--warn)">&#9888; '
            f"{unspec_share:.0f}% of dispatches name no model — those inherit the session "
            f"model rather than the policy tier.</p>"
        )

    return (
        '<div class="card">'
        '<div class="card-title">Model routing gap</div>'
        '<p class="card-note">Share of <span style="color:var(--ac-teal);font-weight:600">'
        'dispatches</span> vs share of <span style="color:var(--ac-rose);font-weight:600">'
        "subagent spend</span>, by tier. Policy: haiku for fan-out, sonnet for bounded "
        "execution. A tier that takes far more spend than dispatches is doing work it "
        "was not asked to do.</p>"
        # Column header: two tracks share one .hb-row, so the reader needs to know
        # which half is which before the bars mean anything.
        '<div class="hb-row" style="margin-bottom:6px">'
        '<div class="hb-label"></div>'
        '<div class="hb-track" style="background:none;height:auto">'
        '<span style="font-size:10px;text-transform:uppercase;letter-spacing:0.04em;'
        'color:var(--ac-teal);font-weight:600">dispatches</span></div>'
        '<div class="hb-val"></div>'
        '<div class="hb-track" style="background:none;height:auto">'
        '<span style="font-size:10px;text-transform:uppercase;letter-spacing:0.04em;'
        'color:var(--ac-rose);font-weight:600">spend</span></div>'
        '<div class="hb-val"></div></div>'
        f'<div class="hbars">{rows_html}</div>'
        f'<p class="dist-note">{total_spawns:,} dispatches · '
        f"{_fmt_value(total_spend, 'cost')} subagent spend</p>{flag}</div>"
    )


def _error_breakdown_card(rows: list[dict[str, Any]]) -> str:
    """Tool failures ranked by kind, windowed with the rest of the panel.

    Shares the `tool_errors` column with the full failure-kinds region, but that
    one groups by *who* the failure implicates; this is the flat ranked view the
    2x2 needs. Kinds, not tools — the two columns cannot be joined.
    """
    kinds: dict[str, int] = {}
    calls = 0
    for row in rows:
        raw = row.get("tool_errors")
        if not raw:
            continue
        try:
            parsed: dict[str, int] = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        for kind, n in parsed.items():
            kinds[kind] = kinds.get(kind, 0) + int(n)
        calls += _tool_call_total(row)

    body = '<p class="empty">No tool-error data in this window.</p>'
    if kinds:
        top = sorted(kinds.items(), key=lambda kv: -kv[1])[:6]
        peak = top[0][1] or 1
        total = sum(kinds.values())
        body = "".join(
            _hbar(
                name.replace("_", " "),
                f"{cnt:,}",
                cnt / peak * 100,
                _ERROR_KIND_COLORS.get(name, "var(--ac-blue)"),
            )
            for name, cnt in top
        )
        rate = f"{total / calls * 100:.2f} per 100 calls" if calls else "rate unavailable"
        body = (
            f'<div class="hbars">{body}</div><p class="dist-note">{total:,} failures · {rate}</p>'
        )

    return (
        '<div class="card">'
        '<div class="card-title">Error Type Breakdown</div>'
        '<p class="card-note">Tool failures by kind. <code>blocked_by_hook</code> is a '
        "guard working, not a defect — read it against the others, not with them.</p>"
        f"{body}</div>"
    )


def _context_health_panel(rows: list[dict[str, Any]], store: Path, cutoff: str | None) -> str:
    """Context Health KPI panel: subagent concurrency, activity, attribution,
    bash antipatterns, interruptions, hook blocks."""
    if not rows:
        return '<p class="empty">No sessions in this window.</p>'

    total_cost = sum(float(r.get("cost_units") or 0) for r in rows)

    by_agent, _bm, spawns = _subagent_totals(store, since=cutoff)
    sub_n = sum(int(s["n"]) for s in by_agent.values())
    sub_cost = sum(s["cost"] for s in by_agent.values())
    sub_share = sub_cost / total_cost * 100 if total_cost else 0.0
    heavy = sum(1 for r in rows if (r.get("max_context") or 0) > 150_000)
    heavy_cost = sum(
        float(r.get("cost_units") or 0) for r in rows if (r.get("max_context") or 0) > 150_000
    )
    heavy_share = heavy_cost / total_cost * 100 if total_cost else 0.0

    # Friction signals (interruptions, bash antipatterns, hook blocks) moved to
    # Session Health 2026-08-19 — they describe how a session ran, not how context was
    # managed. What replaces them is compaction discipline.
    #
    # `compact_trigger` is null on sessions that never compacted, so the denominator is
    # compacted sessions only: an "auto" share over all sessions would dilute with
    # sessions that had nothing to compact. An auto trigger is direct evidence the
    # proactive-compaction rule was NOT followed — the session hit the threshold before
    # a phase boundary rescued it.
    compacted = [r for r in rows if r.get("compact_trigger")]
    auto_n = sum(1 for r in compacted if str(r["compact_trigger"]) == "auto")
    auto_share = auto_n * 100 / len(compacted) if compacted else 0.0
    tslc = [
        float(r["turns_since_last_compact"])
        for r in rows
        if r.get("turns_since_last_compact") is not None
    ]

    palette = [
        "var(--ac-violet)",
        "var(--ac-teal)",
        "var(--ac-blue)",
        "var(--ac-orange)",
        "var(--ac-rose)",
        "var(--ac-green)",
    ]

    type_counts: dict[str, int] = {}
    for r in rows:
        for rec in _spawn_records(r):
            key = str(rec.get("type") or "unknown")
            type_counts[key] = type_counts.get(key, 0) + 1
    type_total = sum(type_counts.values()) or 1
    type_bars = (
        "".join(
            _hbar(
                name,
                f"{cnt / type_total * 100:.0f}%",
                cnt / max(type_counts.values()) * 100,
                palette[i % len(palette)],
            )
            for i, (name, cnt) in enumerate(sorted(type_counts.items(), key=lambda kv: -kv[1])[:6])
        )
        or '<p class="empty">No agent spawns recorded.</p>'
    )

    attr_bars = ""
    if by_agent:
        top = sorted(by_agent.items(), key=lambda kv: -kv[1]["cost"])[:6]
        peak = top[0][1]["cost"] or 1
        attr_bars = "".join(
            _hbar(
                name,
                f"{st['cost'] / sub_cost * 100:.0f}%" if sub_cost else "0%",
                st["cost"] / peak * 100,
                palette[i % len(palette)],
            )
            for i, (name, st) in enumerate(top)
        )

    # Subagent spend by model. Main-loop model share lives on Session Health — it is a
    # property of how the session itself ran, not of the work that fanned out.
    sub_model_cost = sum(s["cost"] for s in _bm.values())
    sub_model_n = sum(int(s["n"]) for s in _bm.values())
    sub_model_bars = (
        "".join(
            _hbar(
                _short_model(name),
                f"{st['cost'] / sub_model_cost * 100:.0f}%",
                st["cost"] / max(s["cost"] for s in _bm.values()) * 100,
                palette[i % len(palette)],
            )
            for i, (name, st) in enumerate(sorted(_bm.items(), key=lambda kv: -kv[1]["cost"])[:6])
        )
        if sub_model_cost
        else '<p class="empty">No subagent model data in this window.</p>'
    )

    quality = "".join(
        [
            _kpi(
                "Compaction discipline",
                f"{auto_share:.0f}% auto" if compacted else "—",
                (
                    f"{auto_n} of {len(compacted):,} compactions"
                    if compacted
                    else "no compactions in window"
                ),
                "accent-orange",
                (
                    "&#9888; Auto-rescued — compact at phase boundaries"
                    if auto_share > 50
                    else "&#10003; Mostly proactive"
                ),
                "bad" if auto_share > 50 else "good",
            ),
            _kpi(
                "Turns before compaction",
                f"{_percentile(tslc, 50):,.0f}" if tslc else "—",
                f"p50 over {len(tslc):,} compacted sessions",
                "accent-red",
            ),
            _kpi(
                "Subagent sessions",
                f"{sub_n:,}",
                f"{sub_share:.0f}% of usage \u00b7 {heavy} heavy",
                "accent-left",
                f"&#9889; {heavy_share:.0f}% usage in heavy sessions",
                "warn" if heavy_share > 40 else "",
            ),
        ]
    )

    return (
        # KPI row
        f'<div class="ikpi-grid four" style="grid-template-columns:repeat(3,1fr)">{quality}</div>\n'
        # 2x2: the four subagent/error frames. Concurrency and Main-loop model were
        # dropped from this tab 2026-08-19 \u2014 they describe session shape, not the
        # economics of spawned work, and Session Health already carries that frame.
        '<div class="grid-2x2">'
        '<div class="card">'
        '<div class="card-title">Subagent Activity</div>'
        f'<div class="mini-stats">'
        f"<div><b>{sub_n:,}</b><span>Transcripts</span></div>"
        f'<div><b style="color:var(--ac-teal)">{sub_share:.0f}%</b><span>Share of usage</span></div>'
        f'<div><b style="color:var(--ac-orange)">{heavy}</b><span>Heavy sessions</span></div>'
        f'<div><b style="color:var(--ac-rose)">{heavy_share:.0f}%</b>'
        f"<span>Heavy usage</span></div></div>"
        f'<p class="card-note" style="margin-top:8px">Agents by type</p>'
        f'<div class="hbars">{type_bars}</div></div>'
        '<div class="card">'
        '<div class="card-title">Subagent model</div>'
        '<p class="card-note">Spawned-agent spend by model. '
        "Policy: haiku for fan-out, sonnet for bounded execution.</p>"
        f'<div class="hbars">{sub_model_bars}</div>'
        f'<p class="dist-note">{sub_model_n:,} agents \u00b7 '
        f"{_fmt_value(sub_model_cost, 'cost')} attributed</p></div>"
        '<div class="card">'
        '<div class="card-title">Subagent Attribution</div>'
        '<p class="card-note">Share of subagent spend by type. '
        "<em>unattributed</em> = coverage gap.</p>"
        f'<div class="hbars">{attr_bars or "<p class=empty>No subagent spend.</p>"}</div>'
        f'<p class="dist-note">{sub_n:,} transcripts \u00b7 {sum(spawns.values()):,} agents \u00b7 '
        f"{sub_share:.0f}% of usage</p></div>"
        f"{_routing_gap_card(rows, _bm)}"
        "</div>"
    )


def _windowed_region(store: Path, panel_fn) -> str:
    """Shared windowing wrapper for Session Health and Context Health."""
    all_rows = _work_sessions(read_all(store))
    if not all_rows:
        return '<p class="empty">No session data yet.</p>'

    newest = max(str(r["date"]) for r in all_rows)
    panels, buttons = [], []
    for key, label, days in INSIGHTS_WINDOWS:
        cutoff = (_date.fromisoformat(newest) - timedelta(days=days)).isoformat() if days else None
        rows = [r for r in all_rows if cutoff is None or str(r["date"]) >= cutoff]
        is_default = key == _INSIGHTS_DEFAULT_WINDOW
        buttons.append(
            f'<button type="button" class="win-btn{" active" if is_default else ""}" '
            f'data-win="{key}">{label}</button>'
        )
        hidden = "" if is_default else ' style="display:none"'
        panels.append(
            f'<div class="win-panel" data-win="{key}"{hidden}>{panel_fn(rows, store, cutoff)}</div>'
        )

    frame = (
        f'<p class="card-note">Windowed to the most recent data '
        f"(newest observation {html.escape(newest)}). Percentiles and shares are "
        f"computed over the selected window only.</p>"
    )
    return (
        f'<div class="win-toggle" role="group" aria-label="Time window">'
        f"{''.join(buttons)}</div>\n{frame}\n{''.join(panels)}"
    )


def render_session_health_region(store: Path) -> str:
    """Windowed Session Health region: session shape, parallelism, duration, friction."""
    return _windowed_region(store, _session_health_panel)


def render_cost_efficiency_region(store: Path) -> str:
    """Windowed Cost & Efficiency region: the token/cost/cache chart grid."""
    return _windowed_region(store, _cost_efficiency_panel)


def render_context_health_kpi_region(store: Path) -> str:
    """Windowed Context Health region: subagents, antipatterns, hooks."""
    return _windowed_region(store, _context_health_panel)


def render_insights_kpi_region(store: Path) -> str:
    """The metrics insights read, windowed 7d/30d/90d/all.

    All windows are computed server-side and emitted together; the toggle only
    changes which is visible, so switching never re-reads the store. Windowing
    matters here beyond freshness: an all-time view of subagent attribution is
    dominated by pre-CLI-2.1.201 transcripts that structurally cannot carry a
    name, which buries how well recent work is attributed.
    """
    all_rows = _work_sessions(read_all(store))
    if not all_rows:
        return '<p class="empty">No session data yet.</p>'

    newest = max(str(r["date"]) for r in all_rows)
    panels, buttons = [], []
    for key, label, days in INSIGHTS_WINDOWS:
        cutoff = (_date.fromisoformat(newest) - timedelta(days=days)).isoformat() if days else None
        rows = [r for r in all_rows if cutoff is None or str(r["date"]) >= cutoff]
        is_default = key == _INSIGHTS_DEFAULT_WINDOW
        buttons.append(
            f'<button type="button" class="win-btn{" active" if is_default else ""}" '
            f'data-win="{key}">{label}</button>'
        )
        hidden = "" if is_default else ' style="display:none"'
        panels.append(
            f'<div class="win-panel" data-win="{key}"{hidden}>'
            f"{_insights_panel(rows, store, cutoff)}</div>"
        )

    frame = (
        f'<p class="card-note">Windowed to the most recent data '
        f"(newest observation {html.escape(newest)}). Percentiles and shares are computed "
        f"over the selected window only.</p>"
    )
    return (
        f'<div class="win-toggle" role="group" aria-label="Insights window">'
        f"{''.join(buttons)}</div>\n{frame}\n{''.join(panels)}"
    )


def render_token_grid_region(store: Path) -> str:
    """Input and output tokens, each per-session and per-day — a true 2x2.

    Per-session answers "how heavy is a typical session"; per-day answers "how
    much am I doing". They move independently — fewer, larger sessions raise one
    and lower the other — so neither substitutes for the other.
    """
    rows = _work_sessions(read_all(store))
    if not rows:
        return '<p class="empty">No session data yet.</p>'

    by_day: dict[str, dict[str, float]] = {}
    for r in rows:
        day = by_day.setdefault(str(r["date"]), {"in": 0.0, "out": 0.0, "n": 0.0})
        day["in"] += float(r.get("input_tokens") or 0) + float(r.get("cache_read_tokens") or 0)
        day["out"] += float(r.get("output_tokens") or 0)
        day["n"] += 1

    def _pts(key: str) -> list[Point]:
        return [
            Point(date=d, value=v[key], regime="", n=int(v["n"])) for d, v in sorted(by_day.items())
        ]

    in_session = [
        float(r.get("input_tokens") or 0) + float(r.get("cache_read_tokens") or 0) for r in rows
    ]
    out_session = [float(r.get("output_tokens") or 0) for r in rows]

    def _panel(title: str, note: str, p50: float, p90: float, pts: list[Point], unit: str) -> str:
        return (
            '<div class="card">'
            f'<div class="card-title">{title}</div>'
            f'<p class="card-note">{note}</p>'
            f'<div class="mini-stats">'
            f"<div><b>{_fmt_value(p50, unit)}</b><span>p50</span></div>"
            f'<div><b style="color:var(--ac-orange)">{_fmt_value(p90, unit)}</b>'
            f"<span>p90</span></div></div>"
            f'<div class="trend-cell">{_sparkline_svg(pts[-14:], unit=unit)}</div>'
            "</div>"
        )

    return (
        '<div class="grid-2x2">'
        + _panel(
            "Input tokens per session",
            "Fresh input plus cache reads. Cache reads bill at ~10% of fresh input.",
            _percentile(in_session, 50) if in_session else 0.0,
            _percentile(in_session, 90) if in_session else 0.0,
            _pts("in"),
            "tokens",
        )
        + _panel(
            "Input tokens per day",
            "Daily intake across every session. Grows with volume, not session size.",
            _percentile([v["in"] for v in by_day.values()], 50) if by_day else 0.0,
            _percentile([v["in"] for v in by_day.values()], 90) if by_day else 0.0,
            _pts("in"),
            "tokens",
        )
        + _panel(
            "Output tokens per session",
            "Output bills ~5&times; input — the primary cost lever.",
            _percentile(out_session, 50) if out_session else 0.0,
            _percentile(out_session, 90) if out_session else 0.0,
            _pts("out"),
            "tokens",
        )
        + _panel(
            "Output tokens per day",
            "Daily output volume. The 14-day trend is under each figure.",
            _percentile([v["out"] for v in by_day.values()], 50) if by_day else 0.0,
            _percentile([v["out"] for v in by_day.values()], 90) if by_day else 0.0,
            _pts("out"),
            "tokens",
        )
        + "</div>"
    )


# ---------------------------------------------------------------------------
# Pipeline health region (GUA-138)
# ---------------------------------------------------------------------------

_RETRO_HEADER = re.compile(r"^## R\d+", re.MULTILINE)
_INSIGHTS_DATE = re.compile(r"^## \d{4}-\d{2}-\d{2}", re.MULTILINE)
_FEEDBACK_RUN_HEADER = re.compile(r"^# Feedback Run\s*[—-]\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)
_GROWTH_ENTRY = re.compile(r"^\[(?:discovered|confirmed|corrected)\]", re.MULTILINE)


def _age_label(dt: _datetime | None, *, now: _datetime) -> tuple[str, str]:
    """Return (glyph, text) describing how long ago *dt* was.

    Freshness thresholds:
      green  ✓  < 24 h
      yellow ⚠  1–7 d
      red    ✗  > 7 d  or never seen
    """
    if dt is None:
        return "✗", "never"
    delta = now - dt
    hours = delta.total_seconds() / 3600
    if hours < 24:
        if hours < 1:
            mins = int(delta.total_seconds() / 60)
            return "✓", f"{mins}m ago"
        return "✓", f"{int(hours)}h ago"
    days = int(hours / 24)
    if days == 1:
        return "⚠", "1d ago"
    if days <= 7:
        return "⚠", f"{days}d ago"
    return "✗", f"{days}d ago"


def _cell_style(glyph: str) -> str:
    if glyph == "✓":
        return "color:var(--good)"
    if glyph == "⚠":
        return "color:var(--warn)"
    return "color:var(--bad)"


def render_pipeline_health_region(store: Path, sounding_root: Path | None = None) -> str:
    """Compact pipeline-health card for the Loop Health tab.

    Reads five sources to answer whether each stage of the metacognition
    pipeline last ran recently:

    * Capture  — ``sessions.db`` mtime  (librarian-owned; guacamayo reads it)
    * Insights — ``insights-log.md`` max date header
    * Feedback — ``feedback-log.md`` last ``# Feedback Run`` header (grey when never run)
    * Retro    — ``tooling-ledger-log.md`` last ``## R<N>`` header
    * Config   — ``tooling-ledger.md`` open hypothesis count

    Color coding: green (<24 h), yellow (1–7 d), red (>7 d or absent).
    Each cell also renders the row count used so the frame is always visible.

    Only Capture comes from *store*; the other four live under guacamayo's
    ``.sounding/``. Per D1 the store default points at librarian's DB, so
    deriving the sounding root from *store* resolves into librarian and every
    stage but Capture silently reads a non-existent path and renders "never" —
    a dead-looking loop that is actually alive. Callers pass *sounding_root*
    explicitly; the store-relative fallback is kept only for the co-located
    layout used by tests.
    """
    now = _datetime.now(UTC)
    if sounding_root is None:
        sounding_root = store.parent.parent / ".sounding"

    # ── Capture: sessions.db mtime ──────────────────────────────────────────
    cap_dt: _datetime | None = None
    cap_rows: int = 0
    if store.exists():
        mtime = store.stat().st_mtime
        cap_dt = _datetime.fromtimestamp(mtime, tz=UTC)
        # Row count from the factstore (already loaded elsewhere; cheap re-read here)
        try:
            rows = read_all(store)
            cap_rows = len(rows)
        except Exception:
            cap_rows = 0
    cap_glyph, cap_label = _age_label(cap_dt, now=now)

    # ── Insights: latest date header in insights-log.md ─────────────────────
    ins_dt: _datetime | None = None
    ins_path = sounding_root / "insights" / "insights-log.md"
    if ins_path.exists():
        text = ins_path.read_text(encoding="utf-8", errors="replace")
        dates = _INSIGHTS_DATE.findall(text)
        if dates:
            latest = max(d.lstrip("# ").strip() for d in dates)
            try:
                ins_dt = _datetime.fromisoformat(latest).replace(tzinfo=UTC)
            except ValueError:
                pass
    ins_glyph, ins_label = _age_label(ins_dt, now=now)

    # ── Retro: last ## R<N> header in tooling-ledger-log.md ─────────────────
    retro_dt: _datetime | None = None
    retro_label_text = "never"
    ledger_log = sounding_root / "tooling-ledger-log.md"
    if ledger_log.exists():
        text = ledger_log.read_text(encoding="utf-8", errors="replace")
        headers = _RETRO_HEADER.findall(text)
        if headers:
            # tooling-ledger-log.md sections are NOT chronological (R0, R1, R10, R11, R9…R2).
            # Pick the header whose date is latest; fall back to highest round number.
            best_header = None
            best_dt: _datetime | None = None
            best_round = -1
            for hdr in headers:
                idx = text.find(hdr)
                snippet = text[idx : idx + 120]
                date_m = re.search(r"\d{4}-\d{2}-\d{2}", snippet)
                round_m = re.search(r"## R(\d+)", hdr)
                round_n = int(round_m.group(1)) if round_m else -1
                if date_m:
                    try:
                        dt = _datetime.fromisoformat(date_m.group()).replace(tzinfo=UTC)
                        if best_dt is None or dt > best_dt:
                            best_dt = dt
                            best_header = hdr
                            best_round = round_n
                    except ValueError:
                        pass
                if best_dt is None and round_n > best_round:
                    best_round = round_n
                    best_header = hdr
            last_header = best_header  # e.g. "## R11"
            # Find the matching occurrence to extract date
            idx = text.find(last_header)
            snippet = text[idx : idx + 120]
            date_match = re.search(r"\d{4}-\d{2}-\d{2}", snippet)
            if date_match:
                try:
                    retro_dt = _datetime.fromisoformat(date_match.group()).replace(tzinfo=UTC)
                    retro_label_text = f"{last_header.strip()} · {date_match.group()}"
                except ValueError:
                    retro_label_text = last_header.strip()
            else:
                retro_label_text = last_header.strip()
    retro_glyph, retro_age = _age_label(retro_dt, now=now)

    # ── Config: open hypothesis count in tooling-ledger.md ──────────────────
    hyp_count = 0
    ledger_active = sounding_root / "tooling-ledger.md"
    if ledger_active.exists():
        text = ledger_active.read_text(encoding="utf-8", errors="replace")
        # Count non-header table rows (hypothesis rows start with |)
        rows_found = [
            ln
            for ln in text.splitlines()
            if ln.startswith("|") and not re.match(r"\|[-\s|]+\|", ln)
        ]
        # Subtract the header row
        hyp_count = max(0, len(rows_found) - 1)

    # ── Feedback: last # Feedback Run header in feedback-log.md ─────────────
    # Manual gate, but still observable: a gate that never fires is exactly what
    # a "healthy" pipeline would otherwise hide. Absent log renders grey "never
    # run" rather than red, so an unfired gate reads as awaiting its first run.
    fb_dt: _datetime | None = None
    fb_path = sounding_root / "telemetry" / "feedback-log.md"
    if fb_path.exists():
        dates = _FEEDBACK_RUN_HEADER.findall(fb_path.read_text(encoding="utf-8", errors="replace"))
        if dates:
            try:
                fb_dt = _datetime.fromisoformat(max(dates)).replace(tzinfo=UTC)
            except ValueError:
                fb_dt = None
    if fb_dt is None:
        fb_glyph, fb_label = "—", "never run"
        fb_detail, fb_style = "manual gate — not yet run", "color:var(--text-3)"
    else:
        fb_glyph, fb_label = _age_label(fb_dt, now=now)
        fb_detail, fb_style = "manual gate", _cell_style(fb_glyph)

    def _stage(name: str, glyph: str, label: str, detail: str, style: str) -> str:
        return (
            f'<div class="ph-cell" style="{style}">'
            f'<div class="ph-name">{html.escape(name)}</div>'
            f'<div class="ph-glyph">{glyph}</div>'
            f'<div class="ph-label">{html.escape(label)}</div>'
            f'<div class="ph-detail" style="font-size:11px;color:var(--text-3)">'
            f"{html.escape(detail)}</div>"
            f"</div>"
        )

    config_label = f"{hyp_count} pending" if hyp_count else "0 pending"
    config_style = "color:var(--warn)" if hyp_count > 5 else "color:var(--text-2)"

    cells = "".join(
        [
            _stage("Capture", cap_glyph, cap_label, f"{cap_rows} rows", _cell_style(cap_glyph)),
            _stage(
                "Insights",
                ins_glyph,
                ins_label,
                ins_path.name if ins_path.exists() else "not found",
                _cell_style(ins_glyph),
            ),
            _stage("Feedback", fb_glyph, fb_label, fb_detail, fb_style),
            _stage("Retro", retro_glyph, retro_age, retro_label_text, _cell_style(retro_glyph)),
            _stage("Config", "·", config_label, "open hypotheses", config_style),
        ]
    )

    return (
        '<div class="card">'
        '<div class="card-title">Pipeline health</div>'
        '<p class="card-note">Each stage of the metacognition pipeline — last run time '
        "and freshness. Green &lt;24 h, yellow 1–7 d, red &gt;7 d or never. "
        "Feedback is a permanent human gate — manual, but still aged, so a gate "
        "that never fires cannot hide behind a healthy loop.</p>"
        f'<div class="ph-grid" style="display:flex;gap:12px;flex-wrap:wrap;margin-top:12px">'
        f"{cells}</div>"
        '<p style="font-size:11px;color:var(--text-3);margin-top:8px;font-style:italic">'
        "Capture = sessions.db mtime; Insights = insights-log.md max date; "
        "Feedback = feedback-log.md last run header; "
        "Retro = tooling-ledger-log.md last R# header; Config = open hypothesis rows.</p>"
        "</div>"
    )


def render_scope_decisions_region(scope_log: Path | None) -> str:
    """Render the triage pipeline card from scope-decisions.jsonl."""
    if not scope_log or not scope_log.exists():
        return (
            '<div class="card">'
            '<div class="card-title">Triage pipeline</div>'
            '<p class="card-note">No scope decisions yet. '
            "Run <code>/workflow-scope &lt;issue#&gt;</code> to triage a backlog issue.</p>"
            "</div>"
        )

    records = []
    for line in scope_log.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not records:
        return (
            '<div class="card">'
            '<div class="card-title">Triage pipeline</div>'
            '<p class="card-note">No scope decisions recorded yet.</p>'
            "</div>"
        )

    total = len(records)
    outcomes = [r for r in records if r.get("outcome")]
    ready = sum(1 for r in outcomes if r["outcome"] == "ready")
    blocked = sum(1 for r in outcomes if r["outcome"] == "blocked")
    retries = sum(int(r.get("retries") or 0) for r in outcomes)

    entry_points: dict[str, int] = {}
    for r in records:
        ep = r.get("entry_point", "unknown")
        entry_points[ep] = entry_points.get(ep, 0) + 1

    ep_bar = "".join(
        f'<div style="flex:{cnt};background:{_scope_color(ep)};display:flex;'
        f"align-items:center;justify-content:center;font-size:10px;color:white;"
        f'font-weight:600;min-width:30px;border-radius:3px">{ep}</div>'
        for ep, cnt in sorted(entry_points.items(), key=lambda kv: -kv[1])
    )

    job_types: dict[str, int] = {}
    for r in records:
        jt = r.get("job_type", "unknown")
        job_types[jt] = job_types.get(jt, 0) + 1

    jt_bar = "".join(
        f'<div style="flex:{cnt};background:{_job_type_color(jt)};display:flex;'
        f"align-items:center;justify-content:center;font-size:10px;color:white;"
        f'font-weight:600;min-width:30px;border-radius:3px">{jt}</div>'
        for jt, cnt in sorted(job_types.items(), key=lambda kv: -kv[1])
    )

    return (
        '<div class="card">'
        '<div class="card-title">Triage pipeline</div>'
        f'<p class="card-note">{total} issues scoped. '
        f"{ready} reached READY, {blocked} blocked, {retries} total retries.</p>"
        f'<div style="display:flex;height:24px;border-radius:5px;overflow:hidden;'
        f'margin:12px 0;gap:2px">{ep_bar}</div>'
        '<div style="display:flex;gap:16px;font-size:11px;color:var(--text-2);margin-bottom:8px">'
        '<span style="display:flex;align-items:center;gap:4px">'
        '<span style="width:8px;height:8px;border-radius:50%;background:var(--s3)"></span>'
        "plan (research skipped)</span>"
        '<span style="display:flex;align-items:center;gap:4px">'
        '<span style="width:8px;height:8px;border-radius:50%;background:var(--s1)"></span>'
        "research</span>"
        '<span style="display:flex;align-items:center;gap:4px">'
        '<span style="width:8px;height:8px;border-radius:50%;background:var(--s4)"></span>'
        "refine</span></div>"
        f'<div style="display:flex;height:24px;border-radius:5px;overflow:hidden;'
        f'margin:8px 0;gap:2px">{jt_bar}</div>'
        '<div style="display:flex;gap:16px;font-size:11px;color:var(--text-2);margin-bottom:8px">'
        '<span style="display:flex;align-items:center;gap:4px">'
        '<span style="width:8px;height:8px;border-radius:50%;background:var(--bad)"></span>'
        "debug</span>"
        '<span style="display:flex;align-items:center;gap:4px">'
        '<span style="width:8px;height:8px;border-radius:50%;background:var(--s1)"></span>'
        "new-feature</span>"
        '<span style="display:flex;align-items:center;gap:4px">'
        '<span style="width:8px;height:8px;border-radius:50%;background:var(--ac-violet)"></span>'
        "refactor</span>"
        '<span style="display:flex;align-items:center;gap:4px">'
        '<span style="width:8px;height:8px;border-radius:50%;background:var(--text-3)"></span>'
        "chore</span></div>"
        "</div>"
    )


def _scope_color(entry_point: str) -> str:
    return {
        "research": "var(--s1)",
        "plan": "var(--s3)",
        "refine": "var(--s4)",
    }.get(entry_point, "var(--text-3)")


def _job_type_color(job_type: str) -> str:
    return {
        "debug": "var(--bad)",
        "new-feature": "var(--s1)",
        "refactor": "var(--ac-violet)",
        "chore": "var(--text-3)",
    }.get(job_type, "var(--text-3)")


# ---------------------------------------------------------------------------
# Static-card conversions (GUA-151) — telemetry-fed marker regions replacing
# the hand-maintained cards of the 2026-08-19 board restructure. Every value a
# region renders is recomputed from its source at render time; the only
# hand-set content left on Loop Health / Experiments is architectural
# judgement (plane-strip verdicts and break sentences).
# ---------------------------------------------------------------------------


def _fmt_tokens_k(value: float) -> str:
    """Format a token count as the board's whole-k convention (102k)."""
    return f"{value / 1000:.0f}k"


def render_session_context_region(store: Path) -> str:
    """SESSION-CONTEXT region: live peak-context and over-150k tiles.

    Replaces the hand-set "0% today / 117k p90" tiles that reported success
    while the live 7-day figure was 23% over 150k (the pre-existing Tier 1
    case). Windowed to the 7 days ending at the newest observation, same
    anchoring as `_window_cutoff` — wall-clock anchoring would empty the
    window whenever the batch job has not run yet.
    """
    rows = _work_sessions(read_all(store))
    if not rows:
        return '<p class="empty">No session data yet.</p>'

    newest = max(str(r["date"]) for r in rows)
    cutoff = (_date.fromisoformat(newest) - timedelta(days=7)).isoformat()
    window = [r for r in rows if str(r["date"]) >= cutoff]
    scored = [float(r["max_context"]) for r in window if r.get("max_context")]

    if not scored:
        return (
            '<div class="card"><div class="card-title">Peak context per session</div>'
            f'<p class="card-note">No max_context observations in the 7 days ending '
            f"{html.escape(newest)}.</p></div>"
        )

    p50 = _percentile(scored, 50)
    p90 = _percentile(scored, 90)
    over_pct = 100 * sum(1 for v in scored if v >= _CONTEXT_LIMIT) / len(scored)
    over_color = "var(--good)" if over_pct < 30 else "var(--bad)"
    fence = (
        f"Computed from {len(scored)} of {len(window)} sessions carrying "
        f"<code>max_context</code>, 7 days ending {html.escape(newest)}."
    )

    return (
        '<div class="card-row">'
        '<div class="card" style="flex:1">'
        '<div class="card-title">Peak context per session (7-day window)</div>'
        '<p class="card-note"><span class="direction good">&darr; Lower is better.</span> '
        "Staying below 150k avoids the 5&times; cost cliff.</p>"
        '<div class="stat-row">'
        f'<div class="stat"><span class="value" style="color:var(--s1)">{_fmt_tokens_k(p50)}</span>'
        '<span class="label">p50 (7d)</span></div>'
        f'<div class="stat"><span class="value" style="color:var(--s2)">{_fmt_tokens_k(p90)}</span>'
        '<span class="label">p90 (7d)</span></div>'
        "</div>"
        f'<div class="trend-cell">{trend_7d("max_context_p50", store, unit="tokens")}</div>'
        f'<p style="font-size:11px;color:var(--text-3);margin-top:8px">{fence}</p>'
        "</div>"
        '<div class="card" style="flex:1">'
        '<div class="card-title">% sessions over 150k (7-day window)</div>'
        '<p class="card-note"><span class="direction good">&darr; Lower is better.</span> '
        "Target &lt;30%.</p>"
        '<div class="stat-row">'
        f'<div class="stat"><span class="value" style="color:{over_color}">{over_pct:.0f}%</span>'
        '<span class="label">over 150k (7d)</span></div>'
        "</div>"
        f'<div class="trend-cell">{trend_7d("pct_over_150k", store, unit="%")}</div>'
        f'<p style="font-size:11px;color:var(--text-3);margin-top:8px">{fence}</p>'
        "</div>"
        "</div>"
    )


# The four-way split the signal registry made possible (GUA-151 step 2). A
# verdict row lands in exactly one bucket; the two residual buckets exist so a
# row the patterns do not recognise is *shown*, never silently dropped.
_DECISIVE_VERDICTS = frozenset({"confirmed", "failed", "trending"})
_GAP_BUCKETS: list[tuple[str, str, str]] = [
    ("decisive", "decisive", "var(--good)"),
    ("needs-collection", "needs a collection", "var(--warn)"),
    ("unobservable", "unobservable by design", "var(--text-3)"),
    ("no-typed-metric", "no typed metric", "var(--stale)"),
    ("unregistered", "unregistered signal", "var(--bad)"),
    ("other", "other inconclusive", "var(--s4)"),
]


def _gap_bucket(row: dict[str, Any]) -> str:
    """Classify one verdict row by the typed reason its evidence carries.

    The patterns mirror the evidence strings `verdicts._measure` and
    `score_metric` emit — the registry states are not stored as a column, so
    the evidence line is the join key.
    """
    if str(row.get("verdict") or "") in _DECISIVE_VERDICTS:
        return "decisive"
    evidence = str(row.get("evidence") or "")
    if "needs a collection change" in evidence:
        return "needs-collection"
    if "unobservable by design" in evidence:
        return "unobservable"
    if "no typed metric" in evidence:
        return "no-typed-metric"
    if "unregistered signal" in evidence:
        return "unregistered"
    return "other"


def _metric_prefix(metric: str) -> str:
    """The typed-metric prefix of a ledger metric string, or "no-typed"."""
    m = re.match(r"\s*`?(absence|presence|ratio|count-drop):", str(metric or ""))
    return m.group(1) if m else "no-typed"


def render_measurement_gap_region(verdict_rows: list[dict[str, Any]] | None) -> str:
    """MEASUREMENT-GAP region: four-way split of the newest scoring run.

    Replaces the hand-set measurable-vs-blind binary (49 "no factstore
    signal") with the typed reasons the registry now emits. Only the newest
    `run_at` is counted — earlier runs are trajectory, not current state.
    """
    if not verdict_rows:
        return (
            '<div class="card"><div class="card-title">The measurement gap</div>'
            '<p class="card-note">No verdict rows in <code>experiment_verdicts</code> yet. '
            "Run <code>uv run telemetry --facts</code> to score the ledger.</p></div>"
        )

    newest_run = max(str(r.get("run_at") or "") for r in verdict_rows)
    rows = [r for r in verdict_rows if str(r.get("run_at") or "") == newest_run]
    total = len(rows)
    counts = Counter(_gap_bucket(r) for r in rows)

    # Stat row + mix bar over the four-way split (plus residuals when present).
    stats, segments = [], []
    for key, label, color in _GAP_BUCKETS:
        n = counts.get(key, 0)
        if n == 0 and key in {"unregistered", "other"}:
            continue
        stats.append(
            f'<div class="stat"><span class="value" style="color:{color}">{n}</span>'
            f'<span class="label">{label}</span></div>'
        )
        if n:
            segments.append(
                f'<div class="mix-seg" style="width:{100 * n / total:.1f}%;background:{color}" '
                f'title="{label}: {n} of {total}"></div>'
            )

    # Scorable-per-prefix bars: decisive / total per typed-metric prefix,
    # recomputed from the same run rather than hand-tallied.
    prefix_total = Counter(_metric_prefix(r.get("metric", "")) for r in rows)
    prefix_decisive = Counter(
        _metric_prefix(r.get("metric", "")) for r in rows if _gap_bucket(r) == "decisive"
    )
    prefix_rows = ""
    widest = max(prefix_total.values(), default=1)
    for prefix in ("absence", "presence", "ratio", "count-drop", "no-typed"):
        n_total = prefix_total.get(prefix, 0)
        if not n_total:
            continue
        n_dec = prefix_decisive.get(prefix, 0)
        color = "var(--s1)" if n_dec else "var(--bad)"
        prefix_rows += (
            f'<div class="rec-row"><div class="rec-name">{prefix}:</div>'
            f'<div class="rec-track"><div class="rec-fill" '
            f'style="width:{100 * n_total / widest:.0f}%;background:{color};opacity:.6"></div></div>'
            f'<div class="rec-n">{n_dec}/{n_total}</div></div>'
        )

    run_day = html.escape(newest_run[:10])
    return (
        '<div class="card">'
        '<div class="card-title">The measurement gap</div>'
        f'<p class="card-note">Latest scoring run ({run_day}): <strong>{total} hypotheses '
        f"scored, {counts.get('decisive', 0)} decisive</strong>. The rest carry a typed "
        "reason — a claim awaiting a collection change, a claim no telemetry could ever "
        "see, and a claim with no countable metric are different problems with different "
        "fixes.</p>"
        f'<div class="mix-bar">{"".join(segments)}</div>'
        f'<div class="stat-row">{"".join(stats)}</div>'
        f'<div class="rec">{prefix_rows}</div>'
        f'<p style="font-size:11px;color:var(--text-3);margin-top:10px">Computed from the '
        f"{total} <code>experiment_verdicts</code> rows of run {html.escape(newest_run)}; "
        f"decisive = confirmed / failed / trending. Bars show decisive/total per "
        f"typed-metric prefix.</p>"
        "</div>"
    )


# GUA-151 step 3: the harness card. The rule the static card stated becomes
# the assertion — a cell's state derives from *recency* (gap since the last
# successful run vs the job's cadence) and *breadth* (unique hooks in the pass
# log vs threshold), never from exit codes: every stalled job also exits 0.
_JOB_FINISHED = re.compile(
    r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) --- run finished \(exit (\d+)\)$", re.MULTILINE
)
_HARNESS_HOOK_THRESHOLD = 5
_HARNESS_WINDOW_DAYS = 14


def _job_runs(log_path: Path) -> list[_datetime]:
    """Timestamps of successful (exit 0) run completions in a telemetry log.

    Timestamps are naive local time as the cron wrapper writes them; callers
    compare against a naive `now` in the same clock.
    """
    if not log_path.exists():
        return []
    runs: list[_datetime] = []
    for day, clock, exit_code in _JOB_FINISHED.findall(
        log_path.read_text(encoding="utf-8", errors="replace")
    ):
        if exit_code != "0":
            continue
        try:
            runs.append(_datetime.fromisoformat(f"{day}T{clock}"))
        except ValueError:
            continue
    return sorted(runs)


def _gap_days_label(delta_days: float) -> str:
    if delta_days < 1:
        hours = delta_days * 24
        return f"{hours:.0f}h" if hours >= 1 else f"{hours * 60:.0f}m"
    return f"{delta_days:.0f}d"


def _harness_cell(
    name: str,
    cadence: str,
    runs: list[_datetime],
    *,
    now: _datetime,
    warn_after_h: float,
    bad_after_h: float,
    detail_extra: str = "",
) -> str:
    """One hz-cell: state from the gap since the last successful run."""
    if not runs:
        state, color, bg = "&#10007; never ran", "var(--bad)", "var(--bad-bg)"
        detail = "No successful run in the log window."
        day_bar = ""
    else:
        last = runs[-1]
        gap_h = (now - last).total_seconds() / 3600
        if gap_h <= warn_after_h:
            state, color, bg = "&#10003; healthy", "var(--good)", "var(--good-bg)"
        elif gap_h <= bad_after_h:
            state, color, bg = (
                f"~ {_gap_days_label(gap_h / 24)} since last",
                "var(--warn)",
                "var(--warn-bg)",
            )
        else:
            state, color, bg = (
                f"&#10007; {_gap_days_label(gap_h / 24)} gap",
                "var(--bad)",
                "var(--bad-bg)",
            )

        # Longest silence between consecutive runs (and trailing silence to now)
        # over the whole log — how the 08-04 -> 08-17 facts gap stays visible
        # even after the job recovers.
        gaps = [(runs[i + 1] - runs[i], runs[i], runs[i + 1]) for i in range(len(runs) - 1)]
        longest = max(gaps, default=None, key=lambda g: g[0])
        detail = f"Last successful run <b>{last.strftime('%m-%d %H:%M')}</b>."
        if longest and longest[0].days >= 2:
            detail += (
                f" Longest gap <b>{longest[0].days}d</b> "
                f"({longest[1].strftime('%m-%d')} &rarr; {longest[2].strftime('%m-%d')})."
            )
        if detail_extra:
            detail += f" {detail_extra}"

        # One block per day, newest right: filled when >=1 successful run.
        days = [
            (now - timedelta(days=offset)).date()
            for offset in range(_HARNESS_WINDOW_DAYS - 1, -1, -1)
        ]
        ran = {r.date() for r in runs}
        day_bar = (
            '<div style="display:flex;gap:2px;margin-top:6px" title="one block per day, '
            f'oldest left, {_HARNESS_WINDOW_DAYS} days">'
            + "".join(
                f'<span style="flex:1;height:8px;border-radius:2px;'
                f"background:{'var(--good)' if d in ran else 'var(--bad)'};"
                f'opacity:{"0.8" if d in ran else "0.35"}" title="{d.isoformat()}: '
                f'{"ran" if d in ran else "no successful run"}"></span>'
                for d in days
            )
            + "</div>"
        )

    return (
        f'<div class="hz-cell" style="--hc:{color}">'
        f'<div class="hz-name">{html.escape(name)}</div><div class="hz-sub">{html.escape(cadence)}</div>'
        f'<span class="hz-state" style="background:{bg};color:{color}">{state}</span>'
        f'<div class="hz-detail">{detail}</div>{day_bar}'
        "</div>"
    )


def render_harness_region(
    logs_dir: Path,
    pass_log: Path,
    store: Path,
    *,
    now: _datetime | None = None,
    hook_threshold: int = _HARNESS_HOOK_THRESHOLD,
) -> str:
    """HARNESS region: collection-job liveness from the logs themselves.

    Cells: board (10-min tick), facts (daily), verdict scoring (newest
    `run_at` in the store), hook pass-log breadth (unique hooks vs threshold).
    """
    # Naive *local* wall-clock, to match the clock the cron wrapper stamps the
    # logs with (structlog lines in the same files are UTC; those are not the
    # lines parsed here).
    now = now or _datetime.now(UTC).astimezone().replace(tzinfo=None)

    board_cell = _harness_cell(
        "board",
        "every 10 min",
        _job_runs(logs_dir / "telemetry-board.log"),
        now=now,
        warn_after_h=1,
        bad_after_h=6,
    )
    facts_cell = _harness_cell(
        "facts",
        "daily 09:00",
        _job_runs(logs_dir / "telemetry-facts.log"),
        now=now,
        warn_after_h=36,
        bad_after_h=72,
        detail_extra="Local JSONL rotates in ~5 days; a multi-day gap loses sessions.",
    )

    # Verdict scoring: recency of the newest run_at, not a log file — the
    # store is the artifact the job exists to write.
    verdict_rows = read_verdicts(store)
    if verdict_rows:
        newest_run = max(str(r.get("run_at") or "") for r in verdict_rows)
        run_count = len({str(r.get("run_at") or "") for r in verdict_rows})
        scored = sum(1 for r in verdict_rows if str(r.get("run_at") or "") == newest_run)
        try:
            newest_dt = _datetime.fromisoformat(newest_run).replace(tzinfo=None)
            gap_h = (now - newest_dt).total_seconds() / 3600
        except ValueError:
            gap_h = float("inf")
        if gap_h <= 36:
            v_state, v_color, v_bg = "&#10003; healthy", "var(--good)", "var(--good-bg)"
        elif gap_h <= 72:
            v_state, v_color, v_bg = "~ aging", "var(--warn)", "var(--warn-bg)"
        else:
            v_state, v_color, v_bg = "&#10007; stale", "var(--bad)", "var(--bad-bg)"
        v_detail = (
            f"Scored <b>{scored}</b> hypotheses in the newest run "
            f"({html.escape(newest_run[:16])}) across <b>{run_count}</b> recorded runs."
        )
    else:
        v_state, v_color, v_bg = "&#10007; no runs", "var(--bad)", "var(--bad-bg)"
        v_detail = "No rows in <code>experiment_verdicts</code>."
    verdict_cell = (
        f'<div class="hz-cell" style="--hc:{v_color}">'
        '<div class="hz-name">verdict scoring</div><div class="hz-sub">per insights run</div>'
        f'<span class="hz-state" style="background:{v_bg};color:{v_color}">{v_state}</span>'
        f'<div class="hz-detail">{v_detail}</div></div>'
    )

    # Hook breadth: unique hooks writing the pass log vs the threshold. Full
    # log + narrow breadth means most hooks exit 0 without calling log_pass —
    # unobservable, not absent.
    hook_events = parse_hook_log(pass_log)
    hook_counts = Counter(str(e.get("hook") or "") for e in hook_events if e.get("hook"))
    breadth = len(hook_counts)
    if breadth >= hook_threshold:
        h_state, h_color, h_bg = "&#10003; healthy", "var(--good)", "var(--good-bg)"
    elif hook_events:
        h_state, h_color, h_bg = (
            f"~ {breadth} of {hook_threshold} hooks",
            "var(--warn)",
            "var(--warn-bg)",
        )
    else:
        h_state, h_color, h_bg = "&#10007; empty log", "var(--bad)", "var(--bad-bg)"
    top = ", ".join(f"<code>{html.escape(k)}</code> {v}" for k, v in hook_counts.most_common(3))
    h_detail = (
        f"<b>{breadth}</b> unique hooks across {len(hook_events)} pass events"
        f"{' (' + top + ')' if top else ''}. Breadth below {hook_threshold} means "
        "hooks exit 0 without logging — unobservable, not absent."
    )
    hooks_cell = (
        f'<div class="hz-cell" style="--hc:{h_color}">'
        '<div class="hz-name">hook pass-log</div><div class="hz-sub">per tool call</div>'
        f'<span class="hz-state" style="background:{h_bg};color:{h_color}">{h_state}</span>'
        f'<div class="hz-detail">{h_detail}</div></div>'
    )

    return (
        f'<div class="hz">{board_cell}{facts_cell}{verdict_cell}{hooks_cell}</div>'
        f'<p style="font-size:11px;color:var(--text-3);margin-top:10px">Derived from '
        f"<code>logs/telemetry-*.log</code> (exit-0 completions only), "
        f"<code>experiment_verdicts</code>, and the hook pass log at render time. "
        f"Cell state asserts on recency and breadth, never exit code.</p>"
    )


# GUA-151 step 4: plane-strip body counts. Only the stat line under each
# plane is derived; stage verdicts and break sentences are architectural
# judgements and stay hand-set (a partial `promote` stage is a judgement no
# query returns). Three marker pairs, one per plane, because the stat lines
# are not contiguous in the markup.


def _findings_totals(store: Path) -> tuple[int, int]:
    """(total findings, blocker findings) from the store's findings table.

    factstore exposes only the writer for this table; the count query lives
    here rather than widening factstore's API for one caller.
    """
    if not store.exists():
        return 0, 0
    conn = sqlite3.connect(store)
    try:
        total = conn.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
        blockers = conn.execute(
            "SELECT COUNT(*) FROM findings WHERE merge_impact = 'blocker'"
        ).fetchone()[0]
    except sqlite3.OperationalError:
        return 0, 0
    finally:
        conn.close()
    return int(total), int(blockers)


def _retro_rounds(ledger_log_path: Path | None) -> list[tuple[int, str]]:
    """(round number, date) per retro round in tooling-ledger-log.md.

    Headers are not chronological in the file, so every header is scanned and
    dated from the 120 chars that follow it (same approach as the
    pipeline-health retro cell). Rounds without a parseable date carry "".
    """
    if not ledger_log_path or not ledger_log_path.exists():
        return []
    text = ledger_log_path.read_text(encoding="utf-8", errors="replace")
    rounds: dict[int, str] = {}
    for match in _RETRO_HEADER.finditer(text):
        num_match = re.search(r"\d+", match.group())
        if not num_match:
            continue
        num = int(num_match.group())
        snippet = text[match.start() : match.start() + 120]
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", snippet)
        rounds.setdefault(num, date_match.group() if date_match else "")
    return sorted(rounds.items())


def _consistency_counts(consistency_path: Path | None) -> tuple[int | None, int | None]:
    """(open inconsistencies, unmatchable plans) from consistency.json."""
    if not consistency_path or not consistency_path.exists():
        return None, None
    try:
        data = json.loads(consistency_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, None
    total = data.get("total")
    unmatchable = data.get("unmatchable_plans")
    return (
        int(total) if isinstance(total, int) else None,
        int(unmatchable) if isinstance(unmatchable, int) else None,
    )


def render_plane_counts_regions(
    store: Path,
    *,
    consistency_path: Path | None,
    experiments: list[Experiment] | None,
    ledger_log_path: Path | None,
    reflections_dir: Path | None,
    pass_log: Path,
    hook_threshold: int = _HARNESS_HOOK_THRESHOLD,
) -> dict[str, str]:
    """The three PLANE-COUNTS-* regions, keyed ready for the injection dict."""
    missing = '<span style="color:var(--text-3)">?</span>'

    findings_total, blockers = _findings_totals(store)
    issues = len(read_issues(store))
    inconsistencies, unmatchable = _consistency_counts(consistency_path)
    work = (
        f"<b>{findings_total:,}</b> findings &middot; <b>{blockers}</b> blockers &middot; "
        f"<b>{issues}</b> issues &middot; "
        f"<b>{inconsistencies if inconsistencies is not None else missing}</b> open inconsistencies &middot; "
        f"<b>{unmatchable if unmatchable is not None else missing}</b> plans unmatchable to an issue"
    )

    sessions = len(read_all(store))
    reflections = (
        len(list(reflections_dir.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*.md")))
        if reflections_dir and reflections_dir.is_dir()
        else None
    )
    rounds = _retro_rounds(ledger_log_path)
    verdict_rows = read_verdicts(store)
    decisive = 0
    live = len(experiments) if experiments else 0
    if verdict_rows:
        newest_run = max(str(r.get("run_at") or "") for r in verdict_rows)
        decisive = sum(
            1
            for r in verdict_rows
            if str(r.get("run_at") or "") == newest_run and _gap_bucket(r) == "decisive"
        )
    meta = (
        f"<b>{sessions:,}</b> sessions &middot; "
        f"<b>{reflections if reflections is not None else missing}</b> reflections &middot; "
        f"<b>{len(rounds)}</b> retro rounds &middot; <b>{live}</b> live hypotheses &middot; "
        f"<b>{decisive}</b> decisive in the latest run"
    )

    hook_events = parse_hook_log(pass_log)
    breadth = len({str(e.get("hook") or "") for e in hook_events if e.get("hook")})
    control = (
        f"<b>{breadth}</b> unique hooks in the pass log (threshold <b>{hook_threshold}</b>) "
        f"&middot; <b>{len(hook_events)}</b> pass events recorded"
    )

    return {
        "PLANE-COUNTS-WORK": work,
        "PLANE-COUNTS-META": meta,
        "PLANE-COUNTS-CONTROL": control,
    }


# GUA-151 step 5: the runway. Dot position from the row's due date, fill from
# its newest verdict, clusters when rows share a deadline. Rows with no due
# date cannot age, so they are counted out loud rather than dropped.


def _runway_dot_class(verdict: str) -> tuple[str, str]:
    """(css background, legend bucket) for a ledger row's newest verdict."""
    return {
        "confirmed": ("var(--good)", "confirmed"),
        "failed": ("var(--bad)", "failed"),
        "trending": ("var(--s1)", "trending"),
    }.get(verdict, ("var(--stale)", "inconclusive"))


def render_runway_region(
    experiments: list[Experiment] | None,
    store: Path | None = None,
    *,
    today: str | None = None,
) -> str:
    """RUNWAY region: every live ledger row on a due-date axis."""
    if not experiments:
        return (
            '<div class="card"><div class="card-title">The runway</div>'
            '<p class="card-note">No live rows in <code>tooling-ledger.md</code>.</p></div>'
        )
    today = today or _datetime.now(UTC).astimezone().date().isoformat()
    latest = _latest_verdicts(store)

    dated: dict[str, list[tuple[Experiment, str]]] = {}
    undated: list[Experiment] = []
    for exp in experiments:
        due = _experiment_due(exp)
        if due is None:
            undated.append(exp)
        else:
            dated.setdefault(due, []).append((exp, due))

    if not dated:
        return (
            '<div class="card"><div class="card-title">The runway</div>'
            f'<p class="card-note"><b>{len(undated)}</b> live rows, none carrying a '
            "due date — nothing can age, so nothing can surface as late.</p></div>"
        )

    axis_min = min(min(dated), today)
    axis_max = max(max(dated), today)
    span = max((_date.fromisoformat(axis_max) - _date.fromisoformat(axis_min)).days, 1)

    def pos(day: str) -> float:
        return 100 * (_date.fromisoformat(day) - _date.fromisoformat(axis_min)).days / span

    today_pos = pos(today)
    overdue_total = 0
    marks = ""
    for due in sorted(dated):
        rows = dated[due]
        is_over = due < today
        if is_over:
            overdue_total += len(rows)
        verdicts = [str((latest.get(exp.name) or {}).get("verdict") or "") for exp, _ in rows]
        if len(rows) > 1:
            names = "; ".join(_truncate(exp.name, 60) for exp, _ in rows[:6])
            more = f" (+{len(rows) - 6} more)" if len(rows) > 6 else ""
            title = (
                f"{len(rows)} hypotheses due {due}"
                f"{' — overdue' if is_over else ''}. {html.escape(names)}{more}"
            )
            marks += (
                f'<div class="rw-cluster" style="left:{pos(due):.1f}%'
                f'{";border-color:var(--bad)" if is_over else ""}" '
                f'title="{title}">{len(rows)}{" &#9873;" if is_over else ""}</div>'
            )
        else:
            exp, _ = rows[0]
            color, bucket = _runway_dot_class(verdicts[0])
            title = html.escape(
                f"{_truncate(exp.name, 80)} — {_truncate(exp.metric, 60)}. "
                f"{bucket}{', overdue' if is_over else ''}. Due {due}."
            )
            marks += (
                f'<div class="rw-dot" style="left:{pos(due):.1f}%;background:{color}'
                f'{";outline:1.5px solid var(--bad)" if is_over else ""}" title="{title}"></div>'
            )

    # Verdict mix over the dated rows, for the legend counts.
    buckets = Counter(
        _runway_dot_class(str((latest.get(exp.name) or {}).get("verdict") or ""))[1]
        for rows in dated.values()
        for exp, _ in rows
    )
    dated_total = sum(len(rows) for rows in dated.values())
    legend = "".join(
        f'<span><i class="rw-sw" style="background:{color}"></i> {bucket} ({buckets[bucket]})</span>'
        for bucket, color in (
            ("confirmed", "var(--good)"),
            ("trending", "var(--s1)"),
            ("failed", "var(--bad)"),
            ("inconclusive", "var(--stale)"),
        )
        if buckets.get(bucket)
    )

    # Quarter-point axis ticks keep the scale readable at any span.
    ticks = "".join(
        f"<span>{(_date.fromisoformat(axis_min) + timedelta(days=round(span * f))).strftime('%b %d')}</span>"
        for f in (0, 0.25, 0.5, 0.75, 1)
    )

    return (
        '<div class="card">'
        f'<div class="card-title">The runway &mdash; {len(experiments)} hypotheses by due date</div>'
        f'<p class="card-note">Each mark is one live ledger row at its due date; clusters '
        f"share a deadline. Fill is the row's newest verdict. "
        f"<strong>{overdue_total} of {dated_total} dated rows are overdue</strong> as of {today}.</p>"
        '<div class="runway">'
        f'<div class="rw-scale"><span></span><div class="rw-ticks">{ticks}</div></div>'
        '<div class="rw-band first"><div class="rw-label">all rows</div>'
        f'<div class="rw-track"><div class="rw-past" style="width:{today_pos:.1f}%"></div>'
        f'<div class="rw-today" style="left:{today_pos:.1f}%"></div>{marks}</div></div>'
        f'<div class="rw-legend">{legend}</div>'
        "</div>"
        f'<p style="font-size:11px;color:var(--text-3);margin-top:10px">'
        f"<b>{len(undated)}</b> rows carry no due date — they cannot age and will never "
        f"surface as late. Derived from <code>tooling-ledger.md</code> + "
        f"<code>experiment_verdicts</code> at render time.</p>"
        "</div>"
    )


# GUA-151 step 6: the decision log. Render-only — telemetry/actions.py already
# carries planes, `reverted`, and `effect_measured` (merged to main the same
# day); this region just reads the normalised records.

_PLANE_ORDER = ("work", "metacognition", "control")
_PLANE_LABEL = {
    "work": "1 &middot; work",
    "metacognition": "2 &middot; metacog",
    "control": "3 &middot; control",
}
_OUTCOME_PILL = {
    "acted": "acc",
    "accepted": "acc",
    "proposed": "pend",
    "deferred": "pend",
    "reverted": "rev",
    "declined": "dec",
    "rejected": "dec",
}


def _decision_target(rec: dict[str, Any]) -> str:
    """Compact human-readable target: repo#issue, repo:branch, or the raw str."""
    target = rec.get("target")
    if isinstance(target, dict):
        repo = str(target.get("repo") or "")
        if target.get("issue_num") is not None:
            return f"{repo}#{target.get('issue_num')}"
        if target.get("branch"):
            return f"{repo}:{target.get('branch')}"
        return repo or "&mdash;"
    return html.escape(str(target)) if target else "&mdash;"


def _effect_cell(rec: dict[str, Any]) -> str:
    effect = rec.get("effect_measured")
    if not effect:
        return '<span style="color:var(--text-3)">not re-read</span>'
    if isinstance(effect, dict):
        verdict = html.escape(str(effect.get("verdict") or ""))
        metric = html.escape(_truncate(str(effect.get("metric") or ""), 40))
        color = {
            "confirmed": "var(--good)",
            "trending": "var(--warn)",
            "failed": "var(--bad)",
        }.get(str(effect.get("verdict") or ""), "var(--text-2)")
        return (
            f'<span style="color:{color}">{verdict}{" &mdash; " + metric if metric else ""}</span>'
        )
    return html.escape(_truncate(str(effect), 60))


def render_decision_log_region(records: list[dict[str, Any]] | None) -> str:
    """DECISION-LOG region: one row per decision, grouped by plane."""
    if not records:
        return (
            '<div class="card"><div class="card-title">What the loops decided</div>'
            '<p class="card-note">No decisions in '
            "<code>.sounding/telemetry/actions.jsonl</code> yet.</p></div>"
        )

    # Effect write-backs share their origin's proposal_id; fold each onto the
    # newest decision row so the effect shows on the decision, not as a
    # duplicate line.
    effects: dict[str, dict[str, Any]] = {}
    decisions: list[dict[str, Any]] = []
    for rec in records:
        pid = str(rec.get("proposal_id") or "")
        if rec.get("effect_measured") and pid:
            effects[pid] = rec
        else:
            decisions.append(rec)
    rows_html = ""
    plane_counts: Counter[str] = Counter()
    ordered = sorted(
        decisions,
        key=lambda r: (
            _PLANE_ORDER.index(str(r.get("plane")))
            if str(r.get("plane")) in _PLANE_ORDER
            else len(_PLANE_ORDER),
            str(r.get("ts") or ""),
        ),
    )
    for rec in ordered:
        plane = str(rec.get("plane") or "work")
        plane_counts[plane] += 1
        outcome = str(rec.get("outcome") or "unknown")
        pill = _OUTCOME_PILL.get(outcome, "pend")
        reason = _truncate(str(rec.get("reason") or ""), 90)
        pid = str(rec.get("proposal_id") or "")
        effect_rec = rec if rec.get("effect_measured") else effects.get(pid, rec)
        rows_html += (
            "<tr>"
            f"<td>{html.escape(str(rec.get('action') or ''))} &mdash; "
            f"{_decision_target(rec)}"
            f'<div style="font-size:11px;color:var(--text-3)">{html.escape(reason)}</div></td>'
            f"<td>{_PLANE_LABEL.get(plane, html.escape(plane))}</td>"
            f'<td><span class="pill {pill}">{html.escape(outcome)}</span></td>'
            f"<td>{_effect_cell(effect_rec)}</td>"
            "</tr>"
        )

    plane_note = " &middot; ".join(
        f"{_PLANE_LABEL[p]}: <b>{plane_counts[p]}</b>" for p in _PLANE_ORDER if plane_counts[p]
    )
    return (
        '<div class="card">'
        '<div class="card-title">What the loops decided &mdash; and what got measured</div>'
        f'<p class="card-note">One row per decision in '
        f"<code>actions.jsonl</code>, grouped by plane ({plane_note}). "
        f'"Effect measured" distinguishes a decision that was re-read from one that '
        f"was never looked at again.</p>"
        '<div class="overflow-x"><table class="dl">'
        "<thead><tr><th>Decision</th><th>Plane</th><th>Disposition</th>"
        "<th>Effect measured?</th></tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table></div>"
        f'<p style="font-size:11px;color:var(--text-3);margin-top:8px">Computed from '
        f"{len(decisions)} decision records ({len(effects)} effect write-backs folded in) "
        f"at render time.</p>"
        "</div>"
    )


# GUA-151: cadence. In the plan's inventory (Tier 2) and required by its
# verification clause (no hand-maintained numbers left on Experiments): the
# retro gaps and the due horizon drift as rounds land, so they are derived
# from the same sources every render.


def render_cadence_region(
    ledger_log_path: Path | None,
    experiments: list[Experiment] | None,
) -> str:
    """CADENCE region: actual retro cadence vs the due horizon rows are given."""
    rounds = [(num, day) for num, day in _retro_rounds(ledger_log_path) if day]
    rounds.sort(key=lambda r: r[1])

    gap_rows = ""
    gaps: list[int] = []
    if len(rounds) >= 2:
        pairs = list(pairwise(rounds))[-6:]
        widest = max(
            ((_date.fromisoformat(b[1]) - _date.fromisoformat(a[1])).days for a, b in pairs),
            default=1,
        )
        for (num_a, day_a), (num_b, day_b) in pairs:
            gap = (_date.fromisoformat(day_b) - _date.fromisoformat(day_a)).days
            gaps.append(gap)
            width = 100 * gap / max(widest, 1)
            gap_rows += (
                f'<div class="rec-row"><div class="rec-name">R{num_a} &rarr; R{num_b} '
                f"<small>{day_a[5:]} &rarr; {day_b[5:]}</small></div>"
                f'<div class="rec-track"><div class="rec-fill" '
                f'style="width:{width:.0f}%;background:var(--s3)"></div></div>'
                f'<div class="rec-n">{gap}d</div></div>'
            )

    horizons = [
        (_date.fromisoformat(due) - _date.fromisoformat(exp.date)).days
        for exp in experiments or []
        if (due := _experiment_due(exp)) and re.match(r"\d{4}-\d{2}-\d{2}$", exp.date or "")
    ]
    horizon_row = ""
    if horizons:
        horizons.sort()
        typical = horizons[len(horizons) // 2]
        horizon_row = (
            f'<div class="rec-row"><div class="rec-name">typical due horizon '
            f"<small>median over {len(horizons)} dated rows</small></div>"
            f'<div class="rec-track"><div class="rec-fill" '
            f'style="width:100%;background:var(--s4)"></div></div>'
            f'<div class="rec-n">{typical}d</div></div>'
        )

    if not gap_rows and not horizon_row:
        return (
            '<div class="card"><div class="card-title">Cadence &mdash; the due-date question</div>'
            '<p class="card-note">No dated retro rounds in the ledger log yet.</p></div>'
        )

    typical_gap = sorted(gaps)[len(gaps) // 2] if gaps else None
    note = (
        f"Retro actually fires every <strong>{min(gaps)}&ndash;{max(gaps)} days</strong> "
        f"(median {typical_gap}d over the last {len(gaps)} intervals)."
        if gaps
        else ""
    )
    return (
        '<div class="card">'
        '<div class="card-title">Cadence &mdash; the due-date question</div>'
        f'<p class="card-note">Due dates written far beyond the actual retro cadence pile '
        f"up unaudited. {note} <code>/hypothesis</code> computes new due dates at 2 retro "
        f"rounds from creation; rows predating it keep their hand-typed horizon.</p>"
        f'<div class="rec">{gap_rows}{horizon_row}</div>'
        f'<p style="font-size:11px;color:var(--text-3);margin-top:8px">Derived from '
        f"retro-round dates in <code>tooling-ledger-log.md</code> and due dates in "
        f"<code>tooling-ledger.md</code> at render time.</p>"
        "</div>"
    )


# GUA-151 step: DATA-BLOCK region. The `const DATA` JS block in the dashboard
# powers legacy line charts (context p50/p90, over-150k, session shape,
# compaction, skill usage, sessions/week). Values were frozen 2026-07-28 and
# reported "0% today" while the live figure was 23% over 150k. This renderer
# recomputes the same series from the factstore at render time so every run
# extends the charts rather than replaying the same flat tail.
#
# Unit conventions (must match the JS fmtVal function):
#   context_p50 / context_p90 : stored in k-tokens (value=100 means 100k),
#       because the JS drawLine call uses unit='tokens' and fmtVal interprets
#       values < 1000 as "Nk" — divide raw max_context by 1000.
#   over150k, single_turn, compaction, skills : raw percentage (0–100).
#   turns_p50 : raw integer count.
#   sessions_week : raw integer count per week bucket.
#   compaction and sessions_week have a regime facet (r field).

_DATA_BLOCK_SERIES: list[tuple[str, str, str]] = [
    # (js_key, metric_name, unit_hint)
    ("context_p50", "max_context_p50", "ktokens"),
    ("context_p90", "max_context_p90", "ktokens"),
    ("over150k", "cost_bucket_pct_over150k", "pct"),
    ("turns_p50", "turns_per_session_p50", "count"),
    ("single_turn", "single_turn_pct", "pct"),
    ("skills", "execution_skill_compliance_pct", "pct"),
    ("compaction", "compaction_pct", "faceted"),
    ("sessions_week", "sessions_per_week", "faceted"),
]


def _series_to_js_points(series: Series, unit_hint: str) -> str:
    """Convert a Series to a compact JS array literal matching the DATA format.

    Faceted series (compaction_pct / sessions_per_week) flatten all panels
    into a single list with an `r` field so the JS drawLine / drawBar
    functions receive a single heterogeneous dataset — the same shape the
    hand-written arrays had.  Continuous series omit the `r` field.
    """

    def _fmt(v: float) -> str:
        # Round to at most 2 decimal places; strip trailing zeros.
        return f"{v:.2f}".rstrip("0").rstrip(".")

    points_js: list[str] = []

    if series.faceted:
        for panel in series.panels:
            for p in panel.points:
                v = p.value / 1000 if unit_hint == "ktokens" else p.value
                r_field = f",r:{json.dumps(panel.regime)}" if panel.regime else ""
                points_js.append(f"{{d:{json.dumps(p.date)},v:{_fmt(v)}{r_field}}}")
    else:
        for p in series.points:
            v = p.value / 1000 if unit_hint == "ktokens" else p.value
            points_js.append(f"{{d:{json.dumps(p.date)},v:{_fmt(v)}}}")

    # Compact: one array per line with no trailing whitespace.
    inner = ",".join(points_js)
    return f"[\n    {inner}\n  ]"


def render_data_block_region(store: Path) -> str:
    """DATA-BLOCK region: regenerated `const DATA` for the dashboard charts.

    Replaces the hand-written series frozen at 2026-07-28 with values recomputed
    from the factstore at render time. The output is a complete `const DATA = {
    ... };` block — the marker region wraps only this block, so the surrounding
    `<script>` tags and chart-rendering code are untouched.
    """
    parts: list[str] = []
    for js_key, metric, unit_hint in _DATA_BLOCK_SERIES:
        period = "week" if metric == "sessions_per_week" else "day"
        series = build_series(metric, store, period)
        js_points = _series_to_js_points(series, unit_hint)
        parts.append(f"  {js_key}: {js_points}")

    data_body = "const DATA = {\n" + ",\n".join(parts) + "\n};"
    return "<script>\n// \u2500\u2500\u2500 Data \u2500\u2500\u2500\n" + data_body + "\n</script>"
