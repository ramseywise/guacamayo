# Handover — 2026-07-30 Execution Day: 3 Waves, 15 Issues, 7 Repos

**Context**: Meta-session dispatched the portfolio-assessment backlog. Morning: traced + fixed the dashboard.html cron regression. Then three execution waves of parallel sonnet agents, one per target repo, plus an evidence-based close pass over stale issues.

## Current State

**All agent branches committed + pushed by Ramsey** (issues close on PR merge):
- Wave 1: `GUA-53-shellcheck-lint`, `AIT-27-verification-loop`, `LIS-84-ci-gate-ragas`, `PLG-85-continuous-eval`, `JOB-26-test-suite-ci`, `ATL-40-golden-datasets`
- Wave 2: `ATL-41-context-engineering`, `AIT-28-token-budget`, `LIB-54-path-traversal`, `GUA-49-eval-runner`, `LIS-85-verification-loop`, `PLG-86-otel-spans`
- Wave 3: `AIT-29-otel-spans`, `LIB-66-answer-graders` (check push state)

**Dashboard cron regression fixed**: librarian `bug/cartographer-dashboard-path` → PR #69 (`--no-dashboard` on facts cron; defaults corrected — old `--ledger` default pointed at a nonexistent file). **PR #69 must merge before the next 09:00 launchd run** or dashboard.html regenerates. Real fix (region injection into context-dashboard.html marker regions) = LIB #68.

**Closed today (evidence pass)**: GUA #31/32/33/34/36/37/39/40/42/48, ATL #37 (PR #39), LIS #77 (PR #83), LAE #28/#102/#105. Done in-session: GUA #35 (required status checks `ci / lint`+`ci / test` now on guacamayo main, strict).

**Not done, back to ready**: GUA #41 (parser stratification — no code exists; matches ledger hypothesis due 08-17).

## Decisions Made

- Bulk-close needs evidence per issue — double-check caught 2 of 10 "merged" issues that weren't (GUA #35, #41).
- GUA #49 eval runner placed in guacamayo `scripts/` (librarian + ~/.claude were mid-flight). Migration to librarian tools/ possible later. Plist NOT installed — Ramsey's step post-merge (instructions in agent report / scripts/com.wiseer.eval-runner.plist).
- Branch creation for cross-repo agents: always `--no-track` — `checkout -b X origin/main` set upstream to main and broke the push flow (fixed via `branch --unset-upstream` on 6 repos).
- PLG #85 fabricated baseline seeds stripped — baselines seed from first real run only.

## Open Threads

- **Wave 4 candidates**: AIT #22/#23 (behind #29 merge), LIB #65 (collides with in-flight dashboard.py work — reconcile first), LIB #68 (region injection), GUA #41/#43/#44/#45/#46/#47/#50, LAE #106 (needs Ramsey's 3 vendoring decisions: manifest-vs-submodule-vs-LFS; PDFs in git or drive+index; WHAT-TO-READ.md per pruned repo).
- **GUA #43/#44 reconciliation**: unmerged librarian branch `GUA-43-dashboard-segmentation` + uncommitted `dashboard.py` diff in `/private/tmp/librarian-gua43` worktree (coverage-table row). Salvage or restart before spawning.
- **Label-lag pattern (retro-worthy)**: 14 issues today were open for already-merged work. Auto-label hook (#42, closed) exists — why didn't it close/transition these? Candidate retro item.
- **Eval-runner follow-on**: 3 of 53 evals.json need a harness (akira, sanyi behavioral; harness-creator) — future issue when GUA #47 Eval tab starts.
- **LIB #66 caveat**: committed baseline is oracle-only (1.0/1.0); wiring real pipeline.search/answer scores is separate live-server work.

## Immediate Next Steps

1. Merge PR #69 (librarian cron fix) — time-sensitive
2. Open + merge PRs for the 14 pushed branches; issues close on merge
3. Install eval-runner plist after GUA #49 merges
4. Answer LAE #106 vendoring questions → spawn it
5. Reconcile GUA #43/#44 in-flight artifacts → wave 4

## Key Files

- `.sounding/tooling-ledger.md` (dashboard hypothesis row updated: failed day 1 → fixed, clock reset)
- `librarian/tools/cartographer/__main__.py`, `cartographer-cron.sh` (on bug branch / PR #69)
- `scripts/eval-runner.sh`, `scripts/com.wiseer.eval-runner.plist` (on GUA-49 branch)
- `guacamayo/.claude/docs/research/ai-eng-portfolio-assessment.md` (the source assessment)
