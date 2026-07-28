"""Tests for review.dao.trends — trend computation and cross-repo tracking."""

from __future__ import annotations

import json

from review.dao.trends import (
    build_trend_report,
    compute_dimension_trends,
    direction_from_counts,
    render_trend_report,
)
from review.schemas.models import (
    DimensionTrend,
    SweepFinding,
    SweepRecord,
    TrendDirection,
    TrendReport,
)
from tests.review.conftest import REPO_ROOT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_sf(
    digest: str,
    category: str = "correctness",
    reporter: str = "akira_scan",
    title: str = "Test finding",
    merge_impact: str = "important",
    file_path: str = "src/foo.py",
    start_line: int | None = 1,
) -> SweepFinding:
    return SweepFinding(
        fingerprint=digest,
        finding_id="AK-001",
        file_path=file_path,
        start_line=start_line,
        category=category,
        reporter=reporter,
        title=title,
        merge_impact=merge_impact,
        evidence_state="verified",
    )


def make_record(repo: str, date: str, findings: list[SweepFinding]) -> SweepRecord:
    return SweepRecord(repo=repo, sweep_date=date, findings=findings)


# ---------------------------------------------------------------------------
# direction_from_counts
# ---------------------------------------------------------------------------


class TestDirectionFromCounts:
    def test_single_count_is_unknown(self):
        assert direction_from_counts([5]) == TrendDirection.UNKNOWN

    def test_empty_is_unknown(self):
        assert direction_from_counts([]) == TrendDirection.UNKNOWN

    def test_decreasing_is_improving(self):
        assert direction_from_counts([10, 5]) == TrendDirection.IMPROVING
        assert direction_from_counts([10, 7, 3]) == TrendDirection.IMPROVING

    def test_increasing_is_degrading(self):
        assert direction_from_counts([3, 7]) == TrendDirection.DEGRADING
        assert direction_from_counts([1, 3, 10]) == TrendDirection.DEGRADING

    def test_equal_first_last_is_stable(self):
        assert direction_from_counts([5, 5]) == TrendDirection.STABLE
        # Mid-point fluctuation doesn't change decision (only first vs last)
        assert direction_from_counts([5, 3, 5]) == TrendDirection.STABLE

    def test_two_counts_boundary(self):
        assert direction_from_counts([0, 0]) == TrendDirection.STABLE
        assert direction_from_counts([1, 0]) == TrendDirection.IMPROVING
        assert direction_from_counts([0, 1]) == TrendDirection.DEGRADING


# ---------------------------------------------------------------------------
# compute_dimension_trends
# ---------------------------------------------------------------------------


class TestComputeDimensionTrends:
    def test_single_sweep_gives_unknown_direction(self):
        sf = make_sf("a", category="correctness")
        sweep = make_record("r", "2026-01-01", [sf])
        trends = compute_dimension_trends([sweep], repo="r")
        assert len(trends) == 1
        assert trends[0].direction == TrendDirection.UNKNOWN

    def test_improving_trend(self):
        prev = make_record("r", "2026-01-01", [make_sf("a"), make_sf("b")])
        curr = make_record("r", "2026-01-02", [make_sf("c")])
        trends = compute_dimension_trends([prev, curr], repo="r")
        correctness = next(t for t in trends if t.dimension == "correctness")
        assert correctness.direction == TrendDirection.IMPROVING
        assert correctness.counts == [2, 1]

    def test_degrading_trend(self):
        prev = make_record("r", "2026-01-01", [make_sf("a")])
        curr = make_record("r", "2026-01-02", [make_sf("b"), make_sf("c")])
        trends = compute_dimension_trends([prev, curr], repo="r")
        correctness = next(t for t in trends if t.dimension == "correctness")
        assert correctness.direction == TrendDirection.DEGRADING
        assert correctness.counts == [1, 2]

    def test_stable_trend(self):
        prev = make_record("r", "2026-01-01", [make_sf("a")])
        curr = make_record("r", "2026-01-02", [make_sf("b")])
        trends = compute_dimension_trends([prev, curr], repo="r")
        correctness = next(t for t in trends if t.dimension == "correctness")
        assert correctness.direction == TrendDirection.STABLE

    def test_multiple_dimensions_tracked_separately(self):
        prev = make_record(
            "r",
            "2026-01-01",
            [make_sf("a", category="correctness"), make_sf("b", category="security")],
        )
        curr = make_record(
            "r",
            "2026-01-02",
            [make_sf("c", category="correctness")],
        )
        trends = compute_dimension_trends([prev, curr], repo="r")
        dims = {t.dimension: t for t in trends}
        assert "correctness" in dims
        assert "security" in dims
        # correctness: 1 → 1 → stable
        assert dims["correctness"].direction == TrendDirection.STABLE
        # security: 1 → 0 → improving
        assert dims["security"].direction == TrendDirection.IMPROVING
        assert dims["security"].counts == [1, 0]

    def test_dimension_absent_in_later_sweep_counts_zero(self):
        prev = make_record("r", "2026-01-01", [make_sf("a", category="security")])
        curr = make_record("r", "2026-01-02", [])
        trends = compute_dimension_trends([prev, curr], repo="r")
        security = next(t for t in trends if t.dimension == "security")
        assert security.counts == [1, 0]

    def test_repo_label_preserved(self):
        sweep = make_record("myrepo", "2026-01-01", [make_sf("x")])
        trends = compute_dimension_trends([sweep], repo="myrepo")
        assert all(t.repo == "myrepo" for t in trends)

    def test_empty_sweeps_returns_empty(self):
        trends = compute_dimension_trends([], repo="r")
        assert trends == []

    def test_three_sweep_trend_uses_full_series(self):
        s1 = make_record("r", "2026-01-01", [make_sf("a"), make_sf("b"), make_sf("c")])
        s2 = make_record("r", "2026-01-02", [make_sf("d"), make_sf("e")])
        s3 = make_record("r", "2026-01-03", [make_sf("f")])
        trends = compute_dimension_trends([s1, s2, s3], repo="r")
        correctness = next(t for t in trends if t.dimension == "correctness")
        assert correctness.counts == [3, 2, 1]
        assert correctness.direction == TrendDirection.IMPROVING

    def test_results_sorted_by_dimension_name(self):
        sfs = [
            make_sf("a", category="security"),
            make_sf("b", category="architecture"),
            make_sf("c", category="correctness"),
        ]
        sweep = make_record("r", "2026-01-01", sfs)
        trends = compute_dimension_trends([sweep], repo="r")
        names = [t.dimension for t in trends]
        assert names == sorted(names)


