"""Tests for review.dao.fingerprint — fingerprint generation, comparison, persistence."""

from __future__ import annotations

import json

from review.fingerprint import (
    compare_sweeps,
    finding_to_sweep_finding,
    latest_sweep_path,
    load_sweep,
    make_fingerprint,
    save_sweep,
)
from review.schemas.models import (
    Category,
    Claim,
    CommentType,
    EvidenceState,
    FileLocation,
    Location,
    MergeImpact,
    Reporter,
    ReviewFinding,
    Severity,
    SweepFinding,
    SweepRecord,
)
from tests.review.conftest import REPO_ROOT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_finding(
    id: str = "AK-001",
    path: str = "src/foo.py",
    start_line: int | None = 10,
    category: Category = Category.CORRECTNESS,
    reporter: Reporter = Reporter.AKIRA_SCAN,
    title: str = "Missing null check",
) -> ReviewFinding:
    return ReviewFinding(
        id=id,
        reporter=reporter,
        category=category,
        evidence_state=EvidenceState.VERIFIED,
        location=Location(
            files=[FileLocation(path=path, start_line=start_line, end_line=start_line)],
        ),
        claim=Claim(title=title, observation="observed"),
        severity=Severity(merge_impact=MergeImpact.IMPORTANT),
        comment_type=CommentType.REQUEST_CHANGE,
    )


def make_sweep_finding(
    digest: str = "abc123",
    file_path: str = "src/foo.py",
    start_line: int | None = 10,
    category: str = "correctness",
    reporter: str = "akira_scan",
    title: str = "Missing null check",
    finding_id: str = "AK-001",
) -> SweepFinding:
    return SweepFinding(
        fingerprint=digest,
        finding_id=finding_id,
        file_path=file_path,
        start_line=start_line,
        category=category,
        reporter=reporter,
        title=title,
        merge_impact="important",
        evidence_state="verified",
    )


# ---------------------------------------------------------------------------
# make_fingerprint
# ---------------------------------------------------------------------------


class TestMakeFingerprint:
    def test_returns_FindingFingerprint(self):
        finding = make_finding()
        fp = make_fingerprint(finding)
        assert fp.file_path == "src/foo.py"
        assert fp.start_line == 10
        assert fp.category == "correctness"
        assert fp.reporter == "akira_scan"
        assert fp.title == "Missing null check"

    def test_digest_is_hex_string(self):
        fp = make_fingerprint(make_finding())
        assert len(fp.digest) == 64
        int(fp.digest, 16)  # must be valid hex

    def test_same_finding_same_digest(self):
        f1 = make_finding()
        f2 = make_finding()
        assert make_fingerprint(f1).digest == make_fingerprint(f2).digest

    def test_different_file_different_digest(self):
        f1 = make_finding(path="src/foo.py")
        f2 = make_finding(path="src/bar.py")
        assert make_fingerprint(f1).digest != make_fingerprint(f2).digest

    def test_different_line_different_digest(self):
        f1 = make_finding(start_line=10)
        f2 = make_finding(start_line=20)
        assert make_fingerprint(f1).digest != make_fingerprint(f2).digest

    def test_different_category_different_digest(self):
        f1 = make_finding(category=Category.CORRECTNESS)
        f2 = make_finding(category=Category.SECURITY)
        assert make_fingerprint(f1).digest != make_fingerprint(f2).digest

    def test_different_title_different_digest(self):
        f1 = make_finding(title="Missing null check")
        f2 = make_finding(title="Unhandled exception")
        assert make_fingerprint(f1).digest != make_fingerprint(f2).digest

    def test_no_files_uses_empty_path(self):
        finding = make_finding()
        finding = finding.model_copy(update={"location": Location(files=[], symbols=[])})
        fp = make_fingerprint(finding)
        assert fp.file_path == ""
        assert fp.start_line is None


# ---------------------------------------------------------------------------
# finding_to_sweep_finding
# ---------------------------------------------------------------------------


