"""Idempotent mutation functions for the board harness (GUA-119, sub-issue B).

Two functions act on `auto_eligible` ProposedAction records:

    auto_close_merged  — closes an issue when its branch is confirmed merged to
                         origin/main AND the PR body names the issue via Closes #N.
                         Declines on is_ancestor=None, missing Closes, or PR-fetch
                         failure.

    auto_fix_label     — removes a label that contradicts the derived column, but
                         ONLY for the unambiguous pairs (e.g. label=in-progress +
                         column=merged). Declines on undetermined column.

Every call — act or decline — appends one JSONL line to
`.sounding/telemetry/actions.jsonl`:

    {ts, action, target, outcome: "acted"|"declined", reason, evidence}

`dry_run=True` prints the line instead of writing it and performs ZERO subprocess
calls to gh.  The test plan's DoD: is_ancestor=None → declined; no-Closes →
declined; undetermined → declined; idempotency; dry-run-does-not-execute.

The public entry point is `run_eligible_actions(proposals, branch_facts, prs, ...)`,
which dispatches only `auto_eligible` records to the matching handler.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from telemetry.board import ProposedAction
from telemetry.consistency import _CLOSES_RE, BranchFact

log = structlog.get_logger(__name__)

# Default actions log path; callers may override via `actions_log`.
_DEFAULT_ACTIONS_LOG = (
    Path(__file__).resolve().parents[1] / ".sounding" / "telemetry" / "actions.jsonl"
)

# Unambiguous (column → labels to remove) pairs — mirrors evaluator._COLUMN_LABEL_MISMATCH.
# These are the only pairs for which auto_fix_label will act unattended.
_UNAMBIGUOUS_FIX: dict[str, frozenset[str]] = {
    "merged": frozenset({"in-progress", "in-review"}),
    "closed": frozenset({"in-progress", "in-review"}),
}


# ---------------------------------------------------------------------------
# Schema vocabulary (2026-08-19)
# ---------------------------------------------------------------------------

# The three architecture layers a decision can act on. Before this, every record
# was a board triage action, so experiment reversals and metacognition decisions
# lived only as ledger prose and never reached the log at all.
PLANE_WORK = "work"  # the work itself: issues, branches, labels
PLANE_METACOGNITION = "metacognition"  # the system observing itself: retro, insights
PLANE_CONTROL = "control"  # the loop that runs the system: jobs, schedules

PLANES = frozenset({PLANE_WORK, PLANE_METACOGNITION, PLANE_CONTROL})

# `reverted` is the addition that matters: "decided, then undone" was previously
# indistinguishable from "never decided", which is exactly what hid the
# fable-as-default reversal (decided and reverted the same day, 2026-07-30).
OUTCOME_ACTED = "acted"
OUTCOME_ACCEPTED = "accepted"
OUTCOME_DECLINED = "declined"
OUTCOME_REJECTED = "rejected"
OUTCOME_REVERTED = "reverted"

OUTCOMES = frozenset(
    {OUTCOME_ACTED, OUTCOME_ACCEPTED, OUTCOME_DECLINED, OUTCOME_REJECTED, OUTCOME_REVERTED}
)

# Action-kind → plane. Board mutations are work-plane; anything the metacognition
# loop decides (retire a skill, promote a pattern) is metacognition-plane; job and
# schedule decisions are control-plane.
_ACTION_PLANE: dict[str, str] = {
    "triage": PLANE_WORK,
    "close_issue": PLANE_WORK,
    "auto_close_merged": PLANE_WORK,
    "fix_label": PLANE_WORK,
    "auto_fix_label": PLANE_WORK,
    "delete_branch": PLANE_WORK,
    "retire_skill": PLANE_METACOGNITION,
    "consolidate_skill": PLANE_METACOGNITION,
    "promote_pattern": PLANE_METACOGNITION,
    "revert_experiment": PLANE_METACOGNITION,
    "ledger_row": PLANE_METACOGNITION,
    "schedule_job": PLANE_CONTROL,
    "disable_job": PLANE_CONTROL,
    "alert_threshold": PLANE_CONTROL,
}


def plane_for_action(action: str) -> str:
    """Map an action kind to its architecture plane.

    Unknown actions default to `work` — the plane every pre-2026-08-19 record
    belonged to — rather than raising, so an unrecognised action still writes a
    well-formed row instead of losing the decision entirely.
    """
    return _ACTION_PLANE.get(action, PLANE_WORK)


def read_actions(actions_log: Path | None = None) -> list[dict[str, Any]]:
    """Read actions.jsonl, normalising pre-2026-08-19 records to the new schema.

    The five original records carry no `plane`, no `effect_measured`, and no
    `proposal_id`. Absent keys are filled with the same defaults a fresh write
    would produce, so callers never branch on record age. Malformed lines are
    skipped rather than failing the read.
    """
    path = actions_log or _DEFAULT_ACTIONS_LOG
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                log.warning("actions.malformed_line", path=str(path))
                continue
            rec.setdefault("plane", plane_for_action(rec.get("action", "")))
            rec.setdefault("effect_measured", None)
            rec.setdefault("proposal_id", "")
            records.append(rec)
    return records


# ---------------------------------------------------------------------------
# Action log
# ---------------------------------------------------------------------------


def _append_action_log(
    record: dict[str, Any],
    actions_log: Path,
    *,
    dry_run: bool,
) -> None:
    """Append one JSONL line to actions.jsonl, or print it on dry_run."""
    line = json.dumps(record, default=str)
    if dry_run:
        print(f"[dry-run] actions.jsonl << {line}")
        return
    actions_log.parent.mkdir(parents=True, exist_ok=True)
    with actions_log.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _log_record(
    action: str,
    target: dict[str, Any],
    outcome: str,
    reason: str,
    evidence: str,
    proposal_id: str = "",
    plane: str | None = None,
    effect_measured: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one actions.jsonl record.

    `proposal_id` is `ProposedAction.id` (`board._stable_id`, a hash over action +
    target only). It is the join key that lets a later tick re-derive the board and
    ask whether the condition this action addressed actually cleared — without it a
    decision cannot be tied back to the proposal that produced it, since `target`
    alone is not unique across action kinds. Defaults to "" so callers that have no
    proposal in hand still write a well-formed row.

    `plane` names the architecture layer the decision acts on (see PLANE_*), so the
    log covers all three planes rather than only triage. It is derived from the
    action kind when not passed explicitly — never guessed at read time, because a
    reader cannot recover it from `target` alone.

    `effect_measured` is written back once a decision's metric resolves; it stays
    None until then. This is what closes the verification break — before it, the
    log recorded that something was decided but never whether it helped.

    Backward compatibility: the five pre-2026-08-19 records carry none of these
    fields. Readers must treat an absent key as None (see `read_actions`), so the
    schema stays append-only and old rows keep parsing unchanged.
    """
    record: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(),
        "action": action,
        "plane": plane or plane_for_action(action),
        "target": target,
        "outcome": outcome,
        "reason": reason,
        "evidence": evidence,
        "effect_measured": effect_measured,
    }
    if proposal_id:
        record["proposal_id"] = proposal_id
    return record


