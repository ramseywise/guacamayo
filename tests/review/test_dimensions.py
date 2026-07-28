"""Tests for Phase 2 dimension agent coverage and schema correctness.

Validates:
- All 5 dimension agents have the required markdown files
- All 5 dimensions have a SKILL.md checklist
- Dimension reporter ID prefixes are enforced by the schema
- Cross-dimension deduplication works (same finding from 2 dimensions clusters)
- Wander agent markdown exists
- Shared scan SKILL.md exists
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from review.dao.deduplication import find_duplicate_clusters
from review.schemas.models import (
    REPORTER_ID_PREFIX,
    Category,
    Reporter,
)
from tests.review.conftest import make_finding

REPO_ROOT = Path("/Users/wiseer/workspace/guacamayo")
SCAN_AGENTS_DIR = REPO_ROOT / "review" / "scan" / "agents"
SCAN_DIMS_DIR = REPO_ROOT / "review" / "scan" / "dimensions"
WANDER_AGENTS_DIR = REPO_ROOT / "review" / "wander" / "agents"
SCAN_SHARED_DIR = REPO_ROOT / "review" / "scan" / "shared"

EXPECTED_DIMENSIONS = ["correctness", "safety", "structure", "agent-quality", "contracts"]


class TestDimensionAgentMarkdowns:
    """Each dimension must have an agent markdown in review/scan/agents/."""

    @pytest.mark.parametrize("dimension", EXPECTED_DIMENSIONS)
    def test_agent_markdown_exists(self, dimension):
        agent_file = SCAN_AGENTS_DIR / f"{dimension}.md"
        assert agent_file.exists(), f"Missing agent markdown: {agent_file}"

    @pytest.mark.parametrize("dimension", EXPECTED_DIMENSIONS)
    def test_agent_markdown_has_frontmatter(self, dimension):
        agent_file = SCAN_AGENTS_DIR / f"{dimension}.md"
        content = agent_file.read_text()
        assert content.startswith("---"), f"{agent_file} must start with YAML frontmatter"
        assert "name:" in content
        assert "tools:" in content
        assert "model:" in content

    @pytest.mark.parametrize(
        "dimension,prefix",
        [
            ("correctness", "CR-"),
            ("safety", "SF-"),
            ("structure", "ST-"),
            ("agent-quality", "AQ-"),
            ("contracts", "CT-"),
        ],
    )
    def test_agent_markdown_references_correct_prefix(self, dimension, prefix):
        agent_file = SCAN_AGENTS_DIR / f"{dimension}.md"
        content = agent_file.read_text()
        assert prefix in content, f"{agent_file} must reference its ID prefix {prefix!r}"


class TestDimensionSkillChecklists:
    """Each dimension must have a SKILL.md checklist."""

    @pytest.mark.parametrize("dimension", EXPECTED_DIMENSIONS)
    def test_skill_md_exists(self, dimension):
        skill_file = SCAN_DIMS_DIR / dimension / "SKILL.md"
        assert skill_file.exists(), f"Missing dimension checklist: {skill_file}"

    @pytest.mark.parametrize("dimension", EXPECTED_DIMENSIONS)
    def test_skill_md_references_agent(self, dimension):
        skill_file = SCAN_DIMS_DIR / dimension / "SKILL.md"
        content = skill_file.read_text()
        # Each SKILL.md should reference its agent name or the dimension name
        assert dimension in content.lower(), (
            f"{skill_file} should reference its dimension {dimension!r}"
        )


class TestWanderAgent:
    def test_wander_agent_markdown_exists(self):
        wander_file = WANDER_AGENTS_DIR / "wander.md"
        assert wander_file.exists(), f"Missing wander agent: {wander_file}"

    def test_wander_agent_has_frontmatter(self):
        wander_file = WANDER_AGENTS_DIR / "wander.md"
        content = wander_file.read_text()
        assert content.startswith("---")
        assert "name:" in content
        assert "WD-" in content

    def test_wander_agent_references_question_impact(self):
        wander_file = WANDER_AGENTS_DIR / "wander.md"
        content = wander_file.read_text()
        assert "question" in content


class TestSharedScanSkill:
    def test_shared_skill_md_exists(self):
        shared_file = SCAN_SHARED_DIR / "SKILL.md"
        assert shared_file.exists(), f"Missing shared scan SKILL.md: {shared_file}"

    def test_shared_skill_references_all_dimensions(self):
        shared_file = SCAN_SHARED_DIR / "SKILL.md"
        content = shared_file.read_text()
        for dim in EXPECTED_DIMENSIONS:
            assert dim in content, f"shared/SKILL.md must reference dimension {dim!r}"


class TestDimensionReporterPrefixes:
    """Schema enforces ID prefixes match dimension reporters."""

    @pytest.mark.parametrize(
        "reporter,prefix",
        [
            (Reporter.CORRECTNESS, "CR"),
            (Reporter.SAFETY, "SF"),
            (Reporter.STRUCTURE, "ST"),
            (Reporter.AGENT_QUALITY, "AQ"),
            (Reporter.CONTRACTS, "CT"),
            (Reporter.WANDER, "WD"),
        ],
    )
    def test_correct_prefix_passes(self, reporter, prefix):
        f = make_finding(id=f"{prefix}-001", reporter=reporter)
        assert f.reporter == reporter

    @pytest.mark.parametrize(
        "reporter,wrong_prefix",
        [
            (Reporter.CORRECTNESS, "SF"),
            (Reporter.SAFETY, "CR"),
            (Reporter.STRUCTURE, "AQ"),
            (Reporter.AGENT_QUALITY, "CT"),
            (Reporter.CONTRACTS, "ST"),
            (Reporter.WANDER, "AK"),
        ],
    )
    def test_wrong_prefix_rejected(self, reporter, wrong_prefix):
        with pytest.raises(ValidationError, match="requires id prefix"):
            make_finding(id=f"{wrong_prefix}-001", reporter=reporter)

    def test_reporter_id_prefix_table_covers_all_dimension_reporters(self):
        dimension_reporters = {
            Reporter.CORRECTNESS,
            Reporter.SAFETY,
            Reporter.STRUCTURE,
            Reporter.AGENT_QUALITY,
            Reporter.CONTRACTS,
            Reporter.WANDER,
        }
        for reporter in dimension_reporters:
            assert reporter in REPORTER_ID_PREFIX, (
                f"REPORTER_ID_PREFIX missing entry for {reporter!r}"
            )

    def test_legacy_reporters_not_in_prefix_table(self):
        legacy = [
            Reporter.AKIRA_SCAN,
            Reporter.AKIRA_WANDER,
            Reporter.SANYI,
            Reporter.LINT,
            Reporter.PLAN_FIDELITY,
        ]
        for reporter in legacy:
            # Legacy reporters have no prefix constraint — any valid ID format works
            assert reporter not in REPORTER_ID_PREFIX


class TestCrossDimensionDeduplication:
    """Same finding from two different dimension agents should cluster together."""

    def test_same_file_same_category_different_dimension_clusters(self):
        # Correctness and structure both flag the same location on the same category
        f1 = make_finding(
            "CR-001",
            reporter=Reporter.CORRECTNESS,
            path="src/core.py",
            start_line=10,
            end_line=20,
            category=Category.CORRECTNESS,
        )
        f2 = make_finding(
            "ST-001",
            reporter=Reporter.STRUCTURE,
            path="src/core.py",
            start_line=12,
            end_line=18,
            category=Category.CORRECTNESS,
        )
        clusters = find_duplicate_clusters([f1, f2])
        assert len(clusters) == 1
        assert len(clusters[0]) == 2

    def test_different_files_different_dimensions_stay_separate(self):
        f1 = make_finding(
            "CR-001",
            reporter=Reporter.CORRECTNESS,
            path="src/a.py",
            start_line=1,
            end_line=10,
        )
        f2 = make_finding(
            "SF-001",
            reporter=Reporter.SAFETY,
            path="src/b.py",
            start_line=1,
            end_line=10,
        )
        clusters = find_duplicate_clusters([f1, f2])
        assert len(clusters) == 2

    def test_cross_dimension_symbol_overlap_clusters(self):
        # Safety and agent-quality both flag the same function
        f1 = make_finding(
            "SF-001",
            reporter=Reporter.SAFETY,
            path="agents/runner.py",
            start_line=1,
            end_line=20,
            symbols=["run_agent"],
            category=Category.SECURITY,
        )
        f2 = make_finding(
            "AQ-001",
            reporter=Reporter.AGENT_QUALITY,
            path="agents/runner.py",
            start_line=5,
            end_line=15,
            symbols=["run_agent"],
            category=Category.AGENT_BEHAVIOR,
        )
        clusters = find_duplicate_clusters([f1, f2])
        # Symbol overlap should cluster them regardless of different categories
        assert len(clusters) == 1

    def test_three_dimension_findings_all_cluster(self):
        # correctness, safety, structure all flag the same location+category
        findings = [
            make_finding(
                "CR-001",
                reporter=Reporter.CORRECTNESS,
                path="src/x.py",
                start_line=1,
                end_line=15,
                category=Category.CORRECTNESS,
            ),
            make_finding(
                "SF-001",
                reporter=Reporter.SAFETY,
                path="src/x.py",
                start_line=5,
                end_line=20,
                category=Category.CORRECTNESS,
            ),
            make_finding(
                "ST-001",
                reporter=Reporter.STRUCTURE,
                path="src/x.py",
                start_line=10,
                end_line=25,
                category=Category.CORRECTNESS,
            ),
        ]
        clusters = find_duplicate_clusters(findings)
        assert len(clusters) == 1
        assert len(clusters[0]) == 3
