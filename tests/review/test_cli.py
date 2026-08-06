"""Tests for review/cli.py — Step 4 coverage (GUA-96).

Covers the `verdict` subcommand (the single verdict entry point for skills)
and `run --report-json` (machine-readable ReviewReport artifact).
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from review.cli import main
from review.driver import DriverConfig, DriverResult, run_review
from review.schemas.models import ReviewReport


def finding_dict(
    id: str = "CR-001",
    reporter: str = "correctness",
    merge_impact: str = "important",
    comment_type: str = "request_change",
) -> dict:
    return {
        "id": id,
        "reporter": reporter,
        "category": "correctness",
        "evidence_state": "verified",
        "location": {"files": [{"path": "review/driver.py", "start_line": 1}], "symbols": []},
        "claim": {"title": "Test finding", "observation": "observed"},
        "severity": {"merge_impact": merge_impact},
        "comment_type": comment_type,
        "basis": [],
    }


class TestVerdictCmd:
    def test_empty_findings_prints_approve(self) -> None:
        """echo '[]' | review-cli verdict → approve (plan done-when)."""
        runner = CliRunner()
        result = runner.invoke(main, ["verdict"], input="[]")
        assert result.exit_code == 0, result.output
        assert result.output.strip() == "approve"

    def test_blocker_prints_request_changes(self, tmp_path: Path) -> None:
        """A blocker finding yields request_changes."""
        fixture = tmp_path / "findings.json"
        fixture.write_text(json.dumps([finding_dict(merge_impact="blocker")]))

        runner = CliRunner()
        result = runner.invoke(main, ["verdict", str(fixture)])
        assert result.exit_code == 0, result.output
        assert result.output.strip() == "request_changes"

    def test_dispatch_failed_prints_insufficient_context(self) -> None:
        """--dispatch-failed forces insufficient_context regardless of findings."""
        runner = CliRunner()
        result = runner.invoke(main, ["verdict", "--dispatch-failed"], input="[]")
        assert result.exit_code == 0, result.output
        assert result.output.strip() == "insufficient_context"

    def test_invalid_finding_exits_nonzero(self) -> None:
        """A finding that fails ReviewFinding validation exits non-zero."""
        runner = CliRunner()
        result = runner.invoke(main, ["verdict"], input='[{"id": "bad"}]')
        assert result.exit_code == 1
        assert "error:" in result.output

    def test_non_array_input_exits_nonzero(self) -> None:
        """A JSON object (not array) exits non-zero with a clear message."""
        runner = CliRunner()
        result = runner.invoke(main, ["verdict"], input='{"findings": []}')
        assert result.exit_code == 1
        assert "JSON array" in result.output


class TestRunReportJson:
    def test_report_json_written(self, tmp_path: Path, monkeypatch) -> None:
        """run --report-json writes a validated ReviewReport with the merge decision."""
        findings_by_dim = {"correctness": [finding_dict()]}

        async def fake_scan(dimension: str, files, config):
            return findings_by_dim.get(dimension, [])

        def stub_run_review(config: DriverConfig, scan_fn=None) -> DriverResult:
            return run_review(config, scan_fn=fake_scan)

        monkeypatch.setattr("review.driver.run_review", stub_run_review)

        report_path = tmp_path / "report.json"
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
                "--report-json",
                str(report_path),
            ],
        )
        assert result.exit_code == 0, result.output
        assert report_path.exists()

        report = ReviewReport.model_validate_json(report_path.read_text())
        assert report.merge_decision.value == "comment"
        assert len(report.findings) == 1
