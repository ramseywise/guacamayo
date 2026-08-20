"""One-shot backfill of `occurred` / `occurred_source` onto existing findings (GUA-109).

The corpus predates occurrence dating, so every legacy row trends on its run `date` —
85 of the first 125 rows share a single day because one bulk sweep emitted them. This
script resolves each row's friction date from the repo it cites and adds the two new
fields in place.

**It never writes `date`, `id`, `repo`, `file`, or `title`.** Those five feed
`_finding_uid` (`factstore.py`), and changing any of them re-keys the row, orphaning
whatever the factstore already recorded against the old UID. The check is enforced, not
merely intended: `--write` re-reads what it wrote and aborts if an identity field moved.

Idempotent by default: a row that already carries `occurred` is left alone unless
`--force`. `--dry-run` is the default, because the JSONL is git-ignored and has no
history to restore from.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from telemetry.occurrence import SOURCE_RUN, SOURCE_UNRESOLVED, resolve_occurred
from telemetry.periods import iso_week

DEFAULT_CORPUS = Path(".claude/docs/review-findings.jsonl")

# Fields that feed `_finding_uid` (factstore.py) plus the row identity. Rewriting any of
# them silently orphans factstore rows, so they are verified byte-identical after a write.
IDENTITY_FIELDS = ("id", "date", "repo", "file", "title")


def read_rows(path: Path) -> list[dict]:
    """Parse the JSONL, preserving order. Blank lines are skipped, not rewritten."""
    rows = []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"FATAL: {path}:{lineno} is not valid JSON: {exc}") from exc
    return rows


def backfill_rows(
    rows: list[dict], *, workspace: Path, force: bool = False
) -> tuple[list[dict], collections.Counter]:
    """Return `(new_rows, source_counts)`. Input rows are not mutated."""
    cache: dict = {}
    counts: collections.Counter = collections.Counter()
    out = []
    for row in rows:
        new = dict(row)
        if "occurred" in row and not force:
            counts["skipped"] += 1
            out.append(new)
            continue

        occurred, source = resolve_occurred(
            row.get("repo", ""),
            row.get("file"),
            row.get("lines"),
            workspace=workspace,
            cache=cache,
        )
        if occurred is None or source == SOURCE_UNRESOLVED:
            # No usable checkout. The run date is the only thing left that is true.
            occurred, source = row.get("date"), SOURCE_RUN
        new["occurred"] = occurred
        new["occurred_source"] = source
        counts[source] += 1
        out.append(new)
    return out, counts


def concentration(rows: list[dict], key: str) -> tuple[float, int, int]:
    """`(max single-day share, distinct days, distinct ISO weeks)` for a date field.

    This is the number the whole issue turns on: while one day holds 68% of the corpus,
    every per-period trend is really measuring "was there a sweep that day".
    """
    days = collections.Counter(r[key] for r in rows if r.get(key))
    if not days:
        return 0.0, 0, 0
    weeks = {iso_week(d) for d in days}
    return max(days.values()) / sum(days.values()), len(days), len(weeks)


def print_table(before: list[dict], after: list[dict], counts: collections.Counter) -> None:
    b_share, b_days, b_weeks = concentration(before, "date")
    a_share, a_days, a_weeks = concentration(after, "occurred")
    print(f"rows: {len(after)}")
    print(f"{'metric':<26}{'before (date)':>16}{'after (occurred)':>18}")
    print(f"{'max single-day share':<26}{b_share:>15.0%}{a_share:>18.0%}")
    print(f"{'distinct dates':<26}{b_days:>16}{a_days:>18}")
    print(f"{'ISO weeks covered':<26}{b_weeks:>16}{a_weeks:>18}")
    print("sources: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    weekly = collections.Counter(iso_week(r["occurred"]) for r in after if r.get("occurred"))
    print("weekly:  " + ", ".join(f"{k}={v}" for k, v in sorted(weekly.items())))


def assert_identity_preserved(before: list[dict], after: list[dict]) -> None:
    """Abort unless every identity field survived byte-identical.

    A backfill that re-keys rows is worse than no backfill: the factstore keeps the old
    UIDs and the corpus silently splits in two.
    """
    if len(before) != len(after):
        raise SystemExit(f"FATAL: row count changed {len(before)} -> {len(after)}")
    for i, (old, new) in enumerate(zip(before, after, strict=True)):
        for field in IDENTITY_FIELDS:
            if old.get(field) != new.get(field):
                raise SystemExit(
                    f"FATAL: row {i} field {field!r} changed "
                    f"{old.get(field)!r} -> {new.get(field)!r}; refusing to write"
                )


def write_atomically(path: Path, rows: list[dict]) -> None:
    """Back up to `<path>.bak`, then replace via a temp file in the same directory.

    `os.replace` is atomic within a filesystem, so an interrupted run leaves either the
    old file or the new one — never a half-written corpus.
    """
    shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--path", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument(
        "--workspace", type=Path, default=Path.home() / "workspace", help="repo checkout root"
    )
    parser.add_argument(
        "--write", action="store_true", help="perform the rewrite (default is a dry run)"
    )
    parser.add_argument(
        "--force", action="store_true", help="re-resolve rows that already have `occurred`"
    )
    args = parser.parse_args(argv)

    if not args.path.exists():
        print(f"FATAL: {args.path} not found", file=sys.stderr)
        return 1

    before = read_rows(args.path)
    after, counts = backfill_rows(before, workspace=args.workspace, force=args.force)
    print_table(before, after, counts)
    assert_identity_preserved(before, after)

    if not args.write:
        print("\ndry run — nothing written. Re-run with --write to apply.")
        return 0

    write_atomically(args.path, after)
    # Re-read from disk: verify what actually landed, not what we meant to land.
    assert_identity_preserved(before, read_rows(args.path))
    print(f"\nwrote {len(after)} rows to {args.path} (backup: {args.path}.bak)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
