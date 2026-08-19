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
        "merged-prs-without-closing-links",
        "cross-repo-prefix-mismatch-branches",
        "stale-merged-branches",
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