# ---------------------------------------------------------------------------
# build_trend_report
# ---------------------------------------------------------------------------


class TestBuildTrendReport:
    def test_basic_structure(self):
        sf_old = make_sf("old")
        sf_new = make_sf("new")
        prev = make_record("r", "2026-01-01", [sf_old])
        curr = make_record("r", "2026-01-02", [sf_new])
        report = build_trend_report(prev, curr)
        assert isinstance(report, TrendReport)
        assert report.repo == "r"
        assert report.from_date == "2026-01-01"
        assert report.to_date == "2026-01-02"

    def test_new_resolved_recurring_populated(self):
        sf_shared = make_sf("shared")
        sf_gone = make_sf("gone")
        sf_arrived = make_sf("arrived")
        prev = make_record("r", "2026-01-01", [sf_shared, sf_gone])
        curr = make_record("r", "2026-01-02", [sf_shared, sf_arrived])
        report = build_trend_report(prev, curr)
        assert {f.fingerprint for f in report.new_findings} == {"arrived"}
        assert {f.fingerprint for f in report.resolved_findings} == {"gone"}
        assert {f.fingerprint for f in report.recurring_findings} == {"shared"}

    def test_dimension_trends_included(self):
        prev = make_record("r", "2026-01-01", [make_sf("a"), make_sf("b")])
        curr = make_record("r", "2026-01-02", [make_sf("c")])
        report = build_trend_report(prev, curr)
        assert len(report.dimension_trends) >= 1
        assert any(t.dimension == "correctness" for t in report.dimension_trends)

    def test_cross_repo_tracking(self):
        # Each repo is tracked independently; trends are labelled by repo
        sf_r1 = make_sf("r1-a")
        sf_r2 = make_sf("r2-a")
        prev_r1 = make_record("repo1", "2026-01-01", [sf_r1, sf_r1])
        curr_r1 = make_record("repo1", "2026-01-02", [sf_r1])
        report_r1 = build_trend_report(prev_r1, curr_r1)

        prev_r2 = make_record("repo2", "2026-01-01", [sf_r2])
        curr_r2 = make_record("repo2", "2026-01-02", [sf_r2, sf_r2])
        report_r2 = build_trend_report(prev_r2, curr_r2)

        # repo1 improving (2 → 1), repo2 degrading (1 → 2)
        r1_trend = next(t for t in report_r1.dimension_trends if t.dimension == "correctness")
        r2_trend = next(t for t in report_r2.dimension_trends if t.dimension == "correctness")
        assert r1_trend.direction == TrendDirection.IMPROVING
        assert r2_trend.direction == TrendDirection.DEGRADING
        assert r1_trend.repo == "repo1"
        assert r2_trend.repo == "repo2"


# ---------------------------------------------------------------------------
# render_trend_report
# ---------------------------------------------------------------------------


