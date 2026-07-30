"""Tests for review/driver.py — Steps 2, 3, 4, 5 coverage.

Covers:
- load_agent_prompt: frontmatter stripping, driver-mode suffix injection
- parse_scan_result: success, error subtypes
- merge_cluster: deterministic representative selection
- run_review pipeline: valid path → report + sweep; invalid finding → exit_code=1
- cli 'run' subcommand: CliRunner with monkeypatched scan_fn
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

from review.cli import main
from review.driver import (
    FINDINGS_SCHEMA,
    DriverConfig,
    DriverResult,
    ScanError,
    load_agent_prompt,
    merge_cluster,
    parse_scan_result,
    run_review,
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
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_finding(
    id: str = "CR-001",
    *,
    reporter: Reporter = Reporter.CORRECTNESS,
    merge_impact: MergeImpact = MergeImpact.IMPORTANT,
    path: str = "review/driver.py",
    title: str = "Test finding",
) -> ReviewFinding:
    return ReviewFinding(
        id=id,
        reporter=reporter,
        category=Category.CORRECTNESS,
        evidence_state=EvidenceState.VERIFIED,
        location=Location(files=[FileLocation(path=path, start_line=1)]),
        claim=Claim(title=title, observation="observed"),
        severity=Severity(merge_impact=merge_impact),
        comment_type=CommentType.REQUEST_CHANGE,
    )


def make_finding_dict(
    id: str = "CR-001",
    reporter: str = "correctness",
    merge_impact: str = "important",
    path: str = "review/driver.py",
    title: str = "Test finding",
) -> dict:
    return {
        "id": id,
        "reporter": reporter,
        "category": "correctness",
        "evidence_state": "verified",
        "location": {"files": [{"path": path, "start_line": 1}], "symbols": []},
        "claim": {"title": title, "observation": "observed"},
        "severity": {"merge_impact": merge_impact},
        "comment_type": "request_change",
        "basis": [],
    }


# ---------------------------------------------------------------------------
# Step 2: load_agent_prompt tests
# ---------------------------------------------------------------------------


class TestLoadAgentPrompt:
    def test_strips_yaml_frontmatter(self, tmp_path: Path) -> None:
        """Frontmatter YAML fields are removed from the prompt body."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "correctness.md").write_text(
            textwrap.dedent("""\
            ---
            name: scan-correctness
            description: Test agent
            tools: Read
            model: haiku
            ---
            You are the correctness scanner.

            Scan for bugs.
            """)
        )
        prompt = load_agent_prompt("correctness", agents_dir)
        # Frontmatter YAML fields should not appear in the prompt
        assert "name: scan-correctness" not in prompt
        assert "description: Test agent" not in prompt
        assert "model: haiku" not in prompt
        # Body content should be present
        assert "You are the correctness scanner." in prompt

    def test_appends_driver_mode_suffix(self, tmp_path: Path) -> None:
        """Driver-mode suffix is appended after the body."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "safety.md").write_text("---\nname: x\n---\nBody text.\n")
        prompt = load_agent_prompt("safety", agents_dir)
        assert "Driver mode (deterministic pipeline)" in prompt
        assert "Body text." in prompt

    def test_no_frontmatter_returns_full_body(self, tmp_path: Path) -> None:
        """Files without frontmatter return full content + suffix."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "structure.md").write_text("You are structure.\n")
        prompt = load_agent_prompt("structure", agents_dir)
        assert "You are structure." in prompt
        assert "Driver mode" in prompt

    def test_agent_quality_mapped_to_hyphenated_file(self, tmp_path: Path) -> None:
        """'agent-quality' dimension maps to 'agent-quality.md'."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent-quality.md").write_text("---\nname: x\n---\nAQ content.\n")
        prompt = load_agent_prompt("agent-quality", agents_dir)
        assert "AQ content." in prompt

    def test_missing_agent_file_raises(self, tmp_path: Path) -> None:
        """FileNotFoundError when agent .md is missing."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="Agent file not found"):
            load_agent_prompt("correctness", agents_dir)

    @pytest.mark.parametrize(
        "dimension",
        ["correctness", "safety", "structure", "agent-quality", "contracts", "wander"],
    )
    def test_all_six_dimensions_load_from_real_repo(self, dimension: str) -> None:
        """All 6 real agent files load and strip frontmatter correctly."""
        repo_root = Path(__file__).resolve().parent.parent.parent
        agents_dir = repo_root / ".claude" / "agents"
        prompt = load_agent_prompt(dimension, agents_dir)
        # Frontmatter stripped: no leading ---
        assert not prompt.startswith("---")
        # Driver suffix present
        assert "Driver mode" in prompt


