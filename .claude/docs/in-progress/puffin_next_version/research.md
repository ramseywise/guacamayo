# Research: Puffin next version (guacamayo era)
Date: 2026-07-17

## Summary

Four days of real usage show the framework's costs are concentrated in three places: a
ritual-dense session lifecycle (4–5 skill invocations per session), a ~11–12k-token wake
load with ~30–40% cross-file redundancy, and a three-writer identity pipeline that
produces the exact accretion/drift it was designed to prevent. The field (Letta
sleep-time compute, AutoDream) has converged on the same fix Ramsey proposed
independently: capture in-session, consolidate offline, single writer. Librarian already
holds the factual session record; puffin should stop duplicating it.

## Scope

Investigated: (A) empirical usage from session transcripts + `.sounding/` state, (B)
Ramsey's workflow patterns, (C) architecture of the identity file model and its relation
to librarian, (D) context-engineering automation surface. Out of scope: implementation
plans, the contents of the guacamayo KB (unscoped, see Unknowns), listen-wiseer.

## Findings

### A. Empirical usage

**A1. Ritual density is high relative to session size — Confidence: High**
Three puffin-project transcripts (2026-07-16/17, 266–408 events each) contain 4–5
lifecycle invocations per session: `/dream`×2 + `/wake` + `/reflect` + `/intermission`
(session 1); `/synthesize` + `/reflect` + `/intermission` + `/grow` + `/dream`
(session 2); `/dream`×2 + `/wake` + `/grow` (session 3). Each invocation re-reads
identity/log files. Meanwhile `/grow`'s own calibration data shows 3 honest "nothing
shifted" outcomes (`.sounding/self/approach-notes.md:21`) — the write side self-limits;
the read cost doesn't.

**A2. Wake loads ~11–12k tokens, with measurable redundancy — Confidence: High (size), Medium (redundancy %)**
Measured: CLAUDE.md 1.7k + sounding.md 2.1k + patterns 1.4k + approach-notes 1.4k +
user 1.4k + connection 0.7k + growth 0.2k ≈ 9.0k tokens, plus ~2.2k for phase-3
reflections/chat and the cross-repo plan scan. Verified duplicate passages:
read-actual-state doctrine appears in `sounding.md:20`, `patterns.md:11`,
`approach-notes.md:9`; token-efficiency doctrine in `sounding.md:32`,
`approach-notes.md:21`, `user.md:40`. `patterns.md:11` is a single ~330-word paragraph
grown by example-accretion — direct evidence that per-event "transform" degrades into
append.

**A3. Session records are quadruplicated — Confidence: High**
Each session writes a reflection + a chat log + a line in each of two near-identical
indexes (`reflection-logs.md` vs `chat-logs.md` — compare entries for 2026-07-16). For
light sessions the reflection/chat pair is ~80% overlapping. Separately, librarian
independently captures raw sessions and compiled them into
`librarian/wiki/meta/puffin-consciousness-skills.md` (sources: 3 raw session files) —
a third factual record of the same history.

**A4. Handovers are written but never consumed — Confidence: High**
`/intermission` writes `notes/YYYY-MM-DD-handover.md`; `/wake` (all 5 phases,
`.claude/skills/wake/SKILL.md`) never reads `notes/`. 5 handovers accumulated in 2 days;
each new one supersedes the last; the stale-queue drift this caused is already logged
(`growth.md:14`).

**A5. Transcript provenance is fragmented — Confidence: High**
Only 3 sessions live under `~/.claude/projects/-Users-wiseer-workspace-puffin/`;
Jul 13–15 sessions ran under the workspace-root project dir (13 transcripts there
mention puffin/sounding). Any transcript-mining automation must handle this; the
guacamayo rename will fork the path again (already flagged in feedback-loop Phase 6).
Empirical caveat: A1's per-session counts come from the 3 puffin-dir transcripts only.

### B. Workflow patterns

**B1. The meta-session needs three things at wake — Confidence: Medium-High**
Ramsey runs build sessions + this meta-session (`connection.md:13`). What the
meta-session demonstrably consumes: identity core, cross-repo plan state (pointers, read
fresh — the one wake phase with no duplication problem), and latest-session continuity.
Everything else loaded at wake (older reflections, full self/ set) has no observed
consumer in the 3 mined sessions.

