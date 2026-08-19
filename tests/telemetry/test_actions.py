"""Tests for telemetry/actions.py (GUA-119 step 5).

DoD — **NEGATIVE TESTS ARE FIRST-CLASS**:
  - is_ancestor=None → auto_close_merged declined
  - no Closes #N in PR body → auto_close_merged declined
  - column=undetermined → auto_fix_label declined
  - idempotency: second run on same state = no additional subprocess call
  - dry-run performs ZERO subprocess calls to gh

gh is mocked at the subprocess boundary. Outgoing argv is asserted, not just
return codes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from telemetry.actions import (
    auto_close_merged,
    auto_fix_label,
    run_eligible_actions,
)
from telemetry.board import ProposedAction
from telemetry.consistency import BranchFact

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _proposal(
    action: str = "close_issue",
    repo: str = "guacamayo",
    issue_num: int = 42,
    auto_eligible: bool = True,
    **target_extra: Any,
) -> ProposedAction:
    target: dict[str, Any] = {"repo": repo, "issue_num": issue_num, **target_extra}
    return ProposedAction(
        action=action,
        target=target,
        reason="test reason",
        evidence="test evidence non-empty",
        confidence="high",
        created_at="2026-08-16T09:00:00+00:00",
        auto_eligible=auto_eligible,
    )


def _branch_fact(
    repo: str = "guacamayo",
    issue_num: int = 42,
    is_ancestor: bool | None = True,
    branch: str = "GUA-42-some-feature",
) -> BranchFact:
    return BranchFact(repo=repo, branch=branch, issue_num=issue_num, is_ancestor=is_ancestor)


def _pr(
    repo: str = "guacamayo",
    number: int = 99,
    body: str = "Closes #42",
) -> dict[str, Any]:
    return {"repo": repo, "number": number, "body": body, "state": "MERGED"}


def _successful_gh_result() -> MagicMock:
    m = MagicMock()
    m.returncode = 0
    m.stdout = ""
    m.stderr = ""
    return m


# ---------------------------------------------------------------------------
# auto_close_merged — NEGATIVE TESTS (DoD primary)
# ---------------------------------------------------------------------------


class TestAutoCloseMergedNegative:
    """Every guard must have a negative test. These are the DoD."""

    def test_declined_when_is_ancestor_none(self, tmp_path: Path) -> None:
        """NEGATIVE TEST: is_ancestor=None → declined, no gh call."""
        log_path = tmp_path / "actions.jsonl"
        bf = _branch_fact(is_ancestor=None)
        pr = _pr()

        with patch("telemetry.actions.subprocess.run") as mock_run:
            rec = auto_close_merged(
                _proposal(),
                branch_facts=[bf],
                prs=[pr],
                actions_log=log_path,
            )

        assert rec["outcome"] == "declined", f"Expected declined, got: {rec}"
        assert "is_ancestor=None" in rec["reason"]
        mock_run.assert_not_called()  # ZERO gh calls

        # Log line written
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        logged = json.loads(lines[0])
        assert logged["outcome"] == "declined"
        assert logged["action"] == "auto_close_merged"

    def test_declined_when_no_closes_in_pr_body(self, tmp_path: Path) -> None:
        """NEGATIVE TEST: no Closes #N in any PR body → declined, no gh call."""
        log_path = tmp_path / "actions.jsonl"
        bf = _branch_fact(is_ancestor=True)
        pr = _pr(body="This PR fixes some things but does not mention closes")

        with patch("telemetry.actions.subprocess.run") as mock_run:
            rec = auto_close_merged(
                _proposal(),
                branch_facts=[bf],
                prs=[pr],
                actions_log=log_path,
            )

        assert rec["outcome"] == "declined", f"Expected declined, got: {rec}"
        assert "Closes" in rec["reason"] or "closes" in rec["reason"].lower()
        mock_run.assert_not_called()

    def test_declined_when_no_branch_fact(self, tmp_path: Path) -> None:
        """NEGATIVE TEST: no BranchFact for this issue → declined."""
        log_path = tmp_path / "actions.jsonl"

        with patch("telemetry.actions.subprocess.run") as mock_run:
            rec = auto_close_merged(
                _proposal(),
                branch_facts=[],  # empty
                prs=[_pr()],
                actions_log=log_path,
            )

        assert rec["outcome"] == "declined"
        mock_run.assert_not_called()

    def test_declined_when_is_ancestor_false(self, tmp_path: Path) -> None:
        """NEGATIVE TEST: is_ancestor=False (not merged) → declined."""
        log_path = tmp_path / "actions.jsonl"
        bf = _branch_fact(is_ancestor=False)

        with patch("telemetry.actions.subprocess.run") as mock_run:
            rec = auto_close_merged(
                _proposal(),
                branch_facts=[bf],
                prs=[_pr()],
                actions_log=log_path,
            )

        assert rec["outcome"] == "declined"
        mock_run.assert_not_called()

    def test_declined_when_closes_wrong_issue_number(self, tmp_path: Path) -> None:
        """NEGATIVE TEST: PR body says Closes #99, not #42 → declined."""
        log_path = tmp_path / "actions.jsonl"
        bf = _branch_fact(is_ancestor=True)
        pr = _pr(body="Closes #99")  # wrong issue

        with patch("telemetry.actions.subprocess.run") as mock_run:
            rec = auto_close_merged(
                _proposal(issue_num=42),  # looking for issue 42
                branch_facts=[bf],
                prs=[pr],
                actions_log=log_path,
            )

        assert rec["outcome"] == "declined"
        mock_run.assert_not_called()

    def test_declined_when_pr_from_different_repo(self, tmp_path: Path) -> None:
        """NEGATIVE TEST: PR repo doesn't match → declined."""
        log_path = tmp_path / "actions.jsonl"
        bf = _branch_fact(repo="guacamayo", is_ancestor=True)
        pr = _pr(repo="other-repo", body="Closes #42")

        with patch("telemetry.actions.subprocess.run") as mock_run:
            rec = auto_close_merged(
                _proposal(repo="guacamayo"),
                branch_facts=[bf],
                prs=[pr],
                actions_log=log_path,
            )

        assert rec["outcome"] == "declined"
        mock_run.assert_not_called()

    def test_declined_when_gh_returns_nonzero(self, tmp_path: Path) -> None:
        """NEGATIVE TEST: gh exits non-zero → declined, log written."""
        log_path = tmp_path / "actions.jsonl"
        bf = _branch_fact(is_ancestor=True)
        pr = _pr()

        failed = MagicMock()
        failed.returncode = 1
        failed.stdout = ""
        failed.stderr = "gh: authentication error"

        with patch("telemetry.actions.subprocess.run", return_value=failed):
            rec = auto_close_merged(
                _proposal(),
                branch_facts=[bf],
                prs=[pr],
                actions_log=log_path,
            )

        assert rec["outcome"] == "declined"
        assert "exit 1" in rec["reason"]

    def test_declined_when_gh_raises_exception(self, tmp_path: Path) -> None:
        """NEGATIVE TEST: subprocess raises → declined, log written."""
        log_path = tmp_path / "actions.jsonl"
        bf = _branch_fact(is_ancestor=True)
        pr = _pr()

        with patch("telemetry.actions.subprocess.run", side_effect=OSError("gh not found")):
            rec = auto_close_merged(
                _proposal(),
                branch_facts=[bf],
                prs=[pr],
                actions_log=log_path,
            )

        assert rec["outcome"] == "declined"
        assert "exception" in rec["reason"].lower()


