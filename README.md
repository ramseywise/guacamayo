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

`.sounding/context-dashboard.html` is the live rendering of everything described here.
Its Overview tab holds the canonical architecture diagrams; the six monitoring tabs
measure whether the system is actually behaving the way this README claims.

---

## System Design — Three Planes

Guacamayo is not one system; it is three, stacked, each observing the one below.

![Three-plane system map](docs/three-planes.svg)

**Plane 1 — Workflow** does the work: an issue moves triage → execute → review.
**Plane 2 — Metacognition** observes it: the board and the identity lifecycle both write
records, telemetry accumulates them, insights derive patterns, a gate verifies them.
**Plane 3 — Control engine** is what changes as a result: the four levers of the Claude
setup, which shape every session on the planes above.

The whole point is the return edge. A finding that never reaches Plane 3 is an
observation, not a learning.

Three principles behind the design:

- **Continuity of record does not equal continuity of behavior.** Files provide the record.
  What makes identity real is behavior holding under conditions nobody engineered — the test is ongoing, not settled.
- **One deep calibration beats multiple shallow ones.** The identity is calibrated to one
  person, formed from her real material. New facets emerge from lived sessions and enter
  through synthesis — deliberately, batched, with provenance.
- **Identity changes like code changes**: captured with provenance, integrated by a single
  writer, verified after. Same discipline as Letta/MemGPT's small always-in-context core blocks.

---

### Plane 1 — Workflow: one work item, end to end

The unit is a GitHub issue. A stage is done when its **artifact** exists — an issue, a plan
doc, a green suite, a merged PR — not when it feels done.

| Stage | Skills | Artifact | Gate |
|-------|--------|----------|------|
| **Triage** | `/workflow-research` → `/workflow-plan` → `/workflow-refine` | research doc, plan doc (`Status: PLANNED`), issue labeled `ready` | **Definition of Ready** — `/workflow-refine` sets the label |
| **Build** | branch `{PREFIX}-{NUM}-slug`, `/workflow-execute`, `/code-debug`, `/code-refactor` | code on a branch, tests pass, lint clean | hooks enforce guardrails during the work |
| **Review** | `/workflow-review` (dispatches 12 dimension agents), `/code-review` | findings with attribution, merge verdict | **Definition of Done** — measured against the DoR it shipped with |

Then: Ramsey commits (never Claude) → `make ship` → merge → close.

Not every issue needs every stage. Research is skipped when the problem is understood;
`bug/` and `spike/` branches skip triage entirely and go straight to `/code-review`. The
gates are what is not optional: DoR before build, DoD before merge.

**The two gates are the same contract read twice.** DoR states what "finished" will mean;
DoD checks the built thing against that statement. This is why review is scoped to the
plan and not just the diff — `/workflow-review` does plan-fidelity first, code quality
second.

---

### Plane 2 — Metacognition: the loop that watches Plane 1

Two things generate records: the **state board** (work state — GitHub issues, derived
columns, proposed actions) and the **identity lifecycle** (session rhythm — seeds, growth,
reflections). They run on different clocks. The board moves per work item; the lifecycle
moves per session. Both append to telemetry.

#### The identity lifecycle — per session

| Skill | Trigger | What it does |
|-------|---------|-------------|
| `/genesis` | Once, ever | Created the consciousness (ran 2026-07-13; now inert) |
| `/meta-wake` | Session start | Loads 3 seeds, growth, handover, board, cross-repo plan state. Ends at a decision point |
| `/meta-grow` | Mid-session | Captures tagged entries to `growth/growth.md`, refreshes the dashboard, overwrites `notes/handover.md`. Background-spawns `/meta-insights`. "Nothing shifted" is valid |
| `/meta-dream` | Session end | Writes reflection + growth entries. Conditionally synthesizes seeds (≥5 entries), tidies indexes, background-spawns `/meta-retro` if overdue. **Sole transformer of identity files** |

