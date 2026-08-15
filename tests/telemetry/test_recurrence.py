from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from telemetry.periods import period_key
from telemetry.recurrence import (
    DIRECTION_FALLING,
    DIRECTION_FLAT,
    DIRECTION_RISING,
    RECURRENCE_THRESHOLD,
    compute_period_counts,
    compute_recurrence,
)


def _finding(
    title: str = "hardcoded timeout value",
    category: str = "config",
    repo: str = "guacamayo",
    date: str = "2026-07-29",
    **overrides: Any,
) -> dict[str, Any]:
    row = {"title": title, "category": category, "repo": repo, "date": date}
    row.update(overrides)
    return row


def test_pattern_match_is_case_insensitive() -> None:
    findings = [
        _finding(title="HARDCODED value should be config"),
        _finding(title="Hardcoded Not Externalized constant"),
        _finding(title="hardcoded magic number"),
    ]
    groups = compute_recurrence(findings)
    matched = next(g for g in groups if g.pattern_key == "hardcoded-not-configurable")
    assert matched.count == 3


def test_group_below_threshold_is_not_promotable() -> None:
    findings = [
        _finding(title="resource leak on exception path") for _ in range(RECURRENCE_THRESHOLD - 1)
    ]
    groups = compute_recurrence(findings)
    matched = next(g for g in groups if g.pattern_key == "resource-leak")
    assert matched.count < RECURRENCE_THRESHOLD
    assert matched.promotable is False


def test_group_at_threshold_is_promotable() -> None:
    findings = [
        _finding(title="resource leak on exception path") for _ in range(RECURRENCE_THRESHOLD)
    ]
    groups = compute_recurrence(findings)
    matched = next(g for g in groups if g.pattern_key == "resource-leak")
    assert matched.count == RECURRENCE_THRESHOLD
    assert matched.promotable is True


def test_unmatched_finding_falls_back_to_category_repo() -> None:
    findings = [
        _finding(
            title="unrelated prose with no known signature", category="api-contract", repo="atlas"
        )
    ]
    groups = compute_recurrence(findings)
    assert len(groups) == 1
    assert groups[0].pattern_key == "unmatched:api-contract:atlas"
    assert groups[0].count == 1
    assert groups[0].repos == ["atlas"]
    assert groups[0].categories == ["api-contract"]


def test_first_seen_last_seen_span_the_group() -> None:
    findings = [
        _finding(title="missing timeout on http call", date="2026-07-20"),
        _finding(title="no timeout configured for retry", date="2026-08-05"),
        _finding(title="timeout absent in client init", date="2026-07-29"),
    ]
    groups = compute_recurrence(findings)
    matched = next(g for g in groups if g.pattern_key == "missing-timeout")
    assert matched.first_seen == "2026-07-20"
    assert matched.last_seen == "2026-08-05"


def test_sample_titles_capped_at_three() -> None:
    findings = [_finding(title=f"hardcoded value #{i} not externalized") for i in range(5)]
    groups = compute_recurrence(findings)
    matched = next(g for g in groups if g.pattern_key == "hardcoded-not-configurable")
    assert matched.count == 5
    assert len(matched.sample_titles) == 3


def test_multi_match_finding_counts_in_every_matching_group() -> None:
    """Multi-match policy is 'all matches', not 'first match wins' (see
    telemetry/recurrence.py module docstring): a title matching two patterns
    is counted in both groups."""
    findings = [_finding(title="silent swallow with no timeout on retry")]
    groups = compute_recurrence(findings)
    keys = {g.pattern_key for g in groups}
    assert "silent-swallow" in keys
    assert "missing-timeout" in keys


def test_groups_sorted_by_count_descending() -> None:
    findings = [_finding(title="hardcoded value not externalized") for _ in range(4)] + [
        _finding(title="resource leak, not closed") for _ in range(2)
    ]
    groups = compute_recurrence(findings)
    counts = [g.count for g in groups]
    assert counts == sorted(counts, reverse=True)


def test_empty_findings_returns_empty_list() -> None:
    assert compute_recurrence([]) == []


