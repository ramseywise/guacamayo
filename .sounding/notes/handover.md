# Handover — 2026-08-02 (late) LIB-60 executed and closed; LIB-65 initiative closed

**Context**: librarian cartographer. All six steps of the LIB-60 plan executed and merged;
issues #60 and #65 closed. **librarian's open-issue count is 0.** A privacy exposure was
found and closed mid-session. Guacamayo identity synthesis ran (36 entries → seeds).

## Current State

**Merged to librarian `main` (verified by content on `origin/main`, not by message):**
- `tools/cartographer/__main__.py` — `--no-derive` / `--since` flags; derivation block runs
  before `from_notes`; fails loud via `EmptyInputError` when the JSONL source yields nothing.
- `tools/cartographer/migrate.py` — `derive_notes()`, `_derive_project()`, `_note_stem()`
  (appends `-<sid8>` so same-day sessions cannot collide), `_render_skeleton()`.
- `tools/cartographer/cron.py` — −400 lines. Entire LLM analysis stage retired
  (`build_analysis_prompt`, `run_analysis`, `save_report`, `extract_and_write_commands`,
  pricing tables, facet loaders). `EmptyInputError` **kept** and re-documented. `--cron` is
  now deterministic and key-free.
- `tools/cartographer/cartographer-cron.sh` — one log per mode
  (`cartographer-facts.log` / `cartographer-cron.log`); `REPO_DIR` fixed to `../..`.
- `tests/unit/test_cron_empty_input.py` — rewritten, 10 tests, both directions.
- `tests/unit/test_migrate_derivation.py` — new, 6 tests.
- `.gitignore` — `raw/`, `data/raw/`, `data/db`, and `data/wiki/meta/session-log.md`.

**Verification captured**: 343 notes derived; second run derives 0; empty `--projects-dir`
→ `FATAL: no JSONL sessions found ... refusing to run on empty input`, exit 1; `--cron`
with `ANTHROPIC_API_KEY` unset → exit 0, 348 files tagged, 14 new wiki dates. Suite:
**539 passed / 2 skipped**, `ruff check .` clean. Guard proven falsifiable by planting
`if False and not sessions:` → 3 tests failed.

**Uncommitted (guacamayo — hers to commit):**
- `.sounding/context-dashboard.html`
- `.sounding/growth/growth.md` (accumulator cleared by this synthesis)
- `.sounding/growth/growth-log.md`, `.sounding/sounding.md`, `.sounding/portfolio.md`
- `.sounding/reflections/2026-08-02_22-13.md` + index line
- `.sounding/notes/handover.md`

## Decisions Made

- **`raw/` and `data/wiki/meta/session-log.md` are now gitignored, and the session log was
  untracked (`git rm --cached`).** librarian is a **PUBLIC** repo. LIB-60's gap-3 fix (real
  topics in the wiki session log) put 237 rows of **verbatim first prompts** into a tracked
  file — a change in kind from the curated summaries in earlier revisions. Earlier history
  is safe; the new rows were not. Do not re-track either path.
- **The amended Step 4 was followed, not the original.** The original said to delete
  `EmptyInputError`; that class shipped via PR #92 the day before and is the fix. The plan
  doc was a snapshot of a repo that had moved.
- **`guacamayo#66` is a phantom** — cited 4× in LIB-65's body as a Phase 3 child, has never
  existed. References **struck in place with a correction note**, not deleted: a parent whose
  AC is "closes when all children close" can never close against an imaginary child, and a
  silently-removed phantom teaches no future grooming pass.
- **LIB-75 was already shipped** — confirmed by content on `origin/main`
  (`git grep -cE "def patch_(input_tokens|skill_economics|tool_trends|friction_regroup)_card"`
  → 4), not by its stale `ready` label.
- **Plan doc stamped `Status: EXECUTED` + `Review: pending`** with a full execution record
  (per-step table, AC table 4/4, two unanticipated findings).

## Open Threads

