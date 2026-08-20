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
single-valued per finding. Re-verified against the live 145-row corpus after the
GUA-115 signatures landed: 4 findings match more than one pattern, so this choice
still has negligible effect on `RECURRENCE_THRESHOLD`-gated promotion in practice.

Trend (GUA-104b): `count` alone is a lifetime total, so a signature that fired
5x in April and stopped is indistinguishable from one firing 5x this week --
which means the friction report ranks by accumulated history, and history is
dominated by whatever has been measured longest. `compute_period_counts` buckets
the same groups by period and `direction` marks the recent surges, so a
newly-rising pattern no longer sorts last.

Occurrence dating (GUA-109): those periods are keyed on each finding's `occurred`
date -- when the cited code was last touched -- not on `date`, the day the sweep
ran. Bucketing on the run date made the trend measure sweep scheduling rather than
friction: one bulk sweep stamped 85 of 125 rows with a single day, so every
signature it touched appeared to spike simultaneously. `direction` is three-valued
for a related reason -- a boolean could not distinguish "this friction stopped"
from "this friction never moved", which are opposite outcomes for a fix.
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

# Direction values (GUA-109). Strings rather than an enum: these are serialized into the
# dashboard and read back from JSON, where an enum would only add a conversion step.
DIRECTION_RISING = "rising"
DIRECTION_FLAT = "flat"
DIRECTION_FALLING = "falling"

# Falling is the mirror of rising: the recent period must be below the prior mean by the
# same multiplier. The extra gate is on the PRIOR mean, not the recent count -- a signature
# has to have had real mass to be worth calling "falling", otherwise every 1 -> 0 signature
# in the corpus reads as an improvement and drowns the ones that matter.
FALLING_MIN_PRIOR_MEAN = RECURRENCE_THRESHOLD

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
    # Added 2026-08-15 (GUA-115): 76 of 145 corpus rows were `unmatched:` fallbacks.
    # Derived by reading every unmatched title, same method as the 2026-08-10 pair.
    # Each of these six clears RECURRENCE_THRESHOLD on its own phrasing -- none was
    # widened to reach n=3 (see `god-module` and its pinning test for the precedent).
    #
    # Absence-of-gate only. The corpus carries no severity or polarity field, so the
    # regex is the sole thing separating "no auth here" from "auth is present" --
    # topic words like "path traversal" match both and are deliberately excluded.
    "unguarded-write": (
        r"(without|lacks|no) (user )?(confirmation|authentication|auth\b|opt-out|approval"
        r"|rate-limit)|unauthenticated"
    ),
    # Work or storage that scales without a ceiling -- distinct from `resource-leak`,
    # which is about a handle never released rather than a bound never set.
    "unbounded-growth": (
        r"unbounded|no rotation|no caching|recomputes all|entire \w+ \w+ on every"
        r"|without (a )?(cap|limit)|no (size )?limit"
    ),
    "race-condition": r"race condition|\btoctou\b|collision risk",
    # Repeated work per call/request. Overlaps `unbounded-growth` on one corpus title
    # that is honestly both (recompute-per-search AND uncached); the all-matches policy
    # counts it in each, which is the intended behaviour, not double-counting to fix.
    "repeated-per-call-work": r"n\+1|per-call import|inline import|on every (search|request|call)",
    # An error that was detected but never reached whoever could act on it.
    "error-not-surfaced": (
        r"not surfaced|logged but not|summary-only|without client-side awareness"
    ),
    "doc-implementation-mismatch": (
        r"does not match implementation|in code vs\.|docstring claims|plan documentation says"
    ),
    # Added 2026-08-19 (GUA-145): cross-repo prefix on a branch mismatches the repo
    # being changed. Source: 2026-07-31 ledger row, three named instances.
    "branch-prefix-mismatch": r"cross-repo prefix|prefix.*mismatch|branch.*wrong repo|wrong.*prefix",
    # Added 2026-08-19 (GUA-145): Bash used where a native tool applies (Read/Grep/
    # Glob/Edit). Source: R7 F5, Bash antipatterns at 49% of all tool calls.
    "substitutable-bash-call": (
        r"bash antipattern|substitutable.*(command|tool)"
        r"|cat.*instead of Read|grep.*instead of Grep"
        r"|find.*instead of Glob"
    ),
    # Added 2026-08-19 (GUA-145): code or config assumes a path that no longer exists
    # after rename/move. Source: R10 F8, file-not-found at +43% in 3 days.
    "stale-path-assumption": (r"file[- ]not[- ]found|stale.*path|path.*removed|no longer exists"),
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
    # GUA-109. A boolean could only say "surging or not", collapsing "this stopped
    # happening" into the same value as "this never moved" -- so a fixed friction and a
    # steady one were indistinguishable. `direction` separates them; `rising` stays as a
    # derived property so #106's consumers keep working unchanged.
    direction: str = DIRECTION_FLAT

    @property
    def rising(self) -> bool:
        """Back-compat view of `direction` for pre-GUA-109 consumers."""
        return self.direction == DIRECTION_RISING


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


