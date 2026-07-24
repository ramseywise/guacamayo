import json
import subprocess

from review.deduplication import find_duplicate_clusters
from review.schemas.models import Category
from tests.review.conftest import make_finding


class TestDeduplication:
    def test_non_overlapping_stay_separate(self):
        f1 = make_finding("AK-001", path="a.py", start_line=1, end_line=5)
        f2 = make_finding("AK-002", path="b.py", start_line=1, end_line=5)
        clusters = find_duplicate_clusters([f1, f2])
        assert len(clusters) == 2

    def test_overlapping_lines_matching_category_clustered(self):
        f1 = make_finding("AK-001", path="a.py", start_line=1, end_line=10)
        f2 = make_finding("AK-002", path="a.py", start_line=8, end_line=15)
        clusters = find_duplicate_clusters([f1, f2])
        assert len(clusters) == 1
        assert len(clusters[0]) == 2

    def test_overlapping_lines_different_category_no_symbols_separate(self):
        f1 = make_finding(
            "AK-001", path="a.py", start_line=1, end_line=10, category=Category.CORRECTNESS
        )
        f2 = make_finding(
            "AK-002", path="a.py", start_line=8, end_line=15, category=Category.SECURITY
        )
        clusters = find_duplicate_clusters([f1, f2])
        assert len(clusters) == 2

    def test_matching_category_no_file_overlap_separate(self):
        f1 = make_finding("AK-001", path="a.py", start_line=1, end_line=5)
        f2 = make_finding("AK-002", path="a.py", start_line=100, end_line=110)
        clusters = find_duplicate_clusters([f1, f2])
        assert len(clusters) == 2

    def test_symbol_overlap_clusters_different_category(self):
        f1 = make_finding(
            "AK-001",
            path="a.py",
            start_line=1,
            end_line=10,
            category=Category.CORRECTNESS,
            symbols=["parse_config"],
        )
        f2 = make_finding(
            "AK-002",
            path="a.py",
            start_line=8,
            end_line=15,
            category=Category.SECURITY,
            symbols=["parse_config"],
        )
        clusters = find_duplicate_clusters([f1, f2])
        assert len(clusters) == 1

    def test_transitive_clustering(self):
        f1 = make_finding("AK-001", path="a.py", start_line=1, end_line=10)
        f2 = make_finding("AK-002", path="a.py", start_line=8, end_line=20)
        f3 = make_finding("AK-003", path="a.py", start_line=18, end_line=30)
        clusters = find_duplicate_clusters([f1, f2, f3])
        assert len(clusters) == 1
        assert len(clusters[0]) == 3

    def test_no_line_range_overlaps_whole_file(self):
        f1 = make_finding("AK-001", path="a.py", start_line=None, end_line=None)
        f2 = make_finding("AK-002", path="a.py", start_line=50, end_line=60)
        clusters = find_duplicate_clusters([f1, f2])
        assert len(clusters) == 1

    def test_all_findings_accounted_for(self):
        findings = [
            make_finding("AK-001", path="a.py", start_line=1, end_line=5),
            make_finding("AK-002", path="b.py", start_line=1, end_line=5),
            make_finding("AK-003", path="a.py", start_line=3, end_line=8),
        ]
        clusters = find_duplicate_clusters(findings)
        all_ids = {f.id for cluster in clusters for f in cluster}
        assert all_ids == {"AK-001", "AK-002", "AK-003"}

    def test_cli_dedup(self):
        f1 = make_finding("AK-001", path="a.py", start_line=1, end_line=10)
        f2 = make_finding("AK-002", path="a.py", start_line=8, end_line=15)
        data = json.dumps([f1.model_dump(mode="json"), f2.model_dump(mode="json")])
        result = subprocess.run(
            ["uv", "run", "review-cli", "dedup"],
            input=data,
            capture_output=True,
            text=True,
            cwd="/Users/wiseer/workspace/guacamayo",
        )
        assert result.returncode == 0
        clusters = json.loads(result.stdout)
        assert len(clusters) == 1
        assert set(clusters[0]) == {"AK-001", "AK-002"}
