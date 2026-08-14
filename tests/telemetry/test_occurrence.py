"""Occurrence-date resolution: line blame, fallback ladder, aliases, caching."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from telemetry.occurrence import (
    SOURCE_BLAME,
    SOURCE_HEAD,
    SOURCE_UNRESOLVED,
    canonical_repo,
    parse_lines,
    resolve_occurred,
)

OLD_DATE = "2026-01-15"
NEW_DATE = "2026-06-20"


def _git(repo: Path, *args: str, date: str | None = None) -> None:
    env = None
    if date is not None:
        stamp = f"{date}T12:00:00"
        env = {
            "GIT_AUTHOR_DATE": stamp,
            "GIT_COMMITTER_DATE": stamp,
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "HOME": str(repo.parent),
        }
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, env=env)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A workspace holding one repo whose two files were committed on different days.

    `old.py` is never touched after the first commit, so blaming it must yield the *old*
    date while HEAD yields the new one — that gap is what proves blame actually ran.
    """
    ws = tmp_path / "workspace"
    ws.mkdir()
    repo = ws / "demo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Tester")

    (repo / "old.py").write_text("alpha\nbravo\ncharlie\ndelta\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feat: old file", date=OLD_DATE)

    (repo / "new.py").write_text("one\ntwo\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feat: new file", date=NEW_DATE)
    return ws


def test_blames_cited_line_to_its_commit(workspace: Path) -> None:
    """A line untouched since the first commit dates to that commit, not to HEAD."""
    occurred, source = resolve_occurred("demo", "old.py", "2", workspace=workspace)
    assert source == SOURCE_BLAME
    assert occurred == OLD_DATE, "blamed HEAD instead of the cited line"


def test_blames_line_range(workspace: Path) -> None:
    """A `start-end` range resolves the same way a single line does."""
    occurred, source = resolve_occurred("demo", "old.py", "2-3", workspace=workspace)
    assert (occurred, source) == (OLD_DATE, SOURCE_BLAME)


def test_distinguishes_files_by_commit_date(workspace: Path) -> None:
    """Two files committed on different days must not collapse to one date."""
    old, _ = resolve_occurred("demo", "old.py", "1", workspace=workspace)
    new, _ = resolve_occurred("demo", "new.py", "1", workspace=workspace)
    assert old == OLD_DATE
    assert new == NEW_DATE


def test_missing_line_range_falls_back_to_whole_file(workspace: Path) -> None:
    """No `lines` value still blames the file rather than dropping to HEAD."""
    occurred, source = resolve_occurred("demo", "old.py", None, workspace=workspace)
    assert (occurred, source) == (OLD_DATE, SOURCE_BLAME)


def test_line_past_eof_falls_back_to_whole_file(workspace: Path) -> None:
    """A stale line number (file shrank since the sweep) must not raise."""
    occurred, source = resolve_occurred("demo", "old.py", "9999", workspace=workspace)
    assert occurred == OLD_DATE
    assert source == SOURCE_BLAME


def test_na_file_falls_back_to_head(workspace: Path) -> None:
    """`n/a` cites no location, so HEAD's date is the best available answer."""
    occurred, source = resolve_occurred("demo", "n/a", None, workspace=workspace)
    assert (occurred, source) == (NEW_DATE, SOURCE_HEAD)


def test_unknown_file_falls_back_to_head(workspace: Path) -> None:
    """A path that no longer exists still dates to the repo, not to nothing."""
    occurred, source = resolve_occurred("demo", "gone.py", "5", workspace=workspace)
    assert (occurred, source) == (NEW_DATE, SOURCE_HEAD)


def test_missing_checkout_is_unresolved(workspace: Path) -> None:
    """A repo that was never cloned here resolves to None without raising."""
    occurred, source = resolve_occurred("nonexistent", "a.py", "1", workspace=workspace)
    assert occurred is None
    assert source == SOURCE_UNRESOLVED


def test_non_git_directory_is_unresolved(workspace: Path) -> None:
    """A plain directory is not a checkout — guard before spending subprocesses."""
    (workspace / "plain").mkdir()
    occurred, source = resolve_occurred("plain", "a.py", "1", workspace=workspace)
    assert (occurred, source) == (None, SOURCE_UNRESOLVED)


def test_alias_maps_worktree_name_to_repo(workspace: Path) -> None:
    """`lib110-phaseA` is a worktree name; it must resolve against `librarian`."""
    (workspace / "demo").rename(workspace / "librarian")
    occurred, source = resolve_occurred("lib110-phaseA", "old.py", "2", workspace=workspace)
    assert (occurred, source) == (OLD_DATE, SOURCE_BLAME)


def test_cache_prevents_duplicate_subprocesses(workspace: Path) -> None:
    """Repeated identical lookups must hit the cache, not re-shell out."""
    cache: dict = {}
    first = resolve_occurred("demo", "old.py", "2", workspace=workspace, cache=cache)
    assert len(cache) == 1
    second = resolve_occurred("demo", "old.py", "2", workspace=workspace, cache=cache)
    assert second == first
    assert len(cache) == 1, "distinct key written for an identical lookup"

    resolve_occurred("demo", "new.py", "1", workspace=workspace, cache=cache)
    assert len(cache) == 2, "distinct lookups must not collide in the cache"


def test_cache_is_optional(workspace: Path) -> None:
    """Omitting the cache must work — the driver may resolve one-off rows."""
    assert resolve_occurred("demo", "old.py", "2", workspace=workspace)[0] == OLD_DATE


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("42", (42, 42)),
        ("42-48", (42, 48)),
        ("152-152", (152, 152)),
        ("  7  ", (7, 7)),
        (None, None),
        ("", None),
        ("n/a", None),
        ("abc", None),
        ("0", None),
        ("48-42", None),
    ],
)
def test_parse_lines(raw: str | None, expected: tuple[int, int] | None) -> None:
    """Malformed ranges cost precision, not the whole resolution."""
    assert parse_lines(raw) == expected


def test_canonical_repo_passes_through_unknown_names() -> None:
    assert canonical_repo("guacamayo") == "guacamayo"
    assert canonical_repo("lib110-phaseA") == "librarian"
