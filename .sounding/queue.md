# Cross-Repo Queue — committed pointer for mobile /wake

*Why this file exists:* On the Mac, `/wake` Phase 4 globs `~/workspace/*/.claude/docs/plans/*.md`
for live cross-repo state. Those plan docs are **git-ignored** (`~/.gitignore_global`), so a
mobile/cloud sandbox clones the repos but not the plans — Phase 4 comes back empty. This file
is committed (lives in `.sounding/`, which travels), so it survives the clone and gives mobile
sessions the same orientation the Mac gets from the plan glob.

*What it is:* a **pointer**, not a copy (per `docs.md` "pointers not copies" and guacamayo's own
"continuity files hold pointers, never copies"). It names where live state lives and its last-known
Status. It drifts if not refreshed — treat entries older than a few days as suspect and re-derive
from the source when on the Mac. **Refresh cadence:** update at `/grow` and `/dream`, same
as the handover. The Mac plan glob remains source of truth; this is the mobile shadow.

Legend: `=>` marks a pick-up point (decision / next step / verification owed).

---

## Live pick-up points (as of 2026-07-20 evening)

**guacamayo** (this repo)
- GH Issues #3,#5,#6,#7,#8 — all EXECUTED, changes in worktrees awaiting merge+commit.
  => Merge order: #7 → #8 → #3 → #5 → #6. Add ledger rows for #3, #5, #8. Then close issues.
- GH Issue #4 (akira/SANYI composition) — refinement, failed DoR. Needs /workflow-research.
- `2026-07-20-consciousness-identity-model.md` — EXECUTED. dream-ledger-gate hook live.
- `2026-07-18-skills-refs-evals-norm.md` — EXECUTED (P0-4 complete; P5b deferred).
- `2026-07-17-feedback-loop.md` — EXECUTED.

**ai-project-template**
- `2026-07-18-template-full-mirror-redesign.md` — EXECUTED (all 7 steps + session 16 cleanup).
  => Push `python-ci.yml` to main to unblock rendered projects' CI.
- `2026-07-20-consolidate-capability-reference.md` — EXECUTED.
- sync-global-skills.sh updated with DELIBERATELY_EXCLUDED[] + reverse guard (#5).
  => Ramsey: review and commit ai-project-template changes.

**librarian**
- `2026-07-17-learn-ai-ingest-guacamayo-loop.md` — EXECUTED (M1-M4; M2 second batch + M5 follow-on).
- `2026-07-17-knowledge-compaction.md` — EXECUTED.

**listen-wiseer**
- All phases EXECUTED or COMPLETE. Phase 7a ABANDONED.

**playground**
- `rag-latency-optimization.md` — E1 DONE (streaming), E2 OBSOLETE. E3-E6 viable, lower priority.
  => Next: E3 (Flash-Lite quality regression) or E4 (context chunk reduction).

**contracts rollout** (cross-repo)
- SANYI confirmation interviews still owed on all three SANYI.md files.

---

## How mobile /wake uses this

1. Run the normal Phase 4 plan glob. If it returns results (Mac), use them — they're authoritative.
2. If it returns nothing (sandbox), read this file for cross-repo orientation instead.
3. Bodies of the plans referenced here won't be in the sandbox (git-ignored). To act on one,
   either work from the pointer + the repo's committed code, or continue on the Mac.