def _occurred_date(finding: dict[str, Any]) -> str:
    """The date to trend on: `occurred` when present, else the run `date` (GUA-109).

    The single date accessor, for the same reason `_matched_keys` is the single matcher:
    `compute_period_counts` and `compute_recurrence` must never disagree about when a
    finding happened, or the trend on a card would contradict the first/last-seen beside it.

    The `date` fallback is what makes this safe to deploy against a partially-backfilled
    corpus -- a row written before GUA-109 still lands in a period rather than vanishing
    from the trend.
    """
    return str(finding.get("occurred") or finding.get("date") or "")


def compute_period_counts(
    findings: list[dict[str, Any]], period: str = RISING_PERIOD
) -> dict[str, dict[str, int]]:
    """Per-signature, per-period finding counts: `{pattern_key: {period_key: n}}`.

    Same grouping as `compute_recurrence` (shared `_matched_keys`, so the same
    all-matches policy), bucketed by `telemetry.periods.period_key`.

    Bucketed on `occurred` (the friction date) falling back to `date` -- see
    `_occurred_date`. Findings with neither cannot be placed in a period and are excluded.
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
        date = _occurred_date(finding)
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


def _direction(period_counts: dict[str, int], period: str, today: str) -> str:
    """Which way a signature's per-period counts are trending.

    Returns `rising`, `falling`, or `flat`. The most recent COMPLETE period is compared
    against the mean of the `RISING_LOOKBACK` periods before it, counting a period with no
    findings as a real zero rather than skipping it -- a signature that stopped firing must
    read as falling, not as flat.

    - **rising**: recent `> RISING_MULTIPLIER x` the prior mean, AND recent
      `>= RECURRENCE_THRESHOLD` in absolute terms, which suppresses 0 -> 1 as an
      infinite rise.
    - **falling**: recent `< prior mean / RISING_MULTIPLIER`, AND the prior mean was at
      least `FALLING_MIN_PRIOR_MEAN` -- the mass gate is on the *prior* side, because what
      makes a decline worth reporting is that there was something there to decline from.
    - **flat**: everything else, including every signature with no counts at all.

    The trailing period is excluded when incomplete (Open Question 5). A three-day-old week
    is not a low week, and treating it as one is the single most likely source of a false
    flag -- in both directions, which matters more now that `falling` is also reportable.

    "Most recent" is measured against `today`, NOT against the last period that happens to
    have data. Reading it off the observed keys would make every signature rising at its own
    final burst: a pattern that fired 5x in April and stopped would compare that April week
    against the three empty weeks before it and flag, which is precisely backwards.
    """
    if not period_counts:
        return DIRECTION_FLAT

    # The last period that has fully elapsed as of `today`, whether or not this
    # signature fired in it. An absent key here is a real zero.
    recent_key = period_key(today, period)
    if period_bounds(recent_key, period)[1] > today:
        recent_key = previous_period_key(recent_key, period)

    recent = period_counts.get(recent_key, 0)

    prior_key = recent_key
    prior: list[int] = []
    for _ in range(RISING_LOOKBACK):
        prior_key = previous_period_key(prior_key, period)
        prior.append(period_counts.get(prior_key, 0))
    prior_mean = sum(prior) / len(prior)

    if recent >= RECURRENCE_THRESHOLD and recent > RISING_MULTIPLIER * prior_mean:
        return DIRECTION_RISING
    if prior_mean >= FALLING_MIN_PRIOR_MEAN and recent < prior_mean / RISING_MULTIPLIER:
        return DIRECTION_FALLING
    return DIRECTION_FLAT


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

    Each group also carries `period_counts` at `period` and a `direction`
    derived from them (GUA-104b, three-valued since GUA-109; `rising` remains
    available as a property). `direction` is computed against `today`
    (defaulting to the real current date) so the incomplete trailing period can
    be excluded; pass it explicitly to make a trend test deterministic.

    Periods and `first_seen`/`last_seen` are keyed on each finding's `occurred` date, not
    the date its sweep ran -- see `_occurred_date`.

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
        date = _occurred_date(finding)

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
            direction=_direction(period_counts.get(key, {}), period, today),
        )
        for key, bucket in buckets.items()
    ]
    groups.sort(key=lambda g: (not g.rising, -g.count, g.pattern_key))

    log.info(
        "recurrence.computed",
        groups=len(groups),
        promotable=sum(1 for g in groups if g.promotable),
        rising=sum(1 for g in groups if g.rising),
        falling=sum(1 for g in groups if g.direction == DIRECTION_FALLING),
        findings=len(findings),
        period=period,
    )
    return groups