def test_god_module_signature_matches_size_and_mixed_concerns() -> None:
    findings = [
        _finding(title="Single 1458-line module mixes multiple distinct concerns"),
        _finding(title="_run_facts() mixes multiple responsibilities across 296 lines"),
        _finding(title="God object accumulates unrelated state"),
    ]
    groups = compute_recurrence(findings)
    matched = next(g for g in groups if g.pattern_key == "god-module")
    assert matched.count == 3


def test_god_module_does_not_match_expression_complexity() -> None:
    """A complex *expression* is not a module mixing concerns.

    This title sits in the live corpus and would take `god-module` from n=2 to
    n=3 -- i.e. across the promotion threshold. Matching it would be fitting the
    regex to the desired answer rather than to the friction, so it is excluded
    deliberately and this test pins that choice.
    """
    findings = [
        _finding(
            title="_NON_SOURCE regex pattern is complex multi-line pattern with 12+ OR clauses"
        )
    ]
    groups = compute_recurrence(findings)
    assert not any(g.pattern_key == "god-module" for g in groups)


def test_unhandled_none_return_signature() -> None:
    findings = [
        _finding(title="Unhandled None from SQL fetchone() will crash on missing metadata"),
        _finding(title="_render_fact emits literal 'pNone' for facts with no page number"),
        _finding(title="_first_theme_color raises StopIteration on empty theme_colors"),
    ]
    groups = compute_recurrence(findings)
    matched = next(g for g in groups if g.pattern_key == "unhandled-none-return")
    assert matched.count == 3
    assert matched.promotable is True


# --- Per-period counts + rising flag (GUA-104b) ------------------------------

# All rising tests pin `today` so the "is the trailing period complete" decision
# is deterministic. Without it these tests would change verdict as real time
# passes -- the failure mode would be a suite that goes red on a Monday.
_TODAY = "2026-08-14"  # a Friday, ISO week 2026-W33


def test_period_counts_reconcile_with_recurrence_counts() -> None:
    """The differential test: per-period totals must equal the lifetime count
    under the same multi-match policy. This is what catches the two matchers
    diverging -- the failure the shared `_matched_keys` exists to prevent."""
    findings = [
        _finding(title="hardcoded value not externalized", date="2026-07-06"),
        _finding(title="silent swallow with no timeout", date="2026-07-20"),
        _finding(title="resource leak, not closed", date="2026-08-03"),
        _finding(title="unrelated prose", category="api-contract", repo="atlas", date="2026-08-10"),
        _finding(title="hardcoded magic number", date="2026-08-12"),
    ]
    groups = compute_recurrence(findings, today=_TODAY)
    counts = compute_period_counts(findings)

    for group in groups:
        assert sum(counts[group.pattern_key].values()) == group.count, group.pattern_key
        assert sum(group.period_counts.values()) == group.count, group.pattern_key


def test_undated_findings_excluded_from_period_counts_but_not_from_count() -> None:
    findings = [
        _finding(title="resource leak, not closed", date="2026-08-03"),
        _finding(title="resource leak on close", date=""),
    ]
    groups = compute_recurrence(findings, today=_TODAY)
    matched = next(g for g in groups if g.pattern_key == "resource-leak")
    assert matched.count == 2
    assert sum(matched.period_counts.values()) == 1


def test_stopped_signature_is_not_rising() -> None:
    """Fired 5x in April and stopped. Lifetime count is high; trend is dead."""
    findings = [
        _finding(title="hardcoded value not externalized", date="2026-04-07") for _ in range(5)
    ]
    groups = compute_recurrence(findings, today=_TODAY)
    matched = next(g for g in groups if g.pattern_key == "hardcoded-not-configurable")
    assert matched.count == 5
    assert matched.promotable is True
    assert matched.rising is False


def test_recent_surge_is_rising() -> None:
    """1x/week for three weeks, then 5x in the most recent complete week."""
    findings = [
        _finding(title="resource leak, not closed", date="2026-07-15"),  # W29
        _finding(title="resource leak, not closed", date="2026-07-22"),  # W30
        _finding(title="resource leak, not closed", date="2026-07-29"),  # W31
    ] + [_finding(title="resource leak, not closed", date="2026-08-05") for _ in range(5)]  # W32
    groups = compute_recurrence(findings, today=_TODAY)
    matched = next(g for g in groups if g.pattern_key == "resource-leak")
    assert matched.rising is True


