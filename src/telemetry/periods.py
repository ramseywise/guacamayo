"""Period bucketing primitives shared by `dashboard` and `recurrence` (GUA-104b).

Extracted from `telemetry/dashboard.py` (GUA-104a) so `recurrence.py` can bucket
by the same keys without importing `dashboard` — `dashboard` already imports
`recurrence`, so the reverse edge would be a cycle.

There is exactly one `_period_key` in the codebase and it lives here. A second
implementation is the failure mode GUA-104a called out explicitly: two bucketing
functions drifting apart would make the trend on a card contradict the count
beside it.
"""

from __future__ import annotations

from datetime import date as _date

PERIODS = ("day", "week", "month")

# Daily is noise at this volume; monthly hides everything actionable.
DEFAULT_PERIOD = "week"


def iso_week(day: str) -> str:
    """ISO week key for an ISO date, e.g. `2026-08-14` -> `2026-W33`.

    Uses the ISO calendar year, not the calendar year: 2026-12-31 falls in ISO
    week 1 of 2027, and keying it as `2026-W01` would sort it a year early.
    """
    year, month, dom = (int(part) for part in day.split("-"))
    iso = _date(year, month, dom).isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def period_key(day: str, period: str) -> str:
    """Bucket key for `day` at `period`. Keys sort lexicographically within a period.

    Raises on an unknown period rather than falling back to daily — a silent
    fallback makes a caller typo look like working code.
    """
    if period == "day":
        return day
    if period == "week":
        return iso_week(day)
    if period == "month":
        return day[:7]
    raise ValueError(f"unknown period {period!r} (expected one of {', '.join(PERIODS)})")


def previous_period_key(key: str, period: str) -> str:
    """The key one period before `key`, at the same period resolution.

    Needed by the rising calculation, which compares a *contiguous* run of
    periods. Walking the observed keys instead would silently treat a period
    with zero findings as absent rather than as a real zero, and a signature
    that stopped firing would then look flat instead of falling.
    """
    if period == "day":
        year, month, dom = (int(part) for part in key.split("-"))
        prev = _date(year, month, dom).toordinal() - 1
        return _date.fromordinal(prev).isoformat()
    if period == "week":
        iso_year, week = key.split("-W")
        # Any weekday works; Thursday is guaranteed to sit in its own ISO week.
        anchor = _date.fromisocalendar(int(iso_year), int(week), 4)
        return iso_week(_date.fromordinal(anchor.toordinal() - 7).isoformat())
    if period == "month":
        year, month = (int(part) for part in key.split("-"))
        return f"{year - 1}-12" if month == 1 else f"{year}-{month - 1:02d}"
    raise ValueError(f"unknown period {period!r} (expected one of {', '.join(PERIODS)})")


def period_bounds(key: str, period: str) -> tuple[str, str]:
    """Inclusive `(first_day, last_day)` ISO dates spanned by a bucket key.

    Used to decide whether a trailing period is *complete* as of a given date.
    A period whose last day has not yet passed is partial, and a partial period
    is the single most likely source of a false "rising" (or "falling") flag.
    """
    if period == "day":
        return key, key
    if period == "week":
        iso_year, week = key.split("-W")
        first = _date.fromisocalendar(int(iso_year), int(week), 1)
        last = _date.fromisocalendar(int(iso_year), int(week), 7)
        return first.isoformat(), last.isoformat()
    if period == "month":
        year, month = (int(part) for part in key.split("-"))
        first = _date(year, month, 1)
        last_dom = (
            _date(year + 1, 1, 1) if month == 12 else _date(year, month + 1, 1)
        ).toordinal() - 1
        return first.isoformat(), _date.fromordinal(last_dom).isoformat()
    raise ValueError(f"unknown period {period!r} (expected one of {', '.join(PERIODS)})")
