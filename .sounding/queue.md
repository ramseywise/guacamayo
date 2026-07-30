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

## Live pick-up points (as of 2026-07-30 evening)

**ai-project-template** — AIT-32/33/34 all EXECUTED as commits on `AIT-34-design-rigor-gaps` (b27bd2a → 5852798 → 4eac907 → 8f8bac3); AIT-32 branch tip = 4eac907. Commits 4eac907 (=AIT-33) + 8f8bac3 (=AIT-34) have auto-generated messages.
  => Next: Ramsey rewords both via `git rebase -i 5852798`, re-points AIT-32 branch, pushes, opens PRs (#32/#33 with `py_project_root=backend` pin release note; #34 stacked). Closes #32–34 on merge.

**guacamayo GUA-60** — review driver built, uncommitted on `GUA-60-review-driver` (266 tests + ruff clean; max_turns 15→30).
  => Next: Ramsey reviews + commits; after 7pm usage reset run `review-cli run` ×2 + `trends` for DoD 1+3.

**PRs owed**: listen-wiseer `bug/verification-test-conftest` (pushed), librarian `GUA-44-context-overhead-audit-v2` (pushed).

**Execution day 2026-07-30** — 3 waves dispatched the assessment backlog. 14 branches committed + pushed, awaiting PR + merge (issues close on merge):
- Wave 1: GUA-53, AIT-27, LIS-84, PLG-85, JOB-26, ATL-40
- Wave 2: ATL-41, AIT-28, LIB-54, GUA-49, LIS-85, PLG-86
- Wave 3: AIT-29, LIB-66
  => Next: open/merge PRs; install eval-runner plist after GUA-49 merges.

**Time-sensitive**: librarian PR #69 (cron dashboard fix) must merge before the next 09:00 launchd run.

**Closed via evidence pass**: GUA #31–34/36/37/39/40/42/48, ATL #37, LIS #77, LAE #28/#102/#105. GUA #35 done in-session (CI checks required on main). GUA #41 back to ready (work never landed).

**Wave 4 queue**: AIT #22/#23, LIB #65 (reconcile in-flight dashboard.py first), LIB #68 (region injection), GUA #41/#43–47/#50, LAE #106 (blocked on 3 vendoring decisions).

**learn-ai-engineering** — link-check fix (skip vendored idk/) staged on `LAE-bug-dependabot-config`; old PR #95 merged → needs NEW PR.

**guacamayo** — Retro R5 current (07-29). Synthesis ran at /dream 07-30 evening (7 entries processed).

---

## How mobile /wake uses this

1. Run the normal Phase 4 plan glob. If it returns results (Mac), use them — they're authoritative.
2. If it returns nothing (sandbox), read this file for cross-repo orientation instead.
3. Bodies of the plans referenced here won't be in the sandbox (git-ignored). To act on one,
   either work from the pointer + the repo's committed code, or continue on the Mac.
