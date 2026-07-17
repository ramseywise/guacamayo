# Workspace Review Ladder — make entry points, leveled review, headless HITL

Status: EXECUTED (2026-07-17, same session. Deviations: workspace Makefile already
existed with GROUP-scoped precommit/test/pull — extended, not created; Q2 resolved by
Ramsey to print-only, so Step 3's headless probe became moot; `code -g` IDE-open
dropped with it (report path is in the printed flow). Pending verify: L1 zero-agent
behavior, L3 sweep-refusal, L1-vs-L2 token comparison — ledger row.)

## Research

Date: 2026-07-17 (sources read this session)

- `/review-sweep` built + first-run today (`2026-07-17-review-sweep.md`, EXECUTED):
  pipeline works; `fast` token exists but is binary (skip tests), no cost levels.
  Agent defs (`akira-scan`) register at session start → headless `claude -p` runs get
  proper dispatch (fresh session each time) — the make bridge is also the fix for
  mid-session agent registration.
- Per-repo Makefiles own lint/test (listen-wiseer `make lint` verified today). No
  workspace-root Makefile exists.
- `/sanyi` global skill: `review` (diff) vs `audit` (full repo). Contracts: playground,
  librarian, atlas.
- Doc-writer boundary (`~/.claude/rules/docs.md`): READMEs are human-consumed —
  sessions propose reviewed diffs only when explicitly directed (Ramsey directed here);
  she commits.
- Eval-gate rule: skill changes ship with acceptance criteria (second use of the gate).

## Plan

Date: 2026-07-17
Based on: ## Research above

### Goal

One terminal entry point per review level, scoped to any repo set, fully automated with
HITL handled by report-in-IDE instead of blocking prompts.

### Open Questions

1. **Where does "the package" get documented?** Default: global `~/.claude/CLAUDE.md`
   (one paragraph, entry points) + guacamayo README section (Ramsey reviews/commits;
   explicit direction given). ai-project-template gets NO workspace Makefile (it
   scaffolds single repos; workspace layer is machine-level) — only a README line
   pointing at the convention. Confirm/redirect.
2. **Headless permissions**: `claude -p` runs with settings-file permissions; first run
   verifies no interactive prompt kills automation. If it does: fallback documented in
   Makefile comment (run the slash command in-session). Accept fallback? Default: yes.
3. **L3 sanyi scope**: full `/sanyi audit` per repo is the expensive step. Default:
   L3 only ever runs single-repo (`REPO=` required, refuse `sweep`).

### Approach

Extend `/review-sweep` with `level:1|2|3` tokens (replacing binary `fast`, which stays
as alias for level:1) + a `headless` rule (never ask — write `### Needs input` into the
report). New workspace Makefile fans mechanical targets out to per-repo Makefiles and
bridges judgment targets through `claude -p`, ending with `code -g <report>`. Tradeoff:
headless runs cost a fresh session each — that's also what makes agent dispatch and
clean context work.

### Out of Scope

- CI/GitHub Actions wiring
- Auto-applying findings (report-only stays)
- Template shipping a workspace Makefile
- Any human-doc edit beyond the two Ramsey-directed sections

### Steps

#### Step 1: Level tokens in /review-sweep
**Files**: `~/.claude/skills/review-sweep/SKILL.md`
**What**: Routing gains `level:N` (default 2). L1 = diff + mechanical lint + doc flags
(no agents, no tests); L2 = + akira-scan + tests; L3 = + full `/sanyi audit`
(single-repo only) + doc-drift proposed diffs. `fast` = alias for `level:1`. Add
`headless` token: never ask the user; unresolved questions → `### Needs input` section
in the report; always exit having written the report.
**Test**: `/review-sweep repo:listen-wiseer level:1` in-session → no agent spawn, no
tests, report written
**Done when**: three levels dispatch distinctly; headless rule present

#### Step 2: Workspace Makefile
**Files**: `~/workspace/Makefile` (new)
**What**: `REPOS` autodetect (dirs with Makefile); `REPO=`/`REPOS=` scoping;
targets: `lint` `test` (fan-out, fail-fast), `review-fast` `review` `review-deep`
(`claude -p "/review-sweep <scope> level:N headless"` then
`code -g <newest report>`), `help` (both planes + session-side pointers:
/research /plan /execute /config-audit /retro).
**Test**: `make -n review REPO=listen-wiseer` shows the right command; `make lint
REPO=listen-wiseer` passes
**Done when**: help lists everything; L0 runs shell-only with zero tokens

#### Step 3: First headless run (Open Q2 probe)
**What**: `make review-fast REPO=listen-wiseer` for real; observe permission behavior,
report lands, VS Code opens it.
**Done when**: run completes unattended OR fallback documented in Makefile header

#### Step 4: Docs
**Files**: `~/.claude/CLAUDE.md` (Tooling section, ~4 lines: ladder + make entry
points); `guacamayo/README.md` (proposed diff — Ramsey reviews: "the package" section
describing rules/refs/skills/agents/Makefile as one system); ai-project-template
`README.md` one pointer line.
**Done when**: diffs staged for Ramsey's review; no unreviewed human-doc edit

#### Step 5: Ledger row
**Files**: `guacamayo/.claude/docs/tooling-ledger.md`
**Done when**: hypothesis row with the acceptance criteria below

### Test Plan (acceptance criteria — eval gate)

1. L1 run spawns zero agents and skips tests (observable in run output)
2. L2 = today's behavior + tests; L3 refuses multi-repo scope
3. Headless run never blocks; a seeded ambiguous finding lands in `### Needs input`
4. `make review REPO=x` end-to-end: report written in x, opened in VS Code
5. Token check: L1 visibly cheaper than L2 on the same diff (session cost comparison)

### Risks & Rollback

- Headless permission prompts stall automation → Step 3 probes early; fallback = print
  command. Rollback: delete Makefile, revert SKILL.md level routing (git-less ~/.claude:
  keep pre-edit copy in plan doc comment if needed).
- Level creep (levels accreting sub-flags) → hard rule: 3 levels, no sub-flags; new
  needs = new level or nothing.
- `code` CLI absent → guard with `command -v code || echo report path`.
