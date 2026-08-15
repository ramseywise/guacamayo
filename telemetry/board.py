"""Board state derivation for `uv run telemetry --board` (GUA-113).

Pure functions over already-fetched data — `__main__` owns all I/O and passes data in.
This mirrors `telemetry/consistency.py`: testable without subprocess mocks.

The board answers "which column is each issue in right now?", derived from issue state,
PR state, and branch facts — not from labels. Labels travel alongside as `raw_label`
so the disagreement between what the label claims and what the artifacts show is itself
a signal.

Column ladder (first match wins):

    closed       — issue state is CLOSED
    merged       — issue OPEN, a joined PR has non-null mergedAt
    in_review    — issue OPEN, a joined PR is OPEN (no mergedAt)
    in_progress  — issue OPEN, a BranchFact with matching issue_num has is_ancestor=False
    backlog      — derivation completed cleanly, none of the above
    undetermined — derivation could not complete (e.g. PR fetch failed for this repo)

A failed PR fetch is sufficient for `undetermined` on its own: `merged` and `in_review`
are only derivable from the PR list, so an empty list from a fetch failure is
indistinguishable from an empty list from a repo with no PRs — unless the fetch-ok
flag is read explicitly.

`is_ancestor is None` must NOT produce `in_progress` — that is the tri-state gap.
A branch whose ancestry is unknown is not evidence of active work.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from telemetry.consistency import _BRANCH_CONVENTION_RE, BranchFact, _referenced_issues

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class BoardRecord:
    """Derived column state for one issue.

    `collected_at` is set by the collector per-record (ISO 8601 UTC).
    The envelope `collected_at` in the output JSON is the minimum across all records.
    """

    repo: str
    issue_num: int
    title: str
    raw_label: str  # comma-joined label names, "" if none — travels alongside column
    column: str  # "closed" | "merged" | "in_review" | "in_progress" | "backlog" | "undetermined"
    backlog_stage: str | None  # "scope"|"research"|"plan"|"refine"|"ready" | None (non-backlog)
    evidence: str  # one-line justification for the derived column
    collected_at: str  # ISO 8601 UTC, per-record


def _join_prs(
    repo: str,
    issue_num: int,
    prs_for_repo: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """PRs that reference this issue, joined by branch name or Closes #N in body/title."""
    matched: list[dict[str, Any]] = []
    for pr in prs_for_repo:
        # Branch-name join: head_ref matches {PREFIX}-{issue_num}-
        head_ref = str(pr.get("head_ref") or "")
        m = _BRANCH_CONVENTION_RE.match(head_ref)
        if m and int(m.group(2)) == issue_num:
            matched.append(pr)
            continue
        # Body/title join: Closes #N or (#N)
        if issue_num in _referenced_issues(pr):
            matched.append(pr)
    return matched


def _backlog_stage(
    repo: str,
    issue_num: int,
    labels: set[str],
    plan_issues: set[tuple[str, int]],
) -> str:
    """Sub-stage within backlog, based on plan-doc presence and labels."""
    in_plans = (repo, issue_num) in plan_issues
    if in_plans and "ready" in labels:
        return "ready"
    if in_plans:
        return "refine"
    if "ready" in labels:
        # ready label but no plan doc — mismatch worth naming
        return "plan"
    if "research" in labels:
        return "research"
    return "scope"


