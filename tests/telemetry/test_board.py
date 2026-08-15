"""Tests for the board column derivation (GUA-113).

Standing rule: **never ship a guard without a negative test.** Every checker is tested
in both directions — input containing the defect must produce the expected column, and
clean input must not produce false positives.

Two required negative tests per the plan DoD:
    - test_derive_column_undetermined_on_none_ancestor  (is_ancestor=None must not → in_progress)
    - test_derive_column_undetermined_on_pr_fetch_failure  (pr_fetch_ok=False must not → backlog)
"""

from __future__ import annotations

from typing import Any

import pytest

from telemetry.__main__ import EmptyInputError
from telemetry.board import BoardRecord, derive_column, to_board_json
from telemetry.consistency import BranchFact

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _issue(
    number: int = 1,
    repo: str = "guacamayo",
    state: str = "OPEN",
    labels: str = "",
    title: str = "test issue",
    body: str = "",
    **overrides: Any,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "number": number,
        "repo": repo,
        "state": state,
        "labels": labels,
        "title": title,
        "body": body,
    }
    row.update(overrides)
    return row


def _pr(
    number: int = 10,
    repo: str = "guacamayo",
    state: str = "OPEN",
    head_ref: str = "",
    body: str = "",
    title: str = "",
    merged_at: str | None = None,
) -> dict[str, Any]:
    return {
        "number": number,
        "repo": repo,
        "state": state,
        "head_ref": head_ref,
        "body": body,
        "title": title,
        "merged_at": merged_at,
    }


def _branch_fact(
    branch: str = "GUA-1-some-feature",
    repo: str = "guacamayo",
    issue_num: int = 1,
    is_ancestor: bool | None = False,
) -> BranchFact:
    return BranchFact(repo=repo, branch=branch, issue_num=issue_num, is_ancestor=is_ancestor)


def _derive(
    issue: dict[str, Any],
    prs: list[dict[str, Any]] | None = None,
    branch_facts: list[BranchFact] | None = None,
    plan_issues: set[tuple[str, int]] | None = None,
    pr_fetch_ok: bool = True,
    collected_at: str = "2026-08-15T12:00:00+00:00",
) -> BoardRecord:
    return derive_column(
        issue=issue,
        prs_for_repo=prs or [],
        branch_facts_for_repo=branch_facts or [],
        plan_issues=plan_issues or set(),
        pr_fetch_ok=pr_fetch_ok,
        collected_at=collected_at,
    )


# ---------------------------------------------------------------------------
# 1. closed
# ---------------------------------------------------------------------------


def test_derive_column_closed() -> None:
    """CLOSED issue → column=closed, regardless of PRs or branches."""
    record = _derive(
        _issue(state="CLOSED"),
        prs=[_pr(body="Closes #1", merged_at="2026-08-01T00:00:00Z")],
        branch_facts=[_branch_fact(is_ancestor=False)],
    )
    assert record.column == "closed"
    assert record.backlog_stage is None


# ---------------------------------------------------------------------------
# 2. merged
# ---------------------------------------------------------------------------


def test_derive_column_merged_via_branch_name() -> None:
    """OPEN issue + PR joined by branch name with mergedAt → column=merged."""
    record = _derive(
        _issue(number=5),
        prs=[_pr(number=20, head_ref="GUA-5-my-feature", merged_at="2026-08-10T10:00:00Z")],
    )
    assert record.column == "merged"
    assert record.backlog_stage is None
    assert "20" in record.evidence


def test_derive_column_merged_via_closes_body() -> None:
    """OPEN issue + PR joined by Closes #N body with mergedAt → column=merged."""
    record = _derive(
        _issue(number=7),
        prs=[_pr(number=30, body="Closes #7", merged_at="2026-08-11T00:00:00Z")],
    )
    assert record.column == "merged"


# ---------------------------------------------------------------------------
# 3. in_review
# ---------------------------------------------------------------------------


def test_derive_column_in_review_via_closes_body() -> None:
    """OPEN issue + OPEN PR with Closes #N, no mergedAt → column=in_review."""
    record = _derive(
        _issue(number=9),
        prs=[_pr(number=40, body="Closes #9", state="OPEN", merged_at=None)],
    )
    assert record.column == "in_review"
    assert record.backlog_stage is None