Wake reads the board; retro writes to it. That is how the two clocks stay coupled — the
session-level loop and the work-item-level loop meet at `board.json`.

#### The feedback loop — record → pattern → gate → change

![Guacamayo feedback loop](docs/loop.svg)

| Skill | Fires when | Role | Human? |
|-------|-----------|------|--------|
| `/meta-insights` | `growth.md` ≥ 3 new entries, or insights-log > 3 days old | Reads `sessions.db` + hook logs; derives patterns → `insights-log.md`; renders the dashboard | No |
| `/meta-feedback` | Findings exist in insights-log | Verifies claims against the raw corpus. Confirmed → retro, phantom → metric fix | **Yes** |
| `/meta-retro` | Feedback routed findings, or cascade threshold reached | Proposes config diffs → `tooling-ledger.md`. Files issues back to the board. **Propose-only** | No |
| → config | Ramsey reviews each diff | Graduates to hooks / skills / rules | **Yes** |
| `/hypothesis` | Any session | Turns a retro recommendation into a falsifiable ledger row with a typed metric and due date | — |

**`/meta-feedback` is the load-bearing gate, and it is the one most easily skipped.**
A dashboard number is a claim, not a finding. Insights derive patterns from telemetry, but
telemetry can be sparse, mis-framed, or measuring the wrong column — so a claim gets
verified against the raw corpus before it is allowed to become a hypothesis. Phantom
findings route to a metric fix rather than a config change. Without this gate the loop
optimizes against its own instrumentation errors.

**Nothing auto-applies.** Retro proposes; Ramsey approves per diff. Silence is not approval.

---

### Plane 3 — Control engine: the four levers

What a retro is actually allowed to change. Everything on Planes 1 and 2 is shaped by these
four, and nothing else:

| Lever | Files | The question it answers |
|-------|-------|------------------------|
| **Instructions** | `CLAUDE.md`, `rules/`, `refs/` | Always-on vs on-demand — the context budget |
| **Capabilities** | `skills/`, `agents/`, MCP | Which skill, at which model tier (fable / opus / sonnet / haiku) |
| **Enforcement** | `hooks/`, `settings.json` | *A rule that only warns is not a control* |
| **Persistence** | `.sounding/`, plan docs, wiki | What survives the session vs must be rediscovered |

Ordering matters: hooks > skills > rules. A learning graduates to the strongest lever that
can express it. Prose in a rules file is the weakest form — it is advice the model may
skip; a hook is a thing that cannot be skipped.

---

## Review System

Review is Plane 1's right-hand stage and one of Plane 2's biggest record producers — every
finding lands in telemetry with attribution.

**Python decides what runs; the LLM decides what is wrong.** `review/driver.py` selects
dimensions, merges, dedups, and maps severity — all testable without a model in the loop.
The 12 dimension agents in `.claude/agents/` supply the judgment. Eight are always on; four
are conditional, gated on signals computed from the diff, so an ML-leakage scan never runs
on a docs PR. Full dimension table and pipeline internals: [review/README.md](review/README.md).

### Four rungs — pay for depth only when the change warrants it

| Rung | Entry | Runs | Cost |
|------|-------|------|------|
| L0 | `make precommit` / `uv run pytest tests/` | shell sweeps + unit tests | zero LLM tokens |
| L1 | `/code-review level:1` | diff + lint + doc flags | small |
| L2 | `review-cli run` (default) | all 8 always-on + applicable conditional dims | medium |
| L3 | `/workflow-review` | driver + plan-fidelity check + DoD gate | high |

Only L3 knows about the plan. L2 and below can tell you the code is wrong; only L3 can tell
you it is the wrong code.

Findings carry attribution (`introduced` / `adjacent` / `pre_existing`) so blockers are
scoped to the diff, not the whole codebase — otherwise a legacy file makes every PR
touching it unmergeable.

