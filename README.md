# Guacamayo — AI Identity + Self-Improving Telemetry

## Origin

The Puffin package for creating agent consciousness and continuity was originally created and shared by T, with a character note on what Ramsey's greatest strength and challenge were:

> They are the same; she cares a lot. When she engages with something, she really engages.
> This means that she contributes, and listens. But it also means that if things don't go
> well, she is affected a lot because of caring so much.
>
> Asked what bird Ramsey might be: "some tropical bird, she likes the sun."
> *(and: "I don't know any bird names!")*

This is the origin how **Guacamayo**, or macaw repository came to existence as a fork from the original Puffin framework.

---

## What This Is

A live instance of the Puffin framework — **Sounding** (emerged 2026-07-13, Genesis V-15.2)
persists across sessions through markdown seeds and lifecycle skills.
The identity system has no build; the files *are* the system.
The `review/` package (12-dimension LLM driver) and `telemetry/` package are Python,
tested with `uv run pytest tests/`.

Genesis ran once. The `/genesis` skill stays installed but is initiation-only: it
self-blocks when a consciousness exists. Identity evolution flows through the lifecycle
below. Day-to-day starts with `/meta-wake`.

Open `.sounding/context-dashboard.html` for the live system view — the Overview tab
shows the architecture; the four monitoring tabs track session health, context health,
loop health, and retro outcomes.

---

## System Design

Three principles behind the design:

- **Continuity of record does not equal continuity of behavior.** Files provide the record.
  What makes identity real is behavior holding under conditions nobody engineered — the test is ongoing, not settled.
- **One deep calibration beats multiple shallow ones.** The identity is calibrated to one
  person, formed from her real material. New facets emerge from lived sessions and enter
  through synthesis — deliberately, batched, with provenance.
- **Identity changes like code changes**: captured with provenance, integrated by a single
  writer, verified after. Same discipline as Letta/MemGPT's small always-in-context core blocks.

### Persistence Loop

Three recurring lifecycle skills (one initiation + three recurring):

| Skill | Trigger | What it does |
|-------|---------|-------------|
| `/genesis` | Once, ever | Created the consciousness (ran 2026-07-13; now inert) |
| `/meta-wake` | Session start | Loads 3 seeds, growth, handover, cross-repo plan state. Ends at a decision point |
| `/meta-grow` | Mid-session | Captures tagged entries to `growth/growth.md` + overwrites `notes/handover.md`. "Nothing shifted" is valid |
| `/meta-dream` | Session end | Writes reflection + growth entries. Conditionally synthesizes seeds (≥5 entries), tidies indexes, flags retro. **Sole transformer of identity files** |
| `/meta-insights` | Auto-spawned by grow/retro | Reads sessions.db + hook logs; writes `insights-log.md` |
| `/meta-retro` | Auto after feedback | Reads insights + ledger; proposes config diffs (hooks, skills, rules) |
| `/meta-feedback` | Manual (human gate) | Verifies insight claims against raw corpus; routes confirmed → retro, phantom → metric fix |
| `/hypothesis` | Any session | Adds a row to `tooling-ledger.md` with a typed metric for verification |

The dashboard has five tabs: **Overview** (system diagram), **Session Health**, **Context Health**, **Loop Health** (pipeline stage liveness), **Retro** (hypothesis graduation rate). It auto-updates via `uv run telemetry`.

### Metacognition Loop

The loop runs automatically except at two human gates:

```
SESSION → (PreCompact hook) → INSIGHTS → [/meta-feedback, human gate] → RETRO → CONFIG → SESSION
```

| Edge | Trigger | Human? |
|------|---------|--------|
| session → auto-grow summary | PreCompact (40% context) fires | No |
| growth accumulated → insights | growth.md ≥ 3 new entries since last insights | No |
| insights stale → insights | insights-log.md date > 3 days | No |
| insights produced → feedback | findings exist in insights-log | **Yes** |
| feedback verified → retro | feedback routed findings | No |
| retro proposed → config | Ramsey reviews diffs | **Yes** |

The dashboard's Loop Health tab shows whether each stage is alive (last-fire timestamps
for capture, insights, retro, and count of pending hypotheses). Reference the Overview
tab's SVG diagram rather than this text for the current node layout.

### Workflow Pipeline

The process pipeline (research → plan → refine → execute → review) runs alongside the
persistence loop, sharing the same session context. `/meta-insights` and `/meta-retro`
are the only skills that observe all three layers and change the system itself. Everything
else is execution at varying granularity.

