import subprocess

from review.deduplication import find_duplicate_clusters
from review.validation import validate_finding
from tests.review.conftest import make_finding


class TestFullPipeline:
    def test_validate_then_dedup(self):
        f1 = make_finding("AK-001", path="src/main.py", start_line=1, end_line=10)
        f2 = make_finding(
            "SY-001",
            reporter="sanyi",
            path="src/main.py",
            start_line=5,
            end_line=15,
        )
        for f in [f1, f2]:
            ok, err = validate_finding(f.model_dump(mode="json"))
            assert ok, err

        clusters = find_duplicate_clusters([f1, f2])
        assert len(clusters) >= 1
        all_ids = {f.id for c in clusters for f in c}
        assert all_ids == {"AK-001", "SY-001"}

    def test_non_overlapping_findings_separate_clusters(self):
        f1 = make_finding("AK-001", path="a.py", start_line=1, end_line=5)
        f2 = make_finding("SY-001", path="b.py", start_line=100, end_line=110)
        for f in [f1, f2]:
            ok, err = validate_finding(f.model_dump(mode="json"))
            assert ok, err

        clusters = find_duplicate_clusters([f1, f2])
        assert len(clusters) == 2


class TestCLIInstalled:
    def test_version(self):
        result = subprocess.run(
            ["uv", "run", "review-cli", "--version"],
            capture_output=True,
            text=True,
            cwd="/Users/wiseer/workspace/guacamayo",
        )
        assert result.returncode == 0
        assert "0.1.0" in result.stdout

    def test_help_shows_all_subcommands(self):
        result = subprocess.run(
            ["uv", "run", "review-cli", "--help"],
            capture_output=True,
            text=True,
            cwd="/Users/wiseer/workspace/guacamayo",
        )
        assert result.returncode == 0
        for cmd in ["validate-finding", "validate-report", "dedup", "verify-commits"]:
            assert cmd in result.stdout, f"missing subcommand: {cmd}"