class TestRenderTrendReport:
    def test_contains_repo_name(self):
        report = TrendReport(
            repo="myrepo",
            from_date="2026-01-01",
            to_date="2026-01-02",
        )
        md = render_trend_report(report)
        assert "myrepo" in md

    def test_contains_period_dates(self):
        report = TrendReport(
            repo="r",
            from_date="2026-01-01",
            to_date="2026-01-02",
        )
        md = render_trend_report(report)
        assert "2026-01-01" in md
        assert "2026-01-02" in md

    def test_new_findings_listed(self):
        sf = make_sf("abc", title="Bug found")
        report = TrendReport(
            repo="r",
            from_date="2026-01-01",
            to_date="2026-01-02",
            new_findings=[sf],
        )
        md = render_trend_report(report)
        assert "Bug found" in md
        assert "New findings" in md

    def test_resolved_findings_listed(self):
        sf = make_sf("abc", title="Fixed bug")
        report = TrendReport(
            repo="r",
            from_date="2026-01-01",
            to_date="2026-01-02",
            resolved_findings=[sf],
        )
        md = render_trend_report(report)
        assert "Fixed bug" in md
        assert "Resolved findings" in md

    def test_dimension_trends_table(self):
        trend = DimensionTrend(
            dimension="correctness",
            repo="r",
            counts=[3, 1],
            direction=TrendDirection.IMPROVING,
        )
        report = TrendReport(
            repo="r",
            from_date="2026-01-01",
            to_date="2026-01-02",
            dimension_trends=[trend],
        )
        md = render_trend_report(report)
        assert "correctness" in md
        assert "improving" in md
        assert "3" in md
        assert "1" in md

    def test_no_findings_shows_none(self):
        report = TrendReport(repo="r", from_date="2026-01-01", to_date="2026-01-02")
        md = render_trend_report(report)
        assert "None" in md


# ---------------------------------------------------------------------------
# CLI integration — trends command
# ---------------------------------------------------------------------------


class TestTrendsCLI:
    def _write_sweep(self, tmp_path, repo: str, date: str, findings: list[SweepFinding]):
        import time

        record = SweepRecord(repo=repo, sweep_date=date, findings=findings)
        path = tmp_path / f"{repo}-{date}.json"
        path.write_text(record.model_dump_json(indent=2))
        time.sleep(0.02)  # ensure mtime ordering
        return path

    def test_trends_cmd_markdown_output(self, tmp_path):
        import subprocess

        sf_old = make_sf("digest_old", title="Old bug")
        sf_new = make_sf("digest_new", title="New bug")
        prev_path = self._write_sweep(tmp_path, "testrepo", "2026-01-01", [sf_old])
        curr_path = self._write_sweep(tmp_path, "testrepo", "2026-01-02", [sf_new])

        result = subprocess.run(
            [
                "uv",
                "run",
                "review-cli",
                "trends",
                "--repo",
                "testrepo",
                "--previous",
                str(prev_path),
                "--current",
                str(curr_path),
                "--format",
                "markdown",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, result.stderr
        assert "testrepo" in result.stdout
        assert "New bug" in result.stdout
        assert "Old bug" in result.stdout

    def test_trends_cmd_json_output(self, tmp_path):
        import subprocess

        sf_old = make_sf("digest_a", title="A")
        sf_new = make_sf("digest_b", title="B")
        prev_path = self._write_sweep(tmp_path, "testrepo", "2026-01-01", [sf_old])
        curr_path = self._write_sweep(tmp_path, "testrepo", "2026-01-02", [sf_new])

        result = subprocess.run(
            [
                "uv",
                "run",
                "review-cli",
                "trends",
                "--repo",
                "testrepo",
                "--previous",
                str(prev_path),
                "--current",
                str(curr_path),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["repo"] == "testrepo"
        assert "new_findings" in data
        assert "resolved_findings" in data
        assert "recurring_findings" in data
        assert "dimension_trends" in data

    def test_trends_cmd_auto_detect_sweeps(self, tmp_path):
        import subprocess

        sf_old = make_sf("digest_x")
        sf_new = make_sf("digest_y")
        self._write_sweep(tmp_path, "myrepo", "2026-01-01", [sf_old])
        self._write_sweep(tmp_path, "myrepo", "2026-01-02", [sf_new])

        result = subprocess.run(
            [
                "uv",
                "run",
                "review-cli",
                "trends",
                "--repo",
                "myrepo",
                "--reviews-dir",
                str(tmp_path),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["repo"] == "myrepo"

    def test_trends_cmd_fails_with_single_sweep(self, tmp_path):
        import subprocess

        sf = make_sf("only_one")
        self._write_sweep(tmp_path, "myrepo", "2026-01-01", [sf])

        result = subprocess.run(
            [
                "uv",
                "run",
                "review-cli",
                "trends",
                "--repo",
                "myrepo",
                "--reviews-dir",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode != 0
        assert "at least 2" in result.stderr
