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

## Live pick-up points (as of 2026-07-29 evening)

**AI Engineering Portfolio Assessment (2026-07-29)** — 3-session arc complete. 11 new issues created and refined to `ready`:
- AIT #27/#28/#29 — verification loop, token budget, OTel spans (P1 template scaffolds)
- LIS #84/#85 — CI-gate RAGAS evals (P1), verification loop (P2)
- ATL #40/#41 — golden datasets, context engineering (P2)
- LIB #66 — answer-quality graders + golden dataset (P2)
- JOB #26 — test suite + CI 0→1 (P2)
- PLG #85/#86 — continuous eval, OTel spans (P3)
  => All `ready`, no plan docs needed (issue body IS the plan). Execute directly.

**Fleet shipment (2026-07-29 earlier)** — 6 PRs still open awaiting merge:
- listen-wiseer PR #83 · atlas PR #39 · learn-ai-engineering PR #104
- ai-project-template PR #26 · librarian PR #64 · guacamayo PR #56
  => After merges: close related issues; `make pull` sweep.

**guacamayo** (this repo)
- 9 issues in `in-review` need audit/merge. 5 `ready`, 5 `backlog`.
- Retro R4 current (2026-07-28). Growth: 7 entries, synthesis due at /dream.

**librarian**
- #54 (path traversal fix) ready. #66 (answer-quality graders) ready — NEW.

**job-system**
- #15, #18, #19 in-progress; #16, #17 in-review; #26 ready — NEW.

**playground**
- #85/#86 ready — NEW. Older PRs still open: PLG #84/#81/#78.

---

## How mobile /wake uses this

1. Run the normal Phase 4 plan glob. If it returns results (Mac), use them — they're authoritative.
2. If it returns nothing (sandbox), read this file for cross-repo orientation instead.
3. Bodies of the plans referenced here won't be in the sandbox (git-ignored). To act on one,
   either work from the pointer + the repo's committed code, or continue on the Mac.
