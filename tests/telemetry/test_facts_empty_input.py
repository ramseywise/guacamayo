"""The daily facts job must not report success when nothing reached it.

Extracted from ramseywise/librarian tests/unit/test_cron_empty_input.py @ aa3166e
(GUA-93) — the `--facts` from_jsonl fail-loud cases only; the `--cron` starvation
checks stay in librarian with `core/cron.py`. Adapted for the ported entry point:
guacamayo's `telemetry --facts` has no derive-notes step, so the note-derivation
assertions from the source file do not apply here.

For eleven days the weekly cron exited 0 while producing a 67-byte report reading
"No session data available for analysis." — indistinguishable, from the outside, from a
run that worked. That is the failure shape this file exists to prevent: a pipeline that
cannot tell "no input" from "fine".

Every test asserts BOTH directions. A guard that always fired would pass the empty cases
and fail the populated ones, so this suite cannot go green on a job that always exits 1.

See ramseywise/librarian#60, ramseywise/librarian#94.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from telemetry import __main__ as cli
from telemetry import factstore, sessions

# The exact sentinel that used to be written to disk at exit 0.
PLACEHOLDER = "No session data available for analysis."


def _fake_session(sid: str, start: str) -> dict[str, Any]:
    """The shape `parse_session` returns, trimmed to the fields the fact row reads."""
    return {
        "session_id": sid,
        "start_time": start,
        "end_time": start,
        "project_path": "/Users/wiseer/workspace/librarian",
        "session_repos": {"librarian": 2},
        "first_prompt": "why is the daily job emitting nothing?",
        "languages": {"python": 1},
        "tool_counts": {"Read": 3},
        "tool_errors": {},
        "skill_invocations": [],
        "duration_minutes": 5,
        "files_modified": 1,
        "user_message_count": 2,
        "user_interruptions": 0,
        "bash_antipatterns": 0,
        "read_edit_ratio": 1.0,
        "input_tokens": 100,
        "output_tokens": 20,
        "cache_write_tokens": 0,
        "cache_read_tokens": 0,
        "primary_model": "claude-opus-4-6",
    }


class FactsRun:
    """Runs `_run_facts` fully inside a temp dir, and remembers where it pointed it.

    Everything that reaches outside — git scan, region injection, ledger verdicts — is
    switched off by flag, so a call exercises exactly the parse -> upsert path. The
    session source is patched at both read sites: the `__main__` guard
    (`sessions.iter_sessions`) and factstore's module-bound name
    (`factstore.iter_sessions`, bound at import).
    """

    def __init__(self, root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.root = root
        self.projects = root / "projects"
        self.projects.mkdir()
        self.store = root / "sessions.db"
        self._monkeypatch = monkeypatch

    def __call__(self, session_list: list[dict[str, Any]]) -> None:
        self._monkeypatch.setattr(sessions, "iter_sessions", lambda _dir: session_list)
        self._monkeypatch.setattr(factstore, "iter_sessions", lambda _dir: session_list)
        self._monkeypatch.setattr(
            "sys.argv",
            [
                "telemetry",
                "--store",
                str(self.store),
                "--projects-dir",
                str(self.projects),
                "--notes-dir",
                str(self.root / "raw_sessions"),
                "--findings",
                str(self.root / "findings.jsonl"),
                "--no-inject",
                "--no-git",
                "--no-verdicts",
            ],
        )
        cli._run_facts()


@pytest.fixture
def facts_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FactsRun:
    return FactsRun(tmp_path, monkeypatch)


def test_facts_exits_non_zero_on_empty_input(facts_run: FactsRun) -> None:
    """No JSONL means no rows and an empty fact table — at exit 0 that is
    byte-for-byte a healthy run. It must be a hard failure instead."""
    with pytest.raises(SystemExit) as exc:
        facts_run([])
    assert exc.value.code != 0, "empty input must not exit 0"


def test_facts_names_where_it_looked(
    facts_run: FactsRun, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failure that does not say which directory was empty is not actionable."""
    with pytest.raises(SystemExit):
        facts_run([])
    err = capsys.readouterr().err
    assert "FATAL" in err
    assert str(facts_run.projects) in err


def test_facts_writes_no_store_on_empty_input(facts_run: FactsRun) -> None:
    """Failing loud must also mean writing nothing — a populated store from an
    empty run would look like capture happened."""
    with pytest.raises(SystemExit):
        facts_run([])
    if facts_run.store.exists():
        con = sqlite3.connect(facts_run.store)
        try:
            count = con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        finally:
            con.close()
        assert count == 0, "empty input upserted fact rows anyway"


def test_facts_succeeds_when_input_exists(facts_run: FactsRun) -> None:
    """The positive direction — proves the guard is not simply always-on."""
    facts_run([_fake_session("aaaa1111", "2026-07-30T09:00:00+00:00")])  # must not raise

    con = sqlite3.connect(facts_run.store)
    try:
        count = con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    finally:
        con.close()
    assert count == 1, "a session was available but no fact row was written"


def test_placeholder_string_is_never_written(facts_run: FactsRun, tmp_path: Path) -> None:
    """The specific 67-byte artifact from #60 must not reappear under any name."""
    facts_run([_fake_session("bbbb2222", "2026-07-30T09:00:00+00:00")])
    for path in tmp_path.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".json", ".txt"}:
            assert PLACEHOLDER not in path.read_text(encoding="utf-8", errors="ignore"), (
                f"placeholder resurfaced in {path}"
            )
