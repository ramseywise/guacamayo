"""Proposal sightings tracker — count distinct days each proposal_id appears.

board.json is overwritten every tick. actions.jsonl records only decided actions.
A proposal re-derived hundreds of times and never acted on is invisible — this sink
makes that invisible accumulation visible.

Schema (one line per (proposal_id, date) pair):
    {"proposal_id": "abc123", "action": "close_issue", "target": {...},
     "date": "2026-08-19", "ts": "ISO-8601"}

`track_sightings` is the only writer. It deduplicates within a day so a
10-minute cron cadence does not produce phantom sighting counts.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger(__name__)

_DEFAULT_SIGHTINGS_PATH = (
    Path(__file__).resolve().parents[1] / ".sounding" / "telemetry" / "proposal-sightings.jsonl"
)

# Proposals seen on more than this many distinct days without a decision
# are the "invisible accumulation" signal.
STALE_DAYS_THRESHOLD = 3


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def read_sightings(sightings_path: Path | None = None) -> list[dict[str, Any]]:
    """Read existing sightings, skipping malformed lines."""
    path = sightings_path or _DEFAULT_SIGHTINGS_PATH
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                log.warning("sightings.malformed_line", path=str(path))
    return rows


def track_sightings(
    proposals: list[dict[str, Any]],
    sightings_path: Path | None = None,
) -> int:
    """Append one sighting per (proposal_id, today) pair that has not been logged yet.

    Reads existing sightings first and deduplicates within the current day, so
    repeated cron runs on the same date produce exactly one row per proposal.

    Each proposal dict must carry at least "id", "action", and "target".

    Returns the count of new sightings appended.
    """
    path = sightings_path or _DEFAULT_SIGHTINGS_PATH

    existing = read_sightings(path)
    seen_today: set[str] = {row["proposal_id"] for row in existing if row.get("date") == _today()}

    today = _today()
    ts = datetime.now(UTC).isoformat()

    new_rows: list[str] = []
    for proposal in proposals:
        pid = proposal.get("id") or proposal.get("proposal_id", "")
        if not pid:
            continue
        if pid in seen_today:
            continue
        row = {
            "proposal_id": pid,
            "action": proposal.get("action", ""),
            "target": proposal.get("target", {}),
            "date": today,
            "ts": ts,
        }
        new_rows.append(json.dumps(row, default=str))
        seen_today.add(pid)

    if not new_rows:
        log.debug("sightings.no_new", today=today)
        return 0

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for line in new_rows:
            fh.write(line + "\n")

    log.info("sightings.appended", count=len(new_rows), today=today)
    return len(new_rows)


def count_days_by_proposal(
    sightings: list[dict[str, Any]],
) -> dict[str, int]:
    """Map proposal_id -> distinct day count from a list of sighting rows."""
    days_seen: dict[str, set[str]] = defaultdict(set)
    for row in sightings:
        pid = row.get("proposal_id", "")
        d = row.get("date", "")
        if pid and d:
            days_seen[pid].add(d)
    return {pid: len(days) for pid, days in days_seen.items()}


def render_proposal_sightings_card(
    sightings_path: Path | None = None,
) -> str:
    """HTML card showing proposal persistence — the invisible accumulation signal.

    Three stats:
      - Total unique proposals seen (ever)
      - Proposals seen on >STALE_DAYS_THRESHOLD distinct days without a decision
      - Most persistent proposal (highest day count)

    Returns empty string when the sightings file does not exist or is empty, so
    callers may safely include this in a dashboard region regardless of whether
    tracking has started.
    """
    path = sightings_path or _DEFAULT_SIGHTINGS_PATH
    sightings = read_sightings(path)
    if not sightings:
        return ""

    days_by_pid = count_days_by_proposal(sightings)
    total_unique = len(days_by_pid)

    stale = {pid: d for pid, d in days_by_pid.items() if d > STALE_DAYS_THRESHOLD}
    stale_count = len(stale)

    if days_by_pid:
        max_pid, max_days = max(days_by_pid.items(), key=lambda kv: kv[1])
        # Derive action from first matching sighting for labelling
        action_label = ""
        for row in sightings:
            if row.get("proposal_id") == max_pid:
                action_label = row.get("action", "")
                break
        most_persistent = (
            f"{max_days}d ({action_label} {max_pid[:8]})"
            if action_label
            else f"{max_days}d ({max_pid[:8]})"
        )
    else:
        most_persistent = "n/a"
        max_days = 0

    stale_color = "var(--bad)" if stale_count > 0 else "var(--good)"

    return (
        '<div class="card"><div class="card-title">Proposal sightings</div>'
        '<p class="card-note">Each board tick re-derives proposals from scratch. '
        "This card counts distinct days a proposal has been seen — a high count "
        f"without a decision means invisible accumulation (threshold: {STALE_DAYS_THRESHOLD} days).</p>"
        '<div class="stat-row">'
        f'<div class="stat"><span class="value">{total_unique}</span>'
        '<span class="label">unique proposals seen</span></div>'
        f'<div class="stat"><span class="value" style="color:{stale_color}">'
        f'{stale_count}</span><span class="label">stale (&gt;{STALE_DAYS_THRESHOLD}d, no decision)</span></div>'
        f'<div class="stat"><span class="value">{most_persistent}</span>'
        '<span class="label">most persistent</span></div>'
        "</div></div>"
    )