def test_derive_column_in_review_via_branch_name() -> None:
    """OPEN issue + OPEN PR joined by branch name → column=in_review."""
    record = _derive(
        _issue(number=3),
        prs=[_pr(number=15, head_ref="GUA-3-refactor", state="OPEN", merged_at=None)],
    )
    assert record.column == "in_review"


# ---------------------------------------------------------------------------
# 4. in_progress
# ---------------------------------------------------------------------------


def test_derive_column_in_progress() -> None:
    """OPEN issue + BranchFact with matching issue_num and is_ancestor=False → in_progress."""
    record = _derive(
        _issue(number=11),
        branch_facts=[_branch_fact(branch="GUA-11-new-feature", issue_num=11, is_ancestor=False)],
    )
    assert record.column == "in_progress"
    assert record.backlog_stage is None
    assert "is_ancestor=False" in record.evidence


# ---------------------------------------------------------------------------
# 5. backlog
# ---------------------------------------------------------------------------


def test_derive_column_backlog() -> None:
    """OPEN issue, no PRs, no matching branch facts → column=backlog."""
    record = _derive(_issue(number=2))
    assert record.column == "backlog"
    assert record.backlog_stage == "scope"  # default sub-stage


def test_derive_column_backlog_stage_ready() -> None:
    """OPEN issue in plan_issues with 'ready' label → backlog_stage=ready."""
    record = _derive(
        _issue(number=2, labels="ready"),
        plan_issues={("guacamayo", 2)},
    )
    assert record.column == "backlog"
    assert record.backlog_stage == "ready"


def test_derive_column_backlog_stage_refine() -> None:
    """OPEN issue in plan_issues without 'ready' → backlog_stage=refine."""
    record = _derive(
        _issue(number=2, labels="in-progress"),
        plan_issues={("guacamayo", 2)},
    )
    assert record.column == "backlog"
    assert record.backlog_stage == "refine"


def test_derive_column_backlog_stage_research() -> None:
    """OPEN issue not in plan_issues with 'research' label → backlog_stage=research."""
    record = _derive(_issue(number=2, labels="research"))
    assert record.column == "backlog"
    assert record.backlog_stage == "research"


# ---------------------------------------------------------------------------
# 6. NEGATIVE TEST — undetermined on is_ancestor=None
# ---------------------------------------------------------------------------


def test_derive_column_undetermined_on_none_ancestor() -> None:
    """NEGATIVE TEST: is_ancestor=None must NOT produce in_progress or backlog.

    This is the tri-state gap: a branch whose ancestry is unknown is not evidence
    of active work. The column must be 'undetermined', never 'in_progress' or 'backlog'.

    Planting the defect: a BranchFact with is_ancestor=None for this issue.
    A buggy derivation that treats None as False would return in_progress.
    A buggy derivation that ignores None-ancestry branches entirely would return backlog.
    The correct derivation returns undetermined.
    """
    record = _derive(
        _issue(number=13),
        branch_facts=[_branch_fact(branch="GUA-13-foo", issue_num=13, is_ancestor=None)],
    )
    assert record.column == "undetermined", (
        f"Expected 'undetermined' but got {record.column!r}. "
        "is_ancestor=None means origin/main did not resolve — ancestry unknown. "
        "This must not silently absorb into in_progress or backlog."
    )
    assert record.column != "in_progress"
    assert record.column != "backlog"
    assert record.backlog_stage is None


# ---------------------------------------------------------------------------
# 6b. NEGATIVE TEST — undetermined on PR fetch failure
# ---------------------------------------------------------------------------


def test_derive_column_undetermined_on_pr_fetch_failure() -> None:
    """NEGATIVE TEST: pr_fetch_ok=False must NOT produce backlog.

    `merged` and `in_review` are only derivable from the PR list. An empty PR list
    from a fetch failure is indistinguishable from an empty PR list from a repo with
    no PRs — unless the pr_fetch_ok flag is read. Without this flag, a failed fetch
    renders as 'nobody started it', which is the indistinguishability this issue exists
    to prevent.

    Planting the defect: pr_fetch_ok=False with a healthy (empty) branch facts list.
    A buggy derivation that ignores pr_fetch_ok would skip to backlog.
    The correct derivation returns undetermined.
    """
    record = _derive(
        _issue(number=17),
        prs=[],  # empty because fetch failed, not because no PRs
        branch_facts=[],  # healthy empty
        pr_fetch_ok=False,  # the flag that distinguishes failure from "no PRs"
    )
    assert record.column == "undetermined", (
        f"Expected 'undetermined' but got {record.column!r}. "
        "pr_fetch_ok=False means merged/in_review cannot be derived. "
        "This must not silently absorb into backlog."
    )
    assert record.column != "backlog"
    assert record.backlog_stage is None