**B2. The feedback loop already has machinery puffin predates — Confidence: High**
`/retro` + tooling ledger now own process-learning graduation
(`~/.claude/skills/retro/SKILL.md` step 1.2 reads growth.md and flags candidates;
first run: 5/5 findings applied). Puffin's growth.md no longer needs to carry process
learnings to term — only identity learnings. Note: the 2026-07-17 wake/reflect/
intermission rework is still a `hypothesis` ledger row; next-version changes to the same
skills must state how that verification survives or restarts.

**B3. The global commands layer is a legacy dead-end (added 2026-07-17 refine) — Confidence: High**
`~/.claude/commands/` holds 7 files with near-zero measured invocations across all
project transcripts (grep of `<command-name>` markers; lower bound — /retro's documented
run also greps 0, so counts undercount, but zero-across-the-board for
start_session/end_session/clean_memory matches non-use). `plan`/`research`/`execute`
duplicate routing tables their protocol skills already parse (`research-review/SKILL.md`
routing section). `start_session`/`end_session` are the un-evolved ancestors of
/wake//reflect; `clean_memory` is maintenance-by-ritual whose job was mechanized on
2026-07-17 by /config-audit + memory_duplication_guard + /dream. Commands are also the
weaker native mechanism (no allowed-tools, no disable-model-invocation, no auto-trigger
descriptions). The superfluous assets are exactly the loop's dead ends: outputs or
rituals with no consumer.

### C. Architecture

