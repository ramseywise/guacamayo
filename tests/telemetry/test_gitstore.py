"""Repo-activity collection: churn filtering, bot detection, round-trip."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from telemetry.gitstore import (
    _NON_SOURCE,
    collect_commits,
    read_branches,
    read_git_activity,
    read_prs,
    upsert_branches,
    upsert_commits,
    upsert_prs,
)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A tiny git repo with one source file and one vendored artifact."""
    r = tmp_path / "demo"
    r.mkdir()
    run = lambda *a: subprocess.run(a, cwd=r, check=True, capture_output=True)
    run("git", "init", "-q")
    run("git", "config", "user.email", "t@example.com")
    run("git", "config", "user.name", "Tester")
    (r / "app.py").write_text("print(1)\nprint(2)\n")
    (r / "uv.lock").write_text("\n".join(f"line{i}" for i in range(500)))
    run("git", "add", "-A")
    run("git", "commit", "-q", "-m", "feat: add app")
    return r


def test_churn_excludes_lockfiles(repo: Path) -> None:
    """A 500-line lockfile must not swamp a 2-line source change."""
    rows = collect_commits(repo, since="2000-01-01")
    assert len(rows) == 1
    assert rows[0]["insertions"] == 2, "lockfile lines leaked into churn"
    assert rows[0]["files_changed"] == 1


def test_commit_counted_even_when_churn_filtered(repo: Path) -> None:
    """Filtering churn must not drop the commit itself from the count."""
    rows = collect_commits(repo, since="2000-01-01")
    assert rows[0]["commits"] == 1


@pytest.mark.parametrize(
    "path",
    [
        "readings/book.pdf",
        "notebooks/explore.ipynb",
        "uv.lock",
        "app/package-lock.json",
        "data/wiki/.obsidian/plugins/x/main.js",
        "generative-ai/coursera-references/Course/file.py",
        "frontend/node_modules/lib/index.js",
    ],
)
def test_non_source_paths_filtered(path: str) -> None:
    assert _NON_SOURCE.search(path), f"{path} should be excluded from churn"


@pytest.mark.parametrize("path", ["src/app.py", "tools/cartographer/gitstore.py", "README.md"])
def test_source_paths_kept(path: str) -> None:
    assert not _NON_SOURCE.search(path), f"{path} should count as authored source"


