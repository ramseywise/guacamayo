# Cross-Repo Queue — committed pointer for mobile /meta-wake

*Why this file exists:* On the Mac, `/meta-wake` Phase 4 globs `~/workspace/*/.claude/docs/plans/*.md`
for live cross-repo state. Those plan docs are **git-ignored** (`~/.gitignore_global`), so a
mobile/cloud sandbox clones the repos but not the plans — Phase 4 comes back empty. This file
is committed (lives in `.sounding/`, which travels), so it survives the clone and gives mobile
sessions the same orientation the Mac gets from the plan glob.

*What it is:* a **pointer**, not a copy (per `docs.md` "pointers not copies" and guacamayo's own
"continuity files hold pointers, never copies"). It names where live state lives and its last-known
Status. It drifts if not refreshed — treat entries older than a few days as suspect and re-derive
from the source when on the Mac. **Refresh cadence:** update at `/meta-grow` and `/meta-dream`, same
as the handover. The Mac plan glob remains source of truth; this is the mobile shadow.

Legend: `=>` marks a pick-up point (decision / next step / verification owed).

---

## Live pick-up points (as of 2026-08-14)

*Refreshed 2026-08-14 (/meta-dream). Prior entries (status-enum arc, CLA guard-fix duplicates, librarian drain, LAE-115 worktree) all resolved or superseded — dropped.*

**ai-project-template — CI on main is RED and the fix is written but uncommitted.** Branch `bug/ml-shape-rag-promotion` holds a 2-file diff (`copier.yaml` 1060/1069/1663, `template/_scaffold/Makefile.jinja:187`) that fixes `test-render`'s ml_model job. Root cause: copier's `_scaffold/` staging→promotion split — cleanup tasks gated on capability flags, promotion tasks on shape flags, so an `ml_model` render that opts into `include_rag_agent` keeps three trees staged and then deletes them with the staging dir. Verified both directions (negative test reproduces CI; fixed tree passes all four assertions, rendered project 242 passed).
  => Next: Ramsey commits + `make ship`. This unblocks every red `test-render` on AIT main.

**galactus — remote `main` restored (2026-08-14).** `spike/consolidate-claude-setup` was renamed to `main` via the GitHub rename API: history preserved, PRs retargeted, redirects created, default set. Local `main` tracking. The merge audit runs again; 9 merged local branches deleted (12 → 3), worktrees 3 → 1.
  => Next: 10 stale *remote* branches still need deleting (push-equivalent — Ramsey's call). List in `notes/handover.md`.

**Branch/stash residue — the standing cross-repo friction.** Branches are created per *attempt*, not per issue, and nothing closes them. After this session: AIT-63 and the 5 `salvage/*` branches deleted (salvage content still in AIT `stash@{0}`–`stash@{4}`, which are now its **only** copy). Still open: `AIT-62-ml-stage-layering` (ahead:3) and `AIT-64-scaffold-vscode-extensions` (ahead:2) need PRs or closure. Stashes: AIT 5, guacamayo 4, playground 1, librarian 1. Orphaned worktree: `/private/tmp/ait-pr74` (`AIT-70-sanyi-mv-fix`).

**guacamayo** — uncommitted `.sounding/` + `telemetry/` changes sitting on the already-merged `bug/friction-loop-capture-and-findings-pk` checkout.
  => Next: cut a fresh branch before committing.

**Open board counts** (08-14): ai-project-template 3 (#64 vscode extensions, #66 make lint-render, #71 deploy targets), galactus 3 (#4, #5, #11), guacamayo 2 (#104 parent `ready`, #106 rising-friction flag), sisyphus 1 (#33), learn-ai-engineering 1 (#106), playground 1 (#88). Clean: librarian, atlas, listen-wiseer, lebanese-blonde.

**guacamayo ops** — synthesis ran 2026-08-14 (/meta-dream, 17 entries). R10 spawned 2026-08-14 (background). Insights refreshed 2026-08-14 (596 sessions). Standing retro items: `tail`/exit-code-masking rule still missing from `~/.claude/rules/shell.md`; global CLAUDE.md still describes galactus as carrying `workflow-*` (renamed `proto-*` 08-11); **bash antipatterns 29.18/session** vs target 12; file-not-found errors +47 in 3 days (141 → 188); `git update-ref -d` bypasses `risky_git_guard.sh`'s `branch -D` block.

---

## How mobile /meta-wake uses this

1. Run the normal Phase 4 plan glob. If it returns results (Mac), use them — they're authoritative.
2. If it returns nothing (sandbox), read this file for cross-repo orientation instead.
3. Bodies of the plans referenced here won't be in the sandbox (git-ignored). To act on one,
   either work from the pointer + the repo's committed code, or continue on the Mac.
