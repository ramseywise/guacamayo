"""Backfill safety: identity preservation, idempotence, atomic rewrite, fallbacks."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from telemetry.backfill_occurrence import (
    IDENTITY_FIELDS,
    SOURCE_RUN,
    assert_identity_preserved,
    backfill_rows,
    concentration,
    main,
    read_rows,
    write_atomically,
)

COMMIT_DATE = "2026-03-09"
RUN_DATE = "2026-08-04"


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
    ws = tmp_path / "workspace"
    ws.mkdir()
    repo = ws / "demo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Tester")
    (repo / "app.py").write_text("alpha\nbravo\ncharlie\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feat: app", date=COMMIT_DATE)
    return ws


def _row(**over) -> dict:
    base = {
        "id": "CR-001",
        "source": "correctness",
        "date": RUN_DATE,
        "repo": "demo",
        "file": "app.py",
        "lines": "2",
        "title": "something is wrong",
        "category": "logic",
    }
    base.update(over)
    return base


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    path = tmp_path / "findings.jsonl"
    rows = [
        _row(),
        _row(id="CR-002", lines="1-3"),
        _row(id="CR-003", repo="never-cloned", file="x.py"),
    ]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def test_adds_both_fields(workspace: Path, corpus: Path) -> None:
    after, counts = backfill_rows(read_rows(corpus), workspace=workspace)
    assert all("occurred" in r and "occurred_source" in r for r in after)
    assert counts["blame"] == 2


def test_blamed_rows_get_commit_date_not_run_date(workspace: Path, corpus: Path) -> None:
    """The entire point: `occurred` must differ from the sweep's `date`."""
    after, _ = backfill_rows(read_rows(corpus), workspace=workspace)
    assert after[0]["occurred"] == COMMIT_DATE
    assert after[0]["date"] == RUN_DATE, "run date must survive untouched"


def test_unresolvable_repo_falls_back_to_run_date(workspace: Path, corpus: Path) -> None:
    """A row whose checkout is absent keeps the run date, tagged `run`."""
    after, counts = backfill_rows(read_rows(corpus), workspace=workspace)
    orphan = next(r for r in after if r["id"] == "CR-003")
    assert orphan["occurred_source"] == SOURCE_RUN
    assert orphan["occurred"] == orphan["date"] == RUN_DATE
    assert counts[SOURCE_RUN] == 1


def test_identity_fields_are_byte_identical(workspace: Path, corpus: Path) -> None:
    """`date`/`id`/`repo`/`file`/`title` feed finding_uid — none may move."""
    before = read_rows(corpus)
    after, _ = backfill_rows(before, workspace=workspace)
    for old, new in zip(before, after, strict=True):
        for field in IDENTITY_FIELDS:
            assert old.get(field) == new.get(field), f"{field} changed"


def test_input_rows_are_not_mutated(workspace: Path, corpus: Path) -> None:
    """Callers keep a usable `before` snapshot for the comparison table."""
    before = read_rows(corpus)
    backfill_rows(before, workspace=workspace)
    assert all("occurred" not in r for r in before)


def test_idempotent_second_run_changes_nothing(workspace: Path, corpus: Path) -> None:
    once, _ = backfill_rows(read_rows(corpus), workspace=workspace)
    twice, counts = backfill_rows(once, workspace=workspace)
    assert twice == once
    assert counts["skipped"] == len(once), "re-resolved a row that already had `occurred`"


def test_force_re_resolves(workspace: Path, corpus: Path) -> None:
    once, _ = backfill_rows(read_rows(corpus), workspace=workspace)
    for row in once:
        row["occurred"] = "1999-01-01"
    twice, counts = backfill_rows(once, workspace=workspace, force=True)
    assert counts["skipped"] == 0
    assert twice[0]["occurred"] == COMMIT_DATE


def test_assert_identity_preserved_catches_a_changed_date() -> None:
    before = [_row()]
    after = [_row(date="2026-01-01")]
    with pytest.raises(SystemExit, match="date"):
        assert_identity_preserved(before, after)


def test_assert_identity_preserved_catches_dropped_rows() -> None:
    with pytest.raises(SystemExit, match="row count"):
        assert_identity_preserved([_row(), _row(id="CR-002")], [_row()])


def test_write_is_atomic_and_backs_up(tmp_path: Path, corpus: Path) -> None:
    original = corpus.read_text()
    rows = read_rows(corpus)
    rows[0]["occurred"] = COMMIT_DATE
    write_atomically(corpus, rows)
    assert corpus.with_suffix(".jsonl.bak").read_text() == original
    assert read_rows(corpus)[0]["occurred"] == COMMIT_DATE
    assert not list(tmp_path.glob("*.tmp")), "temp file left behind"


def test_concentration_reports_share_and_spread() -> None:
    rows = [{"d": "2026-08-04"}] * 3 + [{"d": "2026-01-01"}]
    share, days, weeks = concentration(rows, "d")
    assert (share, days, weeks) == (0.75, 2, 2)


def test_dry_run_writes_nothing(workspace: Path, corpus: Path, capsys) -> None:
    digest = corpus.read_text()
    assert main(["--path", str(corpus), "--workspace", str(workspace)]) == 0
    assert corpus.read_text() == digest, "dry run modified the corpus"
    assert not corpus.with_suffix(".jsonl.bak").exists()
    assert "dry run" in capsys.readouterr().out


def test_write_flag_applies(workspace: Path, corpus: Path, capsys) -> None:
    assert main(["--path", str(corpus), "--workspace", str(workspace), "--write"]) == 0
    after = read_rows(corpus)
    assert all("occurred" in r for r in after)
    assert "wrote 3 rows" in capsys.readouterr().out


def test_missing_corpus_exits_nonzero(tmp_path: Path, capsys) -> None:
    assert main(["--path", str(tmp_path / "nope.jsonl")]) == 1
    assert "FATAL" in capsys.readouterr().err


def test_malformed_jsonl_reports_line_number(tmp_path: Path) -> None:
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"id": "A"}\nnot json\n')
    with pytest.raises(SystemExit, match="bad.jsonl:2"):
        read_rows(bad)
