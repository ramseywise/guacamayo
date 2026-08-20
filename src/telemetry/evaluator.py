"""Pure proposal evaluator for the board harness (GUA-119, sub-issue A).

`evaluate` is a pure function over inputs `_run_board` already assembles —
records, branch_facts, inconsistencies, cascade_state — and returns
`list[ProposedAction]`.  No subprocess, no gh, no os.system.  The mutation
path lives in `telemetry/actions.py` (sub-issue B); the structural separation
is what makes "no GitHub mutation on the proposal path" a provable property
rather than an instruction.

One rule per trigger from the issue table:

    triage              — open issue, no workflow label
    dispatch_review     — open PR joined to issue (proposal-only, OQ5)
    close_issue         — merged-branch-open-issue inconsistency without Closes #N
                          (with Closes #N the record is also emitted, tagged
                          auto_eligible=True, so the mutation path shares one
                          derivation)
    fix_label           — label contradicts derived column
                          (auto_eligible when the contradiction is unambiguous;
                          suppressed entirely when column is "undetermined" —
                          negative test: undetermined → no fix_label)
    reconcile_plan_status — plan Status: contradicts label
                          (not yet wired — cascade_state does not carry plan
                          status today; placeholder rule logs and skips cleanly)

Adding a new verb here without a matching entry in `ACTIONS` (board.py) raises
at construction time, not at render time — the vocabulary is the schema.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog

from telemetry.board import BoardRecord, ProposedAction
from telemetry.consistency import _CLOSES_RE, Inconsistency

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Label sets — workflow labels the harness understands
# ---------------------------------------------------------------------------

# Labels that place an issue in a named workflow stage.
_WORKFLOW_LABELS: frozenset[str] = frozenset(
    {
        "backlog",
        "refinement",
        "ready",
        "in-progress",
        "in-review",
        "merged",
        "closed",
        "research",
        "blocked",
    }
)

# The unambiguous (label → expected column) pairs for fix_label.
# "unambiguous" = exactly one correct column; every other mapping may have
# legitimate explanations (e.g. "in-progress" + "merged" = sub-issue pattern).
_UNAMBIGUOUS_LABEL_COLUMN: dict[str, str] = {
    # Label says "in-review" but column (from artifacts) says "merged":
    # the PR landed, the label was not retired.
    "in-review": "merged",
}

# For the reverse direction: column → expected label (used to flag label lag).
# These are also unambiguous: the artifact says the issue is merged, the label
# still says something else — only the label is wrong.
_COLUMN_LABEL_MISMATCH: dict[str, frozenset[str]] = {
    # Column=merged, label still says in-progress or in-review → fix the label
    "merged": frozenset({"in-progress", "in-review"}),
    # Column=closed, label still says in-progress or in-review → fix the label
    "closed": frozenset({"in-progress", "in-review"}),
}

# The merged-branch-open-issue inconsistency kind produced by consistency.py.
_MERGED_BRANCH_KIND = "merged-branch-open-issue"


def _now_ts() -> str:
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# Rule: triage
# ---------------------------------------------------------------------------


def _rule_triage(
    records: list[BoardRecord],
) -> list[ProposedAction]:
    """Open issue with no workflow label → triage proposal.

    "No workflow label" means `raw_label` contains none of `_WORKFLOW_LABELS`.
    These issues are invisible to any label-based filter and accumulate silently.
    """
    proposals: list[ProposedAction] = []
    ts = _now_ts()
    for rec in records:
        if rec.column == "closed":
            continue
        labels = {lbl.strip() for lbl in rec.raw_label.split(",") if lbl.strip()}
        if not labels.intersection(_WORKFLOW_LABELS):
            proposals.append(
                ProposedAction(
                    action="triage",
                    target={"repo": rec.repo, "issue_num": rec.issue_num},
                    reason="open issue carries no workflow label — invisible to any label filter",
                    evidence=f"raw_label={rec.raw_label!r}; column={rec.column!r}",
                    confidence="high",
                    created_at=ts,
                )
            )
            log.debug("evaluator.triage", repo=rec.repo, issue=rec.issue_num)
    return proposals


# ---------------------------------------------------------------------------
# Rule: dispatch_review
# ---------------------------------------------------------------------------


def _rule_dispatch_review(
    records: list[BoardRecord],
) -> list[ProposedAction]:
    """Open issue in `in_review` column → dispatch_review proposal.

    `in_review` means a joined OPEN PR was found for this issue.  The proposal
    is proposal-only this cut (OQ5): auto-running /workflow-review is the
    documented follow-up once the actions log shows proposal accuracy.
    """
    proposals: list[ProposedAction] = []
    ts = _now_ts()
    for rec in records:
        if rec.column == "in_review":
            proposals.append(
                ProposedAction(
                    action="dispatch_review",
                    target={"repo": rec.repo, "issue_num": rec.issue_num},
                    reason="open PR found for issue — /workflow-review should run",
                    evidence=f"column=in_review; {rec.evidence}",
                    confidence="medium",
                    created_at=ts,
                )
            )
            log.debug("evaluator.dispatch_review", repo=rec.repo, issue=rec.issue_num)
    return proposals


# ---------------------------------------------------------------------------
# Rule: close_issue
# ---------------------------------------------------------------------------


def _rule_close_issue(
    inconsistencies: list[Inconsistency],
) -> list[ProposedAction]:
    """merged-branch-open-issue inconsistency → close_issue proposal.

    When the inconsistency was produced by a branch that has a matching
    `Closes #N` in its PR body, the record is tagged `auto_eligible=True` so
    the mutation path (sub-issue B) can act unattended.  Without `Closes #N`
    the proposal is emitted without auto_eligible.

    `is_ancestor=None` inconsistencies (origin/main did not resolve) are
    deliberately excluded — their `issue` field is None and there is nothing to
    close.  This is the negative-test shape: `is_ancestor=None` must NOT produce
    a close_issue proposal.
    """
    proposals: list[ProposedAction] = []
    ts = _now_ts()
    for inc in inconsistencies:
        if inc.kind != _MERGED_BRANCH_KIND:
            continue
        if inc.issue is None:
            # origin/main did not resolve — cannot evaluate, do not propose.
            log.debug(
                "evaluator.close_issue.skipped_none_issue",
                repo=inc.repo,
                kind=inc.kind,
            )
            continue

        # Check if evidence mentions a Closes #N (the branch PR body was joined).
        # The detail field from consistency.py names the branch:
        # "branch `GUA-N-slug` is an ancestor of origin/main"
        # The auto_eligible flag requires a Closes #N reference in the evidence
        # to be set — without it we know the branch merged but cannot confirm the
        # PR body names the issue cleanly enough for an unattended close.
        has_closes = bool(_CLOSES_RE.search(inc.detail) or _CLOSES_RE.search(inc.evidence))
        proposals.append(
            ProposedAction(
                action="close_issue",
                target={"repo": inc.repo, "issue_num": inc.issue},
                reason=(
                    f"branch merged to main but issue #{inc.issue} is still open"
                    + ("; PR body references Closes #N" if has_closes else "")
                ),
                evidence=f"kind={inc.kind!r}; detail={inc.detail!r}; evidence={inc.evidence!r}",
                confidence="high" if has_closes else "medium",
                auto_eligible=has_closes,
                created_at=ts,
            )
        )
        log.debug(
            "evaluator.close_issue",
            repo=inc.repo,
            issue=inc.issue,
            auto_eligible=has_closes,
        )
    return proposals


# ---------------------------------------------------------------------------
# Rule: fix_label
# ---------------------------------------------------------------------------


def _rule_fix_label(
    records: list[BoardRecord],
) -> list[ProposedAction]:
    """Label contradicts derived column → fix_label proposal.

    Suppressed entirely when column is "undetermined" — the derivation could not
    complete, so we cannot know which label is right.  This is the negative-test
    shape: undetermined column must produce NO fix_label proposal.

    auto_eligible=True only for the unambiguous pairs in `_COLUMN_LABEL_MISMATCH`.
    """
    proposals: list[ProposedAction] = []
    ts = _now_ts()
    for rec in records:
        if rec.column == "undetermined":
            # NEGATIVE TEST: undetermined column → no fix_label, ever.
            continue
        labels = {lbl.strip() for lbl in rec.raw_label.split(",") if lbl.strip()}
        bad_labels = labels.intersection(_COLUMN_LABEL_MISMATCH.get(rec.column, frozenset()))
        if bad_labels:
            auto_eligible = rec.column in _COLUMN_LABEL_MISMATCH
            proposals.append(
                ProposedAction(
                    action="fix_label",
                    target={"repo": rec.repo, "issue_num": rec.issue_num},
                    reason=(f"label {bad_labels!r} contradicts derived column {rec.column!r}"),
                    evidence=(
                        f"raw_label={rec.raw_label!r}; column={rec.column!r}; "
                        f"evidence={rec.evidence!r}"
                    ),
                    confidence="high",
                    auto_eligible=auto_eligible,
                    created_at=ts,
                )
            )
            log.debug(
                "evaluator.fix_label",
                repo=rec.repo,
                issue=rec.issue_num,
                bad_labels=bad_labels,
            )
    return proposals


# ---------------------------------------------------------------------------
# Rule: reconcile_plan_status (placeholder — cascade_state not yet wired)
# ---------------------------------------------------------------------------


def _rule_reconcile_plan_status(
    cascade_state: dict[str, Any] | None,
) -> list[ProposedAction]:
    """plan Status: contradicts label → reconcile_plan_status proposal.

    Not yet wired: cascade_state carries compaction counters (grows_due,
    retro_due, …) but not per-issue plan Status values.  The rule is present
    so the schema is correct; it produces zero proposals until the caller
    passes structured plan-status data.  Logged at debug so the absence is
    visible in traces without spamming at info.
    """
    if not cascade_state:
        return []
    # Placeholder: no plan-status keys in cascade_state today.
    log.debug("evaluator.reconcile_plan_status.skipped", reason="plan_status_not_in_cascade_state")
    return []


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def evaluate(
    records: list[BoardRecord],
    branch_facts: list[Any],
    inconsistencies: list[Inconsistency],
    cascade_state: dict[str, Any] | None,
) -> list[ProposedAction]:
    """Pure evaluation over board inputs → list of proposed actions.

    Called by `_run_board` after records/facts/inconsistencies are assembled,
    before the atomic write.  Every input is already-fetched data; this function
    performs no I/O.

    `branch_facts` is accepted but not consumed directly — `inconsistencies`
    already captures the merged-branch findings that are this evaluator's source
    for `close_issue`.  The parameter is present so the signature matches the
    plan's specification and the caller does not need to know which inputs each
    rule uses.

    Rules run independently; one raising must not suppress the others.
    """
    proposals: list[ProposedAction] = []

    for rule_fn, rule_args in [
        (_rule_triage, (records,)),
        (_rule_dispatch_review, (records,)),
        (_rule_close_issue, (inconsistencies,)),
        (_rule_fix_label, (records,)),
        (_rule_reconcile_plan_status, (cascade_state,)),
    ]:
        try:
            proposals.extend(rule_fn(*rule_args))  # type: ignore[arg-type]
        except Exception:
            log.exception("evaluator.rule_failed", rule=rule_fn.__name__)

    log.info("evaluator.done", total=len(proposals))
    return proposals