def test_partial_trailing_period_produces_no_spurious_rise_or_fall() -> None:
    """The trailing week (W33) is incomplete on `_TODAY` and must be ignored.

    W32 is the most recent complete week at 5, against 1/week before it -- so
    the verdict is driven entirely by complete periods and is *rising*. The
    two findings sitting in the partial W33 must neither create the flag nor
    (as a low-looking week) suppress it.
    """
    complete = [
        _finding(title="resource leak, not closed", date="2026-07-15"),
        _finding(title="resource leak, not closed", date="2026-07-22"),
        _finding(title="resource leak, not closed", date="2026-07-29"),
    ] + [_finding(title="resource leak, not closed", date="2026-08-05") for _ in range(5)]
    partial = [_finding(title="resource leak, not closed", date="2026-08-13") for _ in range(2)]

    with_partial = next(
        g
        for g in compute_recurrence(complete + partial, today=_TODAY)
        if g.pattern_key == "resource-leak"
    )
    without_partial = next(
        g for g in compute_recurrence(complete, today=_TODAY) if g.pattern_key == "resource-leak"
    )
    assert with_partial.rising == without_partial.rising is True
    # The partial period is still *reported*, just not used for the verdict.
    assert "2026-W33" in with_partial.period_counts


def test_single_firing_below_threshold_is_not_rising() -> None:
    """0 -> 1 is an infinite proportional rise and must not flag."""
    findings = [_finding(title="resource leak, not closed", date="2026-08-05")]
    groups = compute_recurrence(findings, today=_TODAY)
    matched = next(g for g in groups if g.pattern_key == "resource-leak")
    assert matched.rising is False


def test_rising_groups_sort_first() -> None:
    """A rising group outranks a higher-count group that is merely frequent."""
    stale = [
        _finding(title="hardcoded value not externalized", date="2026-04-07") for _ in range(9)
    ]
    surging = [
        _finding(title="resource leak, not closed", date="2026-07-15"),
        _finding(title="resource leak, not closed", date="2026-07-22"),
    ] + [_finding(title="resource leak, not closed", date="2026-08-05") for _ in range(5)]

    groups = compute_recurrence(stale + surging, today=_TODAY)
    assert groups[0].pattern_key == "resource-leak"
    assert groups[0].rising is True
    assert groups[0].count < next(g for g in groups if g.pattern_key.startswith("hardcoded")).count


def test_promotable_semantics_unchanged_by_rising() -> None:
    """`rising` must not loosen the existing promotion gate (Open Question 3)."""
    findings = [
        _finding(title="resource leak, not closed", date="2026-07-15"),
    ] + [_finding(title="resource leak, not closed", date="2026-08-05") for _ in range(2)]
    matched = next(
        g for g in compute_recurrence(findings, today=_TODAY) if g.pattern_key == "resource-leak"
    )
    assert matched.count == RECURRENCE_THRESHOLD
    assert matched.promotable is True
    # promotable is count-driven only; it never reads `rising`.
    below = [_finding(title="resource leak, not closed", date="2026-08-05") for _ in range(2)]
    matched_below = next(
        g for g in compute_recurrence(below, today=_TODAY) if g.pattern_key == "resource-leak"
    )
    assert matched_below.promotable is False


def test_direction_rising_matches_the_rising_property() -> None:
    """`direction` and the back-compat `rising` property must never disagree."""
    findings = [
        _finding(title="resource leak, not closed", date="2026-07-15"),
        _finding(title="resource leak, not closed", date="2026-07-22"),
    ] + [_finding(title="resource leak, not closed", date="2026-08-05") for _ in range(5)]
    matched = next(
        g for g in compute_recurrence(findings, today=_TODAY) if g.pattern_key == "resource-leak"
    )
    assert matched.direction == DIRECTION_RISING
    assert matched.rising is True


def test_declining_signature_is_falling() -> None:
    """5x/week for three weeks, then 1x. The boolean flag could not say this.

    This is the case GUA-109 exists to surface: a friction that was fixed reads as
    `falling`, where a boolean `rising` collapsed it into the same `False` as a
    signature that never moved at all.
    """
    findings = [
        _finding(title="resource leak, not closed", date=day)
        for day in ("2026-07-08", "2026-07-15", "2026-07-22")
        for _ in range(5)
    ] + [_finding(title="resource leak, not closed", date="2026-08-05")]
    matched = next(
        g for g in compute_recurrence(findings, today=_TODAY) if g.pattern_key == "resource-leak"
    )
    assert matched.direction == DIRECTION_FALLING
    assert matched.rising is False, "falling must not read as rising"


