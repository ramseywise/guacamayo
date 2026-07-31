# Handover — 2026-07-31 19:20 — Board reconciliation, red mains, CI archaeology

**Context**: Meta/dispatcher session in guacamayo. Started as `/wake` board orientation, became a cross-repo audit: closed ~20 issues whose work had already merged, traced the root cause (PRs merging without closing-issue links → guacamayo#67), then chased three separate red-main conditions across librarian, playground, and ai-project-template.

## Current State

**librarian red main — FIXED, staged, awaiting Ramsey's commit.**
Branch `bug/fastapi-dev-dep` (created `--no-track` off `origin/main`). Three files staged: `app/backend/main.py`, `pyproject.toml`, `uv.lock`.
Root cause chain: `tests/unit/test_writeback_security.py` uses `TestClient` as a context manager → runs `lifespan` → imported `.embeddings` → `numpy`. CI runs `uv sync --group dev` (no extras, dictated by ai-project-template's shared `python-ci.yml`), so numpy is absent → 9 test errors.
Fix: `lifespan` now try/except-guards both `api`-extra imports (embeddings warmup, watchfiles watcher) and logs `startup_jobs_skipped`. Both are optimizations, not route requirements. Also removed a vestigial `[project.optional-dependencies] dev` extra, added `fastapi` to the dev group, corrected a stale numpy comment.
Verified both ways: dev-group-only → 319 passed / 1 skipped / ruff clean. Full extras → 318 passed / 2 skipped. **Ramsey's venv was pruned mid-debug and has been restored** (`uv sync --all-extras --group dev`, numpy 2.4.6).

**ai-project-template — diagnosed, NOT fixed.** Two open PRs, both red, and `main` itself red on every matrix leg.
- `main` is broken by two missing `.jinja` extensions: `template/_scaffold/.../agents/{{ lg_agent_dir }}/stall_detector.py` and `verification_loop.py`. Copier copies them verbatim → `Leftover unrendered Jinja found`.
- **PR #35 (`AIT-34-design-rigor-gaps`) is the fix for main** — it has both renamed, gates the `nbks` merge on `has_corpus_pipeline`, adds the smoke test to the lg-agent removal list. 12 legs pass; main passes none.
- PR #35's 7 remaining `test-py` failures are a **stale assertion path, not a template bug**: `.github/workflows/test-render.yml:240` asserts `test -d backend/src/agents/rag_agent`, but the AIT-33 flat layout collapses `py_project_root` to `.` for python-only shapes (`copier.yaml:337-345`), so output lands at `./src`. Lines 245/247 are already unprefixed — 240 was missed. One-line fix: drop the `backend/` prefix.
- PR #35's 8th failure (`test-ts`) is inherited from main: ESLint errors in rendered TS, e.g. `out/render-test/src/agent/context-budget.ts:86:42 comma-dangle`, `139:45 curly`.
- **PR #36 (`AIT-32-decouple-lg-agent-corpus`) still carries the un-suffixed files** and inherits main's break. Rebasing it now gains nothing.

**GUA-62** — 6 commits on `GUA-62-static-analysis-stage`, 962 insertions, tests re-verified (291 passed). Worktree removed. Plan doc: `Status: EXECUTED — 2026-07-31 (pending /workflow-review)`. Needs `git rebase origin/main` before shipping (behind by #68's merge). Issue #62 to close *after* PR merge, per Ramsey.

**Unpushed / unlanded**: `~/.claude` CLA-67 (quick-pr issue-linking rewrite), job-system `bug/stale-quick-pr-override`.

## Decisions Made

- Board labels and CI status are the same defect class — **caches nobody invalidates**. Found drifting in both directions today: open-but-merged (~20 issues), and closed-COMPLETED-but-unmerged (guacamayo#43/#44, whose only code sits on unmerged librarian branches).
- `quick-pr` now derives `Closes #N` from branch name unioned with commit refs, with `ISSUE_REPO` for cross-repo boards (CLA-67). Its `PR already exists → exit 0` early-exit remains a hole — any externally-created PR escapes issue-linking. That is what produced PR #68's malformed body.
- Merge order for AIT: **#35 first** (it unblocks main), then rebase #36. Do not rebase #36 before #35 lands.
- librarian#62 closed with evidence rather than reopened; its three new stale branches split into librarian#73.
- playground#81's EXEMPT broadening filed as a regression in playground#88 (it disabled the issue-linked-branch rule and accepts its own branch name, `fix/ci-pipeline`).

## Open Threads

- **Four FRICTION items Ramsey named for the retro**, now rows in `tooling-ledger.md`: repo-prefix/branch-name mismatch; work not reliably left staged; `make ship`/`make pull` misfiring (ship targets the implicit current checkout — shipped CLA-67 instead of GUA-62); autocompact not firing **in terminal mode**.
- **Ledger row 26 is reopened.** I closed the 07-30 autocompact report as metric confusion after investigating a VS Code transcript. The recurrence specifies terminal mode, which that investigation never covered. Needs a terminal-mode transcript to diagnose.
- **Subagent trust boundary.** A sonnet diagnosis agent inverted diff direction twice at HIGH confidence (claimed main had the `.jinja` rename; prescribed a `nbks` fix the PR had already made). I relayed one error before verifying. Diagnosis agents are reliable on *what failed*, not on *which branch holds the fix* — verify branch-content claims directly.
- Red main is portfolio-wide (3 repos today). Branch protection requiring green checks is the obvious lever — `~/.claude/refs/repo-security-setup.md` has the runbook. Needs a per-repo decision.
- `GUA-43-plan.md` and `GUA-44-plan.md` still read `Status: EXECUTED` while their code is unmerged (librarian#73).
- Unissued LAE branch carrying ~3.4M of untracked artifacts.
- An issue for the `quick-pr` early-exit gap is still unfiled.

## Immediate Next Steps

1. Review and commit the staged `bug/fastapi-dev-dep` diff in librarian — it unblocks that repo's main.
2. Decide on the AIT one-liner (`test-render.yml:240`) — spawn prompt is ready; it's her PR so I didn't touch it.
3. Rebase `GUA-62-static-analysis-stage` onto `origin/main`, then ship.
4. `/dream` should spawn `/workflow-retro` — growth is at 7 entries (synthesis due) and four named FRICTION items are queued.

## Key Files

- `~/workspace/librarian/app/backend/main.py`, `~/workspace/librarian/pyproject.toml`
- `~/workspace/ai-project-template/.github/workflows/test-render.yml:240`, `copier.yaml:337-345`
- `~/.claude/Makefile.common` (quick-pr), `~/workspace/playground/.github/scripts/validate-branch-name.sh:17`
- `.sounding/tooling-ledger.md` (5 rows added today)
- `.claude/docs/plans/GUA-62-plan.md`
