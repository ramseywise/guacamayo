"""Tests for the pre-render store freshness guard (R12 F4, GUA-156).

A decoy store must abort the render loudly — an empty dashboard rendered from a
stale store is byte-for-byte a healthy-looking run.
"""

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from telemetry.__main__ import _assert_store_fresh

# SQLite's date('now') is UTC — the test's clock must match the guard's.
_TODAY = datetime.now(tz=UTC).date()


def _make_store(path: Path, session_dates: list[str]) -> Path:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE sessions (session_id TEXT PRIMARY KEY, date TEXT)")
    conn.executemany(
        "INSERT INTO sessions VALUES (?, ?)",
        [(f"s{i}", d) for i, d in enumerate(session_dates)],
    )
    conn.commit()
    conn.close()
    return path


def test_fresh_store_passes(tmp_path):
    store = _make_store(tmp_path / "fresh.db", [_TODAY.isoformat()])
    _assert_store_fresh(store)  # must not raise


def test_stale_store_aborts(tmp_path):
    old = (_TODAY - timedelta(days=90)).isoformat()
    store = _make_store(tmp_path / "stale.db", [old, old])
    with pytest.raises(SystemExit) as exc_info:
        _assert_store_fresh(store)
    assert exc_info.value.code == 1


def test_empty_store_aborts(tmp_path):
    store = _make_store(tmp_path / "empty.db", [])
    with pytest.raises(SystemExit) as exc_info:
        _assert_store_fresh(store)
    assert exc_info.value.code == 1


def test_boundary_respects_days_window(tmp_path):
    just_inside = (_TODAY - timedelta(days=29)).isoformat()
    store = _make_store(tmp_path / "edge.db", [just_inside])
    _assert_store_fresh(store, days=30)  # must not raise
    with pytest.raises(SystemExit):
        _assert_store_fresh(store, days=7)
