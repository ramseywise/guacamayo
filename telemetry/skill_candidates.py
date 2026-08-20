"""Deterministic N-gram pattern detection for skill-candidate identification.

Reads ``tool_sequence`` rows from ``sessions.db`` (written by the librarian
cartographer after Step 1 / LIB-125) and counts how often each ordered sub-
sequence of tool names appears across execution-intent sessions with no skill
invocation.

The column is NULL for sessions parsed before the LIB-125 migration.  All such
rows are silently excluded — a resolver that returns ``None`` when the entire
population is NULL is unambiguous: it means "no data yet", not "no candidates".

Why ``tool_counts["Skill"]`` rather than ``skill_costs``
---------------------------------------------------------
Both columns record whether a skill ran, but ``tool_counts["Skill"]`` is a
raw tool-call count: zero means *no* skill was invoked at all, regardless of
which skill.  ``skill_costs`` keys are skill names — richer, but the question
here is binary (any invocation / none).  The choice is ``tool_counts`` so that
a session with skill invocations the costs dict missed still scores correctly.
(See plan refinement note §3.)
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any


def detect_skill_candidates(
    sessions: list[dict[str, Any]],
    threshold: int = 3,
    min_n: int = 3,
    max_n: int = 5,
) -> dict[tuple[str, ...], list[str]]:
    """Return N-gram patterns appearing in at least *threshold* qualifying sessions.

    Parameters
    ----------
    sessions:
        Rows from ``sessions.db`` as dicts.  Required keys: ``session_id``,
        ``session_intent``, ``tool_counts`` (JSON string or None),
        ``tool_sequence`` (JSON string or None).
    threshold:
        Minimum number of distinct qualifying sessions a pattern must appear in
        to be reported.  Default 3 (matches the retro's "≥3 sessions" rule).
    min_n, max_n:
        Inclusive range of N-gram lengths to extract.  Default 3–5.

    Returns
    -------
    dict mapping (tool_name, ...) tuples to sorted lists of session_id strings.
    Empty dict when no pattern crosses the threshold.  The caller should check
    whether *all* sessions had ``tool_sequence=NULL`` and return ``None`` from a
    signal resolver in that case (see ``_skill_candidate_count`` in signals.py).
    """
    # Filter to execution-intent sessions with tool_sequence populated and no
    # skill invocations.  Strict equality to "execution" excludes both "meta"
    # and "" / NULL (the large unlabelled bucket) — see plan R2 and test T6.
    candidates: list[dict[str, Any]] = []
    for s in sessions:
        if s.get("session_intent") != "execution":
            continue
        raw_seq = s.get("tool_sequence")
        if not raw_seq:
            # NULL or empty string — pre-migration row, silently skip (T7).
            continue
        try:
            tool_counts: dict[str, Any] = json.loads(s.get("tool_counts") or "{}")
        except (TypeError, ValueError):
            tool_counts = {}
        # Zero Skill calls means no skill was invoked in this session.
        if float(tool_counts.get("Skill", 0)) != 0:
            continue
        candidates.append(s)

    # Accumulate N-gram → set of session IDs across all qualifying sessions.
    ngram_sessions: dict[tuple[str, ...], set[str]] = defaultdict(set)
    for s in candidates:
        raw_seq = s["tool_sequence"]
        try:
            seq: list[str] = json.loads(raw_seq)
        except (TypeError, ValueError):
            continue
        if not isinstance(seq, list):
            continue
        sid = s.get("session_id", "")
        for n in range(min_n, max_n + 1):
            for i in range(len(seq) - n + 1):
                gram = tuple(seq[i : i + n])
                ngram_sessions[gram].add(sid)

    # Return only patterns crossing the threshold, with sorted session lists for
    # deterministic output.
    return {gram: sorted(sids) for gram, sids in ngram_sessions.items() if len(sids) >= threshold}
