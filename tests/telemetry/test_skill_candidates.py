"""Tests for skill-candidate pattern detection (GUA-164).

Tests T4–T8 (detection logic in telemetry/skill_candidates.py) and T10
(signal scorability in telemetry/signals.py).

Design notes
------------
- T4: Threshold boundary — 3 sessions emit; 2 sessions do not.
- T5: Meta session exclusion — sessions with session_intent="meta" are never
  counted even when they carry the target N-gram.
- T6: Unlabelled session exclusion — the filter is ``intent == "execution"``
  NOT ``intent == "meta"``.  A session with intent="" or intent=None must not
  appear in candidates even when it carries the target N-gram.  This test
  covers the 448/1085 unlabelled bucket that would generate false positives if
  the filter were inverted (plan R2, refinement note §7).
- T7: NULL tool_sequence silently skipped — no error, no phantom count.
- T8: Resolver returns None when all rows have NULL tool_sequence — distinguishes
  "no data" from a genuine zero (plan refinement note §2).
- T10: ``skill-candidate-patterns`` is in the REGISTERED set — the signal is
  scorable via signals.is_scorable(), not just declared.
"""

from __future__ import annotations

import json
from typing import Any

from telemetry import signals
from telemetry.signals import SignalSources
from telemetry.skill_candidates import detect_skill_candidates

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _session(
    session_id: str,
    intent: str = "execution",
    seq: list[str] | None = None,
    skill_count: int = 0,
) -> dict[str, Any]:
    """Build a minimal sessions.db row dict for detection tests."""
    tool_counts = {}
    if skill_count:
        tool_counts["Skill"] = skill_count
    return {
        "session_id": session_id,
        "session_intent": intent,
        "tool_sequence": json.dumps(seq) if seq is not None else None,
        "tool_counts": json.dumps(tool_counts),
    }


_BASE_SEQ = ["Read", "Glob", "Bash"]  # a 3-gram used across multiple tests


# ---------------------------------------------------------------------------
# T4 — Threshold boundary
# ---------------------------------------------------------------------------


def test_threshold_three_sessions_emit_pattern() -> None:
    """3 sessions sharing a 3-gram → pattern reported."""
    rows = [
        _session("s1", seq=_BASE_SEQ),
        _session("s2", seq=_BASE_SEQ),
        _session("s3", seq=_BASE_SEQ),
    ]
    result = detect_skill_candidates(rows, threshold=3)
    gram = tuple(_BASE_SEQ)
    assert gram in result, f"Expected {gram} in result; got {result}"
    assert set(result[gram]) == {"s1", "s2", "s3"}


def test_threshold_two_sessions_emit_nothing() -> None:
    """2 sessions sharing a 3-gram → nothing emitted (below threshold=3)."""
    rows = [
        _session("s1", seq=_BASE_SEQ),
        _session("s2", seq=_BASE_SEQ),
    ]
    result = detect_skill_candidates(rows, threshold=3)
    assert result == {}, f"Expected empty result; got {result}"


# ---------------------------------------------------------------------------
# T5 — Meta session exclusion
# ---------------------------------------------------------------------------


def test_meta_sessions_excluded() -> None:
    """Sessions with session_intent='meta' do not contribute to any pattern.

    Even if a meta session repeats the target N-gram, the 3-execution-session
    threshold must be evaluated without it.
    """
    rows = [
        _session("exec1", intent="execution", seq=_BASE_SEQ),
        _session("exec2", intent="execution", seq=_BASE_SEQ),
        # This meta session carries the same N-gram — must not be counted.
        _session("meta1", intent="meta", seq=_BASE_SEQ),
    ]
    # Only 2 execution sessions → below threshold.
    result = detect_skill_candidates(rows, threshold=3)
    assert result == {}, (
        "Meta session should be excluded; only 2 execution sessions so nothing "
        f"should be emitted, but got: {result}"
    )


# ---------------------------------------------------------------------------
# T6 — Unlabelled session exclusion (the critical R2 boundary)
# ---------------------------------------------------------------------------


def test_unlabelled_sessions_excluded_empty_string() -> None:
    """Sessions with session_intent='' must NOT be counted.

    The filter is ``intent == "execution"`` (strict equality), not
    ``intent != "meta"``.  An unlabelled session (intent="") that carries the
    target N-gram must not push a pattern over threshold.
    """
    rows = [
        _session("exec1", intent="execution", seq=_BASE_SEQ),
        _session("exec2", intent="execution", seq=_BASE_SEQ),
        # Unlabelled — the 448/1085 bucket that hides meta sessions.
        _session("unlabelled1", intent="", seq=_BASE_SEQ),
    ]
    result = detect_skill_candidates(rows, threshold=3)
    assert result == {}, (
        "Unlabelled session (intent='') should be excluded; only 2 execution "
        f"sessions so nothing should be emitted, but got: {result}"
    )


def test_unlabelled_sessions_excluded_none_intent() -> None:
    """Sessions with session_intent=None must also be excluded."""
    rows = [
        _session("exec1", intent="execution", seq=_BASE_SEQ),
        _session("exec2", intent="execution", seq=_BASE_SEQ),
        _session("unlabelled2", intent=None, seq=_BASE_SEQ),  # type: ignore[arg-type]
    ]
    result = detect_skill_candidates(rows, threshold=3)
    assert result == {}, (
        "Unlabelled session (intent=None) should be excluded; only 2 execution "
        f"sessions so nothing should be emitted, but got: {result}"
    )


