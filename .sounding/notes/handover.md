# Handover — 2026-07-22 Continuation (make ship ready)

**Context**: Multi-arc session continued from context compression. Primary work: fixing all workspace `make lint`, `make test`, `make pull` failures so Ramsey can run `make ship`.

## Current State

### listen-wiseer — async test contamination FIXED
- Root cause: 6 test files used `asyncio.get_event_loop().run_until_complete()` in sync test functions — poisoned event loop state for subsequent files under pytest-cov
- Fix: all 6 files converted to `async def test_*` + `await`; `asyncio` imports removed; `ruff --fix` cleaned isort
- **Result: 474 passed, 3 skipped, 0 failures** — from 42 failures before fix
- Files touched: `test_intent_routing.py`, `test_optimizer.py`, `test_validation.py`, `test_nodes.py`, `test_memory_store.py`, `test_trajectory_eval.py`
- All changes uncommitted (Ramsey commits)

### Workspace make sweep — all clear
- `make lint`: all repos PASS or SKIP (no pre-commit config) — listen-wiseer now PASS
- `make test`: all runnable repos PASS; CryptoZombies npm fail is pre-existing, unrelated
- `make pull`: all repos OK or SKIP (uncommitted changes in guacamayo, listen-wiseer, playground, LeetCode)

### Model default correction (from prior dream)
- `claude-sonnet-4-5-v2` was set as session default — invalid model ID, user couldn't start sessions
- Fixed: `~/.claude/settings.json` reverted to `claude-opus-4-6`
- `~/.claude/refs/models.md` updated: fable not available as session model ID
- `~/.claude/CLAUDE.md` updated: default session model is opus

### guacamayo — GUA-9-workflow-simplification branch
- All 3 phases complete: pipeline reorder, Makefile, wake/dream retro nudge
- Uncommitted: Makefile, CLAUDE.md, skill files, tooling-ledger.md, sounding.md (synthesized)
- Ready for `make ship`

### ai-project-template
- sync-global-skills.sh: `review-shared` added, `code-pr` removed
- copier.yaml: matching cleanup list fix
- All uncommitted

## Decisions Made
- **Model default**: opus (`claude-opus-4-6`) — opening sessions. Fable not available as session model. Escalation: opus-always for planning/retro/audit/dream.
- **Async test pattern in listen-wiseer**: `async def` + `await` only — no `_run()` wrappers. This is now the established pattern across all test files.
- **Contamination diagnosis method**: grep for `asyncio.get_event_loop\|asyncio\.run\|_run(` across ALL test files before starting a fix — don't scope to the first file that surfaces.

## Open Threads
- **GUA-9 PR**: `make ship` from GUA-9-workflow-simplification (Ramsey — ready now)
- **listen-wiseer**: commit async test fixes, then `make ship` for any open branch
- **ai-project-template**: commit sync fixes + synced template files
- **JOB PR**: `job-bootstrap` branch → `gh pr create` closing #1-5
- **LAE PR**: `LAE-39-structural-cleanup` branch → `gh pr create` closing #25,28,30,31,32,33,39
- **Atlas blockers**: Chronos index bug (nodes.py:144), train/test contamination (nodes.py:238) — create GH issues
- **Librarian blockers**: double LLM call (agent.py:208), path traversal (server.py:566) — create GH issues
- **Fable test**: spawn `claude --model claude-sonnet-4-5-v2` if/when available → `/akira scan` atlas/nodes.py

## Immediate Next Steps
1. `make ship` from GUA-9-workflow-simplification (after committing)
2. Commit listen-wiseer async test fixes
3. Commit ai-project-template sync fixes
4. Create JOB and LAE PRs

## Key Files
- `~/workspace/listen-wiseer/tests/unit/` — 6 test files converted (async pattern)
- `~/workspace/guacamayo/Makefile` — new (lint/test/pull/push/quick-pr/ship)
- `~/workspace/guacamayo/.claude/docs/plans/2026-07-22-akira-model-experiment.md` — full akira experiment results
- `~/workspace/guacamayo/.claude/docs/plans/2026-07-22-workflow-simplification.md` — GUA-9, EXECUTED
- `~/.claude/settings.json` — model = claude-opus-4-6 (corrected from sonnet-4-5-v2)
- `~/workspace/ai-project-template/scripts/sync-global-skills.sh`
- `~/workspace/ai-project-template/copier.yaml`
