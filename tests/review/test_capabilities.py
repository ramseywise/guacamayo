"""Tests for review/capabilities.py — capability advisor resolution.

The point of this module is that a dispatch which never happened must be
distinguishable from one that ran and found nothing, so every failure mode has to
resolve False *with a reason*, and the CLI has to exit non-zero.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from review.capabilities import CAPABILITY_AGENT, resolve_capability_agent
from review.cli import main


def _write_agent(repo: Path, name: str, stem: str = "fog-advisor") -> None:
    agents = repo / ".claude" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / f"{stem}.md").write_text(f"---\nname: {name}\nmodel: haiku\n---\nBody.\n")


class TestResolveCapabilityAgent:
    def test_resolves_when_agent_present_and_named(self, tmp_path: Path) -> None:
        _write_agent(tmp_path, "fog-advisor")
        result = resolve_capability_agent("fog", repo_root=tmp_path)
        assert result["resolved"] is True
        assert result["agent"] == ".claude/agents/fog-advisor.md"
        assert result["reason"] == ""

    def test_unregistered_capability_does_not_resolve(self, tmp_path: Path) -> None:
        result = resolve_capability_agent("not-a-capability", repo_root=tmp_path)
        assert result["resolved"] is False
        assert result["agent"] is None
        assert "no registered agent" in result["reason"]

    def test_missing_agent_file_does_not_resolve(self, tmp_path: Path) -> None:
        result = resolve_capability_agent("fog", repo_root=tmp_path)
        assert result["resolved"] is False
        assert "not found" in result["reason"]

    def test_missing_frontmatter_does_not_resolve(self, tmp_path: Path) -> None:
        agents = tmp_path / ".claude" / "agents"
        agents.mkdir(parents=True)
        (agents / "fog-advisor.md").write_text("No frontmatter here.\n")
        result = resolve_capability_agent("fog", repo_root=tmp_path)
        assert result["resolved"] is False
        assert "front matter" in result["reason"]

    def test_absent_name_field_does_not_resolve(self, tmp_path: Path) -> None:
        agents = tmp_path / ".claude" / "agents"
        agents.mkdir(parents=True)
        (agents / "fog-advisor.md").write_text("---\nmodel: haiku\n---\nBody.\n")
        result = resolve_capability_agent("fog", repo_root=tmp_path)
        assert result["resolved"] is False
        assert "declares no `name:`" in result["reason"]

    def test_name_mismatch_does_not_resolve(self, tmp_path: Path) -> None:
        """A file that parses but registers under another name is a substitution.

        This is the subtle case: the dispatch names `fog-advisor`, the file loads,
        but it registers as something else — so the advisor that answers is not the
        one that was asked for.
        """
        _write_agent(tmp_path, "some-other-agent")
        result = resolve_capability_agent("fog", repo_root=tmp_path)
        assert result["resolved"] is False
        assert "registers as 'some-other-agent'" in result["reason"]

    @pytest.mark.parametrize("capability", sorted(CAPABILITY_AGENT))
    def test_registered_capabilities_resolve_in_real_repo(self, capability: str) -> None:
        repo_root = Path(__file__).resolve().parent.parent.parent
        result = resolve_capability_agent(capability, repo_root=repo_root)
        assert result["resolved"] is True, result["reason"]


class TestResolveCapabilityCLI:
    def test_exit_zero_when_resolved(self, tmp_path: Path) -> None:
        _write_agent(tmp_path, "fog-advisor")
        result = CliRunner().invoke(main, ["resolve-capability", "fog", "--repo", str(tmp_path)])
        assert result.exit_code == 0
        assert '"resolved": true' in result.output

    def test_exit_one_when_unresolved(self, tmp_path: Path) -> None:
        """Stage 4 reads the exit code to tell a hole from a clean pass."""
        result = CliRunner().invoke(main, ["resolve-capability", "fog", "--repo", str(tmp_path)])
        assert result.exit_code == 1
        assert '"resolved": false' in result.output