def test_unlabelled_sessions_not_excluded_when_three_exec() -> None:
    """Positive control: 3 genuine execution sessions still emit the pattern
    even when extra unlabelled sessions are also present."""
    rows = [
        _session("exec1", intent="execution", seq=_BASE_SEQ),
        _session("exec2", intent="execution", seq=_BASE_SEQ),
        _session("exec3", intent="execution", seq=_BASE_SEQ),
        # An unlabelled session carrying the same gram — must be ignored for
        # threshold counting but must not suppress the real pattern either.
        _session("unlabelled3", intent="", seq=_BASE_SEQ),
    ]
    result = detect_skill_candidates(rows, threshold=3)
    gram = tuple(_BASE_SEQ)
    assert gram in result, f"3 execution sessions should emit pattern; got {result}"
    assert "unlabelled3" not in result[gram], (
        "Unlabelled session id must not appear in the pattern's session list"
    )


# ---------------------------------------------------------------------------
# T7 — NULL tool_sequence silently skipped
# ---------------------------------------------------------------------------


def test_null_tool_sequence_silently_skipped() -> None:
    """Sessions with tool_sequence=NULL are silently excluded — no error."""
    rows = [
        _session("no_seq1", seq=None),
        _session("no_seq2", seq=None),
        _session("no_seq3", seq=None),
    ]
    # Should not raise; should return empty (no qualifying sessions with sequences).
    result = detect_skill_candidates(rows, threshold=3)
    assert result == {}


def test_null_tool_sequence_mixed_with_real() -> None:
    """NULL rows are skipped; sessions with sequences are still processed."""
    rows = [
        _session("s1", seq=_BASE_SEQ),
        _session("s2", seq=_BASE_SEQ),
        _session("s3", seq=_BASE_SEQ),
        # Null row — silently excluded, must not affect the above three.
        _session("s4", seq=None),
    ]
    result = detect_skill_candidates(rows, threshold=3)
    gram = tuple(_BASE_SEQ)
    assert gram in result
    assert "s4" not in result[gram]


# ---------------------------------------------------------------------------
# T8 — Resolver returns None pre-migration (all NULL → None, not 0)
# ---------------------------------------------------------------------------


def test_resolver_returns_none_when_all_tool_sequence_null() -> None:
    """When every session has tool_sequence=NULL the resolver returns None.

    This distinguishes "the column does not exist yet" from a genuine zero
    (column exists, data present, no patterns found).
    """
    all_null = [
        _session("pre1", seq=None),
        _session("pre2", seq=None),
        _session("pre3", seq=None),
    ]
    src = SignalSources(sessions=all_null)
    result = signals.resolve("skill-candidate-patterns", src)
    assert result is None, (
        f"All-NULL tool_sequence should return None (pre-migration), got {result}"
    )


def test_resolver_returns_zero_when_sequences_exist_but_no_patterns() -> None:
    """When tool_sequence is populated but no patterns cross threshold, return 0.

    This is the genuine-zero case — the migration ran, sequences exist, but
    there are not enough recurring patterns to report.
    """
    # 2 sessions sharing a 3-gram → below threshold=3.
    two_sessions = [
        _session("s1", seq=_BASE_SEQ),
        _session("s2", seq=_BASE_SEQ),
    ]
    src = SignalSources(sessions=two_sessions)
    result = signals.resolve("skill-candidate-patterns", src)
    assert result == 0.0, f"Sequences exist but below threshold → genuine zero; got {result}"


def test_resolver_returns_positive_count_when_patterns_found() -> None:
    """When patterns are found the resolver returns a positive float count."""
    three_sessions = [
        _session("s1", seq=_BASE_SEQ),
        _session("s2", seq=_BASE_SEQ),
        _session("s3", seq=_BASE_SEQ),
    ]
    src = SignalSources(sessions=three_sessions)
    result = signals.resolve("skill-candidate-patterns", src)
    assert isinstance(result, float) and result > 0, (
        f"3 sessions sharing a 3-gram should give a positive count; got {result}"
    )


def test_resolver_returns_none_when_no_sessions() -> None:
    """Empty session list → None (no data, not zero patterns)."""
    src = SignalSources(sessions=[])
    result = signals.resolve("skill-candidate-patterns", src)
    assert result is None


# ---------------------------------------------------------------------------
# T10 — Signal scorability
# ---------------------------------------------------------------------------


def test_skill_candidate_patterns_is_registered() -> None:
    """``skill-candidate-patterns`` is in the REGISTERED set, not unregistered."""
    assert signals.state_of("skill-candidate-patterns") == signals.REGISTERED


def test_skill_candidate_patterns_is_scorable() -> None:
    """``signals.is_scorable`` returns True — the signal has a working resolver."""
    assert signals.is_scorable("skill-candidate-patterns")


def test_skill_candidate_patterns_in_registered_names() -> None:
    """``registered_names()`` includes ``skill-candidate-patterns``."""
    assert "skill-candidate-patterns" in signals.registered_names()


def test_skill_candidate_patterns_uses_kind_session() -> None:
    """Signal kind is KIND_SESSION — it reads from sessions, not a new store."""
    sig = signals.lookup("skill-candidate-patterns")
    assert sig is not None
    assert sig.kind == signals.KIND_SESSION, (
        f"Expected KIND_SESSION, got {sig.kind!r} — "
        "adding KIND_SEQUENCE would imply a separate store that does not exist "
        "(plan refinement note §2)"
    )
