"""Tests for telemetry/evaluator.py (GUA-119 step 2).

Standing DoD rules:
  - One positive test per rule (triage, dispatch_review, close_issue, fix_label).
  - Negative set: undetermined column → no fix_label; is_ancestor=None-derived
    inconsistency → no close_issue.
  - Import-set test: the evaluator module must not import any mutation capability
    (subprocess, gh wrappers, os.system).

Mirrors the negative-test convention from test_board.py:224,254 —
every guard is tested in both directions.
"""

from __future__ import annotations

from typing import Any

from telemetry.board import BoardRecord, ProposedAction
from telemetry.consistency import BranchFact, Inconsistency
from telemetry.evaluator import evaluate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _record(
    issue_num: int = 1,
    repo: str = "guacamayo",
    column: str = "backlog",
    raw_label: str = "",
    evidence: str = "no artifacts",
    backlog_stage: str | None = "scope",
) -> BoardRecord:
    return BoardRecord(
        repo=repo,
        issue_num=issue_num,
        title="test issue",
        raw_label=raw_label,
        column=column,
        backlog_stage=backlog_stage if column == "backlog" else None,
        evidence=evidence,
        collected_at="2026-08-16T09:00:00+00:00",
    )


def _inc(
    kind: str = "merged-branch-open-issue",
    repo: str = "guacamayo",
    issue: int | None = 5,
    detail: str = "branch `GUA-5-foo` is an ancestor of origin/main",
    evidence: str = "guacamayo#5 is still OPEN after branch merged",
) -> Inconsistency:
    return Inconsistency(kind=kind, repo=repo, issue=issue, detail=detail, evidence=evidence)


def _branch_fact(
    repo: str = "guacamayo",
    branch: str = "GUA-1-some-feature",
    issue_num: int = 1,
    is_ancestor: bool | None = False,
) -> BranchFact:
    return BranchFact(repo=repo, branch=branch, issue_num=issue_num, is_ancestor=is_ancestor)


def _action_for(proposals: list[ProposedAction], action: str) -> list[ProposedAction]:
    return [p for p in proposals if p.action == action]


# ---------------------------------------------------------------------------
# 0. IMPORT-SET TEST — no mutation capability on the proposal path
# ---------------------------------------------------------------------------


def test_evaluator_imports_no_mutation_capability() -> None:
    """NEGATIVE TEST: evaluator.py must not import subprocess, os.system, or gh wrappers.

    The plan's structural safety property: "no GitHub mutation on the proposal
    path" is provable because the evaluator has no subprocess import. This test
    plants the defect by checking the actual import set — not by mocking.

    Planting the defect: if subprocess were imported by the evaluator, this test
    would catch it. If this test passed while subprocess were imported, the guard
    would be hollow.
    """
    import telemetry.evaluator as evaluator_mod

    forbidden_modules = {"subprocess", "shutil"}  # shutil.which + subprocess = gh invocation

    # Check: does the module reference subprocess at all?
    module_globals = vars(evaluator_mod)
    for forbidden in forbidden_modules:
        assert forbidden not in module_globals, (
            f"evaluator.py must not import {forbidden!r} — "
            "it is the mutation path's boundary; importing it is a structural defect"
        )

    # Scan the module's actual source for its full import set
    import ast
    import inspect

    source = inspect.getsource(evaluator_mod)
    tree = ast.parse(source)
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module.split(".")[0])

    for forbidden in forbidden_modules:
        assert forbidden not in imported_names, (
            f"evaluator.py must not import {forbidden!r} at all — "
            "the proposal path must be provably mutation-free. "
            f"Found imports: {imported_names}"
        )

    # Verify os is not imported (os.system / os.popen are the mutation vectors)
    assert "os" not in imported_names, (
        "evaluator.py must not import os — os.system/os.popen would give the "
        "proposal path a mutation capability. Use datetime.now(UTC) directly."
    )


