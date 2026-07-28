"""Trend tracking — finding counts over time per dimension per repo.

Public API
----------
compute_dimension_trends(sweeps, repo) -> list[DimensionTrend]
    Given an ordered list of SweepRecords (oldest first), compute per-dimension
    trend direction for a single repo.

build_trend_report(previous, current) -> TrendReport
    Full diff: new / resolved / recurring + dimension trends for two sweeps.

direction_from_counts(counts) -> TrendDirection
    Pure function: classify a count series as improving / degrading / stable / unknown.
"""

from __future__ import annotations

from collections import defaultdict

from review.dao.fingerprint import compare_sweeps
from review.schemas.models import (
    DimensionTrend,
    SweepRecord,
    TrendDirection,
    TrendReport,
)


def direction_from_counts(counts: list[int]) -> TrendDirection:
    """Classify a count time-series as a trend direction.

    Rules (applied in order):
    - Fewer than 2 data points → UNKNOWN
    - Last value < first value → IMPROVING (fewer findings over time)
    - Last value > first value → DEGRADING (more findings over time)
    - Last value == first value → STABLE
    """
    if len(counts) < 2:
        return TrendDirection.UNKNOWN
    if counts[-1] < counts[0]:
        return TrendDirection.IMPROVING
    if counts[-1] > counts[0]:
        return TrendDirection.DEGRADING
    return TrendDirection.STABLE


def compute_dimension_trends(sweeps: list[SweepRecord], repo: str) -> list[DimensionTrend]:
    """Compute per-dimension finding counts and trend directions.

    Args:
        sweeps: SweepRecords in chronological order (oldest first).
        repo: Repo identifier — used only for labelling the returned models.

    Returns:
        One DimensionTrend per dimension seen across all sweeps, sorted by
        dimension name for deterministic output.
    """
    # Collect per-dimension counts for each sweep in order
    all_dimensions: set[str] = set()
    sweep_counts: list[dict[str, int]] = []

    for sweep in sweeps:
        counts: dict[str, int] = defaultdict(int)
        for finding in sweep.findings:
            counts[finding.category] += 1
        sweep_counts.append(dict(counts))
        all_dimensions.update(counts.keys())

    trends: list[DimensionTrend] = []
    for dimension in sorted(all_dimensions):
        counts_series = [sc.get(dimension, 0) for sc in sweep_counts]
        direction = direction_from_counts(counts_series)
        trends.append(
            DimensionTrend(
                dimension=dimension,
                repo=repo,
                counts=counts_series,
                direction=direction,
            )
        )
    return trends


def build_trend_report(previous: SweepRecord, current: SweepRecord) -> TrendReport:
    """Build a TrendReport comparing two consecutive sweeps.

    Args:
        previous: Earlier sweep (the baseline).
        current: Later sweep (the new state).

    Returns:
        TrendReport with new/resolved/recurring findings and dimension trends
        derived from the pair.
    """
    new_findings, resolved_findings, recurring_findings = compare_sweeps(previous, current)

    # Dimension trends from just these two sweeps
    dimension_trends = compute_dimension_trends([previous, current], repo=current.repo)

    return TrendReport(
        repo=current.repo,
        from_date=previous.sweep_date,
        to_date=current.sweep_date,
        new_findings=new_findings,
        resolved_findings=resolved_findings,
        recurring_findings=recurring_findings,
        dimension_trends=dimension_trends,
    )


def render_trend_report(report: TrendReport) -> str:
    """Render a TrendReport as a human-readable Markdown string."""
    lines: list[str] = []
    lines.append(f"## Trend Report: {report.repo}")
    lines.append(f"Period: {report.from_date} → {report.to_date}")
    lines.append("")

    lines.append(f"### New findings ({len(report.new_findings)})")
    if report.new_findings:
        for f in report.new_findings:
            lines.append(f"- `{f.finding_id}` {f.file_path} — {f.title} [{f.merge_impact}]")
    else:
        lines.append("None")
    lines.append("")

    lines.append(f"### Resolved findings ({len(report.resolved_findings)})")
    if report.resolved_findings:
        for f in report.resolved_findings:
            lines.append(f"- `{f.finding_id}` {f.file_path} — {f.title}")
    else:
        lines.append("None")
    lines.append("")

    lines.append(f"### Recurring findings ({len(report.recurring_findings)})")
    if report.recurring_findings:
        for f in report.recurring_findings:
            lines.append(f"- `{f.finding_id}` {f.file_path} — {f.title} [{f.merge_impact}]")
    else:
        lines.append("None")
    lines.append("")

    lines.append("### Dimension trends")
    lines.append("")
    lines.append("| Dimension | Trend | Counts (oldest→newest) |")
    lines.append("|-----------|-------|------------------------|")
    for trend in report.dimension_trends:
        counts_str = " → ".join(str(c) for c in trend.counts)
        lines.append(f"| {trend.dimension} | {trend.direction.value} | {counts_str} |")

    return "\n".join(lines)
