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

## Live pick-up points (as of 2026-07-24)

**guacamayo** (this repo)
- PR #25 (`GUA-23-review-backbone`) — APPROVED. Ramsey to merge.
  => After merge: delete branches GUA-16, GUA-17, GUA-18. Close #23.
- GH Issues #20 (stage transitions), #21 (dashboard consolidation), #24 (friction signals) — backlog.

**~/.claude (dotclaude)**
- PR #1 (`GUA-16-review-artifact-contract`) — APPROVED. Ramsey to merge.
  => Makefile.common updated: `pull` (rebase + auto-stash), `review` (print target).

**learn-ai-engineering**
- PR #74 (`LAE-39-structural-cleanup`) — APPROVED. 36 commits (30 dependabot + structural).
  => `.pre-commit-config.yaml` added (minimal, notebooks excluded).
  => `make pull` (rebase) incompatible with this branch — used `git merge main`.

**ai-project-template**
- PR #18 (`AIT-makefile-updates`) — APPROVED. Vendored skill sync + dependabot workflow.

**atlas**
- PR #26 (`ATL-22-remove-pycache`) — APPROVED. Pycache removal + Makefile updates.
  => 22 pre-existing ruff errors need separate cleanup PR.
- `ttd.md` — IN PROGRESS (unrelated to current shipping).

**librarian**
- PR #41 (`LIB-makefile-dependabot`) — APPROVED. Makefile + dependabot workflow.

**listen-wiseer**
- All phases EXECUTED or COMPLETE. Phase 7a ABANDONED.

**playground**
- `rag-latency-optimization.md` — E1 DONE, E2 OBSOLETE. E3-E6 lower priority.

**contracts rollout** (cross-repo)
- SANYI confirmation interviews still owed on all three SANYI.md files.

---

## How mobile /wake uses this

1. Run the normal Phase 4 plan glob. If it returns results (Mac), use them — they're authoritative.
2. If it returns nothing (sandbox), read this file for cross-repo orientation instead.
3. Bodies of the plans referenced here won't be in the sandbox (git-ignored). To act on one,
   either work from the pointer + the repo's committed code, or continue on the Mac.
