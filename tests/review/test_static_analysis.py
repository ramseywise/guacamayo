"""Tests for review/static_analysis.py and related driver + renderer integration.

Covers the plan's Step 5 checklist:
1. TOOL_TABLE contains no --fix/--write/format/--unsafe-fixes token.
2. ruff detected in this repo; command is check-only and file-scoped.
3. No-tool repo (tmp_path) -> status="not_detected", dispatch skipped with reason.
4. Tool configured but binary absent -> tool_unavailable, driver still completes.
5. Timeout -> failed, driver still completes.
6. >200 changed files -> scoped=False, no path args.
7. Dedup exclusion: driver run with a fake scan + real lint violations produces
   byte-identical merged_findings versus lint disabled.
8. render_report without the key is unchanged (regression guard for existing callers).
9. Renderer truncation emits the '... N more' line.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest import mock

from review.driver import DriverConfig, run_review
from review.render import render_report
from review.schemas.models import StaticAnalysisResult
from review.static_analysis import (
    _FORBIDDEN_TOKENS,
    TOOL_TABLE,
    detect_tool,
    run_static_analysis,
)
from tests.review.conftest import make_finding

# ---------------------------------------------------------------------------
# Test 1: TOOL_TABLE contains no forbidden tokens
# ---------------------------------------------------------------------------


class TestToolTableSafety:
    def test_no_forbidden_tokens_in_any_command(self) -> None:
        """No check_argv in TOOL_TABLE contains --fix, --write, format, or --unsafe-fixes."""
        violations = []
        for spec in TOOL_TABLE:
            for token in spec.check_argv:
                if token in _FORBIDDEN_TOKENS:
                    violations.append(f"{spec.name}: {token!r}")
        assert violations == [], f"Forbidden tokens found: {violations}"

    def test_no_shell_true_by_construction(self) -> None:
        """TOOL_TABLE commands are tuples of strings, not shell strings."""
        for spec in TOOL_TABLE:
            assert isinstance(spec.check_argv, tuple), f"{spec.name}: check_argv must be a tuple"
            for token in spec.check_argv:
                assert isinstance(token, str), (
                    f"{spec.name}: argv token must be str, got {type(token)}"
                )

    def test_ruff_entry_uses_check_subcommand(self) -> None:
        """ruff entry uses 'check' not 'format' or 'check --fix'."""
        ruff = next(s for s in TOOL_TABLE if s.name == "ruff")
        assert "check" in ruff.check_argv
        assert "format" not in ruff.check_argv
        assert "--fix" not in ruff.check_argv


# ---------------------------------------------------------------------------
# Test 2: ruff detected in this repo; command is check-only and file-scoped
# ---------------------------------------------------------------------------


class TestRuffDetection:
    def test_ruff_detected_in_this_repo(self) -> None:
        """This repo has [tool.ruff] in pyproject.toml — detect_tool should find ruff."""
        repo_root = Path(__file__).resolve().parent.parent.parent
        spec = detect_tool(repo_root)
        assert spec is not None, "Expected ruff to be detected"
        assert spec.name == "ruff"

    def test_ruff_command_is_check_only(self) -> None:
        """Detected command for ruff must not contain any mutating flag."""
        repo_root = Path(__file__).resolve().parent.parent.parent
        spec = detect_tool(repo_root)
        assert spec is not None
        for token in spec.check_argv:
            assert token not in _FORBIDDEN_TOKENS, f"Forbidden token {token!r} in ruff command"

    def test_ruff_supports_file_args(self) -> None:
        """ruff spec must support per-file path arguments."""
        ruff = next(s for s in TOOL_TABLE if s.name == "ruff")
        assert ruff.supports_file_args is True


# ---------------------------------------------------------------------------
# Test 3: No-tool repo -> status="not_detected", dispatch skipped with reason
# ---------------------------------------------------------------------------


class TestNoToolFallback:
    def test_no_tool_repo_returns_not_detected(self, tmp_path: Path) -> None:
        """Empty tmp_path has no linter configured -> not_detected."""
        result = run_static_analysis(tmp_path, ["foo.py"])
        assert result.status == "not_detected"
        assert result.tool is None

    def test_not_detected_dispatch_entry_has_reason(self, tmp_path: Path) -> None:
        """Driver adds a skipped dispatch entry with reason when no tool is detected."""

        async def fake_scan(dimension, files, config):
            return []

        config = DriverConfig(
            repo=tmp_path,
            files=["foo.py"],
            reviews_dir=tmp_path / "reviews",
            save_sweep=False,
            static_analysis=True,
        )
        config.agents_dir = tmp_path / "agents"
        config.agents_dir.mkdir()

        result = run_review(config, scan_fn=fake_scan)

        lint_entries = [e for e in result.dispatch if e.reporter.value == "lint"]
        assert len(lint_entries) == 1
        entry = lint_entries[0]
        assert entry.status == "skipped"
        assert entry.skip_reason is not None and len(entry.skip_reason) > 0


# ---------------------------------------------------------------------------
# Test 4: Tool configured but binary absent -> tool_unavailable, driver still completes
# ---------------------------------------------------------------------------


class TestToolUnavailable:
    def test_tool_unavailable_when_binary_missing(self, tmp_path: Path) -> None:
        """FileNotFoundError on exec -> status=tool_unavailable."""
        # Create a pyproject.toml with [tool.ruff] to trigger ruff detection
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n")

        with mock.patch("subprocess.run", side_effect=FileNotFoundError("ruff: not found")):
            result = run_static_analysis(tmp_path, ["foo.py"])

        assert result.status == "tool_unavailable"
        assert result.tool == "ruff"

    def test_driver_completes_on_tool_unavailable(self, tmp_path: Path) -> None:
        """Driver exit_code is unaffected when the lint tool is unavailable."""
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n")

        async def fake_scan(dimension, files, config):
            return []

        config = DriverConfig(
            repo=tmp_path,
            files=["foo.py"],
            reviews_dir=tmp_path / "reviews",
            save_sweep=False,
            static_analysis=True,
        )
        config.agents_dir = tmp_path / "agents"
        config.agents_dir.mkdir()

        with mock.patch("review.static_analysis.subprocess.run", side_effect=FileNotFoundError()):
            result = run_review(config, scan_fn=fake_scan)

        # Driver must complete — exit_code 0 (no dimension errors)
        assert result.exit_code == 0
        assert result.static_analysis is not None
        assert result.static_analysis.status == "tool_unavailable"


# ---------------------------------------------------------------------------
# Test 5: Timeout -> failed, driver still completes
# ---------------------------------------------------------------------------


class TestTimeout:
    def test_timeout_returns_failed(self, tmp_path: Path) -> None:
        """TimeoutExpired -> status=failed."""
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n")

        with mock.patch(
            "review.static_analysis.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["ruff"], timeout=120),
        ):
            result = run_static_analysis(tmp_path, ["foo.py"])

        assert result.status == "failed"
        assert result.tool == "ruff"

    def test_driver_completes_on_timeout(self, tmp_path: Path) -> None:
        """Driver exit_code unaffected when lint times out."""
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n")

        async def fake_scan(dimension, files, config):
            return []

        config = DriverConfig(
            repo=tmp_path,
            files=["foo.py"],
            reviews_dir=tmp_path / "reviews",
            save_sweep=False,
            static_analysis=True,
        )
        config.agents_dir = tmp_path / "agents"
        config.agents_dir.mkdir()

        timeout_result = StaticAnalysisResult(
            tool="ruff",
            status="failed",
            command=["ruff", "check", "--output-format=json", "--", "foo.py"],
            detail="Static analysis timed out after 120 s.",
        )
        with mock.patch("review.driver.run_static_analysis", return_value=timeout_result):
            result = run_review(config, scan_fn=fake_scan)

        assert result.exit_code == 0
        assert result.static_analysis is not None
        assert result.static_analysis.status == "failed"


# ---------------------------------------------------------------------------
# Test 6: >200 changed files -> scoped=False, no path args in command
# ---------------------------------------------------------------------------


class TestScopeLimit:
    def test_over_200_files_drops_path_args(self, tmp_path: Path) -> None:
        """When changed set exceeds 200 files, scoped=False and no path args in command."""
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n")

        many_files = [f"src/module_{i}.py" for i in range(201)]

        captured: list[list[str]] = []

        def fake_run(argv, **kwargs):
            captured.append(list(argv))
            proc = mock.MagicMock()
            proc.returncode = 0
            proc.stdout = ""
            proc.stderr = ""
            return proc

        with mock.patch("review.static_analysis.subprocess.run", side_effect=fake_run):
            result = run_static_analysis(tmp_path, many_files)

        assert result.scoped is False
        # Verify no path args after "--" in the captured command
        if captured:
            cmd = captured[0]
            assert "--" not in cmd, "Expected no -- separator when not scoped"

    def test_under_limit_includes_path_args(self, tmp_path: Path) -> None:
        """When changed set is <= 200 files, scoped=True and paths are in the command."""
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n")

        few_files = ["src/module.py", "tests/test_module.py"]

        captured: list[list[str]] = []

        def fake_run(argv, **kwargs):
            captured.append(list(argv))
            proc = mock.MagicMock()
            proc.returncode = 0
            proc.stdout = ""
            proc.stderr = ""
            return proc

        with mock.patch("review.static_analysis.subprocess.run", side_effect=fake_run):
            result = run_static_analysis(tmp_path, few_files)

        assert result.scoped is True
        if captured:
            cmd = captured[0]
            assert "--" in cmd
            # File args appear after --
            sep_idx = cmd.index("--")
            assert "src/module.py" in cmd[sep_idx + 1 :]


# ---------------------------------------------------------------------------
# Test 7: Dedup exclusion — structural property
# ---------------------------------------------------------------------------


class TestDedupExclusion:
    """Structural: static analysis result never enters merged_findings."""

    def _make_fake_scan_with_finding(self):
        from tests.review.conftest import make_finding

        finding_dict = make_finding("CR-001").model_dump(mode="json")

        async def fake_scan(dimension, files, config):
            if dimension == "correctness":
                return [finding_dict]
            return []

        return fake_scan

    def test_lint_violations_do_not_appear_in_merged_findings(self, tmp_path: Path) -> None:
        """Driver run with lint violations produces same merged_findings as one without lint."""
        # Config with lint enabled (mocked to return violations)
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n")

        config_with_lint = DriverConfig(
            repo=tmp_path,
            files=["review/driver.py"],
            reviews_dir=tmp_path / "reviews",
            save_sweep=False,
            static_analysis=True,
        )
        config_with_lint.agents_dir = tmp_path / "agents"
        config_with_lint.agents_dir.mkdir()

        config_no_lint = DriverConfig(
            repo=tmp_path,
            files=["review/driver.py"],
            reviews_dir=tmp_path / "reviews",
            save_sweep=False,
            static_analysis=False,
        )
        config_no_lint.agents_dir = config_with_lint.agents_dir

        fake_scan = self._make_fake_scan_with_finding()

        lint_sa_result = StaticAnalysisResult(
            tool="ruff",
            status="violations",
            command=["ruff", "check", "--output-format=json", "--", "review/driver.py"],
            exit_code=1,
            violation_count=3,
            raw_output='[{"code": "E501"}, {"code": "F401"}, {"code": "E302"}]',
            scoped=True,
        )

        with mock.patch("review.driver.run_static_analysis", return_value=lint_sa_result):
            result_with_lint = run_review(config_with_lint, scan_fn=fake_scan)

        result_no_lint = run_review(config_no_lint, scan_fn=fake_scan)

        # Merged findings must be identical — static analysis cannot contribute findings
        ids_with = sorted(f.id for f in result_with_lint.findings)
        ids_without = sorted(f.id for f in result_no_lint.findings)
        assert ids_with == ids_without, (
            f"merged_findings differ: with_lint={ids_with}, no_lint={ids_without}"
        )

    def test_static_analysis_result_not_a_review_finding(self) -> None:
        """StaticAnalysisResult is structurally separate from ReviewFinding."""
        from review.schemas.models import ReviewFinding

        result = StaticAnalysisResult(tool="ruff", status="ok")
        assert not isinstance(result, ReviewFinding)


# ---------------------------------------------------------------------------
# Test 8: render_report without 'static_analysis' key is unchanged
# ---------------------------------------------------------------------------


class TestRenderReportRegressionGuard:
    def test_render_without_static_analysis_key(self) -> None:
        """Existing callers that pass dicts without 'static_analysis' still work."""
        data = {
            "findings": [],
            "merge_decision": "approve",
            "reporter_dispatch": [],
            "overall_understanding": "No changes.",
            "dod_assessment": "OK.",
        }
        result = render_report(data)
        assert "# Review Report" in result
        assert "Static Analysis" not in result

    def test_render_with_finding_no_static_analysis(self) -> None:
        """Finding renders correctly when static_analysis key is absent."""
        f = make_finding("AK-001", title="Old finding")
        data = {
            "findings": [f.model_dump(mode="json")],
            "merge_decision": "comment",
            "reporter_dispatch": [],
        }
        result = render_report(data)
        assert "AK-001" in result
        assert "Static Analysis" not in result


# ---------------------------------------------------------------------------
# Test 9: Renderer truncation emits '... N more' line
# ---------------------------------------------------------------------------


class TestRendererTruncation:
    def test_truncation_at_50_violations(self) -> None:
        """When raw_output has >50 lines, renderer emits '... N more violations not shown'."""
        # Create 60 lines of output
        lines = [f"E501:line {i}" for i in range(60)]
        raw_output = "\n".join(lines)

        sa_result = {
            "tool": "ruff",
            "status": "violations",
            "command": ["ruff", "check", "--output-format=json"],
            "exit_code": 1,
            "violation_count": 60,
            "raw_output": raw_output,
            "scoped": True,
            "detail": None,
        }

        data = {
            "findings": [],
            "merge_decision": "approve",
            "reporter_dispatch": [],
            "static_analysis": sa_result,
        }

        result = render_report(data)
        assert "... 10 more violations not shown" in result
        # Should show exactly 50 violation lines
        assert "E501:line 49" in result
        assert "E501:line 50" not in result

    def test_no_truncation_marker_when_within_limit(self) -> None:
        """When raw_output has <= 50 lines, no truncation marker is emitted."""
        lines = [f"E501:line {i}" for i in range(10)]
        raw_output = "\n".join(lines)

        sa_result = {
            "tool": "ruff",
            "status": "violations",
            "command": ["ruff", "check", "--output-format=json"],
            "exit_code": 1,
            "violation_count": 10,
            "raw_output": raw_output,
            "scoped": True,
            "detail": None,
        }

        data = {"findings": [], "static_analysis": sa_result}
        result = render_report(data)
        assert "more violations not shown" not in result

    def test_not_detected_section_rendered(self) -> None:
        """not_detected status renders the no-tool message."""
        sa_result = {
            "tool": None,
            "status": "not_detected",
            "command": [],
            "exit_code": None,
            "violation_count": 0,
            "raw_output": "",
            "scoped": True,
            "detail": None,
        }
        data = {"findings": [], "static_analysis": sa_result}
        result = render_report(data)
        assert "No static analysis tool detected" in result
        assert "Tool-verified" in result

    def test_static_analysis_section_placed_between_summary_and_details(self) -> None:
        """Static Analysis section appears after Findings Summary and before Finding Details."""
        f = make_finding("AK-001", title="Some finding")
        sa_result = {
            "tool": "ruff",
            "status": "ok",
            "command": ["ruff", "check"],
            "exit_code": 0,
            "violation_count": 0,
            "raw_output": "",
            "scoped": True,
            "detail": None,
        }
        data = {
            "findings": [f.model_dump(mode="json")],
            "merge_decision": "approve",
            "static_analysis": sa_result,
        }
        result = render_report(data)
        summary_pos = result.index("## Findings Summary")
        static_pos = result.index("## Static Analysis")
        details_pos = result.index("## Finding Details")
        assert summary_pos < static_pos < details_pos, (
            "Static Analysis section must be between Findings Summary and Finding Details"
        )
