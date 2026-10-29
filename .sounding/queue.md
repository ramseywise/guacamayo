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

## Live pick-up points (as of 2026-08-15)

*Refreshed 2026-08-15 (/meta-dream, session close). The PR #124 conflict, the galactus `main` repair, the #125 branch, and the tracked-telemetry friction are all **resolved** — dropped from the pick-up list and recorded below as outcomes.*

**guacamayo — PR #124 MERGED (`ee2502e`), closing #109 / #111 / #114 / #115 / #116.** CONFLICTING was never a merge problem — the branch was 5 ahead / 21 behind because a local commit had never been *pushed*. After main moved, one real conflict appeared in `.claude/skills/meta-retro/SKILL.md`. Ramsey saw two, git saw one; both true — the branch renames `workflow-retro/` → `meta-retro/`, and **GitHub lists both sides of a rename pair as separate conflicts**. One file, two names. Resolved by taking GUA-103's file plus main's two hunks.

**galactus — `main` was unbuildable, now FIXED.** A duplicate `ml` key in `pyproject.toml` and a truncated `uv.lock` made `uv run` fail repo-wide from PR #25 until the repair merged. `origin/main` is `f7d407f`; both files parse.
  => **Standing follow-up, still undecided (2 sessions old):** a **parse check on `pyproject.toml`/`uv.lock` as its own pre-merge step**. No pytest case can cover it — a repo whose CI runs through its own package manager has zero coverage of the file that manager parses first. The failure is upstream of the test runner.

**galactus — #20 and #23 CLOSED (2026-08-15).** Both merged without a `Closes #N`, and the merge **auto-deleted the branch that was the only remaining join evidence** — the issue outlived every trace of its own completion.
  => **`Closes #N` must be in the PR body at merge time** or the join is unrecoverable.

**guacamayo — the merged-PR near-miss.** `GUA-125-port-workflow-skill-updates` showed PR #126 MERGED, the signal you delete on. `git merge-base --is-ancestor` said **no**: the branch carried `8dc1ee8` with all four of that session's `/grow` artifacts (handover, queue, growth entries, dashboard). Files ported first, then deleted. **A merged PR is not evidence its branch is landed.**

**Branch residue — cleared.** Deleted: guacamayo `GUA-103-wake-consistency-check`, `GUA-125-*`, `GUA-115-finding-attribution`; galactus `GAL-20-*`, `GAL-4-*`, `GAL-23-proto-pipeline-dry-run`, `spike/prototype-genesis-ml`, `bug/galactus-pyproject-duplicate-ml-key`; `~/.claude` `CLA-14-*`. guacamayo local is `main` + `bug/untrack-telemetry`.

**guacamayo — telemetry sinks UNTRACKED (resolved).** `.sounding/telemetry/*.jsonl`, `cascade-state.json` and `consistency.json` were gitignored **and tracked** — the rule was added after they entered the index, so it did nothing, silently, forever. `git rm --cached` fixed it; the "every session ends owing a telemetry commit" tax is gone.

**Open board counts** (08-15, session close): guacamayo **5**, sisyphus 1, playground 1. Clean: galactus, learn-ai-engineering, librarian, atlas, ai-project-template, listen-wiseer, lebanese-blonde. guacamayo open: #120 (dashboard metrics, ready), #119 (autonomous triage, backlog), #118 (scheduled refresh, backlog), #117 (review-verdict-gate false positives, bug), #113 (board state in a file, ready).
  => **#113 and #117 are the same complaint from two directions** — the board is a cache and nothing keeps it warm. #117 is smaller and is a *live guard emitting false positives*, which makes it the better pickup.

**guacamayo ops** — R10 landed 2026-08-15; cascade acked (`retro_due` 3 / `retro_acked` 3). Insights last ran 2026-08-14 (the 08-15 refresh spawn died on quota exhaustion and appended nothing — verified non-destructive). **Growth synthesis ran at session close**: 17 entries processed, 12 merged into `sounding.md`, 19 disposition rows logged, accumulator cleared to 0. Standing retro items unchanged: `tail`/exit-code-masking rule missing from `~/.claude/rules/shell.md`; bash antipatterns 29.18/session vs target 12; `git update-ref -d` bypasses `risky_git_guard.sh`'s `branch -D` block.

**Uncommitted** — `bug/untrack-telemetry` holds this session's entire `.sounding/` diff, staged and awaiting Ramsey's commit. `.sounding/reflections/2026-08-15_18-18.md` is untracked and needs `git add`.

---

## How mobile /wake uses this

1. Run the normal Phase 4 plan glob. If it returns results (Mac), use them — they're authoritative.
2. If it returns nothing (sandbox), read this file for cross-repo orientation instead.
3. Bodies of the plans referenced here won't be in the sandbox (git-ignored). To act on one,
   either work from the pointer + the repo's committed code, or continue on the Mac.