class TestFindingToSweepFinding:
    def test_produces_SweepFinding(self):
        sf = finding_to_sweep_finding(make_finding())
        assert isinstance(sf, SweepFinding)

    def test_fingerprint_matches_make_fingerprint(self):
        f = make_finding()
        sf = finding_to_sweep_finding(f)
        assert sf.fingerprint == make_fingerprint(f).digest

    def test_fields_populated(self):
        f = make_finding(id="AK-001", path="src/foo.py", start_line=10, title="Bug X")
        sf = finding_to_sweep_finding(f)
        assert sf.finding_id == "AK-001"
        assert sf.file_path == "src/foo.py"
        assert sf.start_line == 10
        assert sf.title == "Bug X"
        assert sf.merge_impact == "important"
        assert sf.evidence_state == "verified"


# ---------------------------------------------------------------------------
# compare_sweeps
# ---------------------------------------------------------------------------


class TestCompareSweeps:
    def _record(self, repo: str, date: str, findings: list[SweepFinding]) -> SweepRecord:
        return SweepRecord(repo=repo, sweep_date=date, findings=findings)

    def test_all_new_when_previous_empty(self):
        sf = make_sweep_finding()
        prev = self._record("r", "2026-01-01", [])
        curr = self._record("r", "2026-01-02", [sf])
        new, resolved, recurring = compare_sweeps(prev, curr)
        assert len(new) == 1
        assert len(resolved) == 0
        assert len(recurring) == 0

    def test_all_resolved_when_current_empty(self):
        sf = make_sweep_finding()
        prev = self._record("r", "2026-01-01", [sf])
        curr = self._record("r", "2026-01-02", [])
        new, resolved, recurring = compare_sweeps(prev, curr)
        assert len(new) == 0
        assert len(resolved) == 1
        assert len(recurring) == 0

    def test_recurring_when_same_digest_both(self):
        sf = make_sweep_finding()
        prev = self._record("r", "2026-01-01", [sf])
        curr = self._record("r", "2026-01-02", [sf])
        new, resolved, recurring = compare_sweeps(prev, curr)
        assert len(new) == 0
        assert len(resolved) == 0
        assert len(recurring) == 1

    def test_mixed_new_resolved_recurring(self):
        sf_a = make_sweep_finding(digest="aaa", title="A")
        sf_b = make_sweep_finding(digest="bbb", title="B")
        sf_c = make_sweep_finding(digest="ccc", title="C")
        # prev has A + B, curr has B + C
        prev = self._record("r", "2026-01-01", [sf_a, sf_b])
        curr = self._record("r", "2026-01-02", [sf_b, sf_c])
        new, resolved, recurring = compare_sweeps(prev, curr)
        assert {f.fingerprint for f in new} == {"ccc"}
        assert {f.fingerprint for f in resolved} == {"aaa"}
        assert {f.fingerprint for f in recurring} == {"bbb"}

    def test_empty_both_returns_empty_lists(self):
        prev = self._record("r", "2026-01-01", [])
        curr = self._record("r", "2026-01-02", [])
        new, resolved, recurring = compare_sweeps(prev, curr)
        assert new == [] and resolved == [] and recurring == []

    def test_new_findings_come_from_current_record(self):
        sf_old = make_sweep_finding(digest="old111", finding_id="AK-001")
        sf_new = make_sweep_finding(digest="new222", finding_id="AK-002")
        prev = self._record("r", "2026-01-01", [sf_old])
        curr = self._record("r", "2026-01-02", [sf_new])
        new, _, _ = compare_sweeps(prev, curr)
        assert new[0].finding_id == "AK-002"