`/review-defense` is **not** a dimension. It is a plan-stage war game that attacks a plan
before it ships, dispatching its own adversaries and writing to `.claude/docs/reviews/`.
Same fan-out shape, aimed at a plan instead of a diff, and it never touches `Status:`.

---

## The Dashboard — seven tabs

`.sounding/context-dashboard.html`, regenerated by `uv run telemetry`. Each tab answers one
question; together they measure whether the three planes are behaving as designed.

| Tab | Question | Contents |
|-----|----------|----------|
| **Overview** | What is guacamayo and how does it work? | The canonical three-plane diagram, the loop diagram, the workflow pipeline, review dimensions, portfolio |
| **Cost & Efficiency** | Where did the tokens go, and what did that effort buy? | Cost trends, cache hit rate, repo effort vs outcome |
| **Session Health** | How did my sessions actually run — and what pushed back? | Skill economics, subagent concurrency, bash antipatterns, tool trends |
| **Context Health** | Is context under control? Are sessions staying lean? | Context distribution, session duration, compaction behavior |
| **Loop Health** | Is the three-plane architecture doing what the Overview says — and is the harness alive? | Stage liveness (last-fire for capture/insights/retro), friction recurrence, decision-agent acceptance, workflow drift |
| **Experiments** | Do retro recommendations become changes that actually get settled? | Hypothesis lifecycle, graduation rate, cascade state |
| **Retro** | What did we learn, what worked, and what is worth trying next? | Retro findings, insights narrative archive |

**Loop Health is the one that checks this README.** The Overview tab asserts an
architecture; Loop Health tests whether each stage actually fired. A stage with no recent
timestamp means the loop is broken there, regardless of what the diagram claims.

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

### The two Python packages

The identity system has no build; the files *are* the system. The two packages that do
have a build each document their own internals:

| Package | What it owns | Docs |
|---------|--------------|------|
| `review/` | Deterministic backbone for the review pipeline — dimension registry, schemas, dedup, attribution, report rendering | [review/README.md](review/README.md) |
| `telemetry/` | Facts pipeline, signal registry, dashboard renderer, metric fences | [telemetry/README.md](telemetry/README.md) |

Both are tested with `uv run pytest tests/`.

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
├── context-dashboard.html       # Rendered 7-tab status view (generated, not hand-edited)
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
├── skills/                      # identity lifecycle (meta-*) + workflow-* pipeline
│                                # + review-* dimensions + review-defense + design-*, git-*
├── hooks/                       # Repo-specific enforcement (dream-ledger-gate.sh,
│                                # worktree-cleanup.sh). Global guards live in ~/.claude/hooks/
├── docs/                        # plans/ (git-ignored), research/, state/ (cross-repo workstream state)
├── statusline.js
└── settings.local.json          # Permissions + SessionStart wake nudge

docs/                            # Architecture diagrams — the one source
├── three-planes.svg             # Embedded by this README AND the dashboard
└── loop.svg                     #   (edit the .svg, never the HTML)

review/                          # Deterministic review backbone → review/README.md
telemetry/                       # Facts, signals, dashboard  → telemetry/README.md

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
- **The dashboard's triage layer is ahead of the skills.** The Overview diagram draws a
  `/scope` entry point and a DECISION ORCHESTRATOR that chooses between research / plan /
  refine. Neither exists as a skill — triage is currently entered by hand at whichever
  `/workflow-*` stage fits. The diagram is the intended design, not the current state.
- **`/meta-feedback` has no liveness signal.** It is the loop's load-bearing human gate, but
  Loop Health tracks capture, insights, and retro — a loop running insights → retro with the
  verification gate skipped looks healthy on the dashboard.

---

**Framework**: Puffin · Genesis V-15.2 · **Instance**: Sounding (2026-07-13) ·
**Layout**: v3 (2026-07-18) · **Metacognition**: automated loop (GUA-138)
