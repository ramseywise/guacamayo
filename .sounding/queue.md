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

## Live pick-up points (as of 2026-08-01)

*Refreshed 2026-08-01 late (/grow, post-R7). GUA-63, GUA-73 and the whole AIT #40–#44 arc are gone from this list — all landed and closed.*

**`~/.claude` (dotclaude) — THE ONE REAL OWED ITEM.** CLA-71 guard fix `2863fb4` is **still not on origin/main** (verified `merge-base --is-ancestor`). It sits on **two identical branches** — `bug/risky-guard-variable-cd` and `CLA-8-insights-computed-columns` — with an empty diff between them and no upstream on either; the checkout is currently on the CLA-8 one. `main` is behind 40. `risky_git_guard.sh` resolves a mid-chain `cd` (takes the LAST) and blocks `$VAR` targets without asserting a path it never resolved; suite 20 → 26 green.
  => Next: Ramsey picks ONE branch, deletes the duplicate, pushes + ships.

**guacamayo GUA-63 / GUA-73 — LANDED, ISSUES STILL OPEN.** PRs #76 and #77 are MERGED and both tips are ancestors of origin/main. But both PRs have **empty bodies and zero closing-issue references**, so #63 still reads `ready` and #73 `in-review`. Cause is the filed-but-unfixed guacamayo#69 (`quick-pr` exits 0 on an existing PR → externally-created PRs escape issue-linking).
  => Next: close #63 and #73 by hand; #69 is the durable fix. GUA-65/#74/#75 unblock once #73 closes.

**ai-project-template — ARC COMPLETE.** #40, #41, #42, #43, #44 all closed 2026-08-01 21:17. The standing DoD question ("close now or after merge?") is resolved by action. New backlog since: **#49** (60-min LLM starter kit — plan doc exists at `.claude/docs/plans/2026-08-01-49-llm-starter-kit.md`), **#50** (security/guards called by nothing, both languages), **#51** (extend unimported-module guard to the Python render).

**learn-ai-engineering** — LAE-30 resolved/discarded 08-01. Live now: an **empty worktree** at `/private/tmp/.../wt-lae-115` holding `LAE-115-case-study-code-test` under a `+` branch lock while zero commits ahead of origin/main. `LAE-28-docs-integration` is fully merged, remote gone, safe to delete.
  => Next: prune the LAE-115 worktree unless a session is actively in it.

**librarian — the big open queue, 8 issues.** #57/#58/#59/#75 all `ready` with 07-31 plan docs (factstore failure-attribution, experiment verdicts as data, ledger chart annotations, region renderers); #65 initiative "Dashboard as a contract", #68 region injection, #61 insights section contract, #64 eval tab, #60 backlog. librarian#73 closed — GUA-43/44/21/LIB-68 landed via `-v2` rebuild branches, verified by content.

**Open board counts** (08-01 late): guacamayo 10, librarian 8, ai-project-template 3, job-system 3, learn-ai-engineering 2, listen-wiseer 1, playground 1. Clean: atlas, lebanese-blonde.

**guacamayo** — R7 ran 2026-08-01; not overdue. Growth accumulator at 9 (threshold 5) → **synthesis due at next /dream**. 33 hypothesis rows, none stale (>2wk); a cluster comes due 08-17. Insights refreshed 08-01 23:24 (323 sessions): cache 96%/84% savings, subagents 648 transcripts = 40% of spend, >150k share 21%. **Bash antipatterns 28.99/session, up again from 28.55** — still the only metric moving the wrong way.

---

## How mobile /wake uses this

1. Run the normal Phase 4 plan glob. If it returns results (Mac), use them — they're authoritative.
2. If it returns nothing (sandbox), read this file for cross-repo orientation instead.
3. Bodies of the plans referenced here won't be in the sandbox (git-ignored). To act on one,
   either work from the pointer + the repo's committed code, or continue on the Mac.
