"""Planted-defect tests for the board consistency checkers (GUA-103).

Standing rule: **never ship a guard without a negative test.** `eslint-plugin-import`'s
`no-unused-modules` reported zero violations against a planted orphan for weeks — a guard
that always passes is worse than none, because it also produces a green check. "It passed"
is not evidence it can fail.

So every checker here is tested in both directions: input containing the defect must
produce a finding, and clean input must produce none. A suite asserting only the first
would pass against a checker that flags everything unconditionally.

The path-checking tests were removed with `check_stale_paths` on 2026-08-14 — the
checker passed every one of them and was still 100% false-positive on the live corpus,
because the tests encoded the assumption the checker got wrong: that a backticked path
in an issue body is a claim the path *exists*. See the `consistency.py` docstring.
"""

from __future__ import annotations

from typing import Any

import pytest

from telemetry.consistency import (
    WIP_LIMIT,
    Inconsistency,
    check_label_artifact,
    to_report,
)


def _issue(
    number: int = 1,
    repo: str = "guacamayo",
    state: str = "OPEN",
    body: str = "",
    labels: str = "",
    **overrides: Any,
) -> dict[str, Any]:
    row = {
        "number": number,
        "repo": repo,
        "state": state,
        "body": body,
        "labels": labels,
        "title": f"issue {number}",
    }
    row.update(overrides)
    return row


def _pr(
    number: int = 10,
    repo: str = "guacamayo",
    state: str = "OPEN",
    body: str = "",
    title: str = "",
) -> dict[str, Any]:
    return {"number": number, "repo": repo, "state": state, "body": body, "title": title}


# --------------------------------------------------------------------------
# check_label_artifact
# --------------------------------------------------------------------------


def test_finds_in_review_without_open_pr() -> None:
    issues = [_issue(number=5, labels="in-review")]
    found = check_label_artifact(issues, prs=[], plan_issues=set())
    assert [f.kind for f in found] == ["label-artifact"]
    assert found[0].issue == 5


def test_in_review_with_open_pr_is_clean() -> None:
    issues = [_issue(number=5, labels="in-review")]
    prs = [_pr(body="Closes #5")]
    assert check_label_artifact(issues, prs, plan_issues=set()) == []


def test_in_review_matches_pr_title_reference() -> None:
    issues = [_issue(number=5, labels="in-review")]
    prs = [_pr(title="GUA-5 consistency check (#5)")]
    assert check_label_artifact(issues, prs, plan_issues=set()) == []


def test_merged_pr_does_not_clear_in_review() -> None:
    """A closed PR is why the label is stale, not evidence that it is fine."""
    issues = [_issue(number=5, labels="in-review")]
    prs = [_pr(state="MERGED", body="Closes #5")]
    assert len(check_label_artifact(issues, prs, plan_issues=set())) == 1


def test_finds_ready_without_plan_doc() -> None:
    issues = [_issue(number=7, labels="ready")]
    found = check_label_artifact(issues, prs=[], plan_issues=set())
    assert len(found) == 1
    assert "ready" in found[0].detail


def test_ready_with_plan_doc_is_clean() -> None:
    issues = [_issue(number=7, labels="ready")]
    found = check_label_artifact(issues, prs=[], plan_issues={("guacamayo", 7)})
    assert found == []


def test_finds_wip_over_limit() -> None:
    issues = [_issue(number=n, labels="in-progress") for n in range(WIP_LIMIT + 1)]
    found = check_label_artifact(issues, prs=[], plan_issues=set())
    wip = [f for f in found if f.issue is None]
    assert len(wip) == 1
    assert str(WIP_LIMIT + 1) in wip[0].evidence


def test_wip_at_limit_is_clean() -> None:
    issues = [_issue(number=n, labels="in-progress") for n in range(WIP_LIMIT)]
    found = check_label_artifact(issues, prs=[], plan_issues=set())
    assert [f for f in found if f.issue is None] == []


def test_closed_issue_labels_are_ignored() -> None:
    issues = [_issue(number=5, state="CLOSED", labels="in-review,ready")]
    assert check_label_artifact(issues, prs=[], plan_issues=set()) == []


# --------------------------------------------------------------------------
# Inconsistency + report shape
# --------------------------------------------------------------------------


def test_evidence_is_mandatory() -> None:
    """A finding without evidence is an assertion, and assertions are why this exists."""
    with pytest.raises(ValueError):
        Inconsistency(kind="label-artifact", repo="r", issue=1, detail="d", evidence="   ")


def test_report_carries_coverage_fields() -> None:
    """An empty report must be distinguishable from an unchecked one."""
    report = to_report(
        [],
        issues_checked=0,
        repos_checked=["guacamayo"],
        unmatchable_plans=26,
    )
    assert report["total"] == 0
    assert report["coverage"]["unmatchable_plans"] == 26
    assert report["issues_checked"] == 0


def test_report_groups_counts_by_kind() -> None:
    items = [
        Inconsistency(kind="plan-issue-drift", repo="a", issue=1, detail="d", evidence="e"),
        Inconsistency(kind="plan-issue-drift", repo="a", issue=2, detail="d", evidence="e"),
        Inconsistency(kind="label-artifact", repo="a", issue=3, detail="d", evidence="e"),
    ]
    report = to_report(
        items,
        issues_checked=3,
        repos_checked=["a"],
        unmatchable_plans=0,
    )
    assert report["counts_by_kind"] == {"plan-issue-drift": 2, "label-artifact": 1}
    assert report["total"] == 3