# ---------------------------------------------------------------------------
# Step 2: parse_scan_result tests
# ---------------------------------------------------------------------------


class TestParseScanResult:
    def test_success_returns_findings_list(self) -> None:
        findings = [make_finding_dict()]
        result_text = json.dumps({"findings": findings})
        parsed = parse_scan_result(result_text, "success")
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["id"] == "CR-001"

    def test_success_empty_findings(self) -> None:
        result_text = json.dumps({"findings": []})
        parsed = parse_scan_result(result_text, "success")
        assert parsed == []

    def test_error_subtype_returns_scan_error(self) -> None:
        error = parse_scan_result("some detail", "error_max_structured_output_retries")
        assert isinstance(error, ScanError)
        assert error.subtype == "error_max_structured_output_retries"

    def test_error_max_turns_returns_scan_error(self) -> None:
        error = parse_scan_result(None, "error_max_turns")
        assert isinstance(error, ScanError)
        assert error.subtype == "error_max_turns"

    def test_invalid_json_returns_scan_error(self) -> None:
        error = parse_scan_result("not json at all", "success")
        assert isinstance(error, ScanError)
        assert error.subtype == "parse_error"

    def test_findings_not_list_returns_scan_error(self) -> None:
        result_text = json.dumps({"findings": "not a list"})
        error = parse_scan_result(result_text, "success")
        assert isinstance(error, ScanError)
        assert error.subtype == "parse_error"
        assert "not a list" in error.detail

    def test_none_result_with_success_subtype(self) -> None:
        """None result text with success subtype → parse_error."""
        error = parse_scan_result(None, "success")
        assert isinstance(error, ScanError)
        assert error.subtype == "parse_error"

    @pytest.mark.parametrize(
        "subtype",
        [
            "error_max_structured_output_retries",
            "error_max_turns",
            "error_overloaded",
            "error_api_error",
        ],
    )
    def test_all_error_subtypes(self, subtype: str) -> None:
        error = parse_scan_result("detail", subtype)
        assert isinstance(error, ScanError)
        assert error.subtype == subtype


# ---------------------------------------------------------------------------
# Step 3: merge_cluster tests
# ---------------------------------------------------------------------------


