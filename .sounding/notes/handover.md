# Handover — 2026-08-19 22:15 Dispatch session closed the board (PR #155 merged)

**Context**: Pure dispatcher session. Woke on GUA-151 just pushed; ended with the entire
guacamayo board cleared to one deliberate backlog item. Nine agent spawns did the work.

## Current State
- **Board: one open issue** — #154 (hidden-region audit, backlog, gated on per-region
  confirmation from Ramsey — attended pass, never autonomous).
- **PR #155 merged** (`c1f3b31` on main): six commits combining GUA-149 (telemetry truth
  pass), GUA-150 (metacognition automation Session A+B + docs), GUA-152 (job-type
  classification + dashboard bar) + workflow-scope dispatch rule + tab-count restore.
- **Closed this session**: #145, #149 (auto via Closes), #150, #151, #152 — all verified
  by content on origin/main before closing. All manual closes logged to
  `.sounding/telemetry/actions.jsonl`.
- **Worktrees**: all cleaned. Orphan `agent-af83c918` removed (verified: branch merged via
  PR #140, uncommitted edits byte-identical to PR #147's landed content). Source branches
  GUA-149/150/152 deleted after tree-verification against the combined branch.
- **Live checkout**: on merged branch `GUA-149-150-152-combined`; safe to checkout main
  and delete. `board.json` has session churn (uncommitted).

## Decisions Made
- Splitting → task checklists held; combined 3 branches → 1 PR via cherry-pick (worked,
  with one caught regression — see below).
- Dispatch rule codified in `workflow-scope/SKILL.md`: a triage spawn executes the
  orchestrator skill, never the bare one-stage `triage` agent (both #149/#152 stalled at
  `plan` when I spawned the bare worker).
- #152 Q2 resolved by refine agent: job-type bar added (cheap copy of ep_bar pattern).
- Signal count settled by live recount at execute: 64 total / 21 registered.

## Open Threads
- **Closes-line enforcement**: PRs #134, #153, #155 all merged missing `Closes #N` lines
  (5 issues closed manually this week). The closes_link_guard exists (tested on #135) but
  is evidently not catching the actual PR-creation path. Retro input — needs a hook on
  `gh pr create` or a PR template, not memory.
- **Cherry-pick conflict resolutions need invariant checks**: assembly agent's own
  completeness verification passed while it had reverted #150's seven-tab fix. Fixed in
  `b4c2b47`; the detector was a cross-doc content grep.
- **Session ran on fable by accident** — dispatch work on judgment-tier budget. Check
  launch path / settings before next session.
- #154 execution: attended, per-region (unhide / retire / keep), ~260KB/run invisible.

## Immediate Next Steps
1. `git checkout main && git pull` in the live checkout; delete `GUA-149-150-152-combined`.
2. Decide `board.json` churn: commit or discard.
3. Retro (R12) was spawned at dream-close for the tooling changes — verify it landed.
4. When ready for #154: attended session, region-by-region.

## Key Files
- `.claude/skills/workflow-scope/SKILL.md` (dispatch rule + job-type classification)
- `telemetry/dashboard.py` (retro-parse fix ~6983; job-type bar ~7115)
- `.sounding/telemetry/actions.jsonl` (close decisions audit trail)
- `.claude/docs/plans/2026-08-19-telemetry-truth-pass.md` + `-workflow-scope-job-type.md`
  (both EXECUTED via PR #155 — update Status: lines if not already)
