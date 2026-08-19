"""Tests for telemetry.compaction.compact_insights_log."""

from __future__ import annotations

from datetime import date as _date
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from telemetry.compaction import compact_insights_log

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _section(date: str, body: str = "body text\n") -> str:
    return f"## {date} (N sessions, 2026-07-15 to {date})\n\n{body}"


def _make_log(sections: list[str]) -> str:
    return "".join(sections)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_old_sections_moved_to_archive(tmp_path: Path) -> None:
    """Sections older than keep_days go to archive; recent sections stay."""
    today = _date(2026, 8, 19)
    old_date = str(today - timedelta(days=100))  # older than 90-day window
    new_date = str(today - timedelta(days=10))  # within 90-day window

    log_path = tmp_path / "insights-log.md"
    archive_path = tmp_path / "insights-log-archive.md"

    log_path.write_text(_make_log([_section(old_date), _section(new_date)]))

    with patch("telemetry.compaction._today", return_value=today):
        archived = compact_insights_log(log_path, archive_path, keep_days=90)

    assert archived == 1

    # Archive received the old section
    archive_text = archive_path.read_text()
    assert old_date in archive_text
    assert new_date not in archive_text

    # Live log contains only the recent section
    log_text = log_path.read_text()
    assert new_date in log_text
    assert old_date not in log_text


def test_all_recent_nothing_archived(tmp_path: Path) -> None:
    """If all sections are within keep_days, archive is untouched."""
    today = _date(2026, 8, 19)
    recent = str(today - timedelta(days=5))

    log_path = tmp_path / "insights-log.md"
    archive_path = tmp_path / "insights-log-archive.md"
    original = _make_log([_section(recent)])
    log_path.write_text(original)

    with patch("telemetry.compaction._today", return_value=today):
        archived = compact_insights_log(log_path, archive_path, keep_days=90)

    assert archived == 0
    assert not archive_path.exists()
    assert log_path.read_text() == original


def test_all_old_everything_archived(tmp_path: Path) -> None:
    """If all sections are old, live log is left empty."""
    today = _date(2026, 8, 19)
    old1 = str(today - timedelta(days=120))
    old2 = str(today - timedelta(days=95))

    log_path = tmp_path / "insights-log.md"
    archive_path = tmp_path / "insights-log-archive.md"
    log_path.write_text(_make_log([_section(old1), _section(old2)]))

    with patch("telemetry.compaction._today", return_value=today):
        archived = compact_insights_log(log_path, archive_path, keep_days=90)

    assert archived == 2
    assert old1 in archive_path.read_text()
    assert old2 in archive_path.read_text()
    assert log_path.read_text() == ""


def test_archive_appends_not_overwrites(tmp_path: Path) -> None:
    """Running compaction twice appends to the archive rather than replacing it."""
    today = _date(2026, 8, 19)
    old1 = str(today - timedelta(days=200))
    old2 = str(today - timedelta(days=150))

    log_path = tmp_path / "insights-log.md"
    archive_path = tmp_path / "insights-log-archive.md"

    # First run: archive old1
    log_path.write_text(_make_log([_section(old1), _section(old2)]))
    with patch("telemetry.compaction._today", return_value=today):
        compact_insights_log(log_path, archive_path, keep_days=90)

    # Second run: now old2 is the only section left in the log (which is also old)
    with patch("telemetry.compaction._today", return_value=today):
        compact_insights_log(log_path, archive_path, keep_days=90)

    archive_text = archive_path.read_text()
    # Both dates should appear in the archive
    assert old1 in archive_text
    assert old2 in archive_text


def test_missing_log_returns_zero(tmp_path: Path) -> None:
    """A missing log_path is handled gracefully — returns 0."""
    result = compact_insights_log(
        tmp_path / "nonexistent.md",
        tmp_path / "archive.md",
    )
    assert result == 0


def test_empty_log_returns_zero(tmp_path: Path) -> None:
    """A log with no ## sections returns 0 and leaves files untouched."""
    log_path = tmp_path / "insights-log.md"
    log_path.write_text("# Header only, no sections\n")
    archive_path = tmp_path / "archive.md"

    result = compact_insights_log(log_path, archive_path)

    assert result == 0
    assert not archive_path.exists()


def test_archive_dir_created_if_missing(tmp_path: Path) -> None:
    """archive_path parent directory is created when it does not exist."""
    today = _date(2026, 8, 19)
    old = str(today - timedelta(days=100))

    log_path = tmp_path / "insights-log.md"
    log_path.write_text(_section(old))

    archive_path = tmp_path / "subdir" / "nested" / "archive.md"

    with patch("telemetry.compaction._today", return_value=today):
        archived = compact_insights_log(log_path, archive_path, keep_days=90)

    assert archived == 1
    assert archive_path.exists()
