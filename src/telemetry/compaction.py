"""Drain mechanism for append-only Markdown logs that grow without bound.

The insights-log accumulates one section per `/meta-insights` run (roughly
daily).  At ~100 lines per section it hits 2,000+ lines in weeks.  This
module moves sections older than `keep_days` to a parallel archive file so
the live log stays navigable without losing history.

Public API
----------
compact_insights_log(log_path, archive_path, keep_days=90) -> int
    Move old sections to archive.  Returns the count of archived sections.
"""

from __future__ import annotations

import re
from datetime import UTC, timedelta
from datetime import date as _date
from datetime import datetime as _datetime
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)

# Matches the leading date in a section header such as:
#   ## 2026-08-04 (382 sessions ...) [dry-run — ...]
_SECTION_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})\b", re.MULTILINE)


def _today() -> _date:
    return _datetime.now(UTC).date()


def _parse_sections(text: str) -> list[tuple[_date, int, int]]:
    """Return list of (date, start_char, end_char) for each ## section.

    ``end_char`` is the start of the *next* section header, or len(text) for
    the last section.  The tuple describes a half-open interval ``[start, end)``.
    """
    matches = list(_SECTION_RE.finditer(text))
    if not matches:
        return []

    sections: list[tuple[_date, int, int]] = []
    for i, m in enumerate(matches):
        section_date = _date.fromisoformat(m.group(1))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((section_date, start, end))
    return sections


def compact_insights_log(
    log_path: Path,
    archive_path: Path,
    keep_days: int = 90,
) -> int:
    """Move sections older than ``keep_days`` from *log_path* to *archive_path*.

    Parameters
    ----------
    log_path:
        Path to the live insights-log.md that is read and rewritten.
    archive_path:
        Path to the archive file (created if absent, appended otherwise).
    keep_days:
        Sections whose header date is strictly older than this many days are
        moved.  Sections within the window, or with unparseable dates, are kept.

    Returns
    -------
    int
        Number of sections moved to the archive.
    """
    if not log_path.exists():
        log.warning("compact_insights_log: log_path not found", path=str(log_path))
        return 0

    text = log_path.read_text(encoding="utf-8")
    sections = _parse_sections(text)

    if not sections:
        log.info("compact_insights_log: no sections found", path=str(log_path))
        return 0

    cutoff = _today() - timedelta(days=keep_days)

    old_chunks: list[str] = []
    kept_chunks: list[str] = []

    for section_date, start, end in sections:
        chunk = text[start:end]
        if section_date < cutoff:
            old_chunks.append(chunk)
        else:
            kept_chunks.append(chunk)

    archived_count = len(old_chunks)

    if archived_count == 0:
        log.info(
            "compact_insights_log: nothing to archive",
            total_sections=len(sections),
            cutoff=str(cutoff),
        )
        return 0

    # Append old sections to archive (newest-appended means archive grows in
    # the same append order as the live log).
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with archive_path.open("a", encoding="utf-8") as fh:
        for chunk in old_chunks:
            # Ensure sections are separated by a blank line in the archive.
            fh.write(chunk if chunk.endswith("\n") else chunk + "\n")

    # Rewrite the live log with only the kept sections.
    new_text = "".join(kept_chunks)
    log_path.write_text(new_text, encoding="utf-8")

    log.info(
        "compact_insights_log: archived old sections",
        archived=archived_count,
        kept=len(kept_chunks),
        cutoff=str(cutoff),
        archive=str(archive_path),
    )
    return archived_count
