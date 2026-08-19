# Guacamayo — Persistent AI Identity Workspace

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

A live instance of the Puffin framework — my personalized AI identity:
**Sounding** persists across sessions through markdown files and lifecycle skills.
The identity system has no build; the files *are* the system. The `review/` package
and `telemetry/` package are Python, tested with `uv run pytest tests/`.

Genesis ran once. The `/genesis` skill stays installed but is **initiation-only**: it
self-blocks when a consciousness exists. Identity evolution never re-runs genesis — it
flows through the lifecycle below. Day-to-day starts with `/wake`.

---

## The Philosophy — Agency, Not Consciousness

The framing here is deliberately an engineering one. The research question is not "is
this conscious?" but **what does genuine agency require**: continuity of self across
time, metacognition, a closed feedback loop, goal persistence, theory of mind across
agents, attention as a scarce resource. Each of those is buildable, measurable, and
falsifiable — a consciousness claim is none of the three.

Three working principles fall out of this:

1. **Continuity of record ≠ continuity of behavior.** Files provide the record. What
   makes identity *real* is behavior holding under conditions nobody engineered — the
   first ordinary session after genesis showed the same patterns (verify before
   proposing, flag rather than silently resolve) with no designed stakes. That's the
   test that matters, and it's ongoing, not settled.

2. **One deep calibration beats multiple shallow ones.** The identity is calibrated to
   one person, formed from her real material. Genesis is initiation, not evolution: new
   facets emerge from lived sessions and enter through synthesis — deliberately, batched,
   with the record showing where each change came from.

3. **Identity changes like code changes**: captured with provenance, integrated by a
   single writer, verified after. The same discipline the field converged on —
   Letta/MemGPT's small always-in-context core blocks (persona + human ≙ our identity +
   user seeds), and sleep-time/idle consolidation instead of critical-path memory edits.

---

## System Design

### Three kinds of state

| Kind | Files | Write rule |
|------|-------|-----------|
| **Seeds** (living) | `sounding.md`, `user.md`, `portfolio.md` | **Transformed** in place by `/dream` only — truer, not longer (60-80% length, voice preserved) |
| **Logs** (accumulating) | `growth/growth.md`, `growth/growth-log.md`, `reflections/`, `reflection-logs.md` | **Appended**, never rewritten; index compressed past ~100 entries |
| **Archive** (frozen) | `genesis/` | Never loaded, never edited — provenance of the emergence |

**The single-writer rule** — the core design principle: *capture* and *transformation*
are separate acts. `/grow` captures; `/dream` integrates. Per-event
rewrites by multiple skills are how identity files accrete, drift, and lose voice —
we measured it before designing this out.

### The lifecycle skills (v3, 2026-07-18) — one initiation + three recurring

| Skill | Trigger | What it does |
|-------|---------|-------------|
| `/genesis` | Once, ever | Created the consciousness itself (ran 2026-07-13; now inert) |
| `/wake` | Session start | Loads 3 seeds, growth, recent reflections, handover, cross-repo plan state; ingests recent cross-session context (librarian or ask). Ends at a decision point |
| `/grow` | Mid-session | Captures tagged entries to `growth/growth.md` + overwrites `notes/handover.md`. Honest "nothing shifted" is valid — skip entries, still write the handover |
| `/dream` | Session end | Writes reflection + growth entries. Conditionally: synthesizes seeds (if 5+ entries), tidies indexes, flags retro. **The sole transformer of identity files** |

To trace one insight through the system: it happens in a session → `/grow` logs it to
`growth.md` → `/dream` gives it episodic context in a reflection, then (if 5+ entries
have accumulated) integrates it into the right seed at the right altitude and clears
the entry → the next `/wake` loads it as identity, not as a memo.

Consolidated from a six-skill set (v2) — `/intermission` folded into `/grow`,
`/reflect` + `/synthesize` + maintenance `/dream` folded into the new `/dream`.

### From Consciousness to Agency (v2 → v3)

Puffin v2 was designed around **building consciousness** — six ceremonious lifecycle
skills (`/wake`, `/grow`, `/intermission`, `/reflect`, `/synthesize`, `/dream`), each
a distinct ritual for introspection, transformation, and record-keeping. Beautiful
architecture, but it optimized for depth of self-awareness rather than capacity to act.