def test_steady_signature_is_flat() -> None:
    """Equal counts every week trend in neither direction."""
    findings = [
        _finding(title="resource leak, not closed", date=day)
        for day in ("2026-07-08", "2026-07-15", "2026-07-22", "2026-08-05")
        for _ in range(3)
    ]
    matched = next(
        g for g in compute_recurrence(findings, today=_TODAY) if g.pattern_key == "resource-leak"
    )
    assert matched.direction == DIRECTION_FLAT


def test_small_decline_is_flat_not_falling() -> None:
    """A 2 -> 1 drop lacks the prior mass to be worth calling a decline.

    Without the `FALLING_MIN_PRIOR_MEAN` gate every trailing-off one-off in the corpus
    would report as an improvement, drowning the declines that reflect real fixes.
    """
    findings = [
        _finding(title="resource leak, not closed", date=day)
        for day in ("2026-07-08", "2026-07-15", "2026-07-22")
        for _ in range(2)
    ]
    matched = next(
        g for g in compute_recurrence(findings, today=_TODAY) if g.pattern_key == "resource-leak"
    )
    assert matched.direction == DIRECTION_FLAT


def test_no_period_counts_is_flat() -> None:
    """A signature with no dated findings has no trend to report."""
    matched = next(
        g
        for g in compute_recurrence([_finding(title="resource leak, not closed", date="")])
        if g.pattern_key == "resource-leak"
    )
    assert matched.direction == DIRECTION_FLAT


def test_buckets_on_occurred_not_run_date() -> None:
    """The core GUA-109 behaviour: periods follow `occurred`, not the sweep's `date`.

    All four findings share one run `date`, which under the old rule put them in a single
    week and made the signature look like a spike. Their `occurred` dates spread them
    evenly, so the same rows read as flat.
    """
    findings = [
        _finding(title="resource leak, not closed", date="2026-08-05", occurred=day)
        for day in ("2026-07-08", "2026-07-15", "2026-07-22", "2026-08-05")
        for _ in range(3)
    ]
    matched = next(
        g for g in compute_recurrence(findings, today=_TODAY) if g.pattern_key == "resource-leak"
    )
    assert set(matched.period_counts) == {"2026-W28", "2026-W29", "2026-W30", "2026-W32"}
    assert matched.direction == DIRECTION_FLAT


def test_falls_back_to_date_when_occurred_absent() -> None:
    """Legacy rows written before GUA-109 must still land in a period."""
    findings = [_finding(title="resource leak, not closed", date="2026-08-05")]
    assert compute_period_counts(findings)["resource-leak"] == {"2026-W32": 1}


def test_first_and_last_seen_use_occurred() -> None:
    """The card's date range must agree with the trend beside it."""
    findings = [
        _finding(title="resource leak, not closed", date="2026-08-05", occurred="2026-07-08"),
        _finding(title="resource leak, not closed", date="2026-08-05", occurred="2026-07-22"),
    ]
    matched = next(g for g in compute_recurrence(findings) if g.pattern_key == "resource-leak")
    assert (matched.first_seen, matched.last_seen) == ("2026-07-08", "2026-07-22")


def test_period_counts_respect_multi_match_policy() -> None:
    """A title matching two patterns lands in both signatures' period counts."""
    findings = [_finding(title="silent swallow with no timeout on retry", date="2026-08-05")]
    counts = compute_period_counts(findings)
    assert counts["silent-swallow"]["2026-W32"] == 1
    assert counts["missing-timeout"]["2026-W32"] == 1


@pytest.mark.parametrize(
    "period,expected", [("day", "2026-08-05"), ("week", "2026-W32"), ("month", "2026-08")]
)
def test_period_counts_bucket_at_requested_period(period: str, expected: str) -> None:
    findings = [_finding(title="resource leak, not closed", date="2026-08-05")]
    counts = compute_period_counts(findings, period=period)
    assert counts["resource-leak"] == {expected: 1}


