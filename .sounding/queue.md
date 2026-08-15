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

*Refreshed 2026-08-15 (/grow). AIT `bug/ml-shape-rag-promotion` and the galactus main-rename entry are resolved — dropped.*

**galactus — `main` was unbuildable, now FIXED (2026-08-15).** A duplicate `ml` key in `pyproject.toml` and a truncated `uv.lock` made `uv run` fail repo-wide from PR #25 until the repair merged. `origin/main` is now `f7d407f`; both files parse. Fix branch merged and deleted. Local branches: `main` + `GAL-23-proto-pipeline-dry-run`.
  => Standing follow-up: a **parse check on `pyproject.toml`/`uv.lock` as its own pre-merge step**. No pytest case can cover this — the failure is upstream of the test runner.

**guacamayo — PR #124: a push gap that became a one-file conflict.** CONFLICTING was never a merge problem — remote `GUA-103-wake-consistency-check` was 5 ahead / 21 behind because local `6207e0e` was never pushed; the push is still a **fast-forward, no force**. Then PR #126 merged (15:55Z), `main` moved `4e1ad47` → `b5e10aa`, and `git merge-tree` now reports exactly **one** conflict: `.claude/skills/meta-retro/SKILL.md`. Sides are disjoint and both wanted — GUA-103 renames `workflow-retro` → `meta-retro`; main (#126) adds Check B item (5) doc↔config drift and fixes the insights path. Resolution pre-built at `/tmp/meta-retro-resolved.md` (verified: 0 markers, both sides, 0 residual `workflow-*` names).
  => Next: commit the `.sounding/` churn (it blocks the checkout), then `git merge origin/main` on GUA-103, drop in the resolved file, commit, push.

**guacamayo — #125 CLOSED (2026-08-15).** PR #126 merged its work without a `Closes #125`. Verified by content before closing: all 6 files byte-identical on `origin/main` by blob SHA. Branch `GUA-125-port-workflow-skill-updates` is now stale.

**Branch residue.** Deleted this session: galactus `GAL-20-*`, `GAL-4-*`, `spike/prototype-genesis-ml`, `bug/galactus-pyproject-duplicate-ml-key`; guacamayo `GUA-115-finding-attribution`; `~/.claude` `CLA-14-*`. Held deliberately: galactus `GAL-23-proto-pipeline-dry-run` — merged to main, but `2026-08-15-gal-23-hitl-gradient.md` (`Status: REFINED`, `Epistemic: UNTESTED`) names it as the branch for work that was **re-scoped today**. A branch merged to main is evidence about code, not about whether the issue's question was answered.

**guacamayo — tracked telemetry files block branch hygiene.** Hooks write `.sounding/telemetry/*.jsonl` and `cascade-state.json` every session and they are tracked, so `git checkout main` aborts and ordinary cleanup needs a stash. `git fetch origin main:main` is the workaround for fast-forwarding a ref without a checkout.

**Open board counts** (08-15, after closing #125): guacamayo 5, galactus 4, sisyphus 1, playground 1. Clean: learn-ai-engineering, librarian, atlas, ai-project-template, listen-wiseer, lebanese-blonde. Consistency checker: 1 finding (galactus#23 merged-branch-open-issue); 104 of 168 plans join to no issue. Close candidates pending confirmation: galactus #23, galactus #20 (PR #26 merged 08-15, no `Closes` reference). guacamayo #117 stays open until `~/.claude` `CLA-19-retro-recurrence` (5 ahead, unpushed) lands.

**guacamayo ops** — R10 landed 2026-08-15; cascade acked (`retro_due` 3 / `retro_acked` 3). Insights last ran 2026-08-14 — the 08-15 refresh spawn **died on quota exhaustion**, appended nothing (verified: 0 deletions, nothing staged). Growth accumulator at **31 entries** since the 08-11 synthesis; its `Entries Since: 15` header is stale. Standing retro items unchanged: `tail`/exit-code-masking rule missing from `~/.claude/rules/shell.md`; bash antipatterns 29.18/session vs target 12; `git update-ref -d` bypasses `risky_git_guard.sh`'s `branch -D` block.

---

## How mobile /wake uses this

1. Run the normal Phase 4 plan glob. If it returns results (Mac), use them — they're authoritative.
2. If it returns nothing (sandbox), read this file for cross-repo orientation instead.
3. Bodies of the plans referenced here won't be in the sandbox (git-ignored). To act on one,
   either work from the pointer + the repo's committed code, or continue on the Mac.