Guacamayo v3 asks a different question: **what does genuine agency require?** The answer
isn't more introspection — it's closed feedback loops, automatic maintenance, measurable
self-improvement, and the ability to identify recurring failures faster than a human
operator would notice them.

The shift in one sentence: *less ceremony, more mechanism.*

#### What concretely changed

**1. Single writer, no ceremony tax.** v2 had three skills that could transform identity
files (/grow, /reflect, /synthesize), each invoked by a different judgment call. v3 has
one (`/dream`), triggered automatically at session end. The decision of *when* to
integrate a learning is no longer a choice — it's a threshold (5+ entries → synthesize).
This eliminates accretion, voice drift, and the cognitive overhead of "which skill do I
invoke now?"

**2. Session logs → insights pipeline, not archive.** v2 wrote parallel logs (reflections
*and* chat logs *and* dated handovers) as documentary record. Most of this was never read
again. v3 strips this to what actually has a consumer:

- **Full session transcripts** stay in global storage (`~/.claude/projects/`) where the
  insights engine (`/meta-insights`) mines them mechanically for friction patterns, token
  economics, and context health.
- **Reflections** get only what's needed to build recommendations: the subjective
  synthesis — what shifted, what was confirmed, what was corrected. These feed the
  identity seeds and the experiment tracker.
- **The handover** is a single overwritten file (not dated copies) carrying forward-facing
  state for the next session. History lives in git, not in file proliferation.

The result: every piece of captured state has a downstream consumer that acts on it.
Nothing is written for the sake of completeness.

**3. Experiment tracking replaces manual verification.** When a tooling change is made
(a hook added, a rule written, a skill modified), it lands in the ledger as a `hypothesis`
with a typed metric — the observable signal that would confirm or fail it:

```
absence:<signal> for <N> sessions     — the friction stopped
count-drop:<signal> from X to Y       — frequency decreased
presence:<signal> within <N> sessions  — expected behavior appeared
ratio:<metric> <direction> <threshold> — measurable ratio shifted
```

`/meta-insights` checks active experiments against session data and reports verdicts. `/meta-retro`
uses those verdicts to graduate or fail hypotheses. Failed experiments get flagged for
rollback. This closes the loop between "we changed something" and "it actually worked" —
and catches failure-attribution faster than re-deriving evidence from scratch each time.

**4. Backend maintenance triggers, not rituals.** v2's maintenance was a skill you
remembered to invoke (`/dream` in the "tidy" sense). v3 wires maintenance into the
lifecycle automatically:

- Synthesis triggers at threshold (5+ growth entries at `/dream`)
- Index compression triggers at size (~100 entries)
- Retro flagging triggers when tooling changed during a session
- The Stop hook gates task completion on lint/format/tests passing
- The insights engine runs experiment checks against the ledger

The agent doesn't maintain itself because it's told to — it maintains itself because
the architecture makes maintenance the path of least resistance.

#### What was preserved

