"""Tests for telemetry/signals.py — the declared signal namespace.

DoD focus: the four registry states must stay *distinguishable*. The bug this
module exists to fix was 49 ledger rows reporting one collapsed message for four
different causes, so most of these tests assert on which state a name resolves
to, not merely that scoring "works".

Negative cases are first-class: a missing repo must never read as a confirmed
absence, and a resolver with no data must return None rather than 0.
"""

from __future__ import annotations

import json
from datetime import UTC, date, timedelta
from datetime import datetime as _datetime
from pathlib import Path
from typing import Any

from telemetry import signals
from telemetry.signals import SignalSources


def _session(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "session_id": "s1",
        "tool_errors": "",
        "output_tokens": 100,
        "bash_antipatterns": None,
        "session_intent": "execution",
        "skill_costs": "{}",
        "max_context": None,
        "cost_units": 0.0,
        "models": "{}",
    }
    row.update(overrides)
    return row


# --- registry states --------------------------------------------------------


def test_unknown_name_is_unregistered() -> None:
    assert signals.state_of("no-such-signal-anywhere") == signals.UNREGISTERED
    assert signals.lookup("no-such-signal-anywhere") is None


def test_needs_collection_entries_name_their_remedy() -> None:
    """A needs-collection entry is useless without the collection change to make."""
    for name in (
        "unverified-agent-counts-in-promoted-issue-bodies",
        "flat-sibling-issues-without-parent-link",
    ):
        sig = signals.lookup(name)
        assert sig is not None, name
        assert sig.state == signals.NEEDS_COLLECTION, name
        assert sig.remedy, f"{name} parks without saying what to collect"


def test_unobservable_entries_name_a_reason() -> None:
    sig = signals.lookup("variable-cd-misresolution")
    assert sig is not None
    assert sig.state == signals.UNOBSERVABLE
    assert sig.remedy


def test_states_are_mutually_exclusive() -> None:
    """No name may be scorable and simultaneously parked."""
    for sig in signals.all_signals():
        if sig.state == signals.REGISTERED:
            assert sig.resolver is not None, sig.name
        else:
            assert sig.resolver is None, sig.name


def test_normalize_strips_backticks() -> None:
    """The ledger writes some metrics inside code spans (see verdicts._normalize_signal)."""
    assert signals.normalize("`co-authored-by-rule-in-CLAUDE.md`") == (
        "co-authored-by-rule-in-claude.md"
    )
    assert signals.state_of("co-authored-by-rule-in-CLAUDE.md`") == signals.REGISTERED


# --- Class A resolvers ------------------------------------------------------


def test_file_not_found_errors_sums_across_sessions() -> None:
    rows = [
        _session(tool_errors=json.dumps({"file_not_found": 3, "command_failed": 9})),
        _session(tool_errors=json.dumps({"file_not_found": 2})),
    ]
    assert signals.resolve("file-not-found-errors", SignalSources(sessions=rows)) == 5.0


def test_file_not_found_errors_none_when_no_error_data() -> None:
    """No error column at all is 'no data', not a genuine zero."""
    rows = [_session(tool_errors=""), _session(tool_errors=None)]
    assert signals.resolve("file-not-found-errors", SignalSources(sessions=rows)) is None


def test_file_not_found_errors_zero_is_a_real_zero() -> None:
    """Sessions that recorded errors but none of this kind score 0, not None."""
    rows = [_session(tool_errors=json.dumps({"command_failed": 4}))]
    assert signals.resolve("file-not-found-errors", SignalSources(sessions=rows)) == 0.0


def test_unique_hooks_in_pass_log_counts_distinct_hooks() -> None:
    src = SignalSources(
        hook_pass_log=[
            {"hook": "risky_git_guard"},
            {"hook": "risky_git_guard"},
            {"hook": "protected_path_guard"},
        ]
    )
    assert signals.resolve("unique-hooks-in-pass-log", src) == 2.0


def test_unique_hooks_in_pass_log_none_when_log_absent() -> None:
    assert signals.resolve("unique-hooks-in-pass-log", SignalSources()) is None


def test_co_authored_by_sums_trailer_commits() -> None:
    src = SignalSources(
        git_activity=[
            {"commits_claude_trailer": 3},
            {"commits_claude_trailer": 11},
            {"commits_claude_trailer": None},
        ]
    )
    assert signals.resolve("co-authored-by-in-drafted-commits", src) == 14.0


def test_hook_block_resolver_counts_only_exit_2() -> None:
    """Pass events (exit 0) are not blocks — counting them would invert the claim."""
    src = SignalSources(
        hook_log=[
            {"hook": "risky_git_guard", "exit_code": 2},
            {"hook": "risky_git_guard", "exit_code": 0},
            {"hook": "other_hook", "exit_code": 2},
        ]
    )
    assert signals.resolve("worktree-commit-blocks", src) == 1.0


def test_silent_swallow_matches_title_or_category() -> None:
    src = SignalSources(
        findings=[
            {"title": "Error silently swallowed", "category": "correctness"},
            {"title": "Unrelated", "category": "silent-failure"},
            {"title": "Unrelated", "category": "perf"},
        ]
    )
    assert signals.resolve("silent-swallow-findings", src) == 2.0