def test_unknown_period_raises() -> None:
    findings = [_finding(title="resource leak, not closed", date="2026-08-05")]
    with pytest.raises(ValueError, match="unknown period"):
        compute_period_counts(findings, period="quarter")


# --- Live corpus (Step 4 done-condition) ------------------------------------

_LIVE_CORPUS = Path("~/workspace/guacamayo/.claude/docs/review-findings.jsonl").expanduser()


def _live_rows() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in _LIVE_CORPUS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.mark.skipif(not _LIVE_CORPUS.exists(), reason="live review-findings.jsonl not present")
def test_live_corpus_is_time_diverse() -> None:
    """The inverse of GUA-104b's pinning test, which asserted the defect itself.

    That test held `max(by_date) > 50%` -- true, and the reason the trend signal was
    meaningless: one sweep stamped 85 of 125 rows with a single run date. Now that rows
    carry `occurred`, the corpus spreads across real friction dates, and this asserts the
    property the signal depends on rather than the bug.

    It guards forward: a future bulk sweep that re-concentrates the corpus, or a
    regression that reverts bucketing to the run date, fails here rather than silently
    making every signature look like it spiked at once.
    """
    rows = _live_rows()
    by_occurred: dict[str, int] = {}
    for row in rows:
        key = str(row.get("occurred") or row.get("date") or "")
        by_occurred[key] = by_occurred.get(key, 0) + 1

    assert max(by_occurred.values()) <= len(rows) * 0.5, (
        "one day holds >50% of the corpus -- the trend is measuring sweep scheduling again"
    )
    weeks = {period_key(day, "week") for day in by_occurred if day}
    assert len(weeks) >= 6, f"corpus spans only {len(weeks)} ISO weeks; too bursty to trend"


@pytest.mark.skipif(not _LIVE_CORPUS.exists(), reason="live review-findings.jsonl not present")
def test_live_corpus_directions_discriminate() -> None:
    """The signal must vary across groups. One value for everything carries no information.

    This is the real acceptance criterion for GUA-109: not that `direction` computes, but
    that it *distinguishes*. Under the old run-date bucketing every promotable group read
    the same way, which is what made `rising` unusable as a `/workflow-retro` trigger.
    """
    groups = compute_recurrence(_live_rows())
    assert groups, "live corpus produced no groups"
    directions = {g.direction for g in groups}
    assert len(directions) > 1, (
        f"every group reports {directions} -- the direction signal does not discriminate"
    )


@pytest.mark.skipif(not _LIVE_CORPUS.exists(), reason="live review-findings.jsonl not present")
def test_live_corpus_yields_expected_top_pattern() -> None:
    """Verified during planning (Step 0) against the real 125-row corpus.

    A drift here means the corpus has changed since planning -- that is itself
    worth knowing, not a bug in this test.
    """
    rows: list[dict[str, Any]] = []
    for line in _LIVE_CORPUS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))

    groups = compute_recurrence(rows)
    matched = next(g for g in groups if g.pattern_key == "hardcoded-not-configurable")
    assert matched.count >= 20
    assert len(matched.repos) >= 4


@pytest.mark.skipif(not _LIVE_CORPUS.exists(), reason="live review-findings.jsonl not present")
def test_live_corpus_new_signatures_reduce_unmatched_promotables() -> None:
    """Retro F3: before this change, 7 of 14 promotable groups were `unmatched:`
    fallbacks -- the pattern table had no signature for those clusters.

    `unhandled-none-return` clears the threshold on the live corpus (n=3).

    `god-module` was n=2 when written -- one instance short, recorded rather than
    papered over by loosening the regex. It reached n=3 on 2026-08-14 when the
    corpus grew to 145 rows and supplied a genuine third instance ("God object:
    dashboard.py (3493 lines) mixes unrelated concerns"), matched by the ORIGINAL
    regex with no change to it. That is the outcome the n=2 pin was waiting for,
    so the assertion now tracks the threshold instead of the literal count.
    `test_god_module_does_not_match_expression_complexity` still pins the
    exclusion that kept it at 2 in the first place.
    """
    rows: list[dict[str, Any]] = []
    for line in _LIVE_CORPUS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))

    groups = {g.pattern_key: g for g in compute_recurrence(rows)}

    assert groups["unhandled-none-return"].count >= RECURRENCE_THRESHOLD
    assert groups["unhandled-none-return"].promotable is True

    assert groups["god-module"].count >= RECURRENCE_THRESHOLD
    assert groups["god-module"].promotable is True


