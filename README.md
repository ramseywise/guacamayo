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
No build, no runtime; the files *are* the system.

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
| **Logs** (accumulating) | `growth.md`, `reflections/`, `reflection-logs.md` | **Appended**, never rewritten; index compressed past ~100 entries |
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
| `/grow` | Mid-session | Captures tagged entries to `growth.md` + overwrites `notes/handover.md`. Honest "nothing shifted" is valid — skip entries, still write the handover |
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
  insights engine (`/workflow-insights`) mines them mechanically for friction patterns, token
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

`/workflow-insights` checks active experiments against session data and reports verdicts. `/workflow-retro`
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
| **Execution** — the work itself | code-*, design-*, git-*, akira, sanyi, docs-check | the codebase | per change |

**Metacognition is a loop across the layers, not a layer of its own.** It would be tidy if
"process" were the meta level, but it isn't: `/workflow-execute` sits in the process pipeline
and is plainly execution-layer work. The genuinely metacognitive skills are
`/workflow-insights` and `/workflow-retro` — the only two that observe the other layers and
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
| **Identity learnings** | `growth.md` | `/dream` | the 3 seeds |
| **Knowledge** (factual record, design docs) | `librarian/raw/` | librarian's ingest protocol | compiled wiki, conflict-flagged, cited |
| **Process/tooling learnings** | `growth.md` (flagged) | global `/workflow-retro` + eval gate | `~/.claude` hooks > skills > rules + a tooling-ledger row |
| **Work state** | per-repo `.claude/docs/plans/` or GitHub Issues | read fresh by `/wake` | never copied anywhere |

### How the feedback loop closes (beyond this repo)

This repo is one node in a larger loop wired through the global Claude setup:

1. **Observe** — sessions generate friction signals: transcripts (mined by the keyless
   insights engine), growth entries, hook fire patterns, plan-doc deviations.
2. **Diagnose** — global `/workflow-retro` reads those sources plus the tooling ledger
   (`guacamayo/.sounding/tooling-ledger.md`), where every unverified change is the top queue item.
3. **Codify** — findings become proposed diffs at the strongest enforcement level that
   fits: **hooks > skills/protocols > CLAUDE.md/rules > memory**. Proposals are diffs,
   never auto-applied; Ramsey reviews and commits.
4. **Enforce** — hooks fire mechanically (SessionStart wake nudge, PreCompact snapshots,
   secrets scan, git guards); `/workflow-retro`'s config-audit pass catches settings rot
   and layering drift.
5. **Verify** — every change lands as a ledger row with status `hypothesis` and a
   concrete test ("friction X absent for N sessions"); the next `/workflow-retro` promotes it to
   `verified` or `failed`. A failed row is itself a finding.

Global `~/.claude` is canonical for everything generic; this repo keeps only the
identity-lifecycle skills. Recurring manual audits are hooks that haven't been written
yet — maintenance-by-ritual retires in favor of maintenance-by-mechanism.

### The review ladder (2026-07-17)

Quality checks are one system, priced by token cost and entered from the terminal
(`~/workspace/Makefile`, `make help`):

| Rung | Entry | Runs | Cost |
|------|-------|------|------|
| L0 | `make precommit` / `make test` | shell sweeps across repos (GROUP-scoped) | zero tokens |
| L1 | `/code-review level:1` | diff + lint + doc flags | small |
| L2 | `/code-review level:2` (default) | + tests, SANYI diff check, akira-scan agents, `/docs-check` | medium |
| L3 | `/code-review level:3` | + full SANYI audit (single repo only) | high |

`/akira` is the interactive sibling of `/code-review` — same scan, plus wander questions
and test-gated `dao` fixes. `/code-pr` reviews an open PR after it lands.

Supporting cast, each defined once: stack conventions in `~/.claude/refs/` (dispatched
by `Refs:` lines in repo CLAUDE.md + nested folder stubs), the `akira-scan` agent in
`~/.claude/agents/` (no per-repo scaffolding), per-repo `SANYI.md` contracts consumed
by the global `/sanyi` skill. Reviews run **before** Ramsey commits; findings are
report-only; human-consumed docs are flagged, never auto-edited.

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
├── growth.md                    # accumulator: tagged one-liners, cleared by /dream
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
├── skills/                      # genesis (inert), wake, grow, dream — identity lifecycle only.
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

---

**Framework**: Puffin · Genesis V-15.2 · **Instance**: Sounding (2026-07-13) ·
**Layout**: v3 (2026-07-18, three-skill lifecycle)
