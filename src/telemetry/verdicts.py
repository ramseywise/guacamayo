"""Deterministic experiment-verdict computation (LIB-58).

Moves verdict *measurement* out of the LLM step in /workflow-insights step 10.
The LLM's job becomes interpretation of already-computed verdicts, not deriving
them from prose. This module owns the arithmetic; `factstore.append_verdicts`
owns persistence; `dashboard.py` owns rendering the trajectory.

Ledger metric grammar (verified against `tooling-ledger.md`, 2026-08-01, 31
rows, 100% typed coverage):

    <type>:<signal>[-<more-words>] <comparator> <threshold>[%] [<qualifier>...]

Four types, one comparator vocabulary each:
    absence:<signal>      -- zero occurrences of <signal> confirms; "for N ..."
                              is a repeat-window qualifier, not a threshold.
    presence:<signal>      -- >=1 occurrence of <signal> confirms.
    count-drop:<signal>    -- <signal> compared against a numeric threshold via
                              "above"/"below" (falling metrics use "below").
    ratio:<signal>         -- <signal> compared against a percentage (or N/M)
                              threshold via "above"/"below".

A row may carry more than one metric clause (joined by " + "); each clause is
scored independently and the row verdict is the worst of the two (failed >
inconclusive > trending > confirmed, i.e. pessimistic combination) -- see
`_combine`.

Signal → factstore measurement is a closed registry (`_SIGNAL_METRICS`), not a
generic string search: most ledger signals name process/textual events (e.g.
"flat-sibling-issues-without-parent-link", "worktree-commit-blocks") that the
session fact table cannot observe at all. Naively pattern-matching the slug
against session text would either always return 0 (a false "confirmed" for an
absence claim) or require unbounded heuristics. Only signals with a real
factstore column are registered; everything else scores `inconclusive` with
evidence saying so -- never a fabricated confirm/fail.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from telemetry import signals
from telemetry.signals import SignalSources

# ---------------------------------------------------------------------------
# Verdict vocabulary (matches the workflow-insights SKILL.md step 10 vocabulary
# so downstream prose stays consistent with the historical insights-log.md).
# ---------------------------------------------------------------------------

VERDICT_CONFIRMED = "confirmed"
VERDICT_TRENDING = "trending"
VERDICT_INCONCLUSIVE = "inconclusive"
VERDICT_FAILED = "failed"

_VERDICT_SEVERITY = {
    VERDICT_CONFIRMED: 0,
    VERDICT_TRENDING: 1,
    VERDICT_INCONCLUSIVE: 2,
    VERDICT_FAILED: 3,
}


@dataclass(frozen=True)
class Verdict:
    """One scored metric clause."""

    verdict: str
    evidence: str


def _combine(verdicts: list[Verdict]) -> Verdict:
    """Pessimistic combination across clauses in a multi-metric row.

    A row claiming two things is only as good as its worst-scored claim --
    `failed` on either clause means the hypothesis as a whole is not holding,
    `inconclusive` on either means the row cannot yet be called `confirmed`.
    """
    worst = max(verdicts, key=lambda v: _VERDICT_SEVERITY[v.verdict])
    if len(verdicts) == 1:
        return worst
    evidence = "; ".join(v.evidence for v in verdicts)
    return Verdict(worst.verdict, evidence)


# ---------------------------------------------------------------------------
# Metric-clause parsing
# ---------------------------------------------------------------------------

_METRIC_CLAUSE = re.compile(
    r"(?P<type>absence|presence|count-drop|ratio):(?P<signal>[^\s]+)"
    r"(?P<rest>.*?)(?=\s+\+\s+(?:absence|presence|count-drop|ratio):|$)",
    re.IGNORECASE | re.DOTALL,
)
_THRESHOLD = re.compile(
    r"\b(?P<comparator>above|below)\s+(?P<value>\d+(?:\.\d+)?)\s*(?P<pct>%)?"
    r"(?:\s*/\s*(?P<denom>\d+))?"
)


@dataclass(frozen=True)
class MetricClause:
    """One parsed `<type>:<signal> <comparator> <threshold>` clause."""

    metric_type: str  # absence | presence | count-drop | ratio
    signal: str
    comparator: str | None  # "above" | "below" | None (absence/presence have none)
    threshold: float | None
    is_percent: bool
    raw: str


def parse_metric(metric: str) -> list[MetricClause]:
    """Split a ledger Metric cell into its typed clauses.

    Handles multi-clause rows joined by " + " (row 23, 28, 29 in the ledger).
    Unparseable text (empty, "—", or missing a type prefix) returns [].
    """
    if not metric or metric.strip() in {"—", "-"}:
        return []
    clauses: list[MetricClause] = []
    for m in _METRIC_CLAUSE.finditer(metric):
        metric_type = m.group("type").lower()
        signal = m.group("signal").strip()
        rest = m.group("rest") or ""
        thr = _THRESHOLD.search(rest)
        comparator = thr.group("comparator").lower() if thr else None
        value = float(thr.group("value")) if thr else None
        is_percent = bool(thr and thr.group("pct"))
        if thr and thr.group("denom"):
            # "12/18" form -- normalise to a percentage threshold.
            value = round(100 * value / float(thr.group("denom")), 2)
            is_percent = True
        clauses.append(
            MetricClause(
                metric_type=metric_type,
                signal=signal,
                comparator=comparator,
                threshold=value,
                is_percent=is_percent,
                raw=(m.group(0)).strip(),
            )
        )
    return clauses


# ---------------------------------------------------------------------------
# Signal registry: ledger signal-slug -> factstore measurement
# ---------------------------------------------------------------------------
#
# Each entry computes a scalar from `sessions` fact rows (already filtered to
# work-sessions by the caller where that distinction matters -- see
# dashboard._work_sessions). Returns None when the corpus has no data for the
# signal (distinct from a genuine zero), so callers can tell "confirmed by
# absence" apart from "no data to judge absence".


# The signal namespace now lives in `signals.py` so the /hypothesis authoring
# skill and this scorer share one source of truth -- a hypothesis must not be
# writable against a name the scorer will silently fail to resolve.
#
# `_SIGNAL_METRICS` is retained as a thin compatibility view over the registry:
# it maps name -> a callable taking session rows, which is the signature the
# pre-2026-08-19 scorers and their tests use. Signals whose resolver needs a
# source other than session rows are absent from this view by construction --
# they are reached through `_measure` below, which passes the full bundle.
_SIGNAL_METRICS: dict[str, Any] = {
    name: (lambda rows, _n=name: signals.resolve(_n, signals.SignalSources(sessions=rows)))
    for name in signals.registered_names()
}


def _normalize_signal(signal: str) -> str:
    """Normalise a ledger signal slug to its registry key.

    Backticks are stripped because the ledger writes some metrics inside code
    spans (`` `presence:co-authored-by-rule-in-CLAUDE.md` ``). `_METRIC_CLAUSE`
    captures `[^\\s]+` for the signal, so the closing backtick lands inside the
    captured slug and the name can never match a registry key no matter what is
    registered -- three live ledger rows were unscorable for this reason alone
    (2026-08-19), independent of whether their signal existed.
    """
    return signal.strip().strip("`").strip().lower()


# ---------------------------------------------------------------------------
# Measurement front-end
# ---------------------------------------------------------------------------


def _as_sources(rows: list[dict[str, Any]] | SignalSources) -> SignalSources:
    """Accept either a bare session-row list (legacy) or a full source bundle.

    The pre-2026-08-19 signature took only `sessions` rows. Signals backed by
    git tables, the hook logs, findings, or repo files need more, so scorers now
    take a bundle -- but every existing caller and test passes a list, which is
    promoted here rather than at each call site.
    """
    return rows if isinstance(rows, SignalSources) else SignalSources(sessions=rows)


def _measure(clause: MetricClause, src: SignalSources) -> tuple[float | None, Verdict | None]:
    """Resolve a clause's signal to a value, or to the Verdict explaining why not.

    Returns `(value, None)` on success and `(None, verdict)` otherwise. The four
    registry states produce four *distinct* evidence strings -- collapsing them
    into one "no factstore signal registered" message is what made 49 ledger rows
    indistinguishable, hiding the difference between a claim nobody registered, a
    claim awaiting a collection change, and a claim no telemetry could ever see.
    """
    name = _normalize_signal(clause.signal)
    state = signals.state_of(name)
    verb = _MEASURE_VERB[clause.metric_type]

    if state == signals.UNREGISTERED:
        return None, Verdict(
            VERDICT_INCONCLUSIVE,
            f"unregistered signal '{clause.signal}' — cannot {verb}; "
            f"declare it in telemetry/signals.py or rewrite the metric",
        )
    if state == signals.NEEDS_COLLECTION:
        sig = signals.lookup(name)
        return None, Verdict(
            VERDICT_INCONCLUSIVE,
            f"'{clause.signal}' needs a collection change before it can be scored — "
            f"{sig.remedy if sig else ''}",
        )
    if state == signals.UNOBSERVABLE:
        sig = signals.lookup(name)
        return None, Verdict(
            VERDICT_INCONCLUSIVE,
            f"'{clause.signal}' is unobservable by design — {sig.remedy if sig else ''}",
        )

    value = signals.resolve(name, src)
    if value is None:
        return None, Verdict(
            VERDICT_INCONCLUSIVE, f"no data for '{clause.signal}' in the scored window"
        )
    return value, None


_MEASURE_VERB = {
    "absence": "measure absence",
    "presence": "measure presence",
    "count-drop": "measure count-drop",
    "ratio": "measure ratio",
}


# ---------------------------------------------------------------------------
# Per-metric-type verdict rules
# ---------------------------------------------------------------------------


def _score_absence(clause: MetricClause, rows: list[dict[str, Any]] | SignalSources) -> Verdict:
    """absence:<signal> — confirmed iff the registered count is exactly 0.

    Ledger semantics: "absence" always means an event-count signal (e.g.
    bash-antipatterns as a stand-in for "no antipattern occurrences"), never a
    percentage. A registered signal returning a positive count is `failed`
    (the thing we hoped to eliminate is still happening); an unregistered
    signal is `inconclusive` — factstore has no observation channel for most
    absence signals (they describe git/GitHub/hook-log events, not session
    facts), so silence is not evidence.
    """
    value, blocked = _measure(clause, _as_sources(rows))
    if blocked is not None:
        return blocked
    if value == 0:
        return Verdict(VERDICT_CONFIRMED, f"{clause.signal}=0 across scored sessions")
    return Verdict(VERDICT_FAILED, f"{clause.signal}={value} (expected 0)")


def _score_presence(clause: MetricClause, rows: list[dict[str, Any]] | SignalSources) -> Verdict:
    """presence:<signal> — confirmed iff the registered count/value is >0.

    Mirror of absence: a registered signal with any positive occurrence
    confirms; zero occurrences with real data available is `failed` (the
    capability never showed up); no registered signal is `inconclusive`.
    """
    value, blocked = _measure(clause, _as_sources(rows))
    if blocked is not None:
        return blocked
    if value > 0:
        return Verdict(VERDICT_CONFIRMED, f"{clause.signal}={value} observed")
    return Verdict(VERDICT_FAILED, f"{clause.signal}=0 (expected at least one occurrence)")


def _score_count_drop(clause: MetricClause, rows: list[dict[str, Any]] | SignalSources) -> Verdict:
    """count-drop:<signal> <above|below> <N> — a raw-count threshold.

    A single run cannot distinguish "stagnant" from "not yet improved enough"
    for an unbounded count — that distinction needs history across runs, which
    is exactly what the append-only verdict table (and its trajectory render in
    dashboard.py) is for. So a single observation scores only two ways:
    threshold met -> `confirmed`; threshold not met -> `trending` (never
    `failed` from one data point). Declaring a young hypothesis dead belongs to
    /retro once the trajectory shows no movement across runs, not to a single
    insights run.
    """
    value, blocked = _measure(clause, _as_sources(rows))
    if blocked is not None:
        return blocked
    if clause.threshold is None or clause.comparator is None:
        return Verdict(VERDICT_INCONCLUSIVE, f"{clause.signal}={value}, no parseable threshold")
    met = value < clause.threshold if clause.comparator == "below" else value > clause.threshold
    if met:
        return Verdict(
            VERDICT_CONFIRMED, f"{clause.signal}={value} {clause.comparator} {clause.threshold}"
        )
    return Verdict(
        VERDICT_TRENDING,
        f"{clause.signal}={value}, threshold {clause.comparator} {clause.threshold} not yet met",
    )


def _score_ratio(clause: MetricClause, rows: list[dict[str, Any]] | SignalSources) -> Verdict:
    """ratio:<signal> <above|below> <N%> — a percentage/fraction threshold.

    Same confirmed/trending split as count-drop for a not-yet-met threshold;
    a ratio further from its threshold than a fixed "close" band (10 points)
    reads as `failed` rather than `trending` — ratios (unlike raw counts) are
    bounded 0-100, so "half the distance to target" is a meaningful, comparable
    notion of "still plausibly moving" across different signals in a way a
    count-drop's unbounded raw value is not.
    """
    value, blocked = _measure(clause, _as_sources(rows))
    if blocked is not None:
        return blocked
    if clause.threshold is None or clause.comparator is None:
        return Verdict(VERDICT_INCONCLUSIVE, f"{clause.signal}={value}, no parseable threshold")
    met = value < clause.threshold if clause.comparator == "below" else value > clause.threshold
    if met:
        return Verdict(
            VERDICT_CONFIRMED, f"{clause.signal}={value}% {clause.comparator} {clause.threshold}%"
        )
    gap = abs(value - clause.threshold)
    _CLOSE_BAND = 10.0
    if gap <= _CLOSE_BAND:
        return Verdict(
            VERDICT_TRENDING,
            f"{clause.signal}={value}%, within {gap:.1f}pt of {clause.comparator} "
            f"{clause.threshold}% threshold",
        )
    return Verdict(
        VERDICT_FAILED,
        f"{clause.signal}={value}%, {gap:.1f}pt from {clause.comparator} {clause.threshold}% threshold",
    )


_SCORERS = {
    "absence": _score_absence,
    "presence": _score_presence,
    "count-drop": _score_count_drop,
    "ratio": _score_ratio,
}


def score_clause(clause: MetricClause, rows: list[dict[str, Any]] | SignalSources) -> Verdict:
    """Score one parsed metric clause against factstore rows."""
    scorer = _SCORERS[clause.metric_type]
    return scorer(clause, rows)


def score_metric(metric: str, rows: list[dict[str, Any]] | SignalSources) -> Verdict:
    """Score a raw ledger Metric cell (one or more clauses) into one Verdict.

    Empty/unparseable metrics (legacy `—` rows) return `inconclusive` — the
    ledger's own convention for "not yet a checkable metric" (see SKILL.md step
    10: "check legacy hypothesis rows ... if their status text contains a
    checkable signal" — this module does not attempt that prose heuristic;
    it only scores typed metrics, which is 100% ledger coverage as of 2026-08-01).
    """
    clauses = parse_metric(metric)
    if not clauses:
        return Verdict(VERDICT_INCONCLUSIVE, "no typed metric to score")
    scored = [score_clause(c, rows) for c in clauses]
    return _combine(scored)
