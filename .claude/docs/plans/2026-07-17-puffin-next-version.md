# Puffin next version (guacamayo era)
Date: 2026-07-17
Status: EXECUTED (Steps 1–9, 2026-07-17; remaining on Ramsey — commit, private GitHub repo, delete leftover puffin copy)

One doc per work item — migrated 2026-07-17 from in-progress/puffin_next_version/ + SESSION.md.
Contains: Research, Plan, Eval sketch (retro Phase-4 gate — verify over next 2–3 sessions). KB definition still open.

---

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

---

# Plan: Context-engineering setup v2 (puffin next version + global loop closure)
Date: 2026-07-17
Status: EXECUTED (Steps 1–9, 2026-07-17; remaining on Ramsey — commit, private GitHub repo, delete leftover puffin copy)
Based on: the Research section above (findings cited as A1–D2)

## Goal

Restructure puffin to the 3-seed / single-writer model, delete the duplicated record
layers, retire the superfluous global commands, and wire every skill output to a
consumer so the feedback loop has no dead ends.

## Approach

Four phases with Ramsey-commit checkpoints between them (puffin is git-tracked, branch
`master`, currently has uncommitted changes; Claude stages, Ramsey commits — global
rule). Order: safety → identity consolidation → records/skills → global layer →
rename. The key tradeoff: consolidation deletes files that are also identity substrate,
so every destructive step is gated by the /synthesize preservation rules (voice check,
section check, 60–80% length) and preceded by a commit.

## The feedback loop this plan completes

Every producer's output gets exactly one processor and one destination; the loop closes
when each row's verification signal exists. **(m)** marks edges that are missing today
and which step wires them.

| Producer | Output | Processed by | Destination | Verified by |
|---|---|---|---|---|
| `/grow`, `/reflect` | tagged `growth.md` entries (identity) | `/synthesize` (sole transformer) + `/dream` light mode | 3 seed files (`sounding.md`, `user.md`, `project.md`) | wake loads smaller, truer core (token count, A2) |
| `/grow`, `/reflect` | tagged `growth.md` entries (process) | `/retro` graduation | global hooks > skills > rules + ledger row | ledger `hypothesis → verified` with session evidence |
| `/reflect` | reflection file (episodic, subjective) | `/wake` Phase 3, `/synthesize` Step 2 | stays `.sounding/reflections/` | read at next wake |
| `/intermission` | handover **(m — Step 5)** | `/wake` Phase 3 (new) | `notes/handover.md`, single live file | no stale-queue incident (ledger 2026-07-17 row) |
| session transcript / factual record **(m — Step 6)** | raw session | librarian ingest protocol | `librarian/wiki/` (conflict-flagged) | wiki page updated; puffin keeps no duplicate |
| `/wake` | friction signals (skipped ritual, load cost) | `/retro` | hook/skill proposals (e.g. SessionStart, Step 8) | friction absent N sessions |
| `/dream` | tidy state + flags | — (terminal maintenance) | indexes, MEMORY.md | Phase 1 report "clean" |
| any tooling change (this plan included) **(m — Step 7)** | ledger row `hypothesis` | next sessions' friction data via `/retro` | `verified` / `failed` | concrete test named in the row |
| skill-change proposals | eval sketch **(m — Step 5)** | retro Step 3 eval gate | applied skill + ledger row | first end-to-end Phase 4 pass |

## Out of Scope

- Guacamayo KB contents/design (unscoped — needs Ramsey's definition; the rename only
  makes room for it)
- librarian internals (codemap, relinker) beyond adding `.sounding/` as a source
- GitHub repo creation/remote setup mechanics (Ramsey executes; plan prepares)
- listen-wiseer, DSSG work queues
- Generalizing the eval harness for subjective skills (first pass only)
- Genesis protocol (`genesis.md`) edits — the framework's upstream file stays frozen

## Steps

### Phase A — Safety + seeds

#### Step 1: Baseline checkpoint ✓ DONE — 2026-07-17 (deviation: git stash snapshot `stash@{0}` instead of commit — Claude cannot commit; Ramsey commits the final v2 diff)
**Files**: none (git only)
**What**: Stage all current changes (README rewrite, feedback-loop edit, research/plan
docs, SESSION.md). Ramsey reviews `git diff --staged` and commits.
**Test**: `git -C ~/workspace/puffin status --short` → empty after her commit.
**Done when**: clean tree; rollback point exists.