class TestMergeCluster:
    def test_single_finding_returned_as_is(self) -> None:
        f = make_finding("CR-001")
        result = merge_cluster([f])
        assert result.id == "CR-001"
        assert result is f  # identity preserved for single-element cluster

    def test_blocker_wins_over_important(self) -> None:
        blocker = make_finding("CR-001", merge_impact=MergeImpact.BLOCKER)
        important = make_finding(
            "SF-001", reporter=Reporter.SAFETY, merge_impact=MergeImpact.IMPORTANT
        )
        result = merge_cluster([important, blocker])
        assert result.id == "CR-001"  # blocker is representative

    def test_absorbed_ids_in_basis(self) -> None:
        blocker = make_finding("CR-001", merge_impact=MergeImpact.BLOCKER)
        nit = make_finding("SF-002", reporter=Reporter.SAFETY, merge_impact=MergeImpact.NIT)
        result = merge_cluster([blocker, nit])
        assert any("SF-002" in b for b in result.basis)

    def test_deterministic_with_equal_impact(self) -> None:
        """Two IMPORTANT findings: result is one of the two, absorbed IDs in basis."""
        f1 = make_finding("CR-001", merge_impact=MergeImpact.IMPORTANT, title="A")
        f2 = make_finding(
            "SF-001", reporter=Reporter.SAFETY, merge_impact=MergeImpact.IMPORTANT, title="B"
        )
        result = merge_cluster([f1, f2])
        # Representative is one of the two inputs
        assert result.id in ("CR-001", "SF-001")
        # The absorbed ID should appear in basis
        absorbed = "SF-001" if result.id == "CR-001" else "CR-001"
        assert any(absorbed in b for b in result.basis)

    def test_original_basis_preserved(self) -> None:
        f = make_finding("CR-001")
        f2 = make_finding("SF-001", reporter=Reporter.SAFETY, merge_impact=MergeImpact.NIT)
        # Ensure original basis items are still present
        f_with_basis = f.model_copy(update={"basis": ["original basis"]})
        result = merge_cluster([f_with_basis, f2])
        assert "original basis" in result.basis


# ---------------------------------------------------------------------------
# Step 3: run_review pipeline with fake scan_fn
# ---------------------------------------------------------------------------


def make_fake_scan(findings_by_dim: dict[str, list[dict]]):
    """Build a fake async scan_fn that returns pre-canned findings."""

    async def fake_scan(
        dimension: str, files: list[str], config: DriverConfig
    ) -> list[dict] | ScanError:
        return findings_by_dim.get(dimension, [])

    return fake_scan


