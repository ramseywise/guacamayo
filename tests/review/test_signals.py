"""Tests for review.dao.signals — deterministic agent-code detection."""

import json
import subprocess

from review.dao.signals import active_dimensions, detect_signals


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


class TestActiveDimensions:
    def test_no_signals_returns_base_dimensions(self):
        signals = {"is_agent_code": False, "is_pipeline_code": False, "has_sanyi_contracts": False}
        dims = active_dimensions(signals)
        assert set(dims) == {"correctness", "safety", "structure", "wander"}

    def test_agent_code_adds_agent_quality(self):
        signals = {"is_agent_code": True, "is_pipeline_code": False, "has_sanyi_contracts": False}
        dims = active_dimensions(signals)
        assert "agent-quality" in dims
        # Always-on still present
        assert "correctness" in dims
        assert "safety" in dims
        assert "structure" in dims
        assert "wander" in dims

    def test_sanyi_contracts_adds_contracts(self):
        signals = {"is_agent_code": False, "is_pipeline_code": False, "has_sanyi_contracts": True}
        dims = active_dimensions(signals)
        assert "contracts" in dims

    def test_both_conditionals_active(self):
        signals = {"is_agent_code": True, "is_pipeline_code": False, "has_sanyi_contracts": True}
        dims = active_dimensions(signals)
        assert "agent-quality" in dims
        assert "contracts" in dims
        assert len([d for d in dims if d in {"correctness", "safety", "structure", "wander"}]) == 4


class TestDetectSignalsCLI:
    def test_cli_detect_signals_from_args(self, tmp_path):
        f = tmp_path / "agents" / "foo.py"
        f.parent.mkdir()
        f.write_text("x = 1")
        result = subprocess.run(
            ["uv", "run", "review-cli", "detect-signals", "--repo", str(tmp_path), str(f)],
            capture_output=True,
            text=True,
            cwd="/Users/wiseer/workspace/guacamayo",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["signals"]["is_agent_code"] is True
        assert "agent-quality" in data["active_dimensions"]

    def test_cli_detect_signals_from_stdin(self, tmp_path):
        f = tmp_path / "utils.py"
        f.write_text("def add(a, b): return a + b\n")
        payload = json.dumps([str(f)])
        result = subprocess.run(
            ["uv", "run", "review-cli", "detect-signals", "--repo", str(tmp_path)],
            input=payload,
            capture_output=True,
            text=True,
            cwd="/Users/wiseer/workspace/guacamayo",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["signals"]["is_agent_code"] is False
        assert "agent-quality" not in data["active_dimensions"]
        assert "correctness" in data["active_dimensions"]