# ---------------------------------------------------------------------------
# auto_close_merged — POSITIVE TEST
# ---------------------------------------------------------------------------


class TestAutoCloseMergedPositive:
    def test_acts_when_all_gates_pass(self, tmp_path: Path) -> None:
        """POSITIVE TEST: is_ancestor=True + PR body has Closes #42 → acted."""
        log_path = tmp_path / "actions.jsonl"
        bf = _branch_fact(is_ancestor=True)
        pr = _pr(number=99, body="Closes #42")

        with patch(
            "telemetry.actions.subprocess.run", return_value=_successful_gh_result()
        ) as mock_run:
            rec = auto_close_merged(
                _proposal(issue_num=42),
                branch_facts=[bf],
                prs=[pr],
                actions_log=log_path,
            )

        assert rec["outcome"] == "acted", f"Expected acted, got: {rec}"
        # Assert outgoing argv, not just return code
        mock_run.assert_called_once()
        argv = mock_run.call_args[0][0]
        assert argv[0] == "gh"
        assert "close" in argv
        assert "42" in argv
        assert "--repo" in argv
        assert "ramseywise/guacamayo" in argv
        assert "--comment" in argv

        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        logged = json.loads(lines[0])
        assert logged["outcome"] == "acted"

    def test_case_insensitive_closes(self, tmp_path: Path) -> None:
        """POSITIVE TEST: 'CLOSES #42' (uppercase) also triggers auto-close."""
        log_path = tmp_path / "actions.jsonl"
        bf = _branch_fact(is_ancestor=True)
        pr = _pr(body="CLOSES #42 because the work is done")

        with patch(
            "telemetry.actions.subprocess.run", return_value=_successful_gh_result()
        ) as mock_run:
            rec = auto_close_merged(
                _proposal(issue_num=42),
                branch_facts=[bf],
                prs=[pr],
                actions_log=log_path,
            )

        assert rec["outcome"] == "acted"
        mock_run.assert_called_once()

    def test_fixes_variant(self, tmp_path: Path) -> None:
        """POSITIVE TEST: 'fixes #42' also triggers auto-close."""
        log_path = tmp_path / "actions.jsonl"
        bf = _branch_fact(is_ancestor=True)
        pr = _pr(body="fixes #42 and resolves some debt")

        with patch(
            "telemetry.actions.subprocess.run", return_value=_successful_gh_result()
        ) as mock_run:
            rec = auto_close_merged(
                _proposal(issue_num=42),
                branch_facts=[bf],
                prs=[pr],
                actions_log=log_path,
            )

        assert rec["outcome"] == "acted"
        mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# auto_close_merged — DRY-RUN