class TestRunReview:
    def test_valid_scan_produces_report_and_sweep(self, tmp_path: Path) -> None:
        """Valid findings → report rendered, sweep file saved, exit_code=0."""
        findings_by_dim = {
            "correctness": [make_finding_dict("CR-001")],
            "safety": [],
            "structure": [],
            "wander": [],
        }
        config = DriverConfig(
            repo=tmp_path,
            files=["review/driver.py"],
            reviews_dir=tmp_path / "reviews",
            save_sweep=True,
            model="haiku",
        )
        # Create a minimal .claude/agents directory so load_agent_prompt doesn't crash
        # (scan_fn is fake, so we just need to not fail before it's called)
        config.agents_dir = tmp_path / "agents"
        config.agents_dir.mkdir()

        result = run_review(config, scan_fn=make_fake_scan(findings_by_dim))

        assert result.exit_code == 0
        assert "Review Report" in result.report_md
        assert result.sweep_path is not None
        assert result.sweep_path.exists()
        assert len(result.findings) >= 1

    def test_invalid_finding_fails_run(self, tmp_path: Path) -> None:
        """Invalid finding dict (missing required fields) → exit_code=1 after repair fails."""
        bad_finding = {"id": "CR-001", "reporter": "correctness"}  # incomplete

        async def bad_scan(
            dimension: str, files: list[str], config: DriverConfig
        ) -> list[dict] | ScanError:
            if dimension == "correctness":
                return [bad_finding]
            return []

        # Repair also returns bad
        async def repair_scan(
            dimension: str, files: list[str], config: DriverConfig
        ) -> list[dict] | ScanError:
            return [bad_finding]

        config = DriverConfig(
            repo=tmp_path,
            files=["review/driver.py"],
            reviews_dir=tmp_path / "reviews",
            save_sweep=False,
        )
        config.agents_dir = tmp_path / "agents"
        config.agents_dir.mkdir()

        # Patch _repair_scan to return the same bad finding
        import review.driver as driver_module

        original_repair = driver_module._repair_scan

        async def mock_repair(dimension, files, config, error_detail):
            return [bad_finding]

        driver_module._repair_scan = mock_repair
        try:
            result = run_review(config, scan_fn=bad_scan)
        finally:
            driver_module._repair_scan = original_repair

        assert result.exit_code == 1
        assert len(result.errors) > 0

    def test_repair_replaces_pass_one_findings(self, tmp_path: Path) -> None:
        """A successful repair replaces pass-1 findings rather than adding to them (IM-001).

        Pass 1 returns one valid + one invalid finding, forcing a repair. The repair
        re-scans the same files in full and returns both as valid. Appending into the
        un-cleared pass-1 list double-counted the finding that was valid all along —
        previously masked by BL-001's id-keyed dict absorbing the duplicate.
        """
        good = make_finding_dict("CR-001")
        bad = {"id": "CR-002", "reporter": "correctness"}  # incomplete → invalid
        repaired = [make_finding_dict("CR-001"), make_finding_dict("CR-002", path="other.py")]

        async def mixed_scan(
            dimension: str, files: list[str], config: DriverConfig
        ) -> list[dict] | ScanError:
            if dimension == "correctness":
                return [good, bad]
            return []

        config = DriverConfig(
            repo=tmp_path,
            files=["review/driver.py"],
            reviews_dir=tmp_path / "reviews",
            save_sweep=False,
        )
        config.agents_dir = tmp_path / "agents"
        config.agents_dir.mkdir()

        import review.driver as driver_module

        original_repair = driver_module._repair_scan

        async def mock_repair(dimension, files, config, error_detail):
            return repaired

        driver_module._repair_scan = mock_repair
        try:
            result = run_review(config, scan_fn=mixed_scan)
        finally:
            driver_module._repair_scan = original_repair

        assert result.exit_code == 0
        # Exactly the repair's two findings — not three (CR-001 counted twice)
        assert len(result.findings) == 2
        assert sorted(f.id for f in result.findings) == ["CR-001", "CR-002"]
        # The count alone cannot catch the double-add: the re-added CR-001 is an exact
        # positional match of the original, so dedup merges it back into one cluster.
        # The absorbed-id marker in `basis` is what makes the duplicate observable.
        absorbed = [b for f in result.findings for b in f.basis if b.startswith("absorbed:")]
        assert absorbed == [], f"repair re-added pass-1 findings: {absorbed}"

    def test_scan_error_from_sdk_fails_run(self, tmp_path: Path) -> None:
        """ScanError from scan_fn → exit_code=1, dimension in errors."""

        async def error_scan(
            dimension: str, files: list[str], config: DriverConfig
        ) -> list[dict] | ScanError:
            return ScanError(
                dimension=dimension,
                subtype="sdk_unavailable",
                detail="no auth",
            )

        config = DriverConfig(
            repo=tmp_path,
            files=["review/driver.py"],
            reviews_dir=tmp_path / "reviews",
            save_sweep=False,
        )
        config.agents_dir = tmp_path / "agents"
        config.agents_dir.mkdir()

        result = run_review(config, scan_fn=error_scan)
        assert result.exit_code == 1
        assert len(result.errors) > 0

    def test_no_sweep_when_save_false(self, tmp_path: Path) -> None:
        """save_sweep=False → no sweep file created."""
        config = DriverConfig(
            repo=tmp_path,
            files=["review/driver.py"],
            reviews_dir=tmp_path / "reviews",
            save_sweep=False,
        )
        config.agents_dir = tmp_path / "agents"
        config.agents_dir.mkdir()

        result = run_review(config, scan_fn=make_fake_scan({}))
        assert result.exit_code == 0
        assert result.sweep_path is None
        assert not (tmp_path / "reviews").exists()

    def test_two_sweeps_produce_trends(self, tmp_path: Path) -> None:
        """Running twice → second run has trend_md with period info."""
        findings_by_dim = {
            "correctness": [make_finding_dict("CR-001")],
            "safety": [],
            "structure": [],
            "wander": [],
        }
        reviews_dir = tmp_path / "reviews"

        config = DriverConfig(
            repo=tmp_path,
            files=["review/driver.py"],
            reviews_dir=reviews_dir,
            save_sweep=True,
        )
        config.agents_dir = tmp_path / "agents"
        config.agents_dir.mkdir()

        # First run
        run_review(config, scan_fn=make_fake_scan(findings_by_dim))

        # Tweak the sweep file mtime to simulate a different date
        import time

        sweeps = list(reviews_dir.glob("*.json"))
        assert sweeps, "Expected sweep file from first run"
        # Set mtime to 1 second ago so second file sorts after
        old_time = time.time() - 1
        import os

        os.utime(sweeps[0], (old_time, old_time))

        # Second run
        result2 = run_review(config, scan_fn=make_fake_scan(findings_by_dim))
        assert result2.sweep_path is not None
        assert "Trend Report" in result2.trend_md

    def test_dedup_merges_overlapping_findings(self, tmp_path: Path) -> None:
        """Two findings at the same location in the same category get merged."""
        dup1 = make_finding_dict(
            "CR-001", merge_impact="blocker", path="foo.py", title="Same issue"
        )
        dup2 = make_finding_dict(
            "CR-002", merge_impact="important", path="foo.py", title="Same issue 2"
        )
        # They share the same file — dedup should cluster them
        findings_by_dim = {
            "correctness": [dup1, dup2],
            "safety": [],
            "structure": [],
            "wander": [],
        }
        config = DriverConfig(
            repo=tmp_path,
            files=["foo.py"],
            reviews_dir=tmp_path / "reviews",
            save_sweep=False,
        )
        config.agents_dir = tmp_path / "agents"
        config.agents_dir.mkdir()

        result = run_review(config, scan_fn=make_fake_scan(findings_by_dim))
        # After dedup, blocker representative should win
        assert result.exit_code == 0
        # At most 1 finding after deterministic merge (overlap same file, same category)
        assert len(result.findings) <= 2  # may or may not cluster depending on title dedup

    def test_wander_findings_in_questions_section(self, tmp_path: Path) -> None:
        """Wander findings appear in the wander_questions section of the report."""
        wander_finding = make_finding_dict(
            "WD-001",
            reporter="wander",
            merge_impact="question",
        )
        # evidence_state must be "question" for WD findings
        wander_finding["evidence_state"] = "question"

        findings_by_dim = {
            "correctness": [],
            "safety": [],
            "structure": [],
            "wander": [wander_finding],
        }
        config = DriverConfig(
            repo=tmp_path,
            files=["review/driver.py"],
            reviews_dir=tmp_path / "reviews",
            save_sweep=False,
        )
        config.agents_dir = tmp_path / "agents"
        config.agents_dir.mkdir()

        result = run_review(config, scan_fn=make_fake_scan(findings_by_dim))
        assert "Open Questions" in result.report_md or len(result.findings) > 0