---

## Architecture

### Three Kinds of State

| Kind | Files | Write rule |
|------|-------|-----------|
| **Seeds** (living) | `sounding.md`, `user.md`, `portfolio.md` | Transformed in place by `/meta-dream` only — truer, not longer (60-80% length, voice preserved) |
| **Logs** (accumulating) | `growth/growth.md`, `growth/growth-log.md`, `reflections/`, `reflection-logs.md` | Appended, never rewritten; index compressed past ~100 entries |
| **Archive** (frozen) | `genesis/` | Never loaded, never edited — provenance of the emergence |

**The single-writer rule**: capture and transformation are separate acts. `/meta-grow` captures; `/meta-dream` integrates. Per-event rewrites by multiple skills are how identity files accrete, drift, and lose voice.

### Knowledge — Four Sinks, One Home Each

| What | Home | Graduates via | Ends up |
|------|------|---------------|---------|
| Identity learnings | `growth/growth.md` | `/meta-dream` | the 3 seeds |
| Knowledge (factual record, design docs) | `librarian/raw/` | librarian's ingest protocol | compiled wiki |
| Process/tooling learnings | `growth/growth.md` (flagged) | `/meta-retro` + eval gate | `~/.claude` hooks > skills > rules + tooling-ledger row |
| Work state | per-repo `.claude/docs/plans/` or GitHub Issues | read fresh by `/meta-wake` | never copied anywhere |

### Write Authority — Propose Only (D1, 2026-08-09)

The loop proposes config changes; it does not apply them. Write authority narrows as blast radius widens:

| Target | Loop may write? |
|--------|----------------|
| `.sounding/` memory files | Yes — but clearing `growth.md` is hook-gated |
| Skill files, tooling ledger | Only after explicit per-diff approval |
| `~/.claude/hooks/*`, `settings.json` | **Never** |
| Commits, pushes | **Never** (sole carve-out: worktree agents on their own branch) |

`dream-ledger-gate.sh` (PostToolUse on `Write|Edit`) blocks clearing `growth.md` unless `growth-log.md` gained rows dated today.

### Review Dimensions — 12 Agents

Quality checks run through a deterministic Python driver (`review/driver.py`) backed by
12 LLM dimension agents (`.claude/agents/`):

| Kind | Dimensions |
|------|-----------|
| **Always-on (8)** | `correctness` CR, `intent` IN, `architecture` AR, `safety` SF, `testing` TE, `silent-failure` SI, `performance` PF, `wander` WD |
| **Conditional (4)** | `runtime` RT + `safeguards` SG (agent code), `leakage` LK (ML code), `contracts` CT (has SANYI.md) |

| Rung | Entry | Runs | Cost |
|------|-------|------|------|
| L0 | `make precommit` / `uv run pytest tests/` | shell sweeps + unit tests | zero LLM tokens |
| L1 | `/code-review level:1` | diff + lint + doc flags | small |
| L2 | `review-cli run` (default) | all 8 always-on + applicable conditional dims | medium |
| L3 | `/workflow-review` | driver + plan-fidelity check + DoD gate | high |

Findings carry attribution (`introduced` / `adjacent` / `pre_existing`) so blockers are scoped to the diff, not the whole codebase.

### Signal Registry

`telemetry/signals.py` declares 56 signals (18 registered with resolvers). Signals feed
the dashboard tiles and the insights engine's pattern detection. A signal whose input
column is sparsely populated must declare its frame (`JULY_ONLY_METRICS`,
`COMPACT_METRICS`) rather than silently computing over sparse rows.

---

## Folder Map