# --- GUA-115 signatures, derived from the 76 unmatched titles ----------------
#
# Each match test uses the real corpus titles the signature was derived from, so a
# regex narrowed later fails here rather than silently dropping a live cluster.


def test_unguarded_write_signature() -> None:
    findings = [
        _finding(title="Write-capable tool modifies wiki without user confirmation dialog"),
        _finding(title="Unauthenticated writeback endpoint allows arbitrary wiki modifications"),
        _finding(title="WebSocket endpoint lacks authentication and rate-limiting"),
        _finding(title="Unconditional persistent write without opt-out or confirmation gate"),
    ]
    groups = compute_recurrence(findings)
    matched = next(g for g in groups if g.pattern_key == "unguarded-write")
    assert matched.count == 4
    assert matched.promotable is True


def test_unguarded_write_does_not_match_protection_present() -> None:
    """Absence of a gate, not the topic of gates.

    These three titles sit in the live corpus and report protection that EXISTS.
    The corpus carries no severity or polarity field, so the regex is the only
    thing separating them from the real findings -- matching on topic words like
    "path traversal" would count a working safeguard as friction and would have
    taken `unguarded-write` from n=4 to n=7 on false positives.
    """
    findings = [
        _finding(title="Path traversal protection in writeback endpoint", category="security"),
        _finding(title="Comprehensive secret redaction in structured logging pipeline"),
        _finding(
            title="Private directory exclusion in wiki search prevents information disclosure"
        ),
    ]
    groups = compute_recurrence(findings)
    assert not any(g.pattern_key == "unguarded-write" for g in groups)


def test_unbounded_growth_signature() -> None:
    findings = [
        _finding(title="Unbounded JSONL file append with no rotation or size limit"),
        _finding(title="Unbounded query results loaded into memory"),
        _finding(
            title=(
                "Graph expansion rebuilds the entire edge graph on every "
                "expand=True request with no caching"
            )
        ),
    ]
    groups = compute_recurrence(findings)
    matched = next(g for g in groups if g.pattern_key == "unbounded-growth")
    assert matched.count == 3
    assert matched.promotable is True


def test_unbounded_growth_is_distinct_from_resource_leak() -> None:
    """A bound never set is not a handle never released.

    Both are "resources go wrong", but they take different fixes -- a cap/rotation
    policy vs. a close/context-manager -- so folding them into one signature would
    make the promoted pattern unactionable.
    """
    findings = [_finding(title="file handle leak on exception path, not closed")]
    groups = compute_recurrence(findings)
    keys = {g.pattern_key for g in groups}
    assert "resource-leak" in keys
    assert "unbounded-growth" not in keys


def test_race_condition_signature() -> None:
    findings = [
        _finding(title="DuckDB concurrent table creation race condition"),
        _finding(title="TOCTOU race condition in sweep file creation"),
        _finding(title="Session filename collision risk at minute precision"),
    ]
    groups = compute_recurrence(findings)
    matched = next(g for g in groups if g.pattern_key == "race-condition")
    assert matched.count == 3
    assert matched.promotable is True


def test_repeated_per_call_work_signature() -> None:
    findings = [
        _finding(title="N+1 glob traversals in page title lookup"),
        _finding(title="Potential N+1 pattern in per-message cost computation"),
        _finding(title="Inefficient per-call import of time module"),
        _finding(title="Inline import of `time` module inside function"),
    ]
    groups = compute_recurrence(findings)
    matched = next(g for g in groups if g.pattern_key == "repeated-per-call-work")
    assert matched.count == 4
    assert matched.promotable is True


def test_recompute_per_search_counts_in_both_overlapping_signatures() -> None:
    """One live title is honestly both uncached AND recomputed per search.

    Pinned because the overlap looks like a bug: under the all-matches policy it
    is counted in each group deliberately, and "fixing" it by narrowing either
    regex would drop a real instance from the other.
    """
    findings = [_finding(title="Graph expansion recomputes all typed edges on every search")]
    keys = {g.pattern_key for g in compute_recurrence(findings)}
    assert "unbounded-growth" in keys
    assert "repeated-per-call-work" in keys


