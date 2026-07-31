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

## Live pick-up points (as of 2026-07-31 evening)

*Refreshed 2026-07-31 19:20 (/grow). The 07-30 wave entries are gone — those PRs all merged.*

**librarian** — red main FIXED, staged on `bug/fastapi-dev-dep` (main.py + pyproject.toml + uv.lock). Cause: `TestClient` context manager runs `lifespan`, which imported `.embeddings` → numpy, absent under CI's `uv sync --group dev`. Fix guards both `api`-extra startup jobs. Verified 319 passed dev-only / 318 full-extras.
  => Next: Ramsey reviews + commits + ships. Unblocks that repo's main.

**ai-project-template** — main red on EVERY matrix leg (two files missing `.jinja`: `stall_detector.py`, `verification_loop.py`). PR #35 (`AIT-34`) is the fix and passes 12 legs. Its 7 remaining `test-py` failures are a stale assertion at `.github/workflows/test-render.yml:240` (`backend/src/...` vs flat-layout `src/...`) — one-line fix. 8th failure is TS ESLint inherited from main. PR #36 (`AIT-32`) still has the un-suffixed files; do NOT rebase it until #35 merges.
  => Next: decide the one-liner on #35, merge #35, then rebase #36. Separate issue owed for the TS lint errors on main.

**guacamayo GUA-62** — static-analysis stage EXECUTED, 6 commits on `GUA-62-static-analysis-stage` (291 tests green). Plan doc `Status: EXECUTED — 2026-07-31 (pending /workflow-review)`. Behind origin/main by #68.
  => Next: rebase onto origin/main, then ship. Close #62 after PR merge.

**Unpushed local work**: `~/.claude` `CLA-67-quick-pr-issue-linking` (quick-pr derives closing-issue links; PR #68 merged but the global-side change is separate), job-system `bug/stale-quick-pr-override`.

**librarian stale branches (LIB #73)** — `GUA-21-dashboard-consolidation` (1/16), `GUA-43-dashboard-segmentation` (1/17, local-only), `GUA-44-context-overhead-audit` (2/17, local-only). guacamayo#43/#44 are already closed COMPLETED while this code is unmerged. Note the prefix violation: these should be `LIB-`.
  => Next: push the two local-only branches first (single-copy work), then land or discard. Correct `GUA-43-plan.md` / `GUA-44-plan.md` `Status: EXECUTED`.

**Open board counts** (07-31 19:20): guacamayo 8, librarian 9, ai-project-template 4, job-system 3, learn-ai-engineering 1, listen-wiseer 1, playground 1. Clean: atlas, lebanese-blonde.

**Root-cause issues filed today**: guacamayo#67 (PRs merging without closing-issue links — 5 instances), playground#88 (#81's EXEMPT broadening disabled the issue-linked-branch rule), librarian#73 (stale branches).

**guacamayo** — Retro R6 current (07-30). Growth at 7 entries → synthesis due at next /dream. Retro-worthy: yes (4 named FRICTION items + red-main-accepts-merges across 3 repos).

---

## How mobile /wake uses this

1. Run the normal Phase 4 plan glob. If it returns results (Mac), use them — they're authoritative.
2. If it returns nothing (sandbox), read this file for cross-repo orientation instead.
3. Bodies of the plans referenced here won't be in the sandbox (git-ignored). To act on one,
   either work from the pointer + the repo's committed code, or continue on the Mac.