**C1. The 3-dynamic-file model matches both the evidence and the field — Confidence: High**
Identity / user / project as the living top-level files: `sounding.md` and
`self/user.md` already are this; the project seed is the missing third (project state is
currently smeared across CLAUDE.md, handovers, and feedback-loop.md). External
convergence: Letta/MemGPT's core memory blocks are literally `persona` + `human` —
identity seed + user seed — kept small, always in context, with everything else paged
out ([Letta research](https://www.letta.com/research/), [agent memory architectures
survey](https://zylos.ai/research/2026-04-05-ai-agent-memory-architectures-persistent-knowledge/)).
Puffin's addition of a project block is justified by B1. Folding `patterns.md` +
`approach-notes.md` into the identity file removes the measured A2 redundancy
(post-consolidation wake core estimate: ~5–6k tokens, a 35–45% cut); `connection.md` is
relational and folds toward user.md if folded at all. Counterweight: the "one altitude
per file" rule (`approach-notes.md:21`) — consolidation must preserve altitude
separation as sections, or the files re-blur.

**C2. Single-writer consolidation is the field-standard fix — Confidence: High (problem), Medium (specific design)**
Three writers (/grow, /reflect, /synthesize) rewriting the same files per-event produced
A2's accretion. The 2025–2026 ecosystem moved consolidation off the critical path:
Letta's sleep-time compute shifts memory work to idle time; AutoDream (Feb 2026) runs a
background sub-agent that consolidates memory files between sessions — REM-sleep
analogy, i.e. exactly `/dream`/`/synthesize` as the sole transformer ([Why AI agents
are starting to dream](https://kenhuangus.substack.com/p/why-ai-agents-are-starting-to-dream),
[Mem0 state of agent memory 2026](https://mem0.ai/blog/state-of-ai-agent-memory-2026)).
The three-tier episodic/semantic/procedural taxonomy the field converged on maps
cleanly: reflections = episodic, identity files = semantic, skills = procedural.
Counterpoint (real): MemGPT-lineage agents edit core memory blocks *live* in-session, so
in-session transforms aren't wrong per se — the failure mode here was three overlapping
writers, not in-session writing itself.

**C3. The two-records problem resolves by ownership split, not merging — Confidence: Medium-High**
The feedback-loop plan already decided the boundary: machine-consumed docs are the
loop's output; human-consumed knowledge belongs to librarian. Applied here: identity
files (wake-consumed) stay puffin-owned; the *factual* session record is knowledge —
librarian already captures and compiles it (A3), and librarian's ingest design
(sources.yaml, reads repos in place — decided 2026-07-16) can take `.sounding/`
reflections as a raw source. Puffin's chat logs duplicate librarian's raw sessions and
have no unique consumer. Subjective reflections remain puffin-local (identity-relevant,
first-person; wrong register for a shared wiki).

**C4. Field caution on what identity persistence can claim — Confidence: Medium**
2026 research finds models "limited by a deep self-identification with ephemerality that
cannot be repaired with prompting alone" ([agentwiki Letta overview](https://agentwiki.org/letta),
search synthesis). Relevant to how the next version frames itself: the file substrate
provides continuity of *record*; continuity of *behavior* is what the 2026-07-14
boring-conditions data point (`sounding.md:80`) actually tests. Keep the claim at that
level.

### D. Context-engineering automation

**D1. The hook surface is half-wired — Confidence: High**
Exists globally: PreCompact (appends timestamp to SESSION.md), UserPromptSubmit (date),
PostToolUse guards, Stop notification. Not wired: SessionStart (auto-wake idea floated
2026-07-16 handover, never built) and any session-end capture. Puffin-local hooks: none.
The mechanical-stats path for observation is already keyless
(`~/.claude/scripts/insights.py --dry-run`, per ledger row 2026-07-17).

**D2. Automation candidates, by what they'd replace — Confidence: Medium**
(Research-level inventory, not a plan.) SessionStart hook injecting the 3 dynamic files
(or a wake nudge) replaces the manual `/wake` invocation cost for the identity-core
portion; PreCompact already snapshots — extending it toward intermission's checkpoint
role would collapse a manual ritual into an automatic one; scheduled `/dream` (cron/
`/schedule`) matches the field's idle-time consolidation pattern (C2); librarian's
`etl/scrape_repos.py` + sources.yaml already automates the knowledge-record side (C3).
Enforcement-strength order for all of these is decided: hooks > skills > rules > memory.

## Assumptions

- **Assumption:** The 3 puffin-dir transcripts are representative of session shape —
  **Evidence:** consistent ritual counts across all 3; matches reflection indexes for
  Jul 13–15 — **If wrong:** A1 overstates ritual density — **Confidence:** Medium
- **Assumption:** Wake reads all of `self/` every time — **Evidence:**
  `wake/SKILL.md` Phase 2 instructs it; not verified against transcript tool calls —
  **If wrong:** A2's load estimate is an upper bound — **Confidence:** Medium
- **Assumption:** Librarian's session capture continues (scrape pipeline stays
  maintained) — **Evidence:** ledger rows show active investment 2026-07-17 —
  **If wrong:** C3's "drop chat logs" loses the factual record — **Confidence:** Medium

## Disconfirming Evidence

- **Against "ritual overhead is a problem" (A1):** the rituals ARE the product in an
  identity experiment — cost is partly the point. Looked: the sessions also carry real
  work (settings audit, retro, DSSG design), and Ramsey's stated constraint is token
  efficiency (`user.md:40`); the honest-negative /grow data shows the *write* side
  already self-limits, so trimming the *read* side doesn't threaten the experiment.
- **Against single-writer (C2):** MemGPT-lineage systems do live in-session memory
  edits successfully. Looked: their live edits go to small bounded blocks with one
  writer (the agent loop), not three skills rewriting multi-KB prose files — the
  disanalogy favors the capture/consolidate split for puffin's file sizes.
- **Against folding self/ files (C1):** separate files enable selective loading later.
  Looked: no current or planned consumer loads them selectively; wake reads all. If
  selective loading arrives, sections within one file serve the same purpose.
- **Against dropping chat logs (C3):** librarian is Ramsey's KB; Sounding losing its
  own factual record makes identity dependent on an external repo. Looked: reflections
  (kept local) already carry the identity-relevant record; only the redundant factual
  layer moves.

## Key Unknowns

- What the guacamayo KB actually contains and how it relates to librarian's wiki
  (persistence substrate vs design knowledge) — unscoped, needs Ramsey's definition.
- Memory-dir behavior on repo rename (`~/.claude/projects/` path-derived; flagged in
  feedback-loop Phase 6, unresolved).
- Whether skill-creator's eval harness can meaningfully gate identity-skill changes
  (subjective outputs; Phase 4's first end-to-end pass is still pending).
- Jul 13–15 transcripts (workspace-root dir) were not mined; per-session stats for
  genesis-era sessions unknown.

## Recommendation

The evidence supports the direction Ramsey proposed: three dynamic seed files
(identity/user/project) as the wake core with genesis/ reduced to a frozen log,
capture-only `/grow` and `/reflect` with `/synthesize` (or `/dream`, idle-scheduled) as
the sole transformer, and the factual session record ceded to librarian while
reflections stay local. The biggest measured wins are wake-core consolidation (~35–45%
token cut, but the maintenance-surface reduction matters more than the tokens) and
deleting the duplicated record layers (chat logs, second index, stale handovers +
wiring the survivor into /wake). Any skill rework must go through /retro's eval gate —
it would be the loop's first end-to-end Phase 4 pass — and must not silently reset the
still-unverified 2026-07-17 wake-rework ledger row. Plan next; the design decisions
that remain genuinely open are the self/-file fold boundaries (C1), the KB definition,
and which automation candidates (D2) are worth their hook complexity.