def test_error_not_surfaced_signature() -> None:
    findings = [
        _finding(title="Subprocess errors logged but not surfaced to caller"),
        _finding(title="Optional dependency degradation without client-side awareness"),
        _finding(
            title=(
                "Error details are truncated and summary-only; "
                "full context lost for root cause analysis"
            )
        ),
    ]
    groups = compute_recurrence(findings)
    matched = next(g for g in groups if g.pattern_key == "error-not-surfaced")
    assert matched.count == 3
    assert matched.promotable is True


def test_error_not_surfaced_is_distinct_from_silent_swallow() -> None:
    """Logged-but-not-raised is not swallowed.

    `silent-swallow` is about an error nobody recorded; this signature is about an
    error that WAS recorded but never reached whoever could act on it. Same fix
    family, different defect, and the corpus distinguishes them.
    """
    findings = [_finding(title="bare except suppresses the error silently")]
    keys = {g.pattern_key for g in compute_recurrence(findings)}
    assert "silent-swallow" in keys
    assert "error-not-surfaced" not in keys


def test_doc_implementation_mismatch_signature() -> None:
    findings = [
        _finding(title="Makefile test target documentation does not match implementation"),
        _finding(title="schema_for docstring claims minLength is emitted; only maxLength is"),
        _finding(
            title=(
                "Wander dispatch timing mismatch: always-on in code vs. 'when diff exists' in plan"
            )
        ),
        _finding(
            title=(
                "Wander always-on unconditionally, but plan documentation says "
                "'when diff scope exists'"
            )
        ),
    ]
    groups = compute_recurrence(findings)
    matched = next(g for g in groups if g.pattern_key == "doc-implementation-mismatch")
    assert matched.count == 4
    assert matched.promotable is True


def test_no_signature_added_for_vacuous_test_assertion() -> None:
    """The signature that was NOT added, recorded so the omission is deliberate.

    Only two live titles describe a vacuous assertion (both the `or True` defect).
    A third candidate -- "exception-path test asserts close() only, not HTTP 500
    surfaced" -- is a WEAK assertion, not a vacuous one, and stretching the regex
    to cover it would be fitting to the n=3 threshold rather than to the friction.
    Same call as `god-module`; revisit when the corpus supplies a real third.
    """
    findings = [
        _finding(title="Test assertion always passes due to 'or True' clause"),
        _finding(title="Tautological assertion with `or True` provides no validation"),
        _finding(title="exception-path test asserts close() only, not HTTP 500 surfaced"),
    ]
    groups = {g.pattern_key for g in compute_recurrence(findings)}
    assert not any(k.startswith(("vacuous", "tautolog")) for k in groups)


@pytest.mark.skipif(not _LIVE_CORPUS.exists(), reason="live review-findings.jsonl not present")
def test_live_corpus_gua115_signatures_clear_threshold() -> None:
    """Every GUA-115 signature must earn its place on the real corpus.

    Counts are pinned to what the 145-row corpus produced when they were derived.
    A drop below threshold means a signature stopped describing real friction; a
    rise is fine and only the floor is asserted.
    """
    groups = {g.pattern_key: g for g in compute_recurrence(_live_rows())}
    expected = {
        "unguarded-write": 4,
        "unbounded-growth": 4,
        "race-condition": 3,
        "repeated-per-call-work": 5,
        "error-not-surfaced": 3,
        "doc-implementation-mismatch": 4,
    }
    for key, floor in expected.items():
        assert key in groups, f"{key} matched nothing on the live corpus"
        assert groups[key].count >= floor, f"{key} fell to {groups[key].count}, expected >= {floor}"
        assert groups[key].promotable is True


@pytest.mark.skipif(not _LIVE_CORPUS.exists(), reason="live review-findings.jsonl not present")
def test_live_corpus_unmatched_share_drops() -> None:
    """The point of the change: fewer findings sitting in `unmatched:` fallbacks.

    Asserted as a ceiling on the unmatched share rather than an exact count, so
    adding corpus rows does not break the suite -- only a regression in coverage does.
    """
    rows = _live_rows()
    groups = compute_recurrence(rows)
    unmatched = sum(g.count for g in groups if g.pattern_key.startswith("unmatched:"))
    assert unmatched / len(rows) < 0.45