def test_bot_commits_counted_separately(repo: Path) -> None:
    subprocess.run(
        [
            "git",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "Bump dep",
            "--author",
            "dependabot[bot] <b@x>",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    rows = collect_commits(repo, since="2000-01-01")
    total = sum(r["commits"] for r in rows)
    bots = sum(r["commits_bot"] for r in rows)
    assert total == 2
    assert bots == 1, "dependabot author not classified as bot"


def test_store_round_trip(tmp_path: Path) -> None:
    store = tmp_path / "facts.db"
    upsert_commits(
        [
            {
                "repo": "demo",
                "date": "2026-07-20",
                "commits": 3,
                "commits_bot": 1,
                "commits_claude_trailer": 0,
                "insertions": 40,
                "deletions": 5,
                "files_changed": 4,
            }
        ],
        store,
    )
    upsert_prs(
        [
            {
                "repo": "demo",
                "number": 7,
                "state": "MERGED",
                "created_date": "2026-07-18",
                "closed_date": "2026-07-19",
                "merged": 1,
                "additions": 10,
                "deletions": 2,
                "is_bot": 0,
            }
        ],
        store,
    )
    assert read_git_activity(store)[0]["commits"] == 3
    assert read_prs(store)[0]["merged"] == 1


def test_upsert_is_idempotent(tmp_path: Path) -> None:
    """Re-running collection replaces rows rather than double-counting."""
    store = tmp_path / "facts.db"
    row = {
        "repo": "demo",
        "date": "2026-07-20",
        "commits": 3,
        "commits_bot": 0,
        "commits_claude_trailer": 0,
        "insertions": 40,
        "deletions": 5,
        "files_changed": 4,
    }
    upsert_commits([row], store)
    upsert_commits([row], store)
    assert len(read_git_activity(store)) == 1


def test_missing_store_reads_empty(tmp_path: Path) -> None:
    assert read_git_activity(tmp_path / "nope.db") == []


# ---------------------------------------------------------------------------
# Step 1: PR title / body / head_ref collection (GUA-163)
# ---------------------------------------------------------------------------


def test_collect_prs_includes_title_body_head_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    """title, body, and head_ref must land in stored rows from the gh JSON payload."""
    import shutil

    payload = [
        {
            "number": 42,
            "state": "OPEN",
            "createdAt": "2026-08-01T10:00:00Z",
            "closedAt": None,
            "additions": 5,
            "deletions": 1,
            "author": {"login": "ramseywise", "is_bot": False},
            "title": "GUA-163 Add branches table",
            "body": "Closes #163",
            "headRefName": "GUA-163-git-activity-granularity",
        }
    ]
    import json as _json

    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/gh")

    import subprocess as _sp

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        class R:
            returncode = 0
            stdout = _json.dumps(payload)

        return R()

    monkeypatch.setattr(_sp, "run", fake_run)

    from telemetry.gitstore import collect_prs

    rows = collect_prs("guacamayo")
    assert len(rows) == 1
    row = rows[0]
    assert row["title"] == "GUA-163 Add branches table"
    assert row["body"] == "Closes #163"
    assert row["head_ref"] == "GUA-163-git-activity-granularity"


def test_collect_prs_body_truncation(monkeypatch: pytest.MonkeyPatch) -> None:
    """A body longer than 2000 chars must be stored as exactly 2000 chars."""
    import json as _json
    import shutil
    import subprocess as _sp

    long_body = "x" * 3000
    payload = [
        {
            "number": 1,
            "state": "MERGED",
            "createdAt": "2026-08-01T00:00:00Z",
            "closedAt": "2026-08-02T00:00:00Z",
            "additions": 0,
            "deletions": 0,
            "author": {"login": "ramseywise", "is_bot": False},
            "title": "Some PR",
            "body": long_body,
            "headRefName": "some-branch",
        }
    ]
    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/gh")

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        class R:
            returncode = 0
            stdout = _json.dumps(payload)

        return R()

    monkeypatch.setattr(_sp, "run", fake_run)

    from telemetry.gitstore import collect_prs

    rows = collect_prs("guacamayo")
    assert len(rows[0]["body"]) == 2000


# ---------------------------------------------------------------------------
# Step 2: branches table (GUA-163)
# ---------------------------------------------------------------------------


@pytest.fixture
def bare_remote(tmp_path: Path) -> tuple[Path, Path]:
    """A bare remote + a clone with one branch committed."""
    remote = tmp_path / "remote.git"
    remote.mkdir()
    run = lambda *a, cwd=remote: subprocess.run(a, cwd=cwd, check=True, capture_output=True)
    run("git", "init", "--bare", "-q")
    # Clone it so we can push a branch.
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(remote), str(clone)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(clone), "config", "user.email", "t@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(clone), "config", "user.name", "Tester"], check=True, capture_output=True
    )
    (clone / "a.py").write_text("x=1\n")
    subprocess.run(["git", "-C", str(clone), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(clone), "commit", "-q", "-m", "init"], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(clone), "push", "-q", "origin", "HEAD:main"],
        check=True,
        capture_output=True,
    )
    # Add a feature branch.
    subprocess.run(
        ["git", "-C", str(clone), "checkout", "-q", "-b", "GUA-163-feature"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(clone), "push", "-q", "origin", "GUA-163-feature"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(clone), "checkout", "-q", "main"], check=True, capture_output=True
    )
    return clone, remote


def test_collect_branches_basic(bare_remote: tuple[Path, Path]) -> None:
    """collect_branches returns rows for each remote branch; matched PR sets merged/pr_number."""
    clone, _ = bare_remote
    # Simulate a merged PR for the feature branch.
    pr_by_head_ref = {
        "GUA-163-feature": {"number": 163, "merged": 1},
    }
    from telemetry.gitstore import _collect_branches_with_prs

    rows = _collect_branches_with_prs(clone, "guacamayo", pr_by_head_ref)
    by_name = {r["name"]: r for r in rows}
    assert "GUA-163-feature" in by_name
    feat = by_name["GUA-163-feature"]
    assert feat["merged"] == 1
    assert feat["pr_number"] == 163
    # main has no PR — merged=0, pr_number=None
    assert by_name["main"]["merged"] == 0
    assert by_name["main"]["pr_number"] is None


def test_upsert_branches_upserts(tmp_path: Path) -> None:
    """Running upsert twice with the same key must not create duplicates."""
    store = tmp_path / "facts.db"
    row = {
        "repo": "guacamayo",
        "name": "GUA-163-feature",
        "merged": 1,
        "pr_number": 163,
        "head_sha": "abc123",
    }
    upsert_prs([], store)  # initialise store / pull_requests table
    from telemetry.gitstore import _connect

    conn = _connect(store)
    upsert_branches(conn, [row])
    upsert_branches(conn, [row])
    conn.close()
    result = read_branches(store)
    assert len(result) == 1
    assert result[0]["merged"] == 1


def test_collect_branches_skips_head(bare_remote: tuple[Path, Path]) -> None:
    """The HEAD -> origin/main symbolic ref line must not produce a branch row."""
    clone, _ = bare_remote
    from telemetry.gitstore import _collect_branches_with_prs

    rows = _collect_branches_with_prs(clone, "guacamayo", {})
    names = [r["name"] for r in rows]
    assert not any("HEAD" in n for n in names), f"HEAD leaked into branch rows: {names}"