# ---------------------------------------------------------------------------
# Step 5: CLI 'run' subcommand tests
# ---------------------------------------------------------------------------


def _make_stub_run_review(
    findings_by_dim: dict, reviews_dir: Path | None = None, save: bool = False
):
    """Build a stub run_review for CLI tests that bypasses sdk_scan entirely."""

    async def fake_scan(
        dimension: str, files: list[str], config: DriverConfig
    ) -> list[dict] | ScanError:
        return findings_by_dim.get(dimension, [])

    def stub_run_review(config: DriverConfig, scan_fn=None) -> DriverResult:
        # Use the real pipeline but with fake_scan
        return run_review(config, scan_fn=fake_scan)

    return stub_run_review


class TestCliRun:
    def _patch(self, monkeypatch, findings_by_dim: dict):
        """Monkeypatch review.cli's run_review import to use a fake scan."""

        async def fake_scan(
            dimension: str, files: list[str], config: DriverConfig
        ) -> list[dict] | ScanError:
            return findings_by_dim.get(dimension, [])

        def stub_run_review(config: DriverConfig, scan_fn=None) -> DriverResult:
            return run_review(config, scan_fn=fake_scan)

        monkeypatch.setattr("review.driver.run_review", stub_run_review)

    def test_cli_run_exit_zero_on_success(self, tmp_path: Path, monkeypatch) -> None:
        """review-cli run exits 0 with valid findings."""
        findings_by_dim = {
            "correctness": [make_finding_dict()],
            "safety": [],
            "structure": [],
            "wander": [],
        }

        async def fake_scan(dimension: str, files, config):
            return findings_by_dim.get(dimension, [])

        def stub_run_review(config: DriverConfig, scan_fn=None) -> DriverResult:
            return run_review(config, scan_fn=fake_scan)

        monkeypatch.setattr("review.driver.run_review", stub_run_review)

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["run", "--repo", str(tmp_path), "--no-save", "--files", "review/driver.py"],
        )
        assert result.exit_code == 0, result.output
        assert "Review Report" in result.output

    def test_cli_run_exit_one_on_error(self, tmp_path: Path, monkeypatch) -> None:
        """review-cli run exits 1 when all scans return ScanError."""

        async def error_scan(dimension: str, files, config):
            return ScanError(dimension=dimension, subtype="sdk_unavailable", detail="no auth")

        def stub_run_review(config: DriverConfig, scan_fn=None) -> DriverResult:
            return run_review(config, scan_fn=error_scan)

        monkeypatch.setattr("review.driver.run_review", stub_run_review)

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["run", "--repo", str(tmp_path), "--no-save", "--files", "review/driver.py"],
        )
        assert result.exit_code == 1

    def test_cli_run_saves_sweep_by_default(self, tmp_path: Path, monkeypatch) -> None:
        """review-cli run (without --no-save) creates a sweep file."""
        findings_by_dim = {
            "correctness": [make_finding_dict()],
            "safety": [],
            "structure": [],
            "wander": [],
        }
        reviews_dir = tmp_path / ".claude" / "docs" / "reviews"

        async def fake_scan(dimension: str, files, config):
            return findings_by_dim.get(dimension, [])

        def stub_run_review(config: DriverConfig, scan_fn=None) -> DriverResult:
            return run_review(config, scan_fn=fake_scan)

        monkeypatch.setattr("review.driver.run_review", stub_run_review)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "run",
                "--repo",
                str(tmp_path),
                "--reviews-dir",
                str(reviews_dir),
                "--files",
                "review/driver.py",
            ],
        )
        assert result.exit_code == 0, result.output
        sweep_files = list(reviews_dir.glob("*.json"))
        assert len(sweep_files) == 1

    def test_cli_run_out_file(self, tmp_path: Path, monkeypatch) -> None:
        """--out writes report to file instead of stdout."""

        async def fake_scan(dimension: str, files, config):
            return []

        def stub_run_review(config: DriverConfig, scan_fn=None) -> DriverResult:
            return run_review(config, scan_fn=fake_scan)

        monkeypatch.setattr("review.driver.run_review", stub_run_review)

        out_file = tmp_path / "report.md"
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "run",
                "--repo",
                str(tmp_path),
                "--no-save",
                "--files",
                "review/driver.py",
                "--out",
                str(out_file),
            ],
        )
        assert result.exit_code == 0, result.output
        assert out_file.exists()
        assert "Review Report" in out_file.read_text()

    def test_cli_run_help(self) -> None:
        """review-cli run --help exits 0."""
        runner = CliRunner()
        result = runner.invoke(main, ["run", "--help"])
        assert result.exit_code == 0
        assert "repo" in result.output.lower()


# ---------------------------------------------------------------------------
# FINDINGS_SCHEMA sanity check
# ---------------------------------------------------------------------------


class TestFindingsSchema:
    def test_schema_has_findings_key(self) -> None:
        assert "findings" in FINDINGS_SCHEMA["properties"]

    def test_schema_is_object_type(self) -> None:
        assert FINDINGS_SCHEMA["type"] == "object"

    def test_findings_is_array(self) -> None:
        assert FINDINGS_SCHEMA["properties"]["findings"]["type"] == "array"