# ---------------------------------------------------------------------------
# 1. Rule: triage — positive
# ---------------------------------------------------------------------------


def test_triage_open_issue_no_workflow_label() -> None:
    """POSITIVE TEST: open issue with no workflow label → triage proposal."""
    rec = _record(issue_num=10, column="backlog", raw_label="")
    proposals = evaluate([rec], branch_facts=[], inconsistencies=[], cascade_state=None)
    triage = _action_for(proposals, "triage")
    assert len(triage) == 1, f"Expected 1 triage proposal, got {len(triage)}"
    p = triage[0]
    assert p.target == {"repo": "guacamayo", "issue_num": 10}
    assert p.confidence == "high"
    assert p.evidence  # non-empty


def test_triage_open_issue_with_workflow_label_no_proposal() -> None:
    """NEGATIVE TEST: open issue with a workflow label → no triage proposal."""
    rec = _record(issue_num=11, column="backlog", raw_label="ready")
    proposals = evaluate([rec], branch_facts=[], inconsistencies=[], cascade_state=None)
    assert not _action_for(proposals, "triage"), (
        "An issue labelled 'ready' already has a workflow label — triage would be noise"
    )


def test_triage_closed_issue_no_proposal() -> None:
    """NEGATIVE TEST: closed issue → no triage proposal even with no labels."""
    rec = _record(issue_num=12, column="closed", raw_label="")
    proposals = evaluate([rec], branch_facts=[], inconsistencies=[], cascade_state=None)
    assert not _action_for(proposals, "triage"), "Closed issues must not be triaged — they are done"


# ---------------------------------------------------------------------------
# 2. Rule: dispatch_review — positive
# ---------------------------------------------------------------------------


def test_dispatch_review_in_review_column() -> None:
    """POSITIVE TEST: issue in in_review column → dispatch_review proposal."""
    rec = _record(
        issue_num=20,
        column="in_review",
        raw_label="in-progress",
        backlog_stage=None,
        evidence="joined PR #99 is OPEN",
    )
    proposals = evaluate([rec], branch_facts=[], inconsistencies=[], cascade_state=None)
    dispatch = _action_for(proposals, "dispatch_review")
    assert len(dispatch) == 1, f"Expected 1 dispatch_review, got {len(dispatch)}"
    p = dispatch[0]
    assert p.target == {"repo": "guacamayo", "issue_num": 20}
    assert "in_review" in p.evidence or "OPEN" in p.evidence


def test_dispatch_review_not_in_review_no_proposal() -> None:
    """NEGATIVE TEST: issue NOT in in_review → no dispatch_review proposal."""
    rec = _record(issue_num=21, column="in_progress", raw_label="in-progress")
    proposals = evaluate([rec], branch_facts=[], inconsistencies=[], cascade_state=None)
    assert not _action_for(proposals, "dispatch_review"), (
        "dispatch_review should only fire for in_review column"
    )


# ---------------------------------------------------------------------------
# 3. Rule: close_issue — positive + negative
# ---------------------------------------------------------------------------


def test_close_issue_from_merged_branch_inconsistency() -> None:
    """POSITIVE TEST: merged-branch-open-issue inconsistency → close_issue proposal."""
    inc = _inc(kind="merged-branch-open-issue", repo="guacamayo", issue=5)
    proposals = evaluate([], branch_facts=[], inconsistencies=[inc], cascade_state=None)
    close = _action_for(proposals, "close_issue")
    assert len(close) == 1, f"Expected 1 close_issue, got {len(close)}"
    p = close[0]
    assert p.target == {"repo": "guacamayo", "issue_num": 5}
    assert p.confidence in ("high", "medium")


