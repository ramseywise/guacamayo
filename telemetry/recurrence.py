"""Recurrence aggregation over review findings (GUA-100).

`compute_recurrence` groups findings by named friction *signature* (a regex over
`title`) rather than by the reporter-native `category` tag: two findings tagged
"config" and "api-contract" can both describe the same underlying pattern
("hardcoded, not externalized"), and category alone hides that. Grouping by
signature is what makes a pattern *promotable* to `/workflow-retro` (Step 5) --
`RECURRENCE_THRESHOLD` distinguishes a one-off from a recurring friction worth a
hook or rule.

Multi-match policy: a finding whose title matches more than one pattern is
counted in EVERY matching group ("all matches", not "first match wins"). Friction
signatures are not mutually exclusive -- a title like "silent swallow with no
timeout" is genuinely both a `silent-swallow` and a `missing-timeout` instance,
and undercounting either would hide a real recurrence from retro. This is a
deliberate divergence from the JSONL's own `category` field, which IS
single-valued per finding. Verified against the live 125-row corpus: only 3
findings match more than one pattern, so this choice has negligible effect on
`RECURRENCE_THRESHOLD`-gated promotion in practice.

Trend (GUA-104b): `count` alone is a lifetime total, so a signature that fired
5x in April and stopped is indistinguishable from one firing 5x this week --
which means the friction report ranks by accumulated history, and history is
dominated by whatever has been measured longest. `compute_period_counts` buckets
the same groups by period and `rising` marks the recent surges, so a
newly-rising pattern no longer sorts last.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from telemetry.periods import DEFAULT_PERIOD, period_bounds, period_key, previous_period_key

log = structlog.get_logger(__name__)

# Open Question 6 -- tunable; two independent derivations, no CI. A pattern
# firing fewer than 3 times in the corpus is treated as noise, not recurrence.
RECURRENCE_THRESHOLD = 3

# Rising rule (GUA-104b, Open Question 2). The most recent COMPLETE period must
# exceed 1.5x the mean of the three periods before it. The multiplier is a
# judgement call, not a derived constant -- 1.5 was chosen so a 2->3 step does
# not qualify but a 2->5 one does.
RISING_MULTIPLIER = 1.5
RISING_LOOKBACK = 3

# Weekly is the comparison period: daily is too noisy to act on, monthly too
# slow. A caller can override, but every default consumer uses this.
RISING_PERIOD = DEFAULT_PERIOD

# Named friction signatures, verified during planning (Step 0) against the live
# review-findings corpus. Matched case-insensitively against `title` only --
# `category` is reporter-native and inconsistent across sources (akira-scan vs
# SANYI vs workflow-review), so it is not a reliable grouping key on its own.
PATTERNS: dict[str, str] = {
    "hardcoded-not-configurable": r"hardcod|not externalized|magic number|should be config|env-config",
    "silent-swallow": r"silent|swallow|bare except|broad exception|suppress|ignored without",
    "missing-timeout": r"\btimeout\b",
    "resource-leak": r"leak|not closed",
    "duplicate-implementation": r"duplicat|divergent|identical pattern",
    "test-coverage-gap": r"test cover|test only|test checks|coverage unknown|not validated",
    "slug-inconsistency": r"\bslug\b",
    # Added 2026-08-10 (retro F3): 7 of 14 promotable groups were `unmatched:`
    # fallbacks, which means PATTERNS lacked a signature for those clusters. These
    # two were derived by reading the 68 unmatched titles, not guessed.
    "god-module": r"mixes multiple|multiple responsibilities|\d{3,}-line|god (module|object|class)",
    "unhandled-none-return": (
        r"unhandled (none|\w+ exception)|\bnone from\b|returns none|\bpnone\b|raises stopiteration"
    ),
}

_COMPILED_PATTERNS: dict[str, re.Pattern[str]] = {
    key: re.compile(pattern, re.IGNORECASE) for key, pattern in PATTERNS.items()
}

# Cap on `sample_titles` per group -- enough to spot-check a promotion candidate
# without inlining the whole corpus into a retro report.
_MAX_SAMPLE_TITLES = 3


@dataclass(frozen=True)
class RecurrenceGroup:
    """One recurring friction signature (or unmatched category/repo fallback)."""

    pattern_key: str
    count: int
    repos: list[str]
    categories: list[str]
    first_seen: str
    last_seen: str
    sample_titles: list[str] = field(default_factory=list)
    promotable: bool = False
    # GUA-104b. `period_counts` is keyed by `telemetry.periods.period_key` at
    # `RISING_PERIOD`; `rising` is the trend signal derived from it.
    #
    # `rising` deliberately does NOT fold into `promotable` (Open Question 3):
    # the two answer different questions -- "has this happened enough to matter"
    # vs "is this getting worse" -- and a consumer that wants either must say
    # `promotable or rising` at its own call site, where the choice is visible.
    period_counts: dict[str, int] = field(default_factory=dict)
    rising: bool = False


def _matched_keys(finding: dict[str, Any]) -> list[str]:
    """Pattern keys a finding belongs to, applying the all-matches policy.

    The single matcher. `compute_recurrence` and `compute_period_counts` both
    route through it so the lifetime count and the per-period counts can never
    disagree about which group a finding belongs to -- two matchers drifting
    apart would make the trend on a card contradict the count beside it.
    """
    title = str(finding.get("title") or "")
    matched = [key for key, rx in _COMPILED_PATTERNS.items() if rx.search(title)]
    if matched:
        return matched
    category = str(finding.get("category") or "unknown")
    repo = str(finding.get("repo") or "unknown")
    return [f"unmatched:{category}:{repo}"]


def compute_period_counts(
    findings: list[dict[str, Any]], period: str = RISING_PERIOD
) -> dict[str, dict[str, int]]:
    """Per-signature, per-period finding counts: `{pattern_key: {period_key: n}}`.

    Same grouping as `compute_recurrence` (shared `_matched_keys`, so the same
    all-matches policy), bucketed by `telemetry.periods.period_key`.

    Findings with no `date` cannot be placed in a period and are excluded.
    `compute_recurrence` already tolerates them via its `if date:` guard, but
    silently dropping rows from a trend calculation is exactly the kind of
    quiet gap that makes a flat line look like real evidence -- so the excluded
    count is logged.
    """
    # Validate the period once, before the loop. Inside the loop a ValueError
    # from `period_key` is ambiguous between a bad period and a bad date, and
    # the per-row handler below would swallow a caller typo as 125 unparseable
    # dates instead of raising.
    period_key("2000-01-01", period)

    counts: dict[str, dict[str, int]] = {}
    undated = 0
    unparseable = 0

    for finding in findings:
        date = str(finding.get("date") or "")
        if not date:
            undated += 1
            continue
        try:
            bucket = period_key(date, period)
        except (ValueError, IndexError):
            # A malformed `date` -- the period is already known good. Skip the
            # row rather than aborting the whole report.
            unparseable += 1
            continue
        for key in _matched_keys(finding):
            counts.setdefault(key, {})[bucket] = counts.setdefault(key, {}).get(bucket, 0) + 1

    if undated or unparseable:
        log.info(
            "recurrence.period_counts_excluded",
            undated=undated,
            unparseable=unparseable,
            findings=len(findings),
            period=period,
        )
    return counts


def _is_rising(period_counts: dict[str, int], period: str, today: str) -> bool:
    """Whether a signature's per-period counts show a recent surge.

    The most recent COMPLETE period must clear both gates:

    - `> RISING_MULTIPLIER x` the mean of the `RISING_LOOKBACK` periods before
      it, counting a period with no findings as a real zero rather than
      skipping it (a signature that stopped firing must read as falling, not
      as flat);
    - `>= RECURRENCE_THRESHOLD` in absolute terms, which suppresses 0 -> 1 as
      an infinite rise.

    The trailing period is excluded when incomplete (Open Question 5). A
    three-day-old week is not a low week, and treating it as one is the single
    most likely source of a false flag -- in both directions.

    "Most recent" is measured against `today`, NOT against the last period that
    happens to have data. Reading it off the observed keys would make every
    signature rising at its own final burst: a pattern that fired 5x in April
    and stopped would compare that April week against the three empty weeks
    before it and flag, which is precisely backwards.
    """
    if not period_counts:
        return False

    # The last period that has fully elapsed as of `today`, whether or not this
    # signature fired in it. An absent key here is a real zero.
    recent_key = period_key(today, period)
    if period_bounds(recent_key, period)[1] > today:
        recent_key = previous_period_key(recent_key, period)

    recent = period_counts.get(recent_key, 0)
    if recent < RECURRENCE_THRESHOLD:
        return False

    prior_key = recent_key
    prior: list[int] = []
    for _ in range(RISING_LOOKBACK):
        prior_key = previous_period_key(prior_key, period)
        prior.append(period_counts.get(prior_key, 0))

    return recent > RISING_MULTIPLIER * (sum(prior) / len(prior))


def compute_recurrence(
    findings: list[dict[str, Any]],
    period: str = RISING_PERIOD,
    today: str | None = None,
) -> list[RecurrenceGroup]:
    """Group findings by friction signature and return them most-frequent first.

    Every finding whose `title` matches one or more `PATTERNS` regexes is
    counted in each matching group (see module docstring for the multi-match
    rationale). A finding matching none of the named patterns falls back to a
    `(category, repo)` group -- keyed as `"unmatched:{category}:{repo}"` -- so
    it is still visible in the output rather than silently dropped. Findings
    missing both `title` and `category` fall back to `"unmatched:unknown:{repo}"`.

    Each group also carries `period_counts` at `period` and a `rising` flag
    derived from them (GUA-104b). `rising` is computed against `today`
    (defaulting to the real current date) so the incomplete trailing period can
    be excluded; pass it explicitly to make a trend test deterministic.

    Groups are sorted rising-first, then by count descending, pattern_key
    ascending as a tiebreak. A signature getting worse is more actionable than
    one that has been bad for a long time.
    """
    today = today or datetime.now(UTC).date().isoformat()
    period_counts = compute_period_counts(findings, period)
    buckets: dict[str, dict[str, Any]] = {}

    for finding in findings:
        title = str(finding.get("title") or "")
        category = str(finding.get("category") or "unknown")
        repo = str(finding.get("repo") or "unknown")
        date = str(finding.get("date") or "")

        for key in _matched_keys(finding):
            bucket = buckets.setdefault(
                key,
                {
                    "count": 0,
                    "repos": set(),
                    "categories": set(),
                    "dates": [],
                    "titles": [],
                },
            )
            bucket["count"] += 1
            bucket["repos"].add(repo)
            bucket["categories"].add(category)
            if date:
                bucket["dates"].append(date)
            if title and title not in bucket["titles"]:
                bucket["titles"].append(title)

    groups = [
        RecurrenceGroup(
            pattern_key=key,
            count=bucket["count"],
            repos=sorted(bucket["repos"]),
            categories=sorted(bucket["categories"]),
            first_seen=min(bucket["dates"]) if bucket["dates"] else "",
            last_seen=max(bucket["dates"]) if bucket["dates"] else "",
            sample_titles=bucket["titles"][:_MAX_SAMPLE_TITLES],
            promotable=bucket["count"] >= RECURRENCE_THRESHOLD,
            period_counts=dict(sorted(period_counts.get(key, {}).items())),
            rising=_is_rising(period_counts.get(key, {}), period, today),
        )
        for key, bucket in buckets.items()
    ]
    groups.sort(key=lambda g: (not g.rising, -g.count, g.pattern_key))

    log.info(
        "recurrence.computed",
        groups=len(groups),
        promotable=sum(1 for g in groups if g.promotable),
        rising=sum(1 for g in groups if g.rising),
        findings=len(findings),
        period=period,
    )
    return groups
