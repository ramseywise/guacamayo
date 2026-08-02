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

## Live pick-up points (as of 2026-08-02)

*Refreshed 2026-08-02 (/grow, ingest-only). GUA-63/#73 and guacamayo #69/#78 are gone from this list — closed, and #69/#78 verified on main by SHA ancestry. Five librarian issues closed overnight.*

**`~/.claude` (dotclaude) — STILL THE ONE REAL OWED ITEM (24h unchanged).** CLA-71 guard fix `2863fb4` is **still not on origin/main** (re-verified `merge-base --is-ancestor` on 08-02). It sits on **two identical branches** — `bug/risky-guard-variable-cd` and `CLA-8-insights-computed-columns` — with an empty diff between them and no upstream on either. `main` is behind 42. `risky_git_guard.sh` resolves a mid-chain `cd` (takes the LAST) and blocks `$VAR` targets without asserting a path it never resolved; suite 20 → 26 green.
  => Next: Ramsey picks ONE branch, deletes the duplicate, pushes + ships.

**`~/.claude` — new sprawl artifact.** `CLA-78-lint-parity` tip `92649ba` is **unlanded**, but a byte-equivalent commit `36be12e` reached origin/main from the `CLA-74-status-writers` branch. Third instance of the pattern (after AIT #40/#42 and the guard fix) — first one that is cross-issue.
  => Next: delete or rebase `CLA-78-lint-parity`; its content is already on main.

**guacamayo status-enum arc — the live workstream.** #74 `in-review` (Status writers + PostToolUse validation hook), #75 `ready` (migrate plan-doc Status corpus, guacamayo first then 7 repos), #65 `ready` (canonical Status enum), #79 `backlog` (flip hook warn→reject, explicitly gated on #75). Local `main` is behind 12; checkout on `GUA-73-status-enum-design` (PR #80 merged); `GUA-63-session-id-findings` has a gone upstream.
  => Next: order the arc. Note the drift that proves it: plan docs for #69 and #78 still read `IN PROGRESS` / `EXECUTED` while both issues are **closed** — left uncorrected on purpose as a test case for #74's hook.

**ai-project-template — ARC COMPLETE.** #40, #41, #42, #43, #44 all closed 2026-08-01 21:17. The standing DoD question ("close now or after merge?") is resolved by action. New backlog since: **#49** (60-min LLM starter kit — plan doc exists at `.claude/docs/plans/2026-08-01-49-llm-starter-kit.md`), **#50** (security/guards called by nothing, both languages), **#51** (extend unimported-module guard to the Python render).

**learn-ai-engineering** — LAE-30 resolved/discarded 08-01. Live now: an **empty worktree** at `/private/tmp/.../wt-lae-115` holding `LAE-115-case-study-code-test` under a `+` branch lock while zero commits ahead of origin/main. `LAE-28-docs-integration` is fully merged, remote gone, safe to delete.
  => Next: prune the LAE-115 worktree unless a session is actively in it.

**librarian — queue drained 8 → 3.** #57, #58, #59, #61, #75 all closed 2026-08-02 ~11:04. Remaining: #65 initiative "Dashboard as a contract" (`ready`), #85 (`/workflow-insights` reads computed factstore values, `backlog`), #60 (weekly friction cron emits empty analyses — fix or retire, `backlog`).

**Open board counts** (08-02): guacamayo 8, job-system 3, ai-project-template 3, librarian 3, learn-ai-engineering 2, listen-wiseer 1, playground 1. Clean: atlas, lebanese-blonde.

**guacamayo** — R7 ran 2026-08-01; not overdue. Growth accumulator at **15** (threshold 5) → **synthesis due at next /dream**. Insights last refreshed 08-01 23:24 (323 sessions); a fresh background run was spawned 08-02. **Bash antipatterns 28.99/session** — still the only metric moving the wrong way, and I added one to it this session (`grep ... scripts/quick-pr*`, zsh nomatch).

---

## How mobile /wake uses this

1. Run the normal Phase 4 plan glob. If it returns results (Mac), use them — they're authoritative.
2. If it returns nothing (sandbox), read this file for cross-repo orientation instead.
3. Bodies of the plans referenced here won't be in the sandbox (git-ignored). To act on one,
   either work from the pointer + the repo's committed code, or continue on the Mac.
