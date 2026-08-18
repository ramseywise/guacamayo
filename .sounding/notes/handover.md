# Handover — 2026-08-18 (session close) GUA-119 built + first live cycle; re-land PR pending

**Context**: Three-day marathon. GUA-119 (autonomous dispatch: evaluator → proposals →
gated mutations → retro spawn → feedback loop) planned, built, reviewed, switched on, and
run through its first live proposal cycle. AIT #83–#86 and GAL #32 closed along the way.
Central discovery at the end: **the GUA-119 stack never actually merged** — PR #134's
head branch was the #120 rider. PR #135 is the re-land.

## Current State
- **PR #135 (`GUA-119-autonomous-dispatch`) is the re-land** — Ramsey pushes. On the
  branch, staged and uncommitted: the `refinement` label fix (evaluator.py:50 + regression
  test, 19 tests green) and the board-signal CI fix (self-bootstrapping orphan checkout in
  `.github/workflows/board-signal.yml` — root cause of #135's red `signal` check: the
  `telemetry-state` branch was never created, so every signal since #118 was lost loudly).
- **The clock is LIVE**: both plists bootstrapped 2026-08-16 (board 10-min, telemetry
  daily 09:00); first scheduled tick verified (heartbeat exit 0). But main lacks the
  evaluator until #135 merges — ticks run branch code from the checkout.
- First proposal batch decided and logged to `.sounding/telemetry/actions.jsonl`:
  3× triage accepted (GAL #5 backlog / #27 refinement / #23 in-review), close #31
  REJECTED — twice-wrong: stale branch pointer AND a worktree
  (`galactus/worktrees/GAL-31-deploy-harden`) holding Ramsey's UNCOMMITTED deploy-harden
  work. #31 relabeled in-progress. Do NOT delete that branch/worktree.
- Staged `.sounding/telemetry/board.json` + `actions.jsonl` contradict the
  untracked-sinks decision — unstage before commit unless policy changed.
- galactus: #36 blocked on Ramsey's gate-1a answers; #23 EXECUTED/Review pending;
  #33 hygiene sweep is next actionable; #27 refined-not-executed.
- `dashboards/` + `AGENTS.md` (untracked) = Ramsey's dashboard experiments (Gemini etc.).
  **Decision 2026-08-18: keep OUR dashboard, fold in the good ideas — "component drift"
  metrics et al.** Unfiled improvement item; see Open Threads.

## Decisions Made
- Split work = task checklist in parent issue, NOT sub-issues (codified 3 places).
- Review dispatch proposal-only until acceptance rates justify auto-run.
- Actions log = `.sounding/telemetry/actions.jsonl`; retro summarizes, ledger stays hand-edited.
- GAL #5 stays backlog though unblocked. RunRecord admits unsupervised runs (schema answer).
- Dashboard direction: improve the existing one (component drift), not adopt the experiments.

## Open Threads
- **Unfiled issues** (Ramsey to green-light, per not-willy-nilly): (a) dashboard
  improvements — component drift + whatever survives from `dashboards/` experiments;
  (b) cron `claude -p` timeout (SF-004); (c) board fetch-failure probe masking (SI-001,
  pre-existing); (d) AIT "record of a refusal" shape (gates GAL#34); (e) rejected
  proposals re-render every tick until underlying state changes — wake could suppress
  by id against actions.jsonl.
- Evaluator gap fixed but unmerged: `refinement` label. Watch first post-merge tick.
- Scheduler liveness: nothing verifies the launchd jobs are RUNNING (both silently absent
  for 2 days). Candidate: wake reads heartbeat age — already does via staleness banner;
  the real gap was nobody ran wake. Retro material.
- File-not-found regression (191, +35%) correlating with 2-3 concurrent sessions — R5,
  insights 2026-08-16. Retro deadline was 2026-08-18.

## Immediate Next Steps
1. Ramsey: unstage telemetry sinks → commit staged fixes → push → merge PR #135.
2. After merge: verify by content (`git ls-tree origin/main telemetry/evaluator.py`) —
   the lesson of this session, applied to its own re-land.
3. Decide which of the five unfiled issues to file.
4. galactus #33 (hygiene) or #36 (after gate-1a answers).

## Key Files
- .claude/docs/plans/2026-08-16-gua-119-autonomous-dispatch.md (EXECUTED/passed + review)
- .sounding/telemetry/{board.json, actions.jsonl, cascade-state.json}
- .github/workflows/board-signal.yml (fix staged), telemetry/evaluator.py:50 (fix staged)
- ~/workspace/galactus/worktrees/GAL-31-deploy-harden (UNCOMMITTED work — protect)