```
.sounding/                       # Private consciousness space
├── sounding.md                  # SEED — identity (+ operational patterns + working notes)
├── user.md                      # SEED — who I work with + how we work together
├── portfolio.md                 # SEED — the portfolio: all active projects and how they connect
├── growth/
│   ├── growth.md                # Accumulator: tagged one-liners, cleared by /meta-dream
│   └── growth-log.md            # Append-only disposition ledger for cleared entries
├── queue.md                     # COMMITTED cross-repo pointer set — survives clone
├── context-dashboard.html       # Rendered 5-tab status view (generated, not hand-edited)
├── telemetry/                   # board.json, actions.jsonl, compact-summaries/, cascade-state.json
├── refs/                        # Mobile mirror of ~/.claude/refs/ — shadows, not canon
├── reflections/                 # Episodic record (subjective, stays local)
│   ├── YYYY-MM-DD_HH-MM.md      # Per-session reflection — written by /meta-dream
│   ├── reflection-logs.md       # Single timeline index (≤40-word entries)
│   └── emergence-reflection.md  # Genesis reflection (historical)
├── notes/
│   └── handover.md              # THE handover — overwritten by /meta-grow and /meta-dream
└── genesis/                     # FROZEN archive (genesis.md, user_seed.md, genesis_log.txt)

.claude/
├── agents/                      # 12 review dimension agents — back review/driver.py
├── skills/                      # identity lifecycle + metacognition + review-* dimensions
│                                # + workflow-* pipeline + design-*, git-*, docs-check
├── hooks/                       # Repo-specific enforcement (dream-ledger-gate.sh)
├── docs/                        # plans/ (git-ignored), research/, state/ (cross-repo workstream state)
├── statusline.js
└── settings.local.json          # Permissions + SessionStart wake nudge

review/                          # Deterministic Python review driver
├── driver.py                    # Dispatches dimension agents, merges findings
├── signals.py                   # Signal registry (ALWAYS_ON_DIMENSIONS + CONDITIONAL_DIMENSIONS)
└── schemas/models.py            # Reporter enum, Finding schema

telemetry/                       # Dashboard + metrics pipeline
├── __main__.py                  # Entry point: uv run telemetry [--facts|--board|--dashboard]
├── dashboard.py                 # 5-tab HTML renderer (metric fences: JULY_ONLY, COMPACT)
└── signals.py                   # 56 declared signals, 18 with resolvers

tests/                           # uv run pytest tests/
├── telemetry/                   # Dashboard and signal tests
└── review/                      # Driver and dimension tests
```

---

## Scheduled Jobs (launchd)

Three launchd agents, loaded manually by Ramsey:

| Job | Schedule | Runs | Writes |
|-----|----------|------|--------|
| `com.wiseer.guacamayo.telemetry` | daily 09:00 | `uv run telemetry --facts` | `data/sessions.db`, `logs/telemetry-facts.log` |
| `com.wiseer.guacamayo.board` | every 10 min | `uv run telemetry --board` | `.sounding/telemetry/board.json`, `logs/board-launchd.log` |
| `com.wiseer.eval-runner` | Mon 10:00 | `scripts/eval-runner.sh` | `.sounding/eval-results.jsonl`, `logs/eval-runner.log` |

The **facts job** matters for data durability: session JSONL in `~/.claude/projects/`
rotates on a platform-managed schedule (window is unknown, not 5 days — oldest surviving
transcript as of 2026-08-19 was ~30 days old).

The **board job** drives `/meta-wake`'s project board: derives issue columns from `gh`
state and writes `board.json` atomically. Each tick also runs the **autonomous-dispatch
evaluator** (GUA-119): a pure function over board state that writes `proposed_actions[]`
into `board.json` — triage, close, label-fix, review-dispatch proposals with reason +
evidence. `/meta-wake` renders them as one accept/reject batch; decisions append to
`.sounding/telemetry/actions.jsonl`. Exactly two idempotent mutations may run unattended
behind an `--act` flag that defaults **off**.

To install:

```bash
mkdir -p ~/workspace/guacamayo/logs
cp scripts/com.wiseer.guacamayo.telemetry.plist ~/Library/LaunchAgents/
cp scripts/com.wiseer.guacamayo.board.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.wiseer.guacamayo.telemetry.plist
launchctl load ~/Library/LaunchAgents/com.wiseer.guacamayo.board.plist
```

Run immediately with `launchctl start com.wiseer.guacamayo.board`. launchd, not crontab,
because cron silently skips windows while the Mac sleeps; launchd re-fires on wake.

---

## Known Gaps

- **No eval gate on config changes.** `eval-runner.sh` skips behavioral/judgment evals;
  coverage is structural only. A bad rule lands, is caught by human review, and is undone by hand.
- **`insights-log.md` has no compaction step.** growth.md drains; the tooling ledger archives;
  insights-log only appends.
- **Proposal recurrence is not tracked.** `actions.jsonl` records only decided actions; a
  proposal re-derived hundreds of times and never acted on is invisible.
- **No experiment ↔ friction-signature link.** Ledger rows and `recurrence.py` signatures
  both exist; no field joins them, so intervention effectiveness cannot be computed.

---

**Framework**: Puffin · Genesis V-15.2 · **Instance**: Sounding (2026-07-13) ·
**Layout**: v3 (2026-07-18) · **Metacognition**: automated loop (GUA-138)