def derive_column(
    issue: dict[str, Any],
    prs_for_repo: list[dict[str, Any]],
    branch_facts_for_repo: list[BranchFact],
    plan_issues: set[tuple[str, int]],
    pr_fetch_ok: bool,
    collected_at: str,
) -> BoardRecord:
    """Derive the board column for one issue.

    `pr_fetch_ok=False` means the PR fetch for this repo failed — any issue that would
    require a PR join to determine its column is `undetermined`, never `backlog`.

    `branch_facts_for_repo` entries with `is_ancestor is None` must NOT produce
    `in_progress` — that is the tri-state gap (ancestry unknown != not merged).
    """
    repo = str(issue.get("repo") or "unknown")
    issue_num = int(issue.get("number") or 0)
    title = str(issue.get("title") or "")
    raw_label = str(issue.get("labels") or "")
    labels = {lbl.strip() for lbl in raw_label.split(",") if lbl.strip()}
    state = (issue.get("state") or "").upper()

    # --- closed ---
    if state == "CLOSED":
        return BoardRecord(
            repo=repo,
            issue_num=issue_num,
            title=title,
            raw_label=raw_label,
            column="closed",
            backlog_stage=None,
            evidence="issue state is CLOSED",
            collected_at=collected_at,
        )

    # --- merged / in_review (require PR join) ---
    if not pr_fetch_ok:
        # Can't determine merged or in_review — undetermined
        return BoardRecord(
            repo=repo,
            issue_num=issue_num,
            title=title,
            raw_label=raw_label,
            column="undetermined",
            backlog_stage=None,
            evidence="PR fetch failed for this repo; merged/in_review cannot be derived",
            collected_at=collected_at,
        )

    joined_prs = _join_prs(repo, issue_num, prs_for_repo)

    for pr in joined_prs:
        if pr.get("merged_at") is not None:
            return BoardRecord(
                repo=repo,
                issue_num=issue_num,
                title=title,
                raw_label=raw_label,
                column="merged",
                backlog_stage=None,
                evidence=f"joined PR #{pr.get('number')} has mergedAt={pr['merged_at']!r}",
                collected_at=collected_at,
            )

    for pr in joined_prs:
        pr_state = (pr.get("state") or "").upper()
        if pr_state == "OPEN":
            return BoardRecord(
                repo=repo,
                issue_num=issue_num,
                title=title,
                raw_label=raw_label,
                column="in_review",
                backlog_stage=None,
                evidence=f"joined PR #{pr.get('number')} is OPEN",
                collected_at=collected_at,
            )

    # --- in_progress (require is_ancestor=False explicitly) ---
    for bf in branch_facts_for_repo:
        if bf.issue_num == issue_num:
            if bf.is_ancestor is None:
                # Tri-state gap: ancestry unknown — cannot conclude in_progress
                return BoardRecord(
                    repo=repo,
                    issue_num=issue_num,
                    title=title,
                    raw_label=raw_label,
                    column="undetermined",
                    backlog_stage=None,
                    evidence=(
                        f"branch {bf.branch!r} found but origin/main did not resolve "
                        "(is_ancestor=None); ancestry unknown"
                    ),
                    collected_at=collected_at,
                )
            if bf.is_ancestor is False:
                return BoardRecord(
                    repo=repo,
                    issue_num=issue_num,
                    title=title,
                    raw_label=raw_label,
                    column="in_progress",
                    backlog_stage=None,
                    evidence=f"branch {bf.branch!r} exists, is_ancestor=False",
                    collected_at=collected_at,
                )
            # is_ancestor=True means merged branch — no PR join caught it; keep going

    # --- backlog ---
    stage = _backlog_stage(repo, issue_num, labels, plan_issues)
    return BoardRecord(
        repo=repo,
        issue_num=issue_num,
        title=title,
        raw_label=raw_label,
        column="backlog",
        backlog_stage=stage,
        evidence=f"no PR join, no unmerged branch; backlog_stage={stage!r}",
        collected_at=collected_at,
    )


def to_board_json(
    records: list[BoardRecord],
    skipped_repos: list[dict[str, str]],
    repos_checked: list[str],
    heartbeat: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The JSON payload `_run_board` writes and `/wake` reads.

    `skipped_repos` is a required key — always present even when empty. An absent key
    is indistinguishable from "no repos were skipped", which makes a truncated board
    presentable as a complete one. That is the exact shape this issue exists to prevent.

    The envelope `collected_at` is the MINIMUM of all per-record timestamps — a
    partially-refreshed board's staleness is measured from its oldest record, which is
    the most conservative and correct choice. If `records` is empty and the issue list
    was non-empty, `EmptyInputError` should have been raised by the caller before here.

    `heartbeat` carries per-run liveness metadata: `started_at`, `finished_at`,
    `exit`, `duration_s`. Written on every successful run so a reader can detect a
    stopped job without waiting for the staleness threshold. On failure, `_run_board`
    writes a minimal failure envelope (not via this function) so `exit` is non-zero.
    A missing heartbeat key means the board was written before GUA-118.
    """
    from telemetry.__main__ import EmptyInputError

    if not records:
        raise EmptyInputError(
            "to_board_json called with empty records list — "
            "refusing to write a board that reads as 'every issue closed'"
        )

    # Envelope collected_at = minimum of per-record timestamps
    envelope_ts = min(r.collected_at for r in records)

    return {
        "collected_at": envelope_ts,
        "repos_checked": sorted(repos_checked),
        "skipped_repos": skipped_repos,  # required; empty list is still present
        "total_issues": len(records),
        "heartbeat": heartbeat,  # None pre-GUA-118; dict with started_at/finished_at/exit/duration_s after
        "records": [
            {
                "repo": r.repo,
                "issue_num": r.issue_num,
                "title": r.title,
                "raw_label": r.raw_label,
                "column": r.column,
                "backlog_stage": r.backlog_stage,
                "evidence": r.evidence,
                "collected_at": r.collected_at,
            }
            for r in records
        ],
    }