# --- Class B: repo-file content --------------------------------------------


def test_repofile_missing_workspace_is_no_data_not_absence() -> None:
    """The critical negative: a missing checkout must not confirm an absence claim."""
    assert signals.resolve("re-derive-clause-in-retro-step-0", SignalSources()) is None


def test_repofile_missing_repo_is_no_data_not_absence(tmp_path: Path) -> None:
    src = SignalSources(workspace=tmp_path)  # empty workspace, no guacamayo/
    assert signals.resolve("re-derive-clause-in-retro-step-0", src) is None


def test_repofile_counts_matching_files(tmp_path: Path) -> None:
    skill = tmp_path / "guacamayo" / ".claude" / "skills" / "meta-retro"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("Step 0: re-derive the board before reading it.")
    src = SignalSources(workspace=tmp_path)
    assert signals.resolve("re-derive-clause-in-retro-step-0", src) == 1.0


def test_repofile_present_but_unmatched_is_zero(tmp_path: Path) -> None:
    """A file that exists without the pattern is a real zero — the claim failed."""
    skill = tmp_path / "guacamayo" / ".claude" / "skills" / "meta-retro"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("Step 0: read the board.")
    src = SignalSources(workspace=tmp_path)
    assert signals.resolve("re-derive-clause-in-retro-step-0", src) == 0.0


# --- signals registered by the 2026-08-19 backlog audit ---------------------


def test_todowrite_heavy_sessions_counts_only_heavy_ones() -> None:
    """Light sessions are ignored; heavy ones missing TodoWrite are counted."""
    src = SignalSources(
        sessions=[
            # heavy (120 calls), no TodoWrite -> counted
            _session(tool_counts=json.dumps({"Bash": 120})),
            # heavy, has TodoWrite -> not counted
            _session(tool_counts=json.dumps({"Bash": 120, "TodoWrite": 3})),
            # light, no TodoWrite -> below the threshold, ignored entirely
            _session(tool_counts=json.dumps({"Bash": 5})),
        ]
    )
    assert signals.resolve("todowrite-in-heavy-sessions", src) == 1.0


def test_todowrite_heavy_sessions_none_without_data() -> None:
    """No session carries tool_counts -> no data, never a fabricated zero."""
    src = SignalSources(sessions=[_session(tool_counts=None)])
    assert signals.resolve("todowrite-in-heavy-sessions", src) is None


def test_todowrite_heavy_sessions_zero_is_a_real_zero() -> None:
    """Heavy sessions that all call TodoWrite score 0, distinct from None."""
    src = SignalSources(sessions=[_session(tool_counts=json.dumps({"Bash": 200, "TodoWrite": 1}))])
    assert signals.resolve("todowrite-in-heavy-sessions", src) == 0.0


def test_duplicate_ledger_signals_counts_collisions(tmp_path: Path) -> None:
    """Two active rows naming one signal is a collision; a lone row is not."""
    ledger = tmp_path / "guacamayo" / ".sounding"
    ledger.mkdir(parents=True)
    (ledger / "tooling-ledger.md").write_text(
        "| Date | Change | Area | Metric | Status |\n"
        "| 2026-01-01 | a | cost | `ratio:shared-signal above 5%` | hypothesis |\n"
        "| 2026-01-02 | b | cost | `ratio:shared-signal below 9%` | hypothesis |\n"
        "| 2026-01-03 | c | cost | `ratio:lonely-signal above 1%` | hypothesis |\n",
        encoding="utf-8",
    )
    assert (
        signals.resolve("duplicate-active-ledger-signals", SignalSources(workspace=tmp_path)) == 1.0
    )


def test_duplicate_ledger_signals_none_when_ledger_missing(tmp_path: Path) -> None:
    """A missing ledger is no data -- never a confirmed "zero duplicates"."""
    assert (
        signals.resolve("duplicate-active-ledger-signals", SignalSources(workspace=tmp_path))
        is None
    )


# --- meta-feedback liveness (GUA-144) --------------------------------------


def _utc_today() -> date:
    """UTC today, matching the resolver's clock (DTZ011: no naive date.today())."""
    return _datetime.now(UTC).date()


def _write_feedback_log(tmp_path: Path, body: str) -> None:
    log_dir = tmp_path / "guacamayo" / ".sounding" / "telemetry"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "feedback-log.md").write_text(body, encoding="utf-8")


def test_feedback_run_age_is_scorable() -> None:
    """The signal is REGISTERED, not merely declared."""
    assert signals.is_scorable("meta-feedback-run-age-days")


def test_feedback_run_age_none_without_workspace() -> None:
    """No workspace is no data -- an unrun gate must not score as a fresh one."""
    assert signals.resolve("meta-feedback-run-age-days", SignalSources()) is None


def test_feedback_run_age_none_when_log_missing(tmp_path: Path) -> None:
    """The gate has never fired; that is absence of data, not a zero-day age."""
    src = SignalSources(workspace=tmp_path)
    assert signals.resolve("meta-feedback-run-age-days", src) is None


