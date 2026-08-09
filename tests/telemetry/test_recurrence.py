from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from telemetry.recurrence import RECURRENCE_THRESHOLD, compute_recurrence


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


# --- Live corpus (Step 4 done-condition) ------------------------------------

_LIVE_CORPUS = Path("~/workspace/guacamayo/.claude/docs/review-findings.jsonl").expanduser()


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
