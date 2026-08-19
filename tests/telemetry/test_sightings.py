"""Tests for telemetry/sightings.py (GUA-143).

DoD:
  - Seed file; verify dedup on same day.
  - Verify a new date adds a new row.
  - Verify the dashboard card renders the three stats.
  - Verify empty sightings file returns empty card.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from telemetry.sightings import (
    count_days_by_proposal,
    read_sightings,
    render_proposal_sightings_card,
    track_sightings,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _proposal(pid: str, action: str = "triage", repo: str = "guacamayo", issue: int = 1) -> dict:
    return {"id": pid, "action": action, "target": {"repo": repo, "issue_num": issue}}


def _seed_sightings(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


# ---------------------------------------------------------------------------
# track_sightings: dedup within a day
# ---------------------------------------------------------------------------


def test_track_sightings_dedup_same_day(tmp_path: Path) -> None:
    """Two calls on the same day must not double-count a proposal."""
    sink = tmp_path / "sightings.jsonl"

    proposals = [_proposal("abc123", "triage")]

    with patch("telemetry.sightings._today", return_value="2026-08-19"):
        added_first = track_sightings(proposals, sightings_path=sink)
        added_second = track_sightings(proposals, sightings_path=sink)

    assert added_first == 1
    assert added_second == 0  # already logged for today

    rows = read_sightings(sink)
    assert len(rows) == 1
    assert rows[0]["proposal_id"] == "abc123"
    assert rows[0]["date"] == "2026-08-19"


def test_track_sightings_new_day_adds_row(tmp_path: Path) -> None:
    """Same proposal on a different date → new sighting row."""
    sink = tmp_path / "sightings.jsonl"
    proposals = [_proposal("abc123", "close_issue")]

    with patch("telemetry.sightings._today", return_value="2026-08-19"):
        track_sightings(proposals, sightings_path=sink)

    with patch("telemetry.sightings._today", return_value="2026-08-20"):
        added = track_sightings(proposals, sightings_path=sink)

    assert added == 1
    rows = read_sightings(sink)
    assert len(rows) == 2
    dates = {r["date"] for r in rows}
    assert dates == {"2026-08-19", "2026-08-20"}


def test_track_sightings_multiple_proposals(tmp_path: Path) -> None:
    """Multiple distinct proposals → one row each."""
    sink = tmp_path / "sightings.jsonl"
    proposals = [
        _proposal("aaa", "triage", issue=1),
        _proposal("bbb", "close_issue", issue=2),
        _proposal("ccc", "fix_label", issue=3),
    ]

    with patch("telemetry.sightings._today", return_value="2026-08-19"):
        added = track_sightings(proposals, sightings_path=sink)

    assert added == 3
    rows = read_sightings(sink)
    assert len(rows) == 3
    pids = {r["proposal_id"] for r in rows}
    assert pids == {"aaa", "bbb", "ccc"}


def test_track_sightings_empty_proposals(tmp_path: Path) -> None:
    """Empty proposal list → zero rows, no file created."""
    sink = tmp_path / "sightings.jsonl"

    with patch("telemetry.sightings._today", return_value="2026-08-19"):
        added = track_sightings([], sightings_path=sink)

    assert added == 0
    assert not sink.exists()


def test_track_sightings_skips_missing_id(tmp_path: Path) -> None:
    """Proposals without an id field are silently skipped."""
    sink = tmp_path / "sightings.jsonl"
    proposals = [{"action": "triage", "target": {"repo": "x", "issue_num": 1}}]  # no "id"

    with patch("telemetry.sightings._today", return_value="2026-08-19"):
        added = track_sightings(proposals, sightings_path=sink)

    assert added == 0


# ---------------------------------------------------------------------------
# count_days_by_proposal
# ---------------------------------------------------------------------------


def test_count_days_by_proposal() -> None:
    sightings = [
        {"proposal_id": "aaa", "date": "2026-08-17"},
        {"proposal_id": "aaa", "date": "2026-08-18"},
        {"proposal_id": "aaa", "date": "2026-08-19"},
        {"proposal_id": "bbb", "date": "2026-08-19"},
    ]
    counts = count_days_by_proposal(sightings)
    assert counts["aaa"] == 3
    assert counts["bbb"] == 1


def test_count_days_by_proposal_deduplicates_date() -> None:
    """Same (proposal_id, date) pair appearing twice counts as one day."""
    sightings = [
        {"proposal_id": "aaa", "date": "2026-08-19"},
        {"proposal_id": "aaa", "date": "2026-08-19"},  # duplicate
    ]
    counts = count_days_by_proposal(sightings)
    assert counts["aaa"] == 1


# ---------------------------------------------------------------------------
# render_proposal_sightings_card
# ---------------------------------------------------------------------------


def test_render_card_empty_file_returns_empty(tmp_path: Path) -> None:
    sink = tmp_path / "sightings.jsonl"
    result = render_proposal_sightings_card(sightings_path=sink)
    assert result == ""


def test_render_card_renders_stats(tmp_path: Path) -> None:
    """Card shows unique count, stale count, and most-persistent label."""
    sink = tmp_path / "sightings.jsonl"

    # proposal "aaa" seen 4 days (> STALE_DAYS_THRESHOLD=3)
    # proposal "bbb" seen 1 day (not stale)
    rows = []
    for day in ("2026-08-16", "2026-08-17", "2026-08-18", "2026-08-19"):
        rows.append({"proposal_id": "aaa", "action": "triage", "target": {}, "date": day, "ts": ""})
    rows.append(
        {
            "proposal_id": "bbb",
            "action": "close_issue",
            "target": {},
            "date": "2026-08-19",
            "ts": "",
        }
    )

    _seed_sightings(sink, rows)

    card = render_proposal_sightings_card(sightings_path=sink)

    assert "Proposal sightings" in card
    assert "2" in card  # 2 unique proposals
    assert "1" in card  # 1 stale (aaa has 4 days)
    assert "4d" in card  # most persistent = 4 days


def test_render_card_no_stale_proposals(tmp_path: Path) -> None:
    """When no proposals exceed the threshold, stale count is 0."""
    sink = tmp_path / "sightings.jsonl"
    rows = [
        {"proposal_id": "aaa", "action": "triage", "target": {}, "date": "2026-08-19", "ts": ""},
    ]
    _seed_sightings(sink, rows)

    card = render_proposal_sightings_card(sightings_path=sink)
    assert "Proposal sightings" in card
    # stale count should be 0 — 1 unique proposal with 1 day (not > threshold)
    assert ">0<" in card or "0<" in card  # zero in a span