def test_close_issue_auto_eligible_when_closes_in_detail() -> None:
    """close_issue with Closes #N in detail → auto_eligible=True."""
    inc = _inc(
        kind="merged-branch-open-issue",
        issue=7,
        detail="branch `GUA-7-foo` is an ancestor of origin/main (Closes #7)",
    )
    proposals = evaluate([], branch_facts=[], inconsistencies=[inc], cascade_state=None)
    close = _action_for(proposals, "close_issue")
    assert close, "Expected a close_issue proposal"
    assert close[0].auto_eligible is True
    assert close[0].confidence == "high"


def test_close_issue_not_auto_eligible_without_closes() -> None:
    """close_issue without Closes #N → auto_eligible=False, confidence=medium."""
    inc = _inc(
        kind="merged-branch-open-issue",
        issue=8,
        detail="branch `GUA-8-bar` is an ancestor of origin/main",
        evidence="guacamayo#8 is still OPEN after branch merged",
    )
    proposals = evaluate([], branch_facts=[], inconsistencies=[inc], cascade_state=None)
    close = _action_for(proposals, "close_issue")
    assert close, "Expected a close_issue proposal"
    assert close[0].auto_eligible is False
    assert close[0].confidence == "medium"


def test_close_issue_skips_none_issue_inconsistency() -> None:
    """NEGATIVE TEST: is_ancestor=None-derived inconsistency must NOT produce close_issue.

    consistency.py emits a merged-branch-open-issue inconsistency with issue=None when
    origin/main did not resolve (is_ancestor=None). That shape means "we could not
    evaluate ancestry" — proposing to close an unknown issue would be a mutation against
    ambiguous evidence.

    Planting the defect: inconsistency with issue=None (the is_ancestor=None shape).
    A buggy rule that ignores the issue=None check would emit a close_issue proposal.
    The correct rule skips it.
    """
    inc = _inc(
        kind="merged-branch-open-issue",
        issue=None,  # the None shape — origin/main did not resolve
        detail="origin/main did not resolve",
        evidence="could not evaluate merged-branch/open-issue for guacamayo: "
        "origin/main ref unresolvable — branch ancestry check skipped",
    )
    proposals = evaluate([], branch_facts=[], inconsistencies=[inc], cascade_state=None)
    close = _action_for(proposals, "close_issue")
    assert not close, (
        "NEGATIVE TEST FAILED: is_ancestor=None-derived inconsistency (issue=None) "
        "must NOT produce a close_issue proposal — we cannot close an unknown issue. "
        f"Got: {close}"
    )


def test_close_issue_ignores_non_merged_branch_inconsistencies() -> None:
    """NEGATIVE TEST: label-artifact inconsistency → no close_issue proposal."""
    inc = _inc(
        kind="label-artifact",
        issue=9,
        detail="labelled `in-review`",
        evidence="no open PR references this issue",
    )
    proposals = evaluate([], branch_facts=[], inconsistencies=[inc], cascade_state=None)
    assert not _action_for(proposals, "close_issue"), (
        "close_issue must only fire on merged-branch-open-issue, not label-artifact"
    )


# ---------------------------------------------------------------------------
# 4. Rule: fix_label — positive + negative
# ---------------------------------------------------------------------------


def test_fix_label_merged_column_in_review_label() -> None:
    """POSITIVE TEST: column=merged, label=in-review → fix_label proposal."""
    rec = _record(
        issue_num=30,
        column="merged",
        raw_label="in-review",
        backlog_stage=None,
        evidence="joined PR #55 has mergedAt=...",
    )
    proposals = evaluate([rec], branch_facts=[], inconsistencies=[], cascade_state=None)
    fix = _action_for(proposals, "fix_label")
    assert len(fix) == 1, f"Expected 1 fix_label, got {len(fix)}"
    p = fix[0]
    assert p.target == {"repo": "guacamayo", "issue_num": 30}
    assert p.confidence == "high"


