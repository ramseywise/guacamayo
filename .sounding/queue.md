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

## Live pick-up points (as of 2026-07-20)

**guacamayo** (this repo)
- `2026-07-18-skills-refs-evals-norm.md` — EXECUTED (P0-4 complete; P5b deferred).
  => P5b: ADK eval adoption blocked on labeling decision.
- `2026-07-17-feedback-loop.md` — EXECUTED. Phase 4 (/retro eval-gate) pending first real
  skill-change proposal.
- Rename puffin→guacamayo done except: GitHub remote + final commit (on Ramsey).

**ai-project-template**
- `2026-07-20-consolidate-capability-reference.md` — EXECUTED (all 5 phases).
- `2026-07-19-genesis-lifecycle-architecture.md` — EXECUTED.
- `2026-07-19-two-root-scaffold.md` — EXECUTED (all 4 phases).
- `2026-07-17-template-core-redesign.md` — EXECUTED.
- `2026-07-17-evals-suite-port.md` — EXECUTED.
- Multiple worktree branches from parallel agents need merging.
  => Ramsey: review and merge/commit worktree changes.

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