# ---------------------------------------------------------------------------
# auto_close_merged
# ---------------------------------------------------------------------------


def auto_close_merged(
    proposal: ProposedAction,
    branch_facts: list[BranchFact],
    prs: list[dict[str, Any]],
    *,
    owner: str = "ramseywise",
    dry_run: bool = False,
    actions_log: Path = _DEFAULT_ACTIONS_LOG,
) -> dict[str, Any]:
    """Close an issue whose branch is confirmed merged and whose PR body has Closes #N.

    Acts ONLY when:
      1. A BranchFact for this (repo, issue_num) has is_ancestor=True (not None).
      2. A joined PR body matches _CLOSES_RE for this issue number.

    Declines with reason on:
      - is_ancestor=None (ancestry undetermined — not a safe auto-close)
      - No BranchFact found for this issue
      - No PR found with a Closes #N matching this issue
      - gh subprocess failure (PR fetch or close)

    Idempotency: `gh issue close` on an already-closed issue returns exit 0
    with a "Issue is already closed" message — safe to re-run.

    Returns the actions.jsonl record (acted or declined).
    """
    repo = proposal.target.get("repo", "")
    issue_num = proposal.target.get("issue_num")

    # --- gate 1: BranchFact ancestry ---
    matching_facts = [bf for bf in branch_facts if bf.repo == repo and bf.issue_num == issue_num]

    if not matching_facts:
        rec = _log_record(
            action="auto_close_merged",
            target=proposal.target,
            proposal_id=proposal.id,
            outcome="declined",
            reason="no BranchFact found for this (repo, issue_num)",
            evidence=f"branch_facts checked: {len(branch_facts)}",
        )
        _append_action_log(rec, actions_log, dry_run=dry_run)
        log.debug("auto_close_merged.declined.no_branch_fact", repo=repo, issue=issue_num)
        return rec

    # is_ancestor=None for ANY matching fact → decline (ambiguous)
    if any(bf.is_ancestor is None for bf in matching_facts):
        rec = _log_record(
            action="auto_close_merged",
            target=proposal.target,
            proposal_id=proposal.id,
            outcome="declined",
            reason="is_ancestor=None for this branch — ancestry undetermined, not a safe auto-close",
            evidence=f"matching branch facts: {[bf.branch for bf in matching_facts]}",
        )
        _append_action_log(rec, actions_log, dry_run=dry_run)
        log.debug("auto_close_merged.declined.is_ancestor_none", repo=repo, issue=issue_num)
        return rec

    if not any(bf.is_ancestor is True for bf in matching_facts):
        rec = _log_record(
            action="auto_close_merged",
            target=proposal.target,
            proposal_id=proposal.id,
            outcome="declined",
            reason="is_ancestor=False — branch not yet merged to origin/main",
            evidence=f"matching branch facts: {[bf.branch for bf in matching_facts]}",
        )
        _append_action_log(rec, actions_log, dry_run=dry_run)
        log.debug("auto_close_merged.declined.not_merged", repo=repo, issue=issue_num)
        return rec

    # --- gate 2: PR body must have Closes #N for this issue ---
    closing_pr: dict[str, Any] | None = None
    for pr in prs:
        if str(pr.get("repo", "")) != repo:
            continue
        body = str(pr.get("body") or "")
        for m in _CLOSES_RE.finditer(body):
            if int(m.group(1)) == issue_num:
                closing_pr = pr
                break
        if closing_pr:
            break

    if closing_pr is None:
        rec = _log_record(
            action="auto_close_merged",
            target=proposal.target,
            proposal_id=proposal.id,
            outcome="declined",
            reason=f"no PR body found with 'Closes #{issue_num}' — cannot confirm PR→issue link",
            evidence=f"PRs checked for repo {repo!r}: {len([p for p in prs if p.get('repo') == repo])}",
        )
        _append_action_log(rec, actions_log, dry_run=dry_run)
        log.debug("auto_close_merged.declined.no_closes", repo=repo, issue=issue_num)
        return rec

    pr_num = closing_pr.get("number")
    comment = (
        f"Closed automatically by the board harness: branch merged to origin/main "
        f"and PR #{pr_num} body contains `Closes #{issue_num}`."
    )

    # --- act ---
    evidence_str = f"branch is_ancestor=True; PR #{pr_num} body contains Closes #{issue_num}"

    if dry_run:
        rec = _log_record(
            action="auto_close_merged",
            target=proposal.target,
            proposal_id=proposal.id,
            outcome="acted",
            reason=f"branch merged and PR #{pr_num} references Closes #{issue_num} [dry-run]",
            evidence=evidence_str,
        )
        _append_action_log(rec, actions_log, dry_run=True)
        log.info("auto_close_merged.dry_run", repo=repo, issue=issue_num, pr=pr_num)
        return rec

    try:
        result = subprocess.run(
            [
                "gh",
                "issue",
                "close",
                str(issue_num),
                "--repo",
                f"{owner}/{repo}",
                "--comment",
                comment,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        rec = _log_record(
            action="auto_close_merged",
            target=proposal.target,
            proposal_id=proposal.id,
            outcome="declined",
            reason=f"gh issue close failed with exception: {exc}",
            evidence=evidence_str,
        )
        _append_action_log(rec, actions_log, dry_run=False)
        log.warning("auto_close_merged.gh_exception", repo=repo, issue=issue_num, exc=str(exc))
        return rec

    if result.returncode != 0:
        rec = _log_record(
            action="auto_close_merged",
            target=proposal.target,
            proposal_id=proposal.id,
            outcome="declined",
            reason=f"gh issue close returned exit {result.returncode}: {result.stderr.strip()!r}",
            evidence=evidence_str,
        )
        _append_action_log(rec, actions_log, dry_run=False)
        log.warning(
            "auto_close_merged.gh_failed",
            repo=repo,
            issue=issue_num,
            exit=result.returncode,
            stderr=result.stderr.strip(),
        )
        return rec

    rec = _log_record(
        action="auto_close_merged",
        target=proposal.target,
        proposal_id=proposal.id,
        outcome="acted",
        reason=f"branch merged and PR #{pr_num} references Closes #{issue_num}",
        evidence=evidence_str,
    )
    _append_action_log(rec, actions_log, dry_run=False)
    log.info("auto_close_merged.acted", repo=repo, issue=issue_num, pr=pr_num)
    return rec


# ---------------------------------------------------------------------------
# auto_fix_label
# ---------------------------------------------------------------------------


def auto_fix_label(
    proposal: ProposedAction,
    current_labels: list[str],
    *,
    owner: str = "ramseywise",
    dry_run: bool = False,
    actions_log: Path = _DEFAULT_ACTIONS_LOG,
) -> dict[str, Any]:
    """Remove a label that contradicts the derived column for the unambiguous pairs.

    Acts ONLY for (column, label) pairs in _UNAMBIGUOUS_FIX.
    Declines on undetermined column or when no bad label is found.

    `current_labels` is the live label list for the issue (from the board record's
    raw_label, split by caller).  The function removes only the contradicting labels,
    one `gh issue edit --remove-label` call per bad label.

    Idempotency: if the label has already been removed, gh returns exit 0 — safe
    to re-run.

    Returns the actions.jsonl record.
    """
    repo = proposal.target.get("repo", "")
    issue_num = proposal.target.get("issue_num")
    column = proposal.target.get("column", "")

    # --- gate: undetermined column → always decline ---
    if column == "undetermined":
        rec = _log_record(
            action="auto_fix_label",
            target=proposal.target,
            proposal_id=proposal.id,
            outcome="declined",
            reason="column=undetermined — derivation could not complete; cannot know which label is right",
            evidence=f"column={column!r}; labels={current_labels!r}",
        )
        _append_action_log(rec, actions_log, dry_run=dry_run)
        log.debug("auto_fix_label.declined.undetermined", repo=repo, issue=issue_num)
        return rec

    # --- gate: only act on unambiguous pairs ---
    bad_labels = frozenset(current_labels) & _UNAMBIGUOUS_FIX.get(column, frozenset())
    if not bad_labels:
        rec = _log_record(
            action="auto_fix_label",
            target=proposal.target,
            proposal_id=proposal.id,
            outcome="declined",
            reason=f"no unambiguous label contradiction for column={column!r}",
            evidence=f"column={column!r}; labels={current_labels!r}",
        )
        _append_action_log(rec, actions_log, dry_run=dry_run)
        log.debug("auto_fix_label.declined.no_bad_label", repo=repo, issue=issue_num)
        return rec

    evidence_str = f"column={column!r}; bad_labels={sorted(bad_labels)!r}"

    if dry_run:
        rec = _log_record(
            action="auto_fix_label",
            target=proposal.target,
            proposal_id=proposal.id,
            outcome="acted",
            reason=f"removing labels {sorted(bad_labels)!r} contradicting column={column!r} [dry-run]",
            evidence=evidence_str,
        )
        _append_action_log(rec, actions_log, dry_run=True)
        log.info(
            "auto_fix_label.dry_run", repo=repo, issue=issue_num, bad_labels=sorted(bad_labels)
        )
        return rec

    # Remove each bad label individually (gh supports comma-separated but serial is safer)
    failed_labels: list[str] = []
    for label in sorted(bad_labels):
        try:
            result = subprocess.run(
                [
                    "gh",
                    "issue",
                    "edit",
                    str(issue_num),
                    "--repo",
                    f"{owner}/{repo}",
                    "--remove-label",
                    label,
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            failed_labels.append(f"{label} (exception: {exc})")
            continue
        if result.returncode != 0:
            failed_labels.append(f"{label} (exit {result.returncode}: {result.stderr.strip()!r})")

    if failed_labels:
        rec = _log_record(
            action="auto_fix_label",
            target=proposal.target,
            proposal_id=proposal.id,
            outcome="declined",
            reason=f"gh issue edit failed for labels: {failed_labels}",
            evidence=evidence_str,
        )
        _append_action_log(rec, actions_log, dry_run=False)
        log.warning("auto_fix_label.gh_failed", repo=repo, issue=issue_num, failed=failed_labels)
        return rec

    rec = _log_record(
        action="auto_fix_label",
        target=proposal.target,
        proposal_id=proposal.id,
        outcome="acted",
        reason=f"removed labels {sorted(bad_labels)!r} contradicting column={column!r}",
        evidence=evidence_str,
    )
    _append_action_log(rec, actions_log, dry_run=False)
    log.info("auto_fix_label.acted", repo=repo, issue=issue_num, removed=sorted(bad_labels))
    return rec


# ---------------------------------------------------------------------------
# Effect measurement (write-back)
# ---------------------------------------------------------------------------


def record_effect(
    proposal_id: str,
    metric: str,
    verdict: str,
    *,
    checked_at: str | None = None,
    actions_log: Path = _DEFAULT_ACTIONS_LOG,
    dry_run: bool = False,
) -> dict[str, Any] | None:
    """Attach a measured effect to the decision identified by `proposal_id`.

    Appends a new record carrying `effect_measured` rather than rewriting the
    original line — the log is append-only, and rewriting history would destroy
    the very audit trail the log exists to provide. The new record shares the
    original's action/target/plane so a reader grouping by `proposal_id` sees the
    decision and its effect as one story.

    Returns None when `proposal_id` matches no existing decision — measuring the
    effect of a decision that was never logged is a caller error, not something to
    paper over with an orphan record.
    """
    existing = read_actions(actions_log)
    origin = next((r for r in existing if r.get("proposal_id") == proposal_id), None)
    if origin is None:
        log.warning("actions.effect_no_matching_decision", proposal_id=proposal_id)
        return None

    rec = _log_record(
        action=origin.get("action", ""),
        target=origin.get("target", {}),
        proposal_id=proposal_id,
        plane=origin.get("plane"),
        outcome=origin.get("outcome", ""),
        reason=f"effect measured for decision {proposal_id}",
        evidence=f"metric={metric!r} verdict={verdict!r}",
        effect_measured={
            "metric": metric,
            "verdict": verdict,
            "checked_at": checked_at or datetime.now(UTC).isoformat(),
        },
    )
    _append_action_log(rec, actions_log, dry_run=dry_run)
    log.info("actions.effect_recorded", proposal_id=proposal_id, verdict=verdict)
    return rec


# ---------------------------------------------------------------------------
# Public dispatcher
# ---------------------------------------------------------------------------


def run_eligible_actions(
    proposals: list[ProposedAction],
    branch_facts: list[BranchFact],
    prs: list[dict[str, Any]],
    records: list[Any] | None = None,
    *,
    owner: str = "ramseywise",
    dry_run: bool = False,
    actions_log: Path = _DEFAULT_ACTIONS_LOG,
) -> list[dict[str, Any]]:
    """Dispatch auto_eligible proposals to their mutation handlers.

    Only proposals with `auto_eligible=True` are processed. Proposals for actions
    not covered by a handler are logged as declined (unknown action) rather than
    silently ignored.

    `records` is the list of BoardRecord objects, used to supply current_labels
    to auto_fix_label.  If None or a record is not found, auto_fix_label is called
    with labels derived from the proposal's evidence field.

    Returns a list of action log records (one per eligible proposal processed).
    """
    from telemetry.board import BoardRecord

    # Build a quick (repo, issue_num) → raw_label index from records
    label_index: dict[tuple[str, int], str] = {}
    if records:
        for r in records:
            if isinstance(r, BoardRecord):
                label_index[(r.repo, r.issue_num)] = r.raw_label

    results: list[dict[str, Any]] = []

    for proposal in proposals:
        if not proposal.auto_eligible:
            continue

        repo = proposal.target.get("repo", "")
        issue_num = proposal.target.get("issue_num", 0)

        if proposal.action == "close_issue":
            rec = auto_close_merged(
                proposal,
                branch_facts=branch_facts,
                prs=prs,
                owner=owner,
                dry_run=dry_run,
                actions_log=actions_log,
            )
            results.append(rec)

        elif proposal.action == "fix_label":
            # Get current labels from the record index or fall back to empty
            raw_label = label_index.get((repo, issue_num), "")
            current_labels = [lbl.strip() for lbl in raw_label.split(",") if lbl.strip()]

            # Inject column from the matching board record for the undetermined gate
            column = ""
            for r in records or []:
                if isinstance(r, BoardRecord) and r.repo == repo and r.issue_num == issue_num:
                    column = r.column
                    break

            # Build a target copy that carries column for the gate check
            target_with_col = dict(proposal.target)
            target_with_col.setdefault("column", column)

            proposal_with_col = ProposedAction(
                action=proposal.action,
                target=target_with_col,
                reason=proposal.reason,
                evidence=proposal.evidence,
                confidence=proposal.confidence,
                created_at=proposal.created_at,
                auto_eligible=proposal.auto_eligible,
                id=proposal.id,
            )

            rec = auto_fix_label(
                proposal_with_col,
                current_labels=current_labels,
                owner=owner,
                dry_run=dry_run,
                actions_log=actions_log,
            )
            results.append(rec)

        else:
            # Handler not implemented for this action type — log as declined
            rec = _log_record(
                action=proposal.action,
                target=proposal.target,
                proposal_id=proposal.id,
                outcome="declined",
                reason=f"no auto-mutation handler for action={proposal.action!r}",
                evidence="auto_eligible=True but action not in [close_issue, fix_label]",
            )
            _append_action_log(rec, actions_log, dry_run=dry_run)
            results.append(rec)

    return results