def test_feedback_run_age_none_when_log_has_no_headers(tmp_path: Path) -> None:
    """A log with prose but no dated run header carries no run to age."""
    _write_feedback_log(tmp_path, "Notes about feedback but no run header.\n")
    src = SignalSources(workspace=tmp_path)
    assert signals.resolve("meta-feedback-run-age-days", src) is None


def test_feedback_run_age_single_header(tmp_path: Path) -> None:
    """A run ten days ago ages to exactly ten days."""
    ten_days_ago = _utc_today() - timedelta(days=10)
    _write_feedback_log(tmp_path, f"# Feedback Run — {ten_days_ago.isoformat()}\n\nVerified.\n")
    src = SignalSources(workspace=tmp_path)
    assert signals.resolve("meta-feedback-run-age-days", src) == 10.0


def test_feedback_run_age_newest_wins_not_file_order(tmp_path: Path) -> None:
    """The skill appends newest-at-top, but the resolver must not trust order."""
    older = _utc_today() - timedelta(days=30)
    newer = _utc_today() - timedelta(days=3)
    # Deliberately written oldest-first to prove max() beats position.
    _write_feedback_log(
        tmp_path,
        f"# Feedback Run — {older.isoformat()}\n\nOld.\n\n"
        f"# Feedback Run — {newer.isoformat()}\n\nNew.\n",
    )
    src = SignalSources(workspace=tmp_path)
    assert signals.resolve("meta-feedback-run-age-days", src) == 3.0


def test_feedback_run_age_accepts_plain_hyphen(tmp_path: Path) -> None:
    """A hand-written header using "-" instead of the template's em dash parses."""
    today = _utc_today()
    _write_feedback_log(tmp_path, f"# Feedback Run - {today.isoformat()}\n")
    src = SignalSources(workspace=tmp_path)
    assert signals.resolve("meta-feedback-run-age-days", src) == 0.0


# --- GUA-163: git-store backed signals -------------------------------------


def _pr(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "repo": "guacamayo",
        "number": 1,
        "state": "OPEN",
        "created_date": "2026-08-01",
        "closed_date": "",
        "merged": 0,
        "additions": 0,
        "deletions": 0,
        "is_bot": 0,
        "title": "",
        "body": "",
        "head_ref": "",
    }
    row.update(overrides)
    return row


def _branch(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "repo": "guacamayo",
        "name": "main",
        "merged": 0,
        "pr_number": None,
        "head_sha": "abc123",
    }
    row.update(overrides)
    return row


def test_slug_derived_pr_titles_counts_correctly() -> None:
    """Open PRs with a slug-derived title are counted; others are not."""
    src = SignalSources(
        prs=[
            _pr(number=1, state="OPEN", title="GUA-163 Add branches table"),  # slug-derived
            _pr(
                number=2, state="OPEN", title="Add branches table"
            ),  # descriptive title — not counted
            _pr(
                number=3, state="MERGED", title="GUA-100 Merged slug", merged=1
            ),  # merged — not counted
            _pr(number=4, state="OPEN", title="GUA-50 Another slug PR"),  # slug-derived
        ]
    )
    assert signals.resolve("slug-derived-pr-titles", src) == 2.0


def test_merged_prs_without_closing_links() -> None:
    """Merged PRs with no Closes #N or Fixes #N in body are counted."""
    src = SignalSources(
        prs=[
            _pr(
                number=1, state="MERGED", merged=1, body="Closes #100\n\nSome details."
            ),  # has link
            _pr(number=2, state="MERGED", merged=1, body="Fixes #200"),  # has link (Fixes)
            _pr(
                number=3, state="MERGED", merged=1, body="This PR does stuff."
            ),  # no link — counted
            _pr(number=4, state="MERGED", merged=1, body=""),  # no body — counted
            _pr(number=5, state="OPEN", merged=0, body=""),  # open — not counted
        ]
    )
    assert signals.resolve("merged-prs-without-closing-links", src) == 2.0


def test_cross_repo_prefix_mismatch_branches() -> None:
    """A branch using a foreign prefix in the wrong repo is counted as a mismatch."""
    src = SignalSources(
        branches=[
            _branch(repo="guacamayo", name="GUA-21-foo"),  # correct prefix
            _branch(repo="librarian", name="GUA-21-foo"),  # wrong prefix — counted
            _branch(repo="guacamayo", name="main"),  # unformatted — skipped
            _branch(repo="galactus", name="GAL-5-bar"),  # correct prefix
        ]
    )
    assert signals.resolve("cross-repo-prefix-mismatch-branches", src) == 1.0


def test_stale_merged_branches() -> None:
    """Branches with merged=1 are stale; merged=0 branches are not."""
    src_mixed = SignalSources(
        branches=[
            _branch(name="GUA-1-done", merged=1),
            _branch(name="GUA-2-done", merged=1),
            _branch(name="GUA-3-wip", merged=0),
        ]
    )
    assert signals.resolve("stale-merged-branches", src_mixed) == 2.0

    src_clean = SignalSources(
        branches=[
            _branch(name="GUA-4-wip", merged=0),
        ]
    )
    assert signals.resolve("stale-merged-branches", src_clean) == 0.0
