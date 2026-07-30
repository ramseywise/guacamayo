# Handover — 2026-07-30 (Evening) AIT-34 Landed + Isolation Leak Corrected

**Context**: Meta-session (Sounding) closing the 07-30 execution day. Evening arc: AIT-34 worktree dispatch (completed, with isolation leak), LAE link-check fix, /dream with synthesis. Morning arc (3 waves / 15 issues) + afternoon (AIT-33, GUA-60 smoke) in git history + reflections.

## Current State

- **ai-project-template** — checkout on `AIT-34-design-rigor-gaps` = b27bd2a → 5852798 → 4eac907 → 8f8bac3, tree clean. **Both new commits have auto-generated messages needing reword** (agent heredoc swallowed by hook output): `4eac907` = the former staged AIT-33 diff (content byte-correct) → should be `refactor(template): flat layout, terraform + nbks gating (#33)`; `8f8bac3` = AIT-34 (5 files, 102 ins, lint+tests green, Step 8 Scenario C all-PASS) → should be `feat(design): close rigor gaps G3-G6 in scope-poc + DESIGN + gate (#34)`. `AIT-32-decouple-lg-agent-corpus` branch tip is also 4eac907 — after reword, `git branch -f` it to the new SHA. Not soft-reset (would collapse 32/33/34 into one diff).
- **learn-ai-engineering** — link-check fix staged on `LAE-bug-dependabot-config` (`M scripts/link_check.py` +`"idk"` in SKIP_DIRS, `M .gitignore` +`*idk/`), `make test` green. Branch carries stale dep commit 64d89bf; its PR #95 already merged → needs NEW PR. Suggested commit: `fix(lint): skip vendored idk/ in link-check`.
- **guacamayo** — GUA-60 driver work uncommitted on `GUA-60-review-driver` (max_turns 15→30 at driver.py:60; 266 tests + ruff clean). Live smoke (2× `review-cli run` + `trends`) still owed after usage reset — DoD items 1+3.
- **listen-wiseer** — `bug/verification-test-conftest` pushed (89110c8). Needs PR.
- **librarian** — `GUA-44-context-overhead-audit-v2` pushed. Needs PR. PR #69 (dashboard cron fix) time-sensitive — merge before next 09:00 launchd run.
- Untracked `.sounding/dashboard.html` in guacamayo — GUA-21 leftover, verify + delete or commit.

## Decisions Made

- **Worktree isolation is repo-scoped**: a worktree created in the dispatcher's repo does NOT protect a different target repo — the AIT-34 agent (guacamayo worktree, `Repo: ~/workspace/ai-project-template` prompt) worked on the live checkout and committed the staged AIT-33 diff. Rule: cross-repo spawns need the worktree created in the target repo. Logged `[corrected]`, retro-worthy.
- AIT-34 left as stacked commits (no soft-reset) so 32/33/34 stay separable for review.
- LAE fix stacked on the stale branch by staging main's-content+fix so identical changes merge cleanly.

## Open Threads

- AIT-32/33 PR body needs release note: python-only consumers pin `-d py_project_root=backend` before next `copier update`. Draft on request.
- 14 wave branches from the morning awaiting PR + merge (issues close on merge); eval-runner plist after GUA-49 merges.
- Account usage exhaustion masquerades as `error_max_turns` — check quota before diagnosing agents.

## Immediate Next Steps

1. Ramsey: `git rebase -i 5852798` on AIT-34 branch → reword 4eac907 + 8f8bac3 (messages above), `git branch -f AIT-32-decouple-lg-agent-corpus <new-4eac907>`, push both, open PRs (#32/#33 and #34).
2. Ramsey: review + commit `GUA-60-review-driver`; after usage reset run `uv run review-cli run --repo ~/workspace/guacamayo` ×2 + `review-cli trends`.
3. Ramsey: commit + push LAE branch, open new PR; PRs for listen-wiseer + librarian branches; merge librarian PR #69.
4. Issues #32/#33/#34 (AIT), #60 (GUA) close on PR merges.

## Key Files

- ~/workspace/ai-project-template (branch AIT-34-design-rigor-gaps)
- ~/workspace/learn-ai-engineering/scripts/link_check.py
- ~/workspace/guacamayo/review/driver.py
- ~/workspace/guacamayo/.sounding/growth/growth.md
