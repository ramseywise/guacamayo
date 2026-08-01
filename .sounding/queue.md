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

*Refreshed 2026-08-01 (/grow). The 07-31 librarian / AIT-35 / GUA-62 entries are gone — all landed.*

**`~/.claude` (dotclaude)** — CLA-71 guard defect fixed and committed as `2863fb4` on `bug/risky-guard-variable-cd`, **unpushed**. `risky_git_guard.sh` now resolves a mid-chain `cd` (takes the LAST one) and blocks `$VAR` targets without asserting a `Resolved target:` it never resolved. Suite 20 → 26 cases, all green.
  => Next: Ramsey pushes + ships.

**guacamayo GUA-63** — `GUA-63-session-id-findings`, 2 commits, no remote. Verified merge-clean against origin/main (`git merge-tree`), rebased in a probe worktree, `uv run pytest tests/review -q` → 302 passed.
  => Next: Ramsey pushes + opens PR with `Closes #63`.

**learn-ai-engineering LAE-30 — RESOLVED (discarded).** `LAE-30-rl-depth-content` was stale, not single-copy: `rl.md` and `05-RL/README.md` were byte-identical blobs to main; of 86 touched files only 3 genuinely differed and main was ahead in all 3 (pre-TF2 `tf.Session()` code, missing README book-notes section, deleted a `bayesian.yml` main kept). Issue LAE#30 already closed. Branch is gone as of 08-01; nothing owed. (`LAE-28-docs-integration` still exists as a branch — worktree pruned, branch fully merged, safe to delete.)

**ai-project-template** — three fixes staged/committed for #40, #42, #43 (#43 shipped as `de75e98`). PRs #46/#47/#48 all MERGEABLE. Durable patch exports at `.claude/docs/patches/*.patch` (git-ignored) back the `/tmp` worktrees for #40/#42.
  => Next: Ramsey `make ship` from the workspace, merge, close #40/#42/#43. Open DoD question: close now or after merge? Also check whether #42's work already closes #41.

**guacamayo GUA-73** — checkout is on `GUA-73-status-enum-design` with `.claude/docs/specs/plan-doc-status-enum.md` staged. Another session started the Status-enum design; #74/#75 are blocked behind it.

**librarian#73 — CLOSED.** GUA-43/GUA-44/GUA-21/LIB-68 all landed via `-v2` rebuild branches (PRs librarian#77, #78), not the originals — verified by content on main, not by commit message. Plan docs GUA-43/GUA-44/GUA-62 marked COMPLETE. The prefix violation (`GUA-` on librarian branches) is still an open FRICTION row.

**Open board counts** (08-01): guacamayo 10, librarian 8, ai-project-template 5, job-system 3, learn-ai-engineering 1, listen-wiseer 1. Clean: atlas, lebanese-blonde.

**guacamayo** — Retro R6 (07-30) is the last. Growth at 11 entries (threshold 5) → synthesis due at next /dream. **Retro-worthy: yes** — R7 warranted: 4 named FRICTION items from 07-31, red-main-accepts-merges across 3 repos, CLA-71's third recurrence, 29 open hypotheses.

---

## How mobile /wake uses this

1. Run the normal Phase 4 plan glob. If it returns results (Mac), use them — they're authoritative.
2. If it returns nothing (sandbox), read this file for cross-repo orientation instead.
3. Bodies of the plans referenced here won't be in the sandbox (git-ignored). To act on one,
   either work from the pointer + the repo's committed code, or continue on the Mac.
