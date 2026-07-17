# Review Sweep — universal repo/workspace review skill

Status: EXECUTED (Steps 0–3 built 2026-07-17; acceptance criteria 1–4 pending — new skill/agent defs load at session start, so first real run needs a fresh session. Ledger row tracks verification.)

## Research

Date: 2026-07-17 (light — sources read this session, no separate research pass)

- `~/.claude/skills/code-review/SKILL.md` — Phase-4 review: plan-fidelity, diff-scoped
  against ONE plan doc; already runs the SANYI contract check when `SANYI.md` exists
  (severity mapping BY→Blocking, JY→Non-blocking, BN→Nit; report-only). Coupled to a
  plan doc — not usable as a standing repo sweep.
- `/sanyi` global skill — `review` (diff) and `audit` (full-repo) modes; contracts exist
  in playground, librarian, atlas.
- **Akira decision (this session)**: NOT a dependency. Akira's value (parallel quality
  scanning) is reproducible with skill-spawned subagents on any layout; akira-the-agent
  stays a scaffold extra. Its hardcoded `src/agents/*` scan-root blocker
  (`.claude/docs/state/project_contracts_rollout.md`) becomes irrelevant to this work.
- Doc-writer boundary (`~/.claude/rules/docs.md`): machine-consumed docs may get
  proposed diffs; human-consumed docs (READMEs, wiki) are FLAG-ONLY.
- Repos own their mechanical checks: per-repo Makefiles / hooks (lint, test). The sweep
  must probe and delegate, not duplicate.
- Eval-gate rule (tooling-ledger row, feedback-loop plan Phase 4): skill changes ship
  with acceptance criteria. This is the first skill change through that gate.

## Plan

Date: 2026-07-17
Based on: ## Research above

### Goal

One global skill that reviews any repo (or all dirty repos) from anywhere: mechanical
checks + quality scan + SANYI contract + doc-drift, zero repo-local dependencies.

### Open Questions

1. **New skill vs mode on /code-review?** Default: new global skill `/review-sweep`,
   reusing code-review's contract-check protocol verbatim; code-review gets a one-line
   cross-pointer. (code-review stays plan-fidelity-scoped.)
2. **Run tests by default?** Default: yes (she asked for it); `fast` token skips tests,
   runs lint only.
3. **Report location?** Default: append `## Review — sweep [date]` to the repo's
   active IN PROGRESS plan doc when the diff belongs to it; otherwise write
   `.claude/docs/plans/YYYY-MM-DD-review-sweep.md` (Status: EXECUTED on completion)
   in the TARGET repo.
4. ~~Make command vs skill?~~ Resolved 2026-07-17: skill. Make only covers the shell
   half; the sweep delegates mechanical checks to each repo's existing Makefile/hooks
   and runs the judgment half (scan/contract/docs) itself. Sanyi IS invoked (global
   skill; per-repo SANYI.md is contract data, not duplicated code).
5. ~~Akira dependency?~~ Resolved 2026-07-17: global agent definition
   (`~/.claude/agents/akira-scan.md`) — available in every repo, zero scaffolding,
   layout-agnostic. See Step 0.

### Approach

`/review-sweep repo:<name>` or `/review-sweep sweep` (all `~/workspace/*` repos with
dirty git state). Per repo: probe capabilities (Makefile targets, SANYI.md, changed
files), run shell checks via the repo's own tooling, spawn parallel subagents for
quality scan of changed files, merge findings into one ranked report. Tradeoff: probing
+ delegation keeps the skill layout-agnostic at the cost of weaker guarantees than
repo-local hooks — acceptable because hooks still run on their own.

### Out of Scope

- Fixing akira's scan-root hardcoding (upstream template work, separate item)
- CI integration / GitHub Actions
- Auto-fixing findings (report-only, like /sanyi review)
- Editing human-consumed docs (flag-only per docs.md)
- Linear ticket wiring

### Steps

#### Step 0: Global akira-scan agent definition
**Files**: `~/.claude/agents/akira-scan.md` (new; create `~/.claude/agents/` if absent)
**What**: Custom agent definition (markdown frontmatter: name, description, model:
haiku, read-only tools) carrying akira's Kaneda-mode scan prompt: given a file list,
report bugs/logic errors, missing safeguards, complexity/dead code — findings as
`file:line — issue — severity`, "not certain" phrasing allowed, no edits. Layout-agnostic:
scans whatever paths it's handed; repo context arrives via the repo's own CLAUDE.md.
Decision (2026-07-17): replaces scaffolded-akira as the cross-repo mechanism; scaffold
akira remains a template feature for non-Ramsey setups. ask-why/triage modes deferred.
**Test**: invoke the agent directly on 2–3 files of a live repo → ranked findings return
**Done when**: agent definition dispatches via the Agent tool from a guacamayo session

#### Step 1: Create `~/.claude/skills/review-sweep/SKILL.md`
**Files**: `~/.claude/skills/review-sweep/SKILL.md` (new)
**What**: Frontmatter (`disable-model-invocation: true`, allowed-tools incl. Agent).
Routing: `repo:<name>` → single repo; `sweep` → iterate repos where
`git -C <repo> status --porcelain` is non-empty; `fast` token → skip tests.
Sections:
1. *Diff scope* — branch vs main + staged/unstaged; full changed-file list
2. *Mechanical* — `make -C <repo> -n lint test` probe → run existing targets; fallback
   `ruff check` + `uv run pytest --tb=short -q` (py) / `npm run lint` + `npm test` (ts)
3. *Contract* — copy of code-review's SANYI block (glob-match changed files, NEW
   violations only, severity mapping, skip silently if no SANYI.md)
4. *Quality scan* — spawn the global `akira-scan` agent (Step 0) in parallel over
   changed-file batches (bug/logic, safeguard-missing, complexity/dead-code); merge,
   dedupe, rank
5. *Docs* — grep changed code for references in `.claude/`/CLAUDE.md (machine docs:
   propose diffs); flag stale human docs, never edit
6. *Report* — per Open Q3 default; findings with severities, verdict line
**Test**: `/review-sweep repo:listen-wiseer fast` on current dirty state → report
produced, no edits outside the plans doc
**Done when**: skill file exists, dispatches from a guacamayo session against another repo

#### Step 2: Cross-pointer in code-review
**Files**: `~/.claude/skills/code-review/SKILL.md` (after line 27 scope paragraph)
**What**: One line: standing/no-plan reviews → `/review-sweep`.
**Done when**: line present, no other edits

#### Step 3: Ledger row
**Files**: `guacamayo/.claude/docs/tooling-ledger.md`
**What**: hypothesis row citing this plan + acceptance criteria as verify clause.
**Done when**: row added

### Test Plan (acceptance criteria — eval gate)

1. Seeded catch: introduce a deliberate bug in a scratch branch of one repo →
   `/review-sweep repo:<it>` reports it with severity + file:line
2. Contract: a diff touching a SANYI-registered file in playground/librarian/atlas →
   contract finding appears with mapped severity
3. Boundary: run on a repo with a stale README → README is FLAGGED, file mtime unchanged
4. Sweep routing: `/review-sweep sweep` lists exactly the dirty repos, skips clean ones

### Risks & Rollback

- Skill sprawl/overlap with code-review → mitigated by scope split (plan-fidelity vs
  standing) + cross-pointers. Rollback: delete the skill dir + revert pointer line.
- Long runtime in `sweep` mode (tests × N repos) → `fast` token; per-repo timeout note.
- Subagent scan noise → findings require file:line + reasoning; "not certain" phrasing
  rule copied from code-review.