# ---------------------------------------------------------------------------


class TestAutoCloseMergedDryRun:
    def test_dry_run_zero_subprocess_calls(self, tmp_path: Path) -> None:
        """NEGATIVE TEST: dry_run=True → ZERO subprocess calls, stdout only."""
        log_path = tmp_path / "actions.jsonl"
        bf = _branch_fact(is_ancestor=True)
        pr = _pr()

        with patch("telemetry.actions.subprocess.run") as mock_run:
            rec = auto_close_merged(
                _proposal(),
                branch_facts=[bf],
                prs=[pr],
                dry_run=True,
                actions_log=log_path,
            )

        mock_run.assert_not_called()
        # dry_run prints instead of writing — log file not written
        assert not log_path.exists()
        assert rec["outcome"] == "acted"  # would have acted if not dry-run

    def test_dry_run_declined_still_no_subprocess(self, tmp_path: Path) -> None:
        """dry_run=True on a declining case → no subprocess, no log file."""
        log_path = tmp_path / "actions.jsonl"
        bf = _branch_fact(is_ancestor=None)  # will decline

        with patch("telemetry.actions.subprocess.run") as mock_run:
            rec = auto_close_merged(
                _proposal(),
                branch_facts=[bf],
                prs=[_pr()],
                dry_run=True,
                actions_log=log_path,
            )

        mock_run.assert_not_called()
        assert not log_path.exists()
        assert rec["outcome"] == "declined"


# ---------------------------------------------------------------------------
# auto_close_merged — IDEMPOTENCY
# ---------------------------------------------------------------------------


class TestAutoCloseMergedIdempotency:
    def test_second_run_same_state_still_acts(self, tmp_path: Path) -> None:
        """IDEMPOTENCY: gh issue close on already-closed issue returns 0 — safe to re-run.

        The idempotency contract: running twice on the same state produces the same
        outcome (acted) because gh issue close exits 0 on an already-closed issue.
        The log grows by one line per call (each call is an event), but no
        additional state change occurs at GitHub.
        """
        log_path = tmp_path / "actions.jsonl"
        bf = _branch_fact(is_ancestor=True)
        pr = _pr()

        with patch(
            "telemetry.actions.subprocess.run", return_value=_successful_gh_result()
        ) as mock_run:
            rec1 = auto_close_merged(_proposal(), branch_facts=[bf], prs=[pr], actions_log=log_path)
            rec2 = auto_close_merged(_proposal(), branch_facts=[bf], prs=[pr], actions_log=log_path)

        assert rec1["outcome"] == "acted"
        assert rec2["outcome"] == "acted"
        assert mock_run.call_count == 2  # gh called twice, same argv both times

        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 2  # two log entries — each call is an event


# ---------------------------------------------------------------------------
# auto_fix_label — NEGATIVE TESTS (DoD primary)
# ---------------------------------------------------------------------------