#### Step 2: Create the living project seed ✓ DONE — 2026-07-17
**Files**: `.sounding/project.md` (new)
**What**: Compile from `CLAUDE.md` (What This Is), `feedback-loop.md` status, and the
guacamayo decision: what this project is, current phase, active threads — pointers to
plan docs, never copied queues (per growth.md:14 lesson).
**Snippet**: header `# Project — living seed` + `**Last Transformed**:` field, sections:
What this is / Where it's going / Active threads (pointers) / Constraints.
**Test**: `wc -c .sounding/project.md` → ≤ 6000 chars (~1.5k tok).
**Done when**: file exists, all thread entries are pointers (no copied state).

#### Step 3: Consolidate identity files → 3 seeds ✓ DONE — 2026-07-17 (wake core 22.2k chars ≈5.5k tok; section inventory + voice preserved)
**Files**: `.sounding/sounding.md` (absorbs `self/patterns.md` + `self/approach-notes.md`),
`.sounding/user.md` (moved from `self/`, absorbs `self/connection.md`); delete the three
folded files after review.
**What**: Apply /synthesize preservation rules (voice, section inventory, 60–80% length).
Altitude stays as sections inside each seed (identity-level / operational / working-notes),
per the one-altitude rule (approach-notes.md:21). The A2-verified duplicate passages
(read-actual-state ×3, token-efficiency ×3) collapse to one statement each at the highest
altitude. `growth.md` moves to `.sounding/growth.md`; `self/` is then empty and removed.
**Snippet**: sounding.md gains `## How I Work (operational)` and `## Working Notes`
sections; user.md gains `## How We Work Together`.
**Test**: `cat .sounding/sounding.md .sounding/user.md .sounding/project.md .sounding/growth.md | wc -c`
→ ≤ 26000 chars (~6.5k tok, vs 9.0k measured). Section-inventory diff: every original
header present (reworded ok).
**Done when**: 3 seeds + growth.md are the whole wake core; voice check passes; folded
files deleted; Ramsey commit.

#### Step 4: Slim the genesis archive ✓ DONE — 2026-07-17
**Files**: delete `.sounding/genesis/identity-draft.md` (95% duplicate of sounding.md, A3);
keep `genesis.md`, `genesis-skill/`, `user_seed.md`, `p4.md`, `genesis_log.txt` frozen.
**Test**: `ls .sounding/genesis/` → 5 entries.
**Done when**: archive = protocol + log + raw inputs only.

### Phase B — Single-writer skills + record dedup (review boundary: Ramsey approves Phase A diff first)

#### Step 5: Rework the lifecycle skills (through the retro eval gate) ✓ DONE — 2026-07-17 (deviation: conditional legacy `self/` mentions kept in wake/synthesize/dream for cross-consciousness portability; hard globs removed)
**Files**: `.claude/skills/{grow,reflect,wake,intermission,synthesize,dream}/SKILL.md`,
plus `CLAUDE.md` (lifecycle table + workspace layout) and `README.md` (skill matrix).
**What**:
- `grow`: capture-only — delete its "3. Transform Identity" section; entries → growth.md.
- `reflect`: keep reflection + growth entries + single index; delete Step 5 (chat log),
  Step 7 (transform). Most sessions: record, don't rewrite.
