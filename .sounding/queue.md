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

## Live pick-up points (as of 2026-07-30 midday)

**Execution day 2026-07-30** — 3 waves dispatched the assessment backlog. 14 branches committed + pushed, awaiting PR + merge (issues close on merge):
- Wave 1: GUA-53, AIT-27, LIS-84, PLG-85, JOB-26, ATL-40
- Wave 2: ATL-41, AIT-28, LIB-54, GUA-49, LIS-85, PLG-86
- Wave 3: AIT-29, LIB-66
  => Next: open/merge PRs; install eval-runner plist after GUA-49 merges.

**Time-sensitive**: librarian PR #69 (cron dashboard fix) must merge before the next 09:00 launchd run.

**Closed via evidence pass**: GUA #31–34/36/37/39/40/42/48, ATL #37, LIS #77, LAE #28/#102/#105. GUA #35 done in-session (CI checks required on main). GUA #41 back to ready (work never landed).

**Wave 4 queue**: AIT #22/#23, LIB #65 (reconcile in-flight dashboard.py first), LIB #68 (region injection), GUA #41/#43–47/#50, LAE #106 (blocked on 3 vendoring decisions).

**guacamayo** — Retro R5 current (07-29). Growth: 4 entries, synthesis at 5.

---

## How mobile /wake uses this

1. Run the normal Phase 4 plan glob. If it returns results (Mac), use them — they're authoritative.
2. If it returns nothing (sandbox), read this file for cross-repo orientation instead.
3. Bodies of the plans referenced here won't be in the sandbox (git-ignored). To act on one,
   either work from the pointer + the repo's committed code, or continue on the Mac.