def test_fix_label_merged_column_in_progress_label() -> None:
    """POSITIVE TEST: column=merged, label=in-progress → fix_label proposal."""
    rec = _record(
        issue_num=31,
        column="merged",
        raw_label="in-progress",
        backlog_stage=None,
        evidence="joined PR #56 has mergedAt=...",
    )
    proposals = evaluate([rec], branch_facts=[], inconsistencies=[], cascade_state=None)
    fix = _action_for(proposals, "fix_label")
    assert fix, "Expected at least one fix_label proposal"


def test_fix_label_undetermined_column_no_proposal() -> None:
    """NEGATIVE TEST: undetermined column must produce NO fix_label proposal.

    This is the plan's named negative test. An undetermined column means the
    derivation could not complete — we cannot know which label is right, so
    proposing a label change would be a guess.

    Planting the defect: a record with column=undetermined and raw_label=in-review.
    A buggy rule that ignores undetermined would emit a fix_label proposal because
    "in-review" is in _COLUMN_LABEL_MISMATCH for the labels check.
    The correct rule suppresses the proposal entirely.

    Mirrors test_derive_column_undetermined_on_none_ancestor in test_board.py:224.
    """
    rec = _record(
        issue_num=32,
        column="undetermined",
        raw_label="in-review",
        backlog_stage=None,
        evidence="PR fetch failed for this repo; merged/in_review cannot be derived",
    )
    proposals = evaluate([rec], branch_facts=[], inconsistencies=[], cascade_state=None)
    fix = _action_for(proposals, "fix_label")
    assert not fix, (
        "NEGATIVE TEST FAILED: undetermined column must produce NO fix_label proposal. "
        "The derivation could not complete — we cannot know which label is right. "
        f"Got proposals: {fix}"
    )


def test_fix_label_no_proposal_when_labels_agree_with_column() -> None:
    """NEGATIVE TEST: label matches derived column → no fix_label."""
    rec = _record(issue_num=33, column="in_progress", raw_label="in-progress")
    proposals = evaluate([rec], branch_facts=[], inconsistencies=[], cascade_state=None)
    assert not _action_for(proposals, "fix_label"), "No fix_label when label and column agree"


# ---------------------------------------------------------------------------
# 5. Multi-rule interactions
# ---------------------------------------------------------------------------


def test_evaluate_empty_inputs_returns_empty() -> None:
    """Empty records + inconsistencies → no proposals."""
    proposals = evaluate([], branch_facts=[], inconsistencies=[], cascade_state=None)
    assert proposals == []


def test_evaluate_multiple_rules_independent() -> None:
    """Multiple triggering inputs → proposals from each fired rule, independently."""
    # Trigger triage (no workflow label) + close_issue (merged-branch inconsistency)
    rec = _record(issue_num=40, column="in_progress", raw_label="")  # no workflow label
    inc = _inc(kind="merged-branch-open-issue", issue=41)
    proposals = evaluate([rec], branch_facts=[], inconsistencies=[inc], cascade_state=None)
    assert _action_for(proposals, "triage"), "Expected a triage proposal"
    assert _action_for(proposals, "close_issue"), "Expected a close_issue proposal"


def test_evaluate_rule_exception_does_not_suppress_others(monkeypatch: Any) -> None:
    """A rule raising must not suppress the remaining rules.

    Planting the defect: monkeypatch one internal rule to raise, confirm that
    evaluate() still returns proposals from the rules that did not raise.
    """
    import telemetry.evaluator as evaluator_mod

    def _boom(*args: Any, **kwargs: Any) -> list[ProposedAction]:
        raise RuntimeError("injected rule failure")

    monkeypatch.setattr(evaluator_mod, "_rule_triage", _boom)

    # Without fault tolerance, dispatch_review would be suppressed too.
    rec = _record(issue_num=50, column="in_review", raw_label="in-progress", backlog_stage=None)
    proposals = evaluate([rec], branch_facts=[], inconsistencies=[], cascade_state=None)
    # triage rule bombed, but dispatch_review should still have fired
    assert _action_for(proposals, "dispatch_review"), (
        "dispatch_review must not be suppressed by a triage rule failure"
    )