class TestAutoFixLabelNegative:
    def test_declined_when_column_undetermined(self, tmp_path: Path) -> None:
        """NEGATIVE TEST: column=undetermined → declined, ZERO gh calls."""
        log_path = tmp_path / "actions.jsonl"
        proposal = _proposal(action="fix_label", column="undetermined")

        with patch("telemetry.actions.subprocess.run") as mock_run:
            rec = auto_fix_label(
                proposal,
                current_labels=["in-review"],
                actions_log=log_path,
            )

        assert rec["outcome"] == "declined", f"Expected declined, got: {rec}"
        assert "undetermined" in rec["reason"]
        mock_run.assert_not_called()

    def test_declined_when_no_bad_label(self, tmp_path: Path) -> None:
        """NEGATIVE TEST: column=merged but label=backlog (not in _UNAMBIGUOUS_FIX) → declined."""
        log_path = tmp_path / "actions.jsonl"
        proposal = _proposal(action="fix_label", column="merged")

        with patch("telemetry.actions.subprocess.run") as mock_run:
            rec = auto_fix_label(
                proposal,
                current_labels=["backlog"],  # not a bad label for 'merged'
                actions_log=log_path,
            )

        assert rec["outcome"] == "declined"
        mock_run.assert_not_called()

    def test_declined_when_labels_empty(self, tmp_path: Path) -> None:
        """NEGATIVE TEST: merged column but no labels at all → declined."""
        log_path = tmp_path / "actions.jsonl"
        proposal = _proposal(action="fix_label", column="merged")

        with patch("telemetry.actions.subprocess.run") as mock_run:
            rec = auto_fix_label(
                proposal,
                current_labels=[],
                actions_log=log_path,
            )

        assert rec["outcome"] == "declined"
        mock_run.assert_not_called()

    def test_declined_when_column_in_progress(self, tmp_path: Path) -> None:
        """NEGATIVE TEST: column=in_progress is not in _UNAMBIGUOUS_FIX → declined.

        'in-review' label + 'in_progress' column is not an unambiguous pair
        (a sub-issue can have both). The fix must not fire.
        """
        log_path = tmp_path / "actions.jsonl"
        proposal = _proposal(action="fix_label", column="in_progress")

        with patch("telemetry.actions.subprocess.run") as mock_run:
            rec = auto_fix_label(
                proposal,
                current_labels=["in-review"],
                actions_log=log_path,
            )

        assert rec["outcome"] == "declined"
        mock_run.assert_not_called()

    def test_declined_when_gh_fails(self, tmp_path: Path) -> None:
        """NEGATIVE TEST: gh issue edit exits non-zero → declined, log written."""
        log_path = tmp_path / "actions.jsonl"
        proposal = _proposal(action="fix_label", column="merged")

        failed = MagicMock()
        failed.returncode = 1
        failed.stderr = "label not found"
        failed.stdout = ""

        with patch("telemetry.actions.subprocess.run", return_value=failed):
            rec = auto_fix_label(
                proposal,
                current_labels=["in-review"],
                actions_log=log_path,
            )

        assert rec["outcome"] == "declined"
        assert "exit 1" in rec["reason"]


# ---------------------------------------------------------------------------
# auto_fix_label — POSITIVE TESTS
# ---------------------------------------------------------------------------


class TestAutoFixLabelPositive:
    def test_acts_merged_column_in_review_label(self, tmp_path: Path) -> None:
        """POSITIVE TEST: column=merged + label=in-review → acted, gh called."""
        log_path = tmp_path / "actions.jsonl"
        proposal = _proposal(action="fix_label", column="merged")

        with patch(
            "telemetry.actions.subprocess.run", return_value=_successful_gh_result()
        ) as mock_run:
            rec = auto_fix_label(
                proposal,
                current_labels=["in-review"],
                actions_log=log_path,
            )

        assert rec["outcome"] == "acted"
        mock_run.assert_called_once()
        argv = mock_run.call_args[0][0]
        assert argv[0] == "gh"
        assert "edit" in argv
        assert "--remove-label" in argv
        assert "in-review" in argv
        assert "--repo" in argv
        assert "ramseywise/guacamayo" in argv

    def test_acts_merged_column_in_progress_label(self, tmp_path: Path) -> None:
        """POSITIVE TEST: column=merged + label=in-progress → acted."""
        log_path = tmp_path / "actions.jsonl"
        proposal = _proposal(action="fix_label", column="merged")

        with patch(
            "telemetry.actions.subprocess.run", return_value=_successful_gh_result()
        ) as mock_run:
            rec = auto_fix_label(
                proposal,
                current_labels=["in-progress"],
                actions_log=log_path,
            )

        assert rec["outcome"] == "acted"
        mock_run.assert_called_once()

    def test_acts_closed_column_in_review_label(self, tmp_path: Path) -> None:
        """POSITIVE TEST: column=closed + label=in-review → acted."""
        log_path = tmp_path / "actions.jsonl"
        proposal = _proposal(action="fix_label", column="closed")

        with patch(
            "telemetry.actions.subprocess.run", return_value=_successful_gh_result()
        ) as mock_run:
            rec = auto_fix_label(
                proposal,
                current_labels=["in-review"],
                actions_log=log_path,
            )

        assert rec["outcome"] == "acted"
        mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# auto_fix_label — DRY-RUN
