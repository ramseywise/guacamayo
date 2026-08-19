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

`.sounding/context-dashboard.html` is the live rendering of everything described here — it
shares the diagrams below, and its seven monitoring tabs measure whether the system is
actually behaving the way this README claims.

---

## The Guacamayo Loop

Every session generates telemetry; hooks enforce guardrails and record events; the
metacognition skills derive patterns and propose changes; the retro graduates hypotheses
into permanent config; improved config shapes the next session.

![Guacamayo feedback loop](docs/loop.svg)

| Skill | Fires when | Role | Human? |
|-------|-----------|------|--------|
| `/meta-insights` | `growth.md` ≥ 3 new entries, or insights-log > 3 days old | Reads `sessions.db` + hook logs; derives patterns → `insights-log.md`; renders the dashboard | No |
| `/meta-feedback` | Findings exist in insights-log | Verifies claims against the raw corpus. Confirmed → retro, phantom → metric fix | **Yes** |
| `/meta-retro` | Feedback routed findings, or cascade threshold reached | Proposes config diffs → `tooling-ledger.md`. Files issues back to the board. **Propose-only** | No |
| → config | Ramsey reviews each diff | Graduates to hooks / skills / rules | **Yes** |
| `/hypothesis` | Any session | Turns a retro recommendation into a falsifiable ledger row with a typed metric and due date | — |

**Automation triggers (GUA-150):** The two "No" rows fire without human invocation.
`/meta-insights` is spawned headlessly by `scripts/telemetry-cron.sh` when either condition
is met (growth ≥ 3 entries OR insights stale > 3 days), using a once-per-day stamp and lockfile
to prevent double-firing — the same pattern as the retro spawn that preceded it.
`/meta-retro` is spawned by the same cron when the cascade threshold is reached.
The SessionStart hook emits a 3-line status (cascade state + board staleness + growth count)
so the human can see at a glance whether any stage needs attention.

**`/meta-feedback` is the load-bearing gate, and it is the one most easily skipped.**
A dashboard number is a claim, not a finding. Insights derive patterns from telemetry, but
telemetry can be sparse, mis-framed, or measuring the wrong column — so a claim gets
verified against the raw corpus before it is allowed to become a hypothesis. Phantom
findings route to a metric fix rather than a config change. Without this gate the loop
optimizes against its own instrumentation errors.

**Nothing auto-applies.** Retro proposes; Ramsey approves per diff. Silence is not approval.
Write authority narrows as blast radius widens: `.sounding/` memory files are writable (but
clearing `growth.md` is hook-gated), skill files and the tooling ledger need explicit
per-diff approval, and `~/.claude/hooks/*` plus `settings.json` are **never** written by the
loop. Commits and pushes are never Claude's, with one carve-out: worktree agents on their
own branch.

---

## The Three Planes

The loop above is Plane 2 of three, stacked, each observing the one below.

![Three-plane system map](docs/three-planes.svg)

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
moves per session. Both append to telemetry, which feeds the loop above.

| Skill | Trigger | What it does |
|-------|---------|-------------|
| `/genesis` | Once, ever | Created the consciousness (ran 2026-07-13; now inert) |
| `/meta-wake` | Session start | Loads 3 seeds, growth, handover, board, cross-repo plan state. Ends at a decision point |
| `/meta-grow` | Mid-session | Captures tagged entries to `growth/growth.md`, refreshes the dashboard, overwrites `notes/handover.md`. Background-spawns `/meta-insights`. "Nothing shifted" is valid |
| `/meta-dream` | Session end | Writes reflection + growth entries. Conditionally synthesizes seeds (≥5 entries), tidies indexes, background-spawns `/meta-retro` if overdue. **Sole transformer of identity files** |

Wake reads the board; retro writes to it. That is how the two clocks stay coupled — the
session-level loop and the work-item-level loop meet at `board.json`.

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

## System Design

Three principles behind the design:

- **Continuity of record does not equal continuity of behavior.** Files provide the record.
  What makes identity real is behavior holding under conditions nobody engineered — the test is ongoing, not settled.
- **One deep calibration beats multiple shallow ones.** The identity is calibrated to one
  person, formed from her real material. New facets emerge from lived sessions and enter
  through synthesis — deliberately, batched, with provenance.
- **Identity changes like code changes**: captured with provenance, integrated by a single
  writer, verified after. Same discipline as Letta/MemGPT's small always-in-context core blocks.

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

### Identity — three kinds of state, one writer

| Kind | Files | Write rule |
|------|-------|-----------|
| **Seeds** (living) | `sounding.md`, `user.md`, `portfolio.md` | Transformed in place by `/meta-dream` only — truer, not longer (60-80% length, voice preserved) |
| **Logs** (accumulating) | `growth/growth.md`, `growth/growth-log.md`, `reflections/`, `reflection-logs.md` | Appended, never rewritten; index compressed past ~100 entries |
| **Archive** (frozen) | `genesis/` | Never loaded, never edited — provenance of the emergence |