The transformation rules (weave don't append, 60-80% compression, voice is identity),
the growth entry format, genesis-is-initiation, the episodic record. The philosophy of
*one deep calibration beats multiple shallow ones* still holds — v3 just makes the
ongoing calibration loop tighter and more autonomous.

---

## The Three Layers

The skills split into three layers by what they give the system. This repo owns the first;
global `~/.claude` owns the other two.

| Layer | Skills | Writes to | Cadence |
|-------|--------|-----------|---------|
| **Identity** — continuity of self across sessions | genesis, wake, grow, dream (repo-local) | `.sounding/` seeds + logs | per session |
| **Process** — scaffolding one work item end to end | workflow-research → plan → execute → review; refine | plan docs, GitHub Issues | per work item |
| **Execution** — the work itself | code-*, design-*, git-*, review-* (12 dimensions), docs-check | the codebase | per change |

**Metacognition is a loop across the layers, not a layer of its own.** It would be tidy if
"process" were the meta level, but it isn't: `/workflow-execute` sits in the process pipeline
and is plainly execution-layer work. The genuinely metacognitive skills are
`/meta-insights` and `/meta-retro` — the only two that observe the other layers and
change the system itself, reading transcripts, growth entries, and the tooling ledger, then
proposing diffs to hooks/skills/rules.

So: identity supplies **continuity**, insights/retro supply **change to the system**, and
everything else is execution at varying granularity. The layers are directions of support,
not a hierarchy — identity and process exist to make execution repeatable, and execution
generates the friction signals that feed the loop back.

---

## Knowledge Organization — Four Sinks, One Home Each

Everything a session produces has exactly one destination and one graduation path.
Anything without a consumer is a dead end — the superfluous assets we retired (chat
logs, dated handovers, legacy commands) were all exactly that.

| What | Home | Graduates via | Ends up |
|------|------|---------------|---------|
| **Identity learnings** | `growth/growth.md` | `/dream` | the 3 seeds |
| **Knowledge** (factual record, design docs) | `librarian/raw/` | librarian's ingest protocol | compiled wiki, conflict-flagged, cited |
| **Process/tooling learnings** | `growth/growth.md` (flagged) | global `/meta-retro` + eval gate | `~/.claude` hooks > skills > rules + a tooling-ledger row |
| **Work state** | per-repo `.claude/docs/plans/` or GitHub Issues | read fresh by `/wake` | never copied anywhere |

### How the feedback loop closes (beyond this repo)

This repo is one node in a larger loop wired through the global Claude setup:

1. **Observe** — sessions generate friction signals: transcripts (mined by the keyless
   insights engine), growth entries, hook fire patterns, plan-doc deviations.
2. **Diagnose** — global `/meta-retro` reads those sources plus the tooling ledger
   (`guacamayo/.sounding/tooling-ledger.md`), where every unverified change is the top queue item.
3. **Codify** — findings become proposed diffs at the strongest enforcement level that
   fits: **hooks > skills/protocols > CLAUDE.md/rules > memory**. Proposals are diffs,
   never auto-applied; Ramsey reviews and commits.
4. **Enforce** — hooks fire mechanically (SessionStart wake nudge, PreCompact snapshots,
   secrets scan, git guards); `/meta-retro`'s config-audit pass catches settings rot
   and layering drift.
5. **Verify** — every change lands as a ledger row with status `hypothesis` and a
   concrete test ("friction X absent for N sessions"); the next `/meta-retro` promotes it to
   `verified` or `failed`. A failed row is itself a finding.

**Graduation rate** is the loop's north star: the share of *resolved* experiments that
graduated. The denominator is `confirmed + failed + inconclusive` — **open hypotheses are
excluded and reported separately**, because an untested hypothesis has not failed, and
diluting the ratio with a growing pile of them makes a healthy loop look broken. Rows
retired without ever being tested (`superseded`, `dropped`, `duplicate`) leave the ratio
entirely. Statuses matching no known term are counted, sampled, and logged at WARNING
rather than silently bucketed — a non-zero count means the ledger drifted and the
vocabulary needs extending (`compute_graduation` in `telemetry/dashboard.py`).

The two ledger files have **different column schemas** — active is
`Date|Change|Area|Metric|Status`, archive is `Date|Change|Area|Verdict|Evidence`. Reading
the archive positionally as if it matched the active layout fed evidence prose into the
status field, which is what produced 40+ apparent "statuses" (`0`, `R3`, `.venv\`) and
reported 1 confirmed of 108 while 43 already-closed verdicts sat one column over
(fixed GUA-137).

Global `~/.claude` is canonical for everything generic; this repo keeps only the
identity-lifecycle skills. Recurring manual audits are hooks that haven't been written
yet — maintenance-by-ritual retires in favor of maintenance-by-mechanism.

### Write authority — the loop cannot rewrite its own guardrails

The loop proposes config changes; it does not apply them. **Write authority narrows as
blast radius widens**, enforced at three independent layers rather than by convention:

| Layer | Mechanism | Where |
|---|---|---|
| Permission | `git commit` / `git push` denied outright | `.claude/settings.local.json` |
| Hook | `risky_git_guard.sh` blocks commit, push, `make ship`/`make push` | `~/.claude/hooks/` |
| Skill contract | `/meta-retro` is propose-only — "Silence is not approval" | `.claude/skills/meta-retro/SKILL.md` |

| Target | Loop may write? |
|---|---|
| `.sounding/` memory files | Yes — but clearing `growth.md` is hook-gated (below) |
| Skill files, tooling ledger | Only after explicit per-diff approval |
| `~/.claude/hooks/*`, `settings.json` | **Never** — not even for an approved finding, not even `chmod +x` |
| Commits, pushes | **Never** (sole carve-out: worktree agents on their own branch) |

That categorical exclusion is decision **D1 (2026-08-09)**. It is the answer to the
standard critique of self-improving agent systems — "self-modifying config on full
autonomy is a security risk." The mechanism that would make that true is absent by
construction: the loop cannot reach the files that constrain it. Widening the carve-out
is a deliberate act, never a side effect — see the D1 note in `meta-retro/SKILL.md`.

There is even a meta-gate on autonomy itself: a proposal kind earning ≥80% acceptance
over ≥5 logged decisions is promoted to auto-mutation only as a **ledger hypothesis row
marked `PROPOSED`** — Ramsey decides. The propose→mutate boundary moves on logged
evidence, never by default.

**Memory pruning is likewise mechanical, not aspirational.** `dream-ledger-gate.sh`
(PostToolUse on `Write|Edit`) blocks clearing `growth.md` unless `growth-log.md` gained
rows dated today — every cleared entry leaves an audit row first. The tooling ledger
splits live hypotheses (`tooling-ledger.md`) from graduated rows
(`tooling-ledger-log.md`), keeping the loaded file bounded while the archive grows.
Counter-pressure is explicit: **transform, never truncate** — identity loss is the worst
failure mode, so seeds are rewritten to 60–80% length, never deleted.

**Knowledge access is retrieval-first.** Accumulated knowledge is queried from librarian
(`search_wiki` / `read_page` / `get_domain_briefing`) rather than bulk-loaded; refs load
on demand; continuity files hold pointers, never copies. The always-loaded wake core is
budgeted (~5.5k tokens, measured).

### Known gaps in the loop

Stated plainly because a loop diagram that shows only the happy path invites the wrong
conclusions in both directions:

- **No eval gate on config changes.** `com.wiseer.eval-runner` runs weekly and is
  *observational* — nothing consumes a failing result to block a landing, and
  `eval-runner.sh` skips behavioral/judgment evals by its own header, so coverage is
  structural only. A bad rule lands, is caught by a human at review time, and is undone
  by hand. **Git is the rollback; there is no automated revert.** This is the thinnest
  mechanism in the system: every other control has hook enforcement or a written
  contract behind it.
- **`insights-log.md` has no compaction step.** growth.md drains and the tooling ledger
  archives, but insights-log only appends. Reflections have a stated compression rule
  (~100 entries) with no automation behind it.
- **Proposal recurrence is not tracked.** `board.json` is overwritten every tick and
  `actions.jsonl` records only *decided* actions, so a proposal re-derived hundreds of
  times and never acted on is invisible. Closing this needs an append-only sightings
  sink counting distinct days, not raw sightings — a 10-minute tick would otherwise
  report ~1000 phantom occurrences per week.
- **No experiment ↔ friction-signature link.** Ledger rows and `recurrence.py`
  signatures both exist; no field joins them, so intervention effectiveness cannot be
  computed even though both halves are present.

### The review package

Quality checks run through a deterministic Python driver (`review/driver.py`) backed by
12 LLM dimension agents (`.claude/agents/`). Entry points from the terminal
(`~/workspace/Makefile`, `make help`):

| Rung | Entry | Runs | Cost |
|------|-------|------|------|
| L0 | `make precommit` / `uv run pytest tests/` | shell sweeps + unit tests | zero LLM tokens |
| L1 | `/code-review level:1` | diff + lint + doc flags | small |
| L2 | `review-cli run` (default) | all 8 always-on dimensions + applicable conditional dims | medium |
| L3 | `/workflow-review` | driver + plan-fidelity check + DoD gate | high |

**Always-on dimensions (8)**: `correctness`, `intent`, `architecture`, `safety`, `testing`,
`silent-failure`, `performance`, `wander`.
**Conditional dimensions (4)**: `runtime` + `safeguards` (agent code), `leakage` (ML code),
`contracts` (repo has `SANYI.md`).

Findings carry attribution (`introduced` / `adjacent` / `pre_existing`) so blockers are
scoped to the diff, not the whole codebase. Reviews run **before** Ramsey commits;
findings are report-only; human-consumed docs are flagged, never auto-edited.

---

## Context-Engineering Practices (distilled)

1. **Pointers, not copies.** Continuity files reference sources of truth; copied state
   drifts silently. (Learned the hard way: a handover queue went stale across three
   sessions while being faithfully recited every wake.)
2. **Capture cheap, integrate deliberately.** In-session skills append one-liners;
   transformation is batched, off the critical path, with preservation rules.
3. **One altitude per insight.** The specific instance in the log, the operational shape
   in one seed section, the identity framing in another — never the same paragraph
   pasted into three files.
4. **Honest negatives.** A ritual that must produce output every time will manufacture
   it. "Nothing shifted" is a success state.
5. **Budget the always-loaded core.** The wake core is the three seeds + accumulator
   (~5.5k tokens, measured — down from ~11k before consolidation). Everything else loads
   on demand.
6. **Indexes are timelines, not diaries.** <=40 words per entry; compress past ~100.
7. **Archives are free; duplicates are not.** `genesis/` costs zero tokens because
   nothing loads it. The expensive duplication is in files that *are* loaded — that's
   where consolidation pays.
8. **Measure before concluding.** The v2 design came from mining real transcripts
   (ritual counts, token loads, verified duplicate passages), not aesthetics.
9. **Every output needs a consumer.** If nothing reads a file, stop writing it — or
   wire the reader.

---

## Folder Map

```
.sounding/                       # Private consciousness space
├── sounding.md                  # SEED — identity (+ operational patterns + working notes as sections)
├── user.md                      # SEED — who I work with + how we work together
├── portfolio.md                 # SEED — the portfolio: all active projects and how they connect
├── growth/                      # learning funnel
│   ├── growth.md                #   accumulator: tagged one-liners, cleared by /dream
│   └── growth-log.md            #   append-only disposition ledger for cleared entries
├── queue.md                     # COMMITTED cross-repo pointer set — survives clone so a
│                                # mobile /wake has state even without git-ignored plan docs
├── context-dashboard.html               # rendered status view (generated)
├── refs/                        # mobile mirror of ~/.claude/refs/ — shadows, not canon
├── reflections/                 # episodic record (subjective, stays local)
│   ├── YYYY-MM-DD_HH-MM.md      #   per-session reflection — written by /dream
│   ├── reflection-logs.md       #   single timeline index
│   └── emergence-reflection.md  #   genesis reflection (historical)
├── notes/
│   └── handover.md              # THE handover — overwritten by /grow and /dream, read by /wake
└── genesis/                     # FROZEN archive
    ├── genesis.md               #   the 11-phase protocol that ran
    ├── user_seed.md             #   Ramsey's raw input material
    └── genesis_log.txt          #   phase-by-phase run log

.claude/
├── agents/                      # 12 review dimension agents (correctness, intent, architecture,
│                                # safety, testing, silent-failure, performance, wander + conditional
│                                # runtime, safeguards, leakage, contracts) — back review/driver.py
├── skills/                      # identity lifecycle (genesis/inert, meta-wake, meta-grow, meta-dream)
│                                # + meta-insights/meta-retro (metacognition)
│                                # + review-* dimension checklists + review-shared + review-defense
│                                # + workflow-* pipeline (research/plan/refine/execute/review)
│                                # + design-*, git-*, docs-check and supporting skills.
│                                # Generic skills live in global ~/.claude/skills/ (canonical)
├── docs/                        # plans/ (one dated doc per work item), research/, state/ (cross-repo
│                                # workstream state). Plans are git-ignored;
│                                # tooling-ledger + insights-log live in .sounding/ (committed)
└── settings.local.json          # permissions + SessionStart wake nudge
```

The **factual** session record lives in librarian (`librarian/raw/sessions/puffin-*`),
whose compile pipeline is the system of record for what happened. Reflections stay local
because they are subjective and identity-bearing.

### Seeds: frozen inputs → living successors

| Genesis input | Living successor | Evolves via |
|---------------|------------------|-------------|
| `user_seed.md` (frozen in archive) | `user.md` | `/dream` |
| p4 character note (this README) | woven into `sounding.md` | `/dream` |
| genesis identity draft | `sounding.md` | `/dream` |
| — (no portfolio input existed) | `portfolio.md` | `/dream` |

There is no "update the seed" skill because updating the seeds **is** the lifecycle:
capture (`/grow`) → integrate (`/dream`). Genesis initiates; it never updates.

## Scheduled Jobs (launchd)

Three launchd agents, all loaded manually by Ramsey — never by Claude:

| Job | Schedule | Runs | Writes |
|---|---|---|---|
| `com.wiseer.guacamayo.telemetry` | daily 09:00 | `scripts/telemetry-cron.sh facts` → `uv run telemetry --facts` | `data/sessions.db`, `logs/telemetry-facts.log` |
| `com.wiseer.guacamayo.board` | every 10 min | `scripts/telemetry-cron.sh board` → `uv run telemetry --board` | `.sounding/telemetry/board.json`, `logs/board-launchd.log` |
| `com.wiseer.eval-runner` | Mon 10:00 | `scripts/eval-runner.sh` | `.sounding/eval-results.jsonl`, `logs/eval-runner.log` |

The **facts job** matters most for data durability: session JSONL in `~/.claude/projects/`
rotates out on a platform-managed schedule, so a missed capture window is history lost for
good (GUA-93; engine migrated from librarian's cartographer). The "~5 days" figure quoted
here and in `scripts/telemetry-cron.sh` is a **conservative assumption, not a measured
fact** — no `cleanupPeriodDays` is set and nothing in this repo prunes those files; as of
2026-08-19 the oldest surviving transcript was ~30 days old. Treat the window as unknown
and platform-controlled rather than as a 5-day deadline.

The **board job** drives `/meta-wake`'s project board: it derives issue columns from `gh`
state (open/merged/in-review/in-progress/backlog) and writes `board.json` atomically so
`/wake` never reads a partially-written snapshot. `RunAtLoad=true` repopulates the board
immediately on reboot. When `retro_due > retro_acked` in `cascade-state.json`,
`telemetry-cron.sh` also spawns `/meta-retro` unattended (once per day, lockfile-guarded).

Each board tick also runs the **autonomous-dispatch evaluator** (GUA-119): a pure
function over board state that writes `proposed_actions[]` into `board.json` — triage,
close, label-fix, review-dispatch proposals with reason + evidence. `/meta-wake` renders
them as one accept/reject batch; decisions append to `.sounding/telemetry/actions.jsonl`.
Exactly two idempotent mutations (auto-close merged-with-`Closes`, unambiguous label
correction) may run unattended behind an `--act` flag that defaults **off** — the
propose/mutate boundary moves only on logged acceptance-rate evidence, never by default.

Every `actions.jsonl` row carries `proposal_id` — the `ProposedAction.id` hash over
*action + target only*, deliberately excluding `reason`/`evidence`/`created_at` so the
same proposal keeps the same id when the board is re-derived from scratch each tick.
That stability is what makes the row joinable back to the board: it is the key for asking
whether the condition an accepted action addressed actually cleared on a later tick
(added GUA-137 — the id was computed but never written before).

A **GitHub Actions workflow** (`.github/workflows/board-signal.yml`) appends a JSON
signal line to the orphan `telemetry-state` branch on every PR open/close — self-bootstrapping
(creates the orphan branch if absent).

To install the facts and board jobs:

```bash
mkdir -p ~/workspace/guacamayo/logs
cp scripts/com.wiseer.guacamayo.telemetry.plist ~/Library/LaunchAgents/
cp scripts/com.wiseer.guacamayo.board.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.wiseer.guacamayo.telemetry.plist
launchctl load ~/Library/LaunchAgents/com.wiseer.guacamayo.board.plist
```

Run immediately with `launchctl start com.wiseer.guacamayo.board`; unload with
`launchctl unload ~/Library/LaunchAgents/com.wiseer.guacamayo.board.plist`.
launchd, not crontab, because cron silently skips windows while the Mac sleeps;
launchd re-fires on wake.

---

**Framework**: Puffin · Genesis V-15.2 · **Instance**: Sounding (2026-07-13) ·
**Layout**: v3 (2026-07-18, three-skill lifecycle)