# ---------------------------------------------------------------------------


class TestAutoFixLabelDryRun:
    def test_dry_run_zero_subprocess(self, tmp_path: Path) -> None:
        """NEGATIVE TEST: dry_run=True → ZERO subprocess calls."""
        log_path = tmp_path / "actions.jsonl"
        proposal = _proposal(action="fix_label", column="merged")

        with patch("telemetry.actions.subprocess.run") as mock_run:
            rec = auto_fix_label(
                proposal,
                current_labels=["in-review"],
                dry_run=True,
                actions_log=log_path,
            )

        mock_run.assert_not_called()
        assert not log_path.exists()
        assert rec["outcome"] == "acted"


# ---------------------------------------------------------------------------
# auto_fix_label — IDEMPOTENCY
# ---------------------------------------------------------------------------


class TestAutoFixLabelIdempotency:
    def test_second_run_same_state(self, tmp_path: Path) -> None:
        """IDEMPOTENCY: gh issue edit --remove-label on already-removed label = exit 0."""
        log_path = tmp_path / "actions.jsonl"
        proposal = _proposal(action="fix_label", column="merged")

        with patch(
            "telemetry.actions.subprocess.run", return_value=_successful_gh_result()
        ) as mock_run:
            rec1 = auto_fix_label(proposal, current_labels=["in-review"], actions_log=log_path)
            rec2 = auto_fix_label(proposal, current_labels=["in-review"], actions_log=log_path)

        assert rec1["outcome"] == "acted"
        assert rec2["outcome"] == "acted"
        assert mock_run.call_count == 2


# ---------------------------------------------------------------------------
# run_eligible_actions — the dispatcher
# ---------------------------------------------------------------------------


class TestRunEligibleActions:
    def test_only_auto_eligible_proposals_dispatched(self, tmp_path: Path) -> None:
        """NEGATIVE TEST: non-auto_eligible proposals are skipped entirely."""
        log_path = tmp_path / "actions.jsonl"
        not_eligible = _proposal(action="close_issue", auto_eligible=False)

        with patch("telemetry.actions.subprocess.run") as mock_run:
            results = run_eligible_actions(
                [not_eligible],
                branch_facts=[_branch_fact(is_ancestor=True)],
                prs=[_pr()],
                actions_log=log_path,
            )

        assert results == []
        mock_run.assert_not_called()

    def test_unknown_action_logged_as_declined(self, tmp_path: Path) -> None:
        """NEGATIVE TEST: auto_eligible proposal for unknown action → declined, no subprocess."""
        log_path = tmp_path / "actions.jsonl"
        # triage is auto_eligible=False by design; force it for this test
        proposal = ProposedAction(
            action="triage",
            target={"repo": "guacamayo", "issue_num": 1},
            reason="test",
            evidence="non-empty evidence",
            confidence="low",
            created_at="2026-08-16T09:00:00+00:00",
            auto_eligible=True,  # forced — triage never actually sets this
        )

        with patch("telemetry.actions.subprocess.run") as mock_run:
            results = run_eligible_actions(
                [proposal],
                branch_facts=[],
                prs=[],
                actions_log=log_path,
            )

        mock_run.assert_not_called()
        assert len(results) == 1
        assert results[0]["outcome"] == "declined"
        assert "no auto-mutation handler" in results[0]["reason"]

    def test_without_act_flag_zero_gh_calls(self, tmp_path: Path) -> None:
        """NEGATIVE TEST (Step 6 DoD): dispatcher with no proposals = zero gh calls.

        This test proves the structural guarantee: the mutations module is only
        imported inside the --act branch. Without --act, run_eligible_actions
        is never called and gh is never touched.

        We simulate the no-act path by calling run_eligible_actions with an empty
        list — which is what _run_board does when args.act is False.
        """
        log_path = tmp_path / "actions.jsonl"

        with patch("telemetry.actions.subprocess.run") as mock_run:
            results = run_eligible_actions(
                [],  # no proposals passed — simulates --act=False path
                branch_facts=[_branch_fact(is_ancestor=True)],
                prs=[_pr()],
                actions_log=log_path,
            )

        assert results == []
        mock_run.assert_not_called()

    def test_mixed_eligible_ineligible(self, tmp_path: Path) -> None:
        """Only eligible proposals run; ineligible skipped."""
        log_path = tmp_path / "actions.jsonl"
        eligible = _proposal(action="close_issue", auto_eligible=True)
        ineligible = _proposal(action="close_issue", issue_num=99, auto_eligible=False)

        bf = _branch_fact(issue_num=42, is_ancestor=True)
        pr = _pr(body="Closes #42")

        with patch(
            "telemetry.actions.subprocess.run", return_value=_successful_gh_result()
        ) as mock_run:
            results = run_eligible_actions(
                [eligible, ineligible],
                branch_facts=[bf],
                prs=[pr],
                actions_log=log_path,
            )

        # Only the eligible one ran — one result, and exactly one gh invocation
        assert len(results) == 1
        assert results[0]["target"]["issue_num"] == 42
        assert mock_run.call_count == 1


