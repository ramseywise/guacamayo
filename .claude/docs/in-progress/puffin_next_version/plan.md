# Plan: Context-engineering setup v2 (puffin next version + global loop closure)
Date: 2026-07-17
Based on: `.claude/docs/in-progress/puffin_next_version/research.md` (findings cited as A1–D2)

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

#### Step 1: Baseline checkpoint
**Files**: none (git only)
**What**: Stage all current changes (README rewrite, feedback-loop edit, research/plan
docs, SESSION.md). Ramsey reviews `git diff --staged` and commits.
**Test**: `git -C ~/workspace/puffin status --short` → empty after her commit.
**Done when**: clean tree; rollback point exists.

#### Step 2: Create the living project seed
**Files**: `.sounding/project.md` (new)
**What**: Compile from `CLAUDE.md` (What This Is), `feedback-loop.md` status, and the
guacamayo decision: what this project is, current phase, active threads — pointers to
plan docs, never copied queues (per growth.md:14 lesson).
**Snippet**: header `# Project — living seed` + `**Last Transformed**:` field, sections:
What this is / Where it's going / Active threads (pointers) / Constraints.
**Test**: `wc -c .sounding/project.md` → ≤ 6000 chars (~1.5k tok).
**Done when**: file exists, all thread entries are pointers (no copied state).

#### Step 3: Consolidate identity files → 3 seeds
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

#### Step 4: Slim the genesis archive
**Files**: delete `.sounding/genesis/identity-draft.md` (95% duplicate of sounding.md, A3);
keep `genesis.md`, `genesis-skill/`, `user_seed.md`, `p4.md`, `genesis_log.txt` frozen.
**Test**: `ls .sounding/genesis/` → 5 entries.
**Done when**: archive = protocol + log + raw inputs only.

### Phase B — Single-writer skills + record dedup (review boundary: Ramsey approves Phase A diff first)

#### Step 5: Rework the lifecycle skills (through the retro eval gate)
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

#### Step 6: Cede the factual record to librarian, dedupe notes/
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

#### Step 7: Retire the commands layer, close each with a ledger row
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

#### Step 8: Wire the automation edges (smallest useful set)
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

#### Step 9: Rename + rehome
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