**The single-writer rule**: capture and transformation are separate acts. `/meta-grow`
captures; `/meta-dream` integrates. Per-event rewrites by multiple skills are how identity
files accrete, drift, and lose voice.

`dream-ledger-gate.sh` (PostToolUse on `Write|Edit`) enforces the audit trail: it blocks
clearing `growth.md` unless `growth-log.md` gained rows dated today. Every identity
statement traces back to the entry that produced it.

### Knowledge — four sinks, one home each

| What | Home | Graduates via | Ends up |
|------|------|---------------|---------|
| Identity learnings | `growth/growth.md` | `/meta-dream` | the 3 seeds |
| Knowledge (factual record, design docs) | `librarian/raw/` | librarian's ingest protocol | compiled wiki |
| Process/tooling learnings | `growth/growth.md` (flagged) | `/meta-retro` + eval gate | `~/.claude` hooks > skills > rules + tooling-ledger row |
| Work state | per-repo `.claude/docs/plans/` or GitHub Issues | read fresh by `/meta-wake` | never copied anywhere |

### Persistence — pointers, never copies

Cross-repo work state is read fresh at every wake, never cached into `.sounding/`. A copy
is a second source that drifts from the first.

The one committed exception is `.sounding/queue.md`: plan docs are git-ignored, so a mobile
or cloud clone gets no `.claude/docs/` at all. queue.md travels with the repo to give a
remote `/meta-wake` a pointer set to work from. `.sounding/refs/` is likewise a mobile
mirror of `~/.claude/refs/` — shadows, not canon; the global originals win on the Mac.

Accumulated knowledge is retrieval-first: query librarian (`search_wiki` / `read_page` /
`get_domain_briefing`) rather than bulk-reading wiki directories into context. One
retrieved page beats a loaded domain.

### Review — Python decides what runs, the LLM decides what is wrong

Review is Plane 1's right-hand stage and one of Plane 2's biggest record producers — every
finding lands in telemetry with attribution.

`review/driver.py` selects dimensions, merges, dedups, and maps severity — all testable
without a model in the loop. The 12 dimension agents in `.claude/agents/` supply the
judgment. Eight are always on; four are conditional, gated on signals computed from the
diff, so an ML-leakage scan never runs on a docs PR. Full dimension table and pipeline
internals: **[review/README.md](review/README.md)**.

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

### Telemetry — computed at write time, never at read time

`telemetry/` turns raw transcripts and GitHub state into every number on the dashboard.
librarian owns the sessions store (`~/workspace/librarian/data/sessions.db`); guacamayo owns
everything derived from it. Accepted consequence: the dashboard does not work if librarian
is not cloned.

The signal registry declares 63 signals — 20 with resolvers, 6 awaiting an instrumentation
change, 37 unobservable with current data. An unobservable signal is kept rather than
deleted: it names a thing worth measuring and records *why* it cannot be scored yet, which
is what stops the same metric being re-proposed at every retro.

A signal whose input column is sparsely populated must declare its frame rather than
silently averaging over structural nulls, and **every tile renders the row count it was
computed from**. A number without its denominator is not reportable — the same principle as
`/meta-feedback` one layer up. Store ownership, metric fences, and the module map:
**[telemetry/README.md](telemetry/README.md)**.

### Eval harness — structural only, and that is the gap

`scripts/eval-runner.sh` discovers every `evals.json` across `~/workspace/*/` and writes
pass/fail rows to `.sounding/eval-results.jsonl` (366 rows: 363 pass, 3 skip, across 51
skills in 7 repos).

**It validates routing, not judgment.** The runnable format is a set of
`{"input", "expected"}` trigger cases, and the runner checks only whether an input string
looks like it would route to that skill. Behavioral and judgment evals — anything needing
fixtures, an LLM judge, or multi-step execution — are recorded as `needs-harness` and
skipped.

So a config change graduating through `/meta-retro` gets a structural check, not a
behavioral one. A bad rule lands, is caught by human review, and is undone by hand. This is
the loop's weakest link: Plane 3 changes are the ones with the widest blast radius and the
thinnest automated verification. The last run was 2026-07-30.

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

## Known Gaps

- **No eval gate on config changes.** `eval-runner.sh` is structural-only; a bad rule lands, is caught by human review, and is undone by hand.
- **`insights-log.md` has no compaction** (#142). 2,189 lines, append-only, no drain.
- **Proposal recurrence not tracked** (#143). A proposal re-derived every 10-min tick and never acted on is invisible.
- **Experiment ↔ friction-signature link is sparse** (#145). Only 3 of 40+ ledger rows carry `pattern_key`.
- **`/meta-feedback` has no liveness signal** (#144). Loop Health tracks capture/insights/retro but not the verification gate.

---

**Framework**: Puffin · Genesis V-15.2 · **Instance**: Sounding (2026-07-13) ·
**Layout**: v3 (2026-07-18) · **Metacognition**: automated loop (GUA-138)
