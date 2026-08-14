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
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import structlog

log = structlog.get_logger(__name__)

# Open Question 6 -- tunable; two independent derivations, no CI. A pattern
# firing fewer than 3 times in the corpus is treated as noise, not recurrence.
RECURRENCE_THRESHOLD = 3

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


def compute_recurrence(findings: list[dict[str, Any]]) -> list[RecurrenceGroup]:
    """Group findings by friction signature and return them most-frequent first.

    Every finding whose `title` matches one or more `PATTERNS` regexes is
    counted in each matching group (see module docstring for the multi-match
    rationale). A finding matching none of the named patterns falls back to a
    `(category, repo)` group -- keyed as `"unmatched:{category}:{repo}"` -- so
    it is still visible in the output rather than silently dropped. Findings
    missing both `title` and `category` fall back to `"unmatched:unknown:{repo}"`.

    Groups are sorted by count descending, pattern_key ascending as a tiebreak.
    """
    buckets: dict[str, dict[str, Any]] = {}

    for finding in findings:
        title = str(finding.get("title") or "")
        category = str(finding.get("category") or "unknown")
        repo = str(finding.get("repo") or "unknown")
        date = str(finding.get("date") or "")

        matched_keys = [key for key, rx in _COMPILED_PATTERNS.items() if rx.search(title)]
        if not matched_keys:
            matched_keys = [f"unmatched:{category}:{repo}"]

        for key in matched_keys:
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
        )
        for key, bucket in buckets.items()
    ]
    groups.sort(key=lambda g: (-g.count, g.pattern_key))

    log.info(
        "recurrence.computed",
        groups=len(groups),
        promotable=sum(1 for g in groups if g.promotable),
        findings=len(findings),
    )
    return groups