# ---------------------------------------------------------------------------
# load_sweep / save_sweep
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_save_and_load_roundtrip(self, tmp_path):
        sf = make_sweep_finding()
        record = SweepRecord(repo="myrepo", sweep_date="2026-01-01", findings=[sf])
        path = tmp_path / "myrepo-2026-01-01.json"
        save_sweep(record, path)
        loaded = load_sweep(path)
        assert loaded is not None
        assert loaded.repo == "myrepo"
        assert loaded.sweep_date == "2026-01-01"
        assert len(loaded.findings) == 1
        assert loaded.findings[0].fingerprint == sf.fingerprint

    def test_load_missing_file_returns_none(self, tmp_path):
        result = load_sweep(tmp_path / "nonexistent.json")
        assert result is None

    def test_save_creates_parent_dirs(self, tmp_path):
        sf = make_sweep_finding()
        record = SweepRecord(repo="r", sweep_date="2026-01-01", findings=[sf])
        nested = tmp_path / "deep" / "nested" / "r-2026-01-01.json"
        save_sweep(record, nested)
        assert nested.exists()

    def test_save_writes_valid_json(self, tmp_path):
        record = SweepRecord(repo="r", sweep_date="2026-01-01", findings=[])
        path = tmp_path / "r-2026-01-01.json"
        save_sweep(record, path)
        data = json.loads(path.read_text())
        assert data["repo"] == "r"
        assert data["findings"] == []


# ---------------------------------------------------------------------------
# latest_sweep_path
# ---------------------------------------------------------------------------


class TestLatestSweepPath:
    def test_returns_most_recent_file(self, tmp_path):
        import time

        p1 = tmp_path / "myrepo-2026-01-01.json"
        p1.write_text("{}")
        time.sleep(0.02)
        p2 = tmp_path / "myrepo-2026-01-02.json"
        p2.write_text("{}")
        result = latest_sweep_path(tmp_path, "myrepo")
        assert result == p2

    def test_returns_none_when_no_files(self, tmp_path):
        result = latest_sweep_path(tmp_path, "myrepo")
        assert result is None

    def test_ignores_other_repos(self, tmp_path):
        (tmp_path / "other-2026-01-01.json").write_text("{}")
        result = latest_sweep_path(tmp_path, "myrepo")
        assert result is None


# ---------------------------------------------------------------------------
# CLI integration — fingerprint command
# ---------------------------------------------------------------------------


class TestFingerprintCLI:
    def _finding_payload(self) -> list[dict]:
        return [
            {
                "id": "AK-001",
                "reporter": "akira_scan",
                "category": "correctness",
                "evidence_state": "verified",
                "location": {
                    "files": [{"path": "src/foo.py", "start_line": 10, "end_line": 10}],
                    "symbols": [],
                },
                "claim": {"title": "Missing null check", "observation": "obs"},
                "severity": {"merge_impact": "important"},
                "comment_type": "request_change",
            }
        ]

    def test_fingerprint_cmd_outputs_sweep_record(self, tmp_path):
        import subprocess

        payload = json.dumps(self._finding_payload())
        result = subprocess.run(
            [
                "uv",
                "run",
                "review-cli",
                "fingerprint",
                "--repo",
                "testrepo",
                "--sweep-date",
                "2026-01-01",
            ],
            input=payload,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["repo"] == "testrepo"
        assert data["sweep_date"] == "2026-01-01"
        assert len(data["findings"]) == 1
        assert len(data["findings"][0]["fingerprint"]) == 64

    def test_fingerprint_cmd_save_flag(self, tmp_path):
        import subprocess

        payload = json.dumps(self._finding_payload())
        result = subprocess.run(
            [
                "uv",
                "run",
                "review-cli",
                "fingerprint",
                "--repo",
                "testrepo",
                "--sweep-date",
                "2026-07-01",
                "--reviews-dir",
                str(tmp_path),
                "--save",
            ],
            input=payload,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, result.stderr
        saved = list(tmp_path.glob("testrepo-*.json"))
        assert len(saved) == 1

    def test_fingerprint_cmd_no_clobber_on_same_date(self, tmp_path):
        import subprocess

        payload = json.dumps(self._finding_payload())
        base_args = [
            "uv",
            "run",
            "review-cli",
            "fingerprint",
            "--repo",
            "testrepo",
            "--sweep-date",
            "2026-07-01",
            "--reviews-dir",
            str(tmp_path),
            "--save",
        ]
        for _ in range(3):
            subprocess.run(
                base_args,
                input=payload,
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
            )
        saved = list(tmp_path.glob("testrepo-*.json"))
        assert len(saved) == 3
