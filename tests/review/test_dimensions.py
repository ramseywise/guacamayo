"""Tests for dimension agent coverage and schema correctness.

The dimension set mirrors the ``review-*`` skill family in galactus, which is
canonical for dimension vocabulary (reconciled 2026-08-11: 5 → 11).

Validates:
- All 10 dimension agents have the required markdown files
- All 10 dimensions have a SKILL.md checklist
- Dimension reporter ID prefixes are enforced by the schema
- Cross-dimension deduplication works (same finding from 2 dimensions clusters)
- Wander agent markdown exists
- Shared scan SKILL.md exists
- Retired reporters carry no prefix constraint
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from review.deduplication import find_duplicate_clusters
from review.schemas.models import (
    DEPRECATED_REPORTERS,
    REPORTER_ID_PREFIX,
    Category,
    Reporter,
)
from tests.review.conftest import REPO_ROOT as _REPO_ROOT_STR
from tests.review.conftest import make_finding

REPO_ROOT = Path(_REPO_ROOT_STR)
SCAN_AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
SCAN_DIMS_DIR = REPO_ROOT / ".claude" / "skills"
WANDER_AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
SCAN_SHARED_DIR = REPO_ROOT / ".claude" / "skills" / "shared"

# The 10 finding-producing dimensions. `wander` is excluded — it emits questions,
# not findings, and is asserted separately in TestWanderAgent.
EXPECTED_DIMENSIONS = [
    "correctness",
    "intent",
    "architecture",
    "safety",
    "contracts",
    "testing",
    "runtime",
    "safeguards",
    "silent-failure",
    "leakage",
]

# Dimension → ID prefix. Single source of truth for the parametrized prefix tests.
DIMENSION_PREFIXES = {
    "correctness": "CR",
    "intent": "IN",
    "architecture": "AR",
    "safety": "SF",
    "contracts": "CT",
    "testing": "TE",
    "runtime": "RT",
    "safeguards": "SG",
    "silent-failure": "SI",
    "leakage": "LK",
}


class TestDimensionAgentMarkdowns:
    """Each dimension must have an agent markdown in .claude/agents/."""

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

    @pytest.mark.parametrize("dimension,prefix", sorted(DIMENSION_PREFIXES.items()))
    def test_agent_markdown_references_correct_prefix(self, dimension, prefix):
        agent_file = SCAN_AGENTS_DIR / f"{dimension}.md"
        content = agent_file.read_text()
        assert f"{prefix}-" in content, (
            f"{agent_file} must reference its ID prefix {prefix + '-'!r}"
        )


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

    @pytest.mark.parametrize("reporter,prefix", sorted(REPORTER_ID_PREFIX.items()))
    def test_correct_prefix_passes(self, reporter, prefix):
        f = make_finding(id=f"{prefix}-001", reporter=reporter)
        assert f.reporter == reporter

    @pytest.mark.parametrize("reporter,prefix", sorted(REPORTER_ID_PREFIX.items()))
    def test_wrong_prefix_rejected(self, reporter, prefix):
        # Any prefix that is not this reporter's own must be rejected.
        wrong_prefix = next(p for p in sorted(set(REPORTER_ID_PREFIX.values())) if p != prefix)
        with pytest.raises(ValidationError, match="requires id prefix"):
            make_finding(id=f"{wrong_prefix}-001", reporter=reporter)

    def test_every_dimension_has_a_distinct_prefix(self):
        prefixes = list(REPORTER_ID_PREFIX.values())
        assert len(prefixes) == len(set(prefixes)), f"duplicate ID prefixes: {prefixes}"

    def test_reporter_id_prefix_table_covers_all_dimension_reporters(self):
        dimension_reporters = {
            Reporter[dimension.replace("-", "_").upper()] for dimension in EXPECTED_DIMENSIONS
        } | {Reporter.WANDER}
        for reporter in dimension_reporters:
            assert reporter in REPORTER_ID_PREFIX, (
                f"REPORTER_ID_PREFIX missing entry for {reporter!r}"
            )

    def test_non_dimension_reporters_not_in_prefix_table(self):
        # Retired reporters (2026-08-11) plus the non-dimension ones. None carry a
        # prefix constraint — any valid ID format works.
        for reporter in (*DEPRECATED_REPORTERS, Reporter.LINT, Reporter.PLAN_FIDELITY):
            assert reporter not in REPORTER_ID_PREFIX

    def test_deprecated_reporters_still_deserialize(self):
        # Historical sweep records must keep parsing after the 2026-08-11 rename.
        for reporter in DEPRECATED_REPORTERS:
            f = make_finding(id="AK-001", reporter=reporter)
            assert f.reporter == reporter


class TestCrossDimensionDeduplication:
    """Same finding from two different dimension agents should cluster together."""

    def test_same_file_same_category_different_dimension_clusters(self):
        # Correctness and architecture both flag the same location on the same category
        f1 = make_finding(
            "CR-001",
            reporter=Reporter.CORRECTNESS,
            path="src/core.py",
            start_line=10,
            end_line=20,
            category=Category.CORRECTNESS,
        )
        f2 = make_finding(
            "AR-001",
            reporter=Reporter.ARCHITECTURE,
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
        # Safety and runtime both flag the same function
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
            "RT-001",
            reporter=Reporter.RUNTIME,
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
        # correctness, safety, architecture all flag the same location+category
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
                "AR-001",
                reporter=Reporter.ARCHITECTURE,
                path="src/x.py",
                start_line=10,
                end_line=25,
                category=Category.CORRECTNESS,
            ),
        ]
        clusters = find_duplicate_clusters(findings)
        assert len(clusters) == 1
        assert len(clusters[0]) == 3