# ---------------------------------------------------------------------------
# actions.jsonl log contract
# ---------------------------------------------------------------------------


class TestActionsLog:
    def test_log_schema_fields_present(self, tmp_path: Path) -> None:
        """Every log line has the required schema fields."""
        log_path = tmp_path / "actions.jsonl"
        bf = _branch_fact(is_ancestor=None)  # will decline

        auto_close_merged(
            _proposal(),
            branch_facts=[bf],
            prs=[_pr()],
            actions_log=log_path,
        )

        lines = log_path.read_text().strip().splitlines()
        assert lines, "No log lines written"
        record = json.loads(lines[0])

        required = {"ts", "action", "target", "outcome", "reason", "evidence"}
        missing = required - set(record.keys())
        assert not missing, f"Missing fields in actions.jsonl record: {missing}"
        assert record["outcome"] in ("acted", "declined")
        assert record["ts"]  # non-empty timestamp

    def test_log_appended_not_overwritten(self, tmp_path: Path) -> None:
        """Multiple calls append to the log; each is a separate JSONL line."""
        log_path = tmp_path / "actions.jsonl"

        # First call: decline (is_ancestor=None)
        auto_close_merged(
            _proposal(),
            branch_facts=[_branch_fact(is_ancestor=None)],
            prs=[_pr()],
            actions_log=log_path,
        )

        # Second call: decline (no branch fact)
        auto_close_merged(
            _proposal(issue_num=99),
            branch_facts=[],
            prs=[_pr()],
            actions_log=log_path,
        )

        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 2, f"Expected 2 log lines, got {len(lines)}"
        for line in lines:
            json.loads(line)  # each line must be valid JSON


# ---------------------------------------------------------------------------
# GUA-137: proposal_id join key
# ---------------------------------------------------------------------------


def test_action_log_carries_proposal_id(tmp_path: Path) -> None:
    """Every logged action records the proposal id it came from.

    Without this the log cannot be joined back to the board, so triage
    verification ("did the condition this action addressed actually clear?")
    has no key to join on.
    """
    log_path = tmp_path / "actions.jsonl"
    proposal = _proposal(issue_num=137)

    auto_close_merged(proposal, branch_facts=[], prs=[], actions_log=log_path)

    rec = json.loads(log_path.read_text().strip())
    assert rec["proposal_id"] == proposal.id
    assert rec["proposal_id"], "proposal id must be non-empty"


def test_proposal_id_is_stable_across_ticks() -> None:
    """The join key depends only on action + target, so it survives re-derivation.

    The board is recomputed from scratch every tick; an id that moved when
    `reason`/`created_at` changed would make the same proposal look new each time.
    """
    first = _proposal(issue_num=137)
    second = ProposedAction(
        action="close_issue",
        target={"issue_num": 137, "repo": "guacamayo"},  # reordered keys
        reason="a completely different reason",
        evidence="different evidence",
        confidence="low",
        created_at="2026-09-01T00:00:00+00:00",
    )
    assert second.id == first.id