- **`2863fb4` LANDED** (2026-08-03). Rebased to `f58dba4` in a throwaway worktree, then
  `git branch -f main` — a fast-forward ref update, no authored commit. Verified by content
  (`git grep -cE "unexpandable|cannot expand|could not expand" main -- hooks/risky_git_guard.sh`
  → 3). `main` is `[origin/main: ahead 1]` — **hers to push**; that closes dotclaude#13.
  Leftover duplicate pointer `bug/risky-guard-variable-cd` = `f58dba4`; `risky_git_guard.sh`
  blocks me from `branch -D`, so deletion needs her hand.
- **`~/.claude` uncommitted work is now on `CLA-8-config-batch`** (off main, not on it).
  Three unrelated items batched at her direction: workflow-insights (#8), the
  "issues live in the repo they change" convention change (no issue),
  `skills/workflow-plan/references/golden-set-authoring.md` (no issue). Hers to commit.
- **Runtime files untracked** (`git rm --cached`, all intact on disk): `.hook-log.jsonl`,
  `.hook-pass-log.jsonl`, `tasks/`, and the whole `docs/` dir. `.gitignore:33` is now
  `docs/` rather than a single file.
- **`~/.claude/docs/` keeps getting recreated, and LIB-60 did not stop it.** Only the LLM
  *report* stage was deleted; `cron.py:34` still points `INSIGHTS_DIR` at
  `~/.claude/docs/insights`, and `cron.py:337-339` still writes `latest.json` there every
  `--cron` run (last: `2026-08-03T07:40:29Z`). Gitignoring `docs/` fixes the git symptom
  only. Real fix = repoint that writer at `guacamayo/.sounding/insights/`, where insights
  output already lives. Same run reported `sessions_synced: 0` without complaint — `--cron`
  doesn't fail loud on empty the way `--facts` does. **Filed: librarian#94** (`backlog`),
  both defects, with acceptance criteria. Needs `/workflow-plan` in a librarian session.
- **Insights-log path fixed in 5 skill files** — the real file is
  `.sounding/insights/insights-log.md`; five places said `.sounding/insights-log.md`, so
  every reader (`/wake`, `/grow`, `/dream`'s retro spawn, `/workflow-retro`) was pointed at
  a nonexistent file and would have silently reported "no insights data." Fixed in
  `~/.claude/skills/workflow-insights/SKILL.md:242`, `~/.claude/skills/workflow-retro/SKILL.md:60`,
  and guacamayo's `wake/SKILL.md:82`, `grow/SKILL.md:97,105`, `dream/SKILL.md:161`.
  Still stale: `ai-project-template/template/.claude/skills/workflow-insights/SKILL.md:242`
  — vendored payload, never hand-edited; picks the fix up on the next
  `scripts/sync-global-skills.sh` run.
- **AIT#49** — decide: run the 60-minute dry-run, or close accepting the unvalidated AC.
- **Temp renders on disk**: `/tmp/ait58verify`, `/tmp/aitfull{,2,3}`, `/tmp/aitdef{2,3}`,
  `/tmp/ait56render`, `/tmp/ait56ts`, `/tmp/lib60-empty`. Cleanup blocked by
  `destructive_cmd_guard.sh`.
- **No verification step asks "what did this change make newly visible?"** The privacy leak
  came from a fix working correctly. Candidate for a `/workflow-review` DoD line.

## Immediate Next Steps

1. Commit the guacamayo working tree (reflection + synthesis + dashboard + handover).
2. Land or delete `2863fb4` in `~/.claude` — it needs her hand either way.
3. Triage the uncommitted `~/.claude` tooling diff.
4. Pick the next work item: librarian is empty; guacamayo and AIT hold the open board.

## Key Files

- `~/workspace/librarian/tools/cartographer/__main__.py`
- `~/workspace/librarian/tools/cartographer/migrate.py`
- `~/workspace/librarian/tools/cartographer/cron.py`
- `~/workspace/librarian/.gitignore`
- `~/workspace/librarian/.claude/docs/plans/2026-07-31-LIB-60-session-note-derivation.md`
- `~/workspace/guacamayo/.sounding/reflections/2026-08-02_22-13.md`