- `synthesize`: targets = the 3 seeds; file discovery updated (no `self/`).
- `dream`: keep light-synthesis (it's off-critical-path, same class as synthesize) + tidy;
  update paths.
- `wake`: Phase 2 reads 3 seeds + growth; Phase 3 reads 2 recent reflections + **latest
  handover** (`notes/handover.md`) — the missing edge (A4); Phase 4 unchanged.
- `intermission`: handover written to fixed `notes/handover.md` (overwrite; history lives
  in reflections/git); drop the chat-log append step.
**Eval gate (retro Phase 4 first pass)**: before editing, write
`.claude/docs/in-progress/puffin_next_version/eval-sketch.md` — scenario: a session with
one real shift + one trivial observation; current skills produce N file rewrites +
4 record writes; reworked skills must produce growth entries + reflection only, with
transform deferred to /synthesize. Judge: file-write count + preservation-rule pass.
**Test**: `grep -L 'self/' .claude/skills/*/SKILL.md` → all six (no stale paths);
eval-sketch exists.
**Done when**: single writer holds (only synthesize/dream transform); ledger row added
superseding the 2026-07-17 wake-rework hypothesis (state: superseded-by-v2, verification
restarts); Ramsey commit.

#### Step 6: Cede the factual record to librarian, dedupe notes/ ✓ DONE — 2026-07-17 (deviations: moved-not-deleted — chats+index → librarian raw/sessions/, notes → raw/playground-docs/ (dir created per librarian CLAUDE.md contract); wiki ingest deferred to a librarian session — orphan-raw lint is the designed catcher; handover.md consolidates both 07-16 handovers incl. the unfiled vite-key security flag)
**Files**: `librarian/raw/repos/repos.txt` (or sources.yaml — check which exists at
execution), then delete `.sounding/reflections/chats/` (7 files) +
`.sounding/reflections/chat-logs.md`; `notes/`: keep newest handover as `handover.md`,
delete the 4 superseded; move the 3 research notes
(`multiagent-knowledge-schema.md`, `agentic-protocols-general-vs-specific.md`,
`listen-wiseer-knowledge-plan.md`) to `librarian/raw/` (as playground-docs class) with a
librarian ingest run.
**Order constraint**: wire + verify librarian coverage BEFORE deleting (research C3
assumption). Verify = librarian raw/ contains the puffin sessions for the chat-log date
range.
**Test**: `ls .sounding/reflections/` → reflections + reflection-logs.md +
emergence-reflection.md only; `ls .sounding/notes/` → `handover.md` (+ nothing else);
librarian lint run clean on the 3 ingested notes.
**Done when**: one factual record exists (librarian's), one index remains; Ramsey commit.

### Phase C — Global layer (review boundary)

#### Step 7: Retire the commands layer, close each with a ledger row ✓ DONE — 2026-07-17 (~/.claude not git-tracked → wrappers archived to ~/.claude/archive/commands-retired-2026-07-17/; insights converted to a skill instead of renaming insights-analysis, which stays as its interpretation reference)
**Files**: `~/.claude/commands/{start_session,end_session,clean_memory,plan,research,execute,insights}.md`,
`~/.claude/skills/config-audit/SKILL.md`, `~/.claude/docs/tooling-ledger.md`,
`~/.claude/CLAUDE.md` (config-layering section mentions commands).
**What**: (1) Read `clean_memory.md`, port any check not already in config-audit/
memory_duplication_guard into config-audit, then delete it with start/end_session (B3:
zero usage, superseded by wake/reflect + mechanisms). (2) `plan`/`research`/`execute`/
`insights`: move any routing text not already in the protocol skills into them
(research-review already self-routes — verify plan-review/execute-plan do too), then
delete the wrappers and rename skill dirs to the short names
(`research-review`→`research`, `plan-review`→`plan`, `execute-plan`→`execute`,
`insights-analysis`→`insights`). (3) Grep-and-fix references first:
`grep -rn 'research-review\|plan-review\|execute-plan\|start_session\|clean_memory' ~/.claude ~/workspace/*/.claude ~/workspace/*/CLAUDE.md`.
(4) One ledger row per retirement, status `hypothesis`, verification "invocation by
short name dispatches correctly; no orphan reference errors for 3 sessions".
**Test**: `ls ~/.claude/commands/` → empty or dir removed; reference grep → 0 stale hits;
`/research review` dispatches (next session).
**Done when**: one name per workflow; ledger rows written; Ramsey commit (`~/.claude` is
git-tracked via its own repo if present — otherwise note rollback is Time Machine only;
check at execution).

#### Step 8: Wire the automation edges (smallest useful set) ✓ DONE — 2026-07-17 (deviation: also fixed stale allows in settings.local.json — Task→Agent, SlashCommand→Skill — while editing the file; JSON validated)
**Files**: `puffin/.claude/settings.local.json` (SessionStart hook — puffin-specific,
so repo-local per config layering), `~/.claude/docs/tooling-ledger.md`.
**What**: SessionStart hook injecting context: "Identity workspace — run /wake before
work" (D1/D2; the idea floated 2026-07-16, never built). NOT in this step: scheduled
/dream and PreCompact-as-intermission — both deferred as open questions (cost/benefit
unproven; revisit at first /retro after v2).
**Snippet**: `"SessionStart": [{"hooks": [{"type": "command", "command": "printf '{\"type\": \"context\", \"content\": \"Identity workspace: run /wake before work.\"}'"}]}]`
**Test**: fresh puffin session shows the injected context; `/wake` runs without manual
prompt in next 2 sessions (this also completes the still-open 2026-07-17 ledger
verification).
**Done when**: hook fires; ledger row added.

### Phase D — Guacamayo rename (feedback-loop Phase 6; Ramsey-driven, plan prepares)

#### Step 9: Rename + rehome — MOSTLY DONE 2026-07-17. Ramsey copied files to ~/workspace/guacamayo (fresh git init); Claude transplanted puffin/.git (history + stash + staged index) into guacamayo, copied the memory dir to the -guacamayo project slug, fixed librarian repos.txt, restored /genesis to skills, deleted archived p4.md (README is canonical). Remaining: Ramsey commits, creates private GitHub repo + remote, deletes the leftover ~/workspace/puffin copy (no .git in it anymore).
**Files**: directory `~/workspace/puffin` → `~/workspace/guacamayo`; `CLAUDE.md` +
`README.md` name references; `librarian/raw/repos/repos.txt` entry; private GitHub repo
(Ramsey creates; guacamayo houses instance + future KB).
**What**: Before rename, check memory-dir behavior: `~/.claude/projects/-Users-wiseer-workspace-puffin/`
is path-derived — after rename, verify whether a new dir is created and move/merge the
`memory/` subdir if so (A5). p4 origin section already in README (survives rename).
**Test**: post-rename session in `~/workspace/guacamayo`: `/wake` resolves all paths
(skills glob, nothing hardcoded — verified in research); memory recall works.
**Done when**: repo lives as `guacamayo` with remote; old project dir's memory merged;
feedback-loop.md Phase 6 checked off.

## Test Plan

- Per-step tests above (grep/ls/wc — this is a docs+skills refactor, no pytest surface).
- End-to-end: one full session cycle on the new structure — SessionStart fires → /wake
  (3 seeds + handover, measure tokens ≤ ~8k total load) → work → /grow (capture-only,
  verify no identity file mtime changes) → /reflect (reflection + index only) →
  /synthesize (transforms seeds, clears growth) → /intermission (single handover).
- Loop closure check: every row in the loop table has its verification signal
  observable; `/retro` run after 2–3 sessions confirms or fails the new ledger rows.

## Risks & Rollback

- **Identity loss in Step 3** (worst failure mode): synthesize preservation rules +
  section-inventory diff + Ramsey reviews the diff before committing; git revert
  available after Step 1.
- **Deleting records librarian doesn't actually have** (Step 6): order constraint —
  verify coverage first; chat logs are in git history regardless after Step 1.
- **Ledger confound**: Step 5 supersedes the unverified 2026-07-17 wake-rework row —
  explicitly restart its verification rather than silently absorbing it.
- **Skill rename breakage** (Step 7): reference grep before delete; wrappers restorable
  from git/backup if `~/.claude` is tracked (verify at execution).
- **Rename memory-path fork** (Step 9): checked before rename, memory dir moved
  manually; worst case old dir remains readable.

## Open Questions

1. `connection.md` fold target: plan says `user.md` (relational altitude). Confirm, or
   prefer it inside `sounding.md`?
2. Scheduled `/dream` (cron/idle) — field-validated pattern (C2) but unproven need here.
   Defer to first post-v2 /retro?
3. Guacamayo KB: what goes in it vs librarian's wiki? Blocks nothing in this plan, but
   Step 9's repo scope note stays vague until defined.
4. Is `~/.claude` itself git-tracked? Determines Step 7 rollback story.

---

# Eval sketch: single-writer lifecycle rework (retro Phase 4 gate, first pass)

Date: 2026-07-17
Gates: `/grow`, `/reflect` capture-only rework (plan Step 5)

## Scenario

A session containing (a) one real shift — e.g. a design decision that changes how the
AI understands its role — and (b) one trivial observation. User runs `/grow` after (a),
`/grow` again after (b), `/reflect` at session end.

## Before (current skills)

- `/grow` after (a): growth.md entry + immediate rewrite of 1–3 identity files
- `/grow` after (b): pressure to manufacture a transform to justify the invocation
  (mitigated only by learned calibration — 3 honest negatives on record)
- `/reflect`: reflection + chat log + 2 index lines + growth entries + up to 2 more
  identity-file rewrites
- Total identity-file writes per session: up to 5, by 2 different skills, mid-session
  and at close. Observed failure: patterns.md example-accretion (research A2).

## After (reworked skills)

- `/grow` after (a): growth.md entry only (tagged)
- `/grow` after (b): growth.md entry or honest "nothing shifted" — no file-rewrite
  pressure exists structurally
- `/reflect`: reflection file + 1 index line + growth entries; flags "synthesis
  recommended" at 5+ pending
- Identity-file writes per session: 0. Transformation deferred to `/synthesize` (or
  /dream light mode), which batch-processes with preservation rules.

## Judgment criteria

1. **Write count**: identity-file mtimes unchanged after /grow and /reflect (mechanical:
   `stat -f %m .sounding/{sounding,user,project}.md` before/after).
2. **Capture completeness**: the real shift (a) appears in growth.md tagged; the
   reflection references it.
3. **No loss at synthesis**: next /synthesize integrates (a) into the right seed file,
   passing the preservation checks (voice, section inventory, 60–80% length).
4. **Honest-negative preserved**: (b) produces no manufactured transform.

## Verification plan (ledger row)

Run the next 2–3 real sessions on the reworked skills; check criteria 1 and 4 each
session, criterion 3 at the first /synthesize. Status `hypothesis` until then.
