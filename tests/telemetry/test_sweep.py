"""Portfolio sweep: state pass, file selection, ledger, digest — real git, fake review."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from telemetry.repos import Repo
from telemetry.sweep import (
    ReviewOutcome,
    acknowledged_keys,
    collect_state,
    run_sweep,
    select_files,
    update_ledger,
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _commit(repo: Path, rel: str, body: str = "x\n") -> str:
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text(body)
    _git(repo, "add", rel)
    _git(repo, "commit", "-qm", f"edit {rel}")
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    """A clone of a bare origin with one pushed commit on main."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    _git(work, "config", "user.email", "t@t")
    _git(work, "config", "user.name", "t")
    _git(work, "checkout", "-qb", "main")
    _commit(work, "src/a.py")
    _git(work, "push", "-qu", "origin", "main")
    _git(work, "remote", "set-head", "origin", "main")
    return work


def _repo(path: Path, *, review: bool = True) -> Repo:
    return Repo(name=path.name, role="product", visibility="private", path=path, review=review)


def _no_gh(_repo: Path, _args: list[str]) -> list:
    return []


def _finding(path: str, title: str = "bug") -> dict:
    return {
        "id": "CR-001",
        "reporter": "correctness",
        "category": "correctness",
        "evidence_state": "verified",
        "location": {"files": [{"path": path, "start_line": 3}], "symbols": []},
        "claim": {"title": title, "observation": "observed"},
        "severity": {"merge_impact": "important"},
        "comment_type": "request_change",
        "basis": [],
    }


def test_not_cloned_is_reported_not_skipped(tmp_path: Path) -> None:
    st = collect_state(_repo(tmp_path / "missing"), board_path=tmp_path / "b.json", gh=_no_gh)
    assert st.status == "not_cloned"
    assert st.errors


def test_state_reads_drift_tree_and_branches(clone: Path, tmp_path: Path) -> None:
    _commit(clone, "src/b.py")  # local main one ahead of origin
    (clone / "src/a.py").write_text("changed\n")
    (clone / "new.txt").write_text("u\n")
    _git(clone, "push", "-q", "origin", "main:feature/x")
    board = tmp_path / "board.json"
    board.write_text(
        json.dumps(
            {"proposed_actions": [{"action": "close", "target": {"repo": "work", "issue_num": 4}}]}
        )
    )

    def gh(_repo: Path, args: list[str]) -> list | str:
        if "merged" in args:
            return [{"headRefName": "feature/x", "number": 9}]
        return [
            {"number": 1, "title": "t", "author": {"login": "app/dependabot"}, "headRefName": "d"}
        ]

    st = collect_state(_repo(clone), board_path=board, gh=gh)
    assert st.status == "ok", st.errors
    assert st.default_branch == "main"
    assert (st.local_ahead, st.local_behind) == (1, 0)
    assert (st.unstaged, st.untracked) == (1, 1)
    assert st.remote_branches == [{"name": "feature/x", "ahead": 1, "merged_pr": 9}]
    assert len(st.dependabot_prs) == 1 and not st.open_prs
    assert len(st.board_actions) == 1


def test_gh_failure_is_an_error_not_an_empty_list(clone: Path, tmp_path: Path) -> None:
    st = collect_state(
        _repo(clone), board_path=tmp_path / "b.json", gh=lambda _r, _a: "auth required"
    )
    assert any("auth required" in e for e in st.errors)


def test_select_files_since_sha_skips_deleted_and_lockfiles(clone: Path) -> None:
    base = _git(clone, "rev-parse", "HEAD")
    _commit(clone, "src/b.py")
    _commit(clone, "uv.lock")
    _commit(clone, "gone.py")
    _git(clone, "rm", "-q", "gone.py")
    _git(clone, "commit", "-qm", "rm")
    files, dropped = select_files(clone, "HEAD", base, days=30)
    assert files == ["src/b.py"]
    assert dropped == 0


def test_select_files_unknown_sha_falls_back_to_days(clone: Path) -> None:
    files, _ = select_files(clone, "HEAD", "0" * 40, days=30)
    assert files == ["src/a.py"]


def test_ledger_resolves_only_reviewed_files_on_a_clean_run() -> None:
    ledger = {"cursors": {}, "findings": {}}
    first = ReviewOutcome(
        files=["a.py", "b.py"],
        completed=True,
        findings=[
            {
                "fingerprint": "fa",
                "file": "a.py",
                "line": 1,
                "title": "A",
                "merge_impact": "nit",
                "category": "c",
            },
            {
                "fingerprint": "fb",
                "file": "b.py",
                "line": 1,
                "title": "B",
                "merge_impact": "nit",
                "category": "c",
            },
        ],
    )
    update_ledger(ledger, "r", first, "2026-10-01")
    # second run re-reviews a.py only and reports nothing
    update_ledger(ledger, "r", ReviewOutcome(files=["a.py"], completed=True), "2026-10-08")
    assert ledger["findings"]["r:fa"]["status"] == "resolved"
    assert ledger["findings"]["r:fb"]["status"] == "open"  # carried: b.py not re-reviewed

    # an incomplete run never resolves
    update_ledger(ledger, "r", ReviewOutcome(files=["b.py"], completed=False), "2026-10-15")
    assert ledger["findings"]["r:fb"]["status"] == "open"


def test_acknowledged_keys_reads_ticked_markers(tmp_path: Path) -> None:
    digest = tmp_path / "d.md"
    digest.write_text(
        "- [x] **nit** `a.py` — A <!-- fp:r:fa -->\n- [ ] **nit** `b.py` — B <!-- fp:r:fb -->\n"
    )
    assert acknowledged_keys(digest) == {"r:fa"}


def test_run_sweep_end_to_end(clone: Path, tmp_path: Path) -> None:
    sweeps = tmp_path / "sweeps"
    calls: list[list[str]] = []

    async def fake_scan(dimension: str, files: list[str], _config) -> list[dict]:
        calls.append(files)
        return [_finding("src/a.py")] if dimension == "correctness" else []

    repo = _repo(clone)
    digest = run_sweep(
        [repo], today="2026-10-29", sweeps_dir=sweeps, board_path=tmp_path / "b.json",
        gh=_no_gh, scan_fn=fake_scan,
    )  # fmt: skip
    text = digest.read_text()
    assert "## work" in text
    assert "src/a.py:3" in text and "<!-- fp:work:" in text
    assert calls and calls[0] == ["src/a.py"]
    # the throwaway checkout is gone and the user's clone has no extra worktree
    assert not (sweeps / "checkouts" / "work").exists()
    assert len(_git(clone, "worktree", "list").splitlines()) == 1

    ledger = json.loads((sweeps / "findings.json").read_text())
    assert ledger["cursors"]["work"]["sha"] == _git(clone, "rev-parse", "origin/main")
    assert (sweeps / "2026-10-29.state.json").exists()

    # tick it; next sweep with no new commits skips review and carries the ack
    key = next(iter(ledger["findings"]))
    digest.write_text(text.replace("- [ ]", "- [x]"))
    calls.clear()
    text2 = run_sweep(
        [repo], today="2026-11-05", sweeps_dir=sweeps, board_path=tmp_path / "b.json",
        gh=_no_gh, scan_fn=fake_scan,
    ).read_text()  # fmt: skip
    assert not calls
    assert "no new commits since last review" in text2
    assert "### Carried over" in text2 and "- [x] **important** `src/a.py:3`" in text2
    assert (
        json.loads((sweeps / "findings.json").read_text())["findings"][key]["status"]
        == "acknowledged"
    )
