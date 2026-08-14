"""Tests for review.dao.signals — deterministic agent-code detection."""

import json
import subprocess

from review.signals import (
    ALWAYS_ON_DIMENSIONS,
    CONDITIONAL_DIMENSIONS,
    active_dimensions,
    detect_signals,
)
from tests.review.conftest import REPO_ROOT


class TestDetectSignalsAgentCode:
    def test_path_in_agents_dir_triggers_agent_signal(self, tmp_path):
        f = tmp_path / "agents" / "foo.py"
        f.parent.mkdir()
        f.write_text("x = 1")
        signals = detect_signals([str(f)], repo_root=str(tmp_path))
        assert signals["is_agent_code"] is True

    def test_path_with_agent_suffix_triggers_signal(self, tmp_path):
        f = tmp_path / "my_agent" / "logic.py"
        f.parent.mkdir()
        f.write_text("x = 1")
        signals = detect_signals([str(f)], repo_root=str(tmp_path))
        assert signals["is_agent_code"] is True

    def test_anthropic_import_triggers_signal(self, tmp_path):
        f = tmp_path / "src" / "runner.py"
        f.parent.mkdir()
        f.write_text("from anthropic import Anthropic\n")
        signals = detect_signals([str(f)], repo_root=str(tmp_path))
        assert signals["is_agent_code"] is True

    def test_langgraph_import_triggers_signal(self, tmp_path):
        f = tmp_path / "src" / "graph.py"
        f.parent.mkdir()
        f.write_text("from langgraph.graph import StateGraph\n")
        signals = detect_signals([str(f)], repo_root=str(tmp_path))
        assert signals["is_agent_code"] is True

    def test_plain_python_no_agent_import_no_signal(self, tmp_path):
        f = tmp_path / "src" / "utils.py"
        f.parent.mkdir()
        f.write_text("def add(a, b): return a + b\n")
        signals = detect_signals([str(f)], repo_root=str(tmp_path))
        assert signals["is_agent_code"] is False

    def test_no_files_no_signals(self, tmp_path):
        signals = detect_signals([], repo_root=str(tmp_path))
        assert signals["is_agent_code"] is False
        assert signals["is_pipeline_code"] is False
        assert signals["has_sanyi_contracts"] is False


class TestDetectSignalsPipelineCode:
    def test_sql_file_triggers_pipeline_signal(self, tmp_path):
        f = tmp_path / "queries.sql"
        f.write_text("SELECT * FROM users;")
        signals = detect_signals([str(f)], repo_root=str(tmp_path))
        assert signals["is_pipeline_code"] is True

    def test_core_pipelines_path_triggers_signal(self, tmp_path):
        p = tmp_path / "core" / "pipelines" / "etl.py"
        p.parent.mkdir(parents=True)
        p.write_text("x = 1")
        signals = detect_signals([str(p)], repo_root=str(tmp_path))
        assert signals["is_pipeline_code"] is True

    def test_plain_python_no_pipeline_signal(self, tmp_path):
        f = tmp_path / "src" / "utils.py"
        f.parent.mkdir()
        f.write_text("def add(a, b): return a + b\n")
        signals = detect_signals([str(f)], repo_root=str(tmp_path))
        assert signals["is_pipeline_code"] is False


class TestDetectSignalsSanyi:
    def test_sanyi_md_in_root_triggers_signal(self, tmp_path):
        (tmp_path / "SANYI.md").write_text("# SANYI contracts\n")
        signals = detect_signals([], repo_root=str(tmp_path))
        assert signals["has_sanyi_contracts"] is True

    def test_sanyi_md_in_claude_dir_triggers_signal(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "SANYI.md").write_text("# SANYI contracts\n")
        signals = detect_signals([], repo_root=str(tmp_path))
        assert signals["has_sanyi_contracts"] is True

    def test_no_sanyi_md_no_signal(self, tmp_path):
        signals = detect_signals([], repo_root=str(tmp_path))
        assert signals["has_sanyi_contracts"] is False


NO_SIGNALS = {
    "is_agent_code": False,
    "is_pipeline_code": False,
    "is_ml_code": False,
    "has_sanyi_contracts": False,
}


class TestActiveDimensions:
    def test_no_signals_returns_base_dimensions(self):
        dims = active_dimensions(dict(NO_SIGNALS))
        assert set(dims) == set(ALWAYS_ON_DIMENSIONS)

    def test_agent_code_adds_runtime_and_safeguards(self):
        dims = active_dimensions({**NO_SIGNALS, "is_agent_code": True})
        assert "runtime" in dims
        assert "safeguards" in dims
        # Always-on still present
        assert set(ALWAYS_ON_DIMENSIONS).issubset(dims)

    def test_ml_code_adds_leakage(self):
        dims = active_dimensions({**NO_SIGNALS, "is_ml_code": True})
        assert "leakage" in dims

    def test_leakage_absent_without_ml_signal(self):
        assert "leakage" not in active_dimensions(dict(NO_SIGNALS))

    def test_sanyi_contracts_adds_contracts(self):
        dims = active_dimensions({**NO_SIGNALS, "has_sanyi_contracts": True})
        assert "contracts" in dims

    def test_all_conditionals_active(self):
        dims = active_dimensions(
            {
                **NO_SIGNALS,
                "is_agent_code": True,
                "is_ml_code": True,
                "has_sanyi_contracts": True,
            }
        )
        assert set(dims) == set(ALWAYS_ON_DIMENSIONS) | set(CONDITIONAL_DIMENSIONS)

    def test_registry_covers_eleven_dimensions(self):
        # The dimension vocabulary is reconciled with the galactus review-* family.
        assert len(set(ALWAYS_ON_DIMENSIONS) | set(CONDITIONAL_DIMENSIONS)) == 11

    def test_no_dimension_is_both_always_on_and_conditional(self):
        assert not set(ALWAYS_ON_DIMENSIONS) & set(CONDITIONAL_DIMENSIONS)


class TestDetectSignalsCLI:
    def test_cli_detect_signals_from_args(self, tmp_path):
        f = tmp_path / "agents" / "foo.py"
        f.parent.mkdir()
        f.write_text("x = 1")
        result = subprocess.run(
            ["uv", "run", "review-cli", "detect-signals", "--repo", str(tmp_path), str(f)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["signals"]["is_agent_code"] is True
        assert "runtime" in data["active_dimensions"]
        assert "safeguards" in data["active_dimensions"]

    def test_cli_detect_signals_from_stdin(self, tmp_path):
        f = tmp_path / "utils.py"
        f.write_text("def add(a, b): return a + b\n")
        payload = json.dumps([str(f)])
        result = subprocess.run(
            ["uv", "run", "review-cli", "detect-signals", "--repo", str(tmp_path)],
            input=payload,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["signals"]["is_agent_code"] is False
        assert "runtime" not in data["active_dimensions"]
        assert "safeguards" not in data["active_dimensions"]
        assert "correctness" in data["active_dimensions"]