# ---------------------------------------------------------------------------
# 7. to_board_json — skipped_repos always present
# ---------------------------------------------------------------------------


def test_to_board_json_skipped_repos_always_present() -> None:
    """Even with zero skipped repos, skipped_repos key is present and is an empty list."""
    records = [
        BoardRecord(
            repo="guacamayo",
            issue_num=1,
            title="test",
            raw_label="",
            column="backlog",
            backlog_stage="scope",
            evidence="no artifacts",
            collected_at="2026-08-15T12:00:00+00:00",
        )
    ]
    payload = to_board_json(records, skipped_repos=[], repos_checked=["guacamayo"])
    assert "skipped_repos" in payload
    assert payload["skipped_repos"] == []
    assert isinstance(payload["skipped_repos"], list)


# ---------------------------------------------------------------------------
# 8. to_board_json — envelope collected_at is minimum
# ---------------------------------------------------------------------------


def test_to_board_json_envelope_collected_at_is_minimum() -> None:
    """Envelope collected_at equals the earlier of two record timestamps."""
    early = "2026-08-15T10:00:00+00:00"
    late = "2026-08-15T12:00:00+00:00"
    records = [
        BoardRecord(
            repo="guacamayo",
            issue_num=1,
            title="older",
            raw_label="",
            column="backlog",
            backlog_stage="scope",
            evidence="no artifacts",
            collected_at=early,
        ),
        BoardRecord(
            repo="guacamayo",
            issue_num=2,
            title="newer",
            raw_label="",
            column="in_progress",
            backlog_stage=None,
            evidence="branch exists",
            collected_at=late,
        ),
    ]
    payload = to_board_json(records, skipped_repos=[], repos_checked=["guacamayo"])
    assert payload["collected_at"] == early, (
        f"Expected envelope collected_at={early!r} (minimum) but got {payload['collected_at']!r}"
    )


# ---------------------------------------------------------------------------
# 9. empty-fetch guard
# ---------------------------------------------------------------------------


def test_empty_fetch_guard() -> None:
    """to_board_json with empty records list raises EmptyInputError."""
    with pytest.raises(EmptyInputError):
        to_board_json([], skipped_repos=[], repos_checked=["guacamayo"])


# ---------------------------------------------------------------------------
# Additional shape tests
# ---------------------------------------------------------------------------


def test_board_record_carries_all_fields() -> None:
    """Each record in the JSON payload carries all required fields."""
    records = [
        BoardRecord(
            repo="guacamayo",
            issue_num=42,
            title="Board contract",
            raw_label="in-progress,ready",
            column="in_progress",
            backlog_stage=None,
            evidence="branch GUA-42-foo, is_ancestor=False",
            collected_at="2026-08-15T11:00:00+00:00",
        )
    ]
    payload = to_board_json(records, skipped_repos=[], repos_checked=["guacamayo"])
    rec = payload["records"][0]
    for field in (
        "repo",
        "issue_num",
        "title",
        "raw_label",
        "column",
        "backlog_stage",
        "evidence",
        "collected_at",
    ):
        assert field in rec, f"Missing field {field!r} in record"
    assert rec["repo"] == "guacamayo"
    assert rec["issue_num"] == 42
    assert rec["column"] == "in_progress"


def test_merged_pr_in_pr_list_not_joined_to_other_issue() -> None:
    """A merged PR for issue #5 must not affect derivation for issue #6."""
    record = _derive(
        _issue(number=6),
        prs=[_pr(number=50, head_ref="GUA-5-other", merged_at="2026-08-10T00:00:00Z")],
    )
    # Issue 6 has no matching PR (PR is for issue 5), no branches → backlog
    assert record.column == "backlog"


def test_is_ancestor_true_branch_does_not_produce_in_progress() -> None:
    """A merged branch (is_ancestor=True) must not produce in_progress."""
    record = _derive(
        _issue(number=20),
        prs=[],
        branch_facts=[_branch_fact(branch="GUA-20-old", issue_num=20, is_ancestor=True)],
    )
    # Branch is merged but no open PR — falls through to backlog (no undetermined trigger)
    assert record.column != "in_progress"
