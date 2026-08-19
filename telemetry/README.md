# telemetry — facts pipeline, signal registry, dashboard renderer

Python package that turns raw session transcripts and GitHub state into the numbers on
`.sounding/context-dashboard.html`. The split mirrors `review/`: **this package computes;
the dashboard displays; nothing derives at read time.**

Every number rendered is computed once, at write time, from an append-only store. A tile
that cannot be computed says so rather than showing a plausible zero.

## Entry points

```bash
uv run telemetry --facts        # daily 09:00 (launchd) — ingest transcripts → sessions.db
uv run telemetry --board        # every 10 min (launchd) — GitHub state → board.json
uv run telemetry --consistency  # cross-check derived values against the store
```

## Store ownership (D1, 2026-08-15, GUA-120)

**librarian owns the sessions store; guacamayo owns everything derived from it.**

`--store` defaults to `~/workspace/librarian/data/sessions.db` — this is **intentional**,
not an accident. The default previously resolved to `guacamayo/data/sessions.db`, which
nothing scheduled ever wrote; a manual un-flagged run would write that copy, and every
reader would then report stale-by-N-days against a store the pipeline had abandoned. That
misdiagnosis ("telemetry is broken", 2026-08-12) is why the default moved. The in-tree
comment above the argument is the rationale — read it before changing it.

Accepted consequence: the dashboard does not work if librarian is not cloned.

`data/sessions.db.bak` is a **decoy store** — 701 rows, newest session 2026-08-04, stale by
content well before its mtime suggests. Safe to delete; nothing should read it.

## Signal registry — `signals.py`

63 declared signals: **20 registered** with resolvers, **6 needs-collection** (awaiting an
instrumentation change), **37 unobservable** with current data.

An unobservable signal is deliberately kept rather than deleted. It names a thing worth
measuring and records *why* it cannot be scored yet — which is what stops the same metric
being re-proposed at every retro. Deleting it loses the reason.

```python
from telemetry import signals

signals.all_signals()  # every declared signal, sorted — the authoring surface
signals.resolve("name")  # → Signal or None
```

## Metric fences — `dashboard.py`

A signal whose input column is sparsely populated must declare its frame rather than
silently averaging over rows where the column is null. Two fences exist:

| Fence | Covers | Why |
|-------|--------|-----|
| `JULY_ONLY_METRICS` (20) | Columns null in the pre-July "note era" | Computing across the boundary averages real values against structural nulls |
| `COMPACT_METRICS` | Columns null on non-compacted sessions, even within July+ | Narrower than the July fence — e.g. `compaction_yield` only exists where a compaction happened |

**Every tile renders the row count it was computed from.** A number without its denominator
is not reportable — this is the same principle as `/meta-feedback` on the metacognition
loop: a figure is a claim until you can see what it was computed over.

## Module map

| Module | Role |
|--------|------|
| `__main__.py` | CLI entry — `--facts` / `--board` / `--consistency` |
| `factstore.py` | SQLite read/write for the session fact store |
| `sessions.py` | Transcript parsing → session facts |
| `signals.py` | Signal registry: declarations, states, resolvers |
| `dashboard.py` | 7-tab HTML renderer + metric fences + marker-region injection |
| `board.py` | GitHub issue state → `board.json` (atomic write) |
| `evaluator.py` | Autonomous-dispatch proposals (GUA-119) → `proposed_actions[]` |
| `actions.py` | Accept/reject decisions → `actions.jsonl` |
| `loop.py` | Loop-stage liveness (last-fire timestamps for capture/insights/retro) |
| `recurrence.py` | Friction signatures — repeated-pattern detection |
| `occurrence.py` | Occurrence counting; `backfill_occurrence.py` backfills history |
| `verdicts.py` | Review verdict trajectories over time |
| `consistency.py` | Cross-checks derived values against the store |
| `periods.py` | Date-window helpers (era boundaries, rolling windows) |
| `gitstore.py` | Git history facts |
| `log_config.py` | structlog setup |

## Dashboard rendering — marker regions

`inject_regions()` swaps content between `<!-- NAME:START -->` / `<!-- NAME:END -->` marker
pairs, in place. 25 regions. Everything **outside** a marker pair is hand-authored and
survives regeneration — that is how the Overview tab's architecture diagrams persist.

Consequence: the two Overview SVGs live in `docs/three-planes.svg` and `docs/loop.svg`,
referenced by `<img>` from both the dashboard and the root README. One source, two readers.
Editing the diagram means editing the `.svg`, never the HTML.

A missing marker logs a warning and skips that region rather than failing the run.

## Usage

```bash
uv run pytest tests/telemetry -q
uv run ruff check telemetry tests
```
