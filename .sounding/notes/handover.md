# Handover — 2026-08-15 Landing the ML spike, GUA-103 leftovers, branch + board cleanup

**Context**: guacamayo meta session, dispatcher mode. Instruction was "land the spike and whatever
was left from 103 — solve open issues, do not create new ones," then "/grow, clean up branches and
open issues." Most of the session was verification rather than construction: two config files on
another repo's `main` turned out to be unparseable, and a PR that read CONFLICTING turned out never
to have been pushed.

## Current State

### galactus `origin/main` — was unbuildable, now FIXED
For part of 2026-08-15, `main` carried a `pyproject.toml` with a **duplicate `ml` key** (parse error
line 46) and a **truncated `uv.lock`** (invalid value line 499). `uv run` failed repo-wide. No test
detected it: the failure is *upstream of the test runner* — the toolchain cannot start, so no pytest
case can run to fail.

**Resolved.** `origin/main` is now `f7d407f`; both files parse (`pyproject.toml` 3853 bytes,
`uv.lock` 455910 bytes). The fix branch is merged and deleted; galactus local branches are `main` +
`GAL-23-proto-pipeline-dry-run`.

**I reported this as still-broken twice after it was fixed**, because I read `origin/main` from a
local ref fetched hours earlier. `git fetch` makes remote refs a *timestamped cache*, and I treated
it as live state. The thing that caught it was an error from a mutation — `gh pr create` refusing
with "No commits between main and bug/…". For any claim about *remote* state, query the API
(`gh api repos/O/R/git/ref/heads/main`) or fetch immediately before asserting.

### guacamayo PR #124 — a push gap that became a real (tiny) conflict
Diagnosed against the GitHub API, not local refs. The CONFLICTING status was **never** about a
merge: remote `GUA-103-wake-consistency-check` was 5 ahead / 21 behind because local `6207e0e`
(8 ahead) had never been pushed. `origin/GUA-103-…` is still an ancestor of local, so **the push
is a fast-forward — plain `git push`, no force**.

Then PR #126 merged at 15:55Z and `main` moved `4e1ad47` → `b5e10aa`. GUA-103 is now 8 ahead /
**2 behind**, and that merge introduced a genuine conflict — verified with
`git merge-tree --write-tree origin/main GUA-103-…`, which reports exactly **one** file:
`.claude/skills/meta-retro/SKILL.md` (main still has it at `workflow-retro/`; GUA-103 renames the
directory, hence rename-detected).

**The two sides are disjoint and both wanted** — this is a mechanical resolution, not a judgement:
- *GUA-103 side*: `workflow-retro` → `meta-retro` naming migration (frontmatter `name:`,
  `/meta-insights`, `meta-wake/meta-grow/meta-dream`, `F<N>` source line).
- *main side (#126)*: adds Check B item **(5) doc↔config drift**, and fixes the insights path
  `.sounding/insights-log.md` → `.sounding/insights/insights-log.md`.

Resolution = GUA-103's file **plus** main's two hunks. Pre-built and verified at
**`/tmp/meta-retro-resolved.md`** (299 lines; 0 conflict markers, both sides present, 0 residual
`workflow-retro`/`workflow-insights` strings). If that temp file is gone, re-derive it — it is
two Edits on the GUA-103 blob.

**PR #126 merged; guacamayo #125 CLOSED.** It carried no `Closes #125`, so it stayed open on a
technicality. Verified by content before closing: all 6 files from the PR head are byte-identical
on `origin/main` by blob SHA. Its branch `GUA-125-port-workflow-skill-updates` is now stale
(currently checked out).

### Branches — 3 deleted, 3 need `-D`
Deleted with safe `-d` (genuinely merged): galactus `GAL-20-*`, galactus `GAL-4-*`, `~/.claude`
`CLA-14-*`. Two local `main` refs fast-forwarded via `git fetch origin main:main` (works around a
dirty checkout without stashing).

Still present, each needing `-D` (risky-listed, so left for Ramsey):
- galactus `GAL-23-proto-pipeline-dry-run` — **0 ahead of origin/main**, verified by
  `git merge-base --is-ancestor`. `-d` refuses it only because it compares against the branch's own
  stale upstream ref, not against main.
- galactus `spike/prototype-genesis-ml` — 1 ahead (merge commit `79375ea`); PR #25 already merged.
- guacamayo `GUA-115-finding-attribution` — merged, upstream gone; blocked because
  `git checkout main` aborts on dirty tracked telemetry files.

### Board — 12 open issues across 4 repos
guacamayo 6, galactus 4, sisyphus 1, playground 1. Consistency checker: **1 finding**
(galactus#23 merged-branch-open-issue), 104 of 168 plans join to no issue.

- **galactus #20 — CLOSED.** PR #26 merged 14:20Z without a `Closes #20` reference, which is the
  only reason it was still open.
- **galactus #23 — deliberately NOT closed.** The merged-branch signal was misleading: the branch
  `GAL-23-proto-pipeline-dry-run` carried a framing that has since been **superseded**.
  `.claude/docs/plans/2026-08-15-gal-23-hitl-gradient.md` is `Status: REFINED`, `Epistemic:
  UNTESTED`, and supersedes `2026-08-15-gal-23-proto-pipeline-dry-run.md`. The issue is live work
  re-scoped today, not finished work. Its branch was kept for the same reason.
  *A branch merged to main is evidence about code, not about whether the issue's question was
  answered — the consistency checker cannot see a re-scope.*

Stay open:
- **guacamayo #117** — fix is committed at `9a094b1` on `~/.claude` branch `CLA-19-retro-recurrence`
  (5 ahead, **unpushed**). Open until that lands.
- **guacamayo #125** — branch exists, 1 ahead, unmerged.

### Cascade + insights
`retro_due: 3` acked to `retro_acked: 3` after verifying `## R10 — 2026-08-15` exists in
`tooling-ledger-log.md`. The `/workflow-insights` background spawn **died on quota exhaustion**
(resets 17:20 Europe/Berlin) after 21 tool calls — it appended nothing. Verified non-destructive:
0 deletions, nothing staged, 2032 lines. insights-log.md stays at 2026-08-14.

## Decisions Made
- **Ran the consistency checker instead of re-deriving the board by hand** — a conformance claim must
  be produced by invoking the enforcement, per the /wake rule.
- **Did not force branch deletions.** Every remaining one needs `-D`; verified merge status
  independently and left the deletion to Ramsey rather than reaching for the destructive flag.
- **Did not stash the telemetry files** to unblock the guacamayo checkout — they are real hook data.
- **Did not re-spawn insights** after the quota kill. A retry under an exhausted budget is the
  same failure again.
- **Corrected a stale pending-task entry**: I had recorded the #117 hook work as needing a commit.
  It was already committed at `9a094b1`; only two intentional ref deletions remain unstaged
  (`refs/adk-vercel.md`, `refs/google-adk.md` — moved to galactus 2026-08-12).

## Open Threads
- **A parse check on config files belongs as its own pre-merge step**, not a pytest case. galactus
  proved a repo whose CI runs through its own package manager has zero coverage of the file that
  manager parses first.
- **`Closes #N` has to be in the PR body at merge time or the join is unrecoverable.** galactus #20
  escaped even the merged-branch detector because its remote branch was auto-deleted — the evidence
  the checker joins on was erased by the merge itself.
- **Tracked telemetry files block routine branch hygiene.** Hooks write
  `.sounding/telemetry/*.jsonl` + `cascade-state.json` every session and they are tracked, so every
  session ends owing a telemetry commit. Either they move out of the index, or that cost is permanent.
- **Growth synthesis is overdue** — 31 entries since the 2026-08-11 synthesis; the header still
  reads `**Entries Since**: 15` and is stale. /dream should synthesize.
- The dssg client-name exposure in a public repo (from 2026-08-14) is still **undecided**.

## Immediate Next Steps
1. **Commit the guacamayo `.sounding/` churn first** — it is what blocks `git checkout
   GUA-103-wake-consistency-check` (dirty `queue.md` + telemetry differ across branches).
   Everything below is gated on it.
2. **Resolve + push PR #124**, in this order:
   ```
   git checkout GUA-103-wake-consistency-check
   git merge origin/main                      # conflicts in exactly 1 file
   cp /tmp/meta-retro-resolved.md .claude/skills/meta-retro/SKILL.md
   git add .claude/skills/meta-retro/SKILL.md && git commit
   git push                                   # fast-forward on its own ref, no --force
   ```
3. Delete `GUA-125-port-workflow-skill-updates` (PR #126 merged, #125 closed) — needs a checkout
   off it first.
4. Run `/dream` — synthesis is overdue at 33 entries.
5. Decide the standing follow-up: a **parse check on `pyproject.toml`/`uv.lock` as its own
   pre-merge step**. galactus proved no pytest case can cover it.

## Key Files
- `~/workspace/galactus/pyproject.toml`, `~/workspace/galactus/uv.lock` (staged fix)
- `~/workspace/guacamayo/.sounding/telemetry/cascade-state.json`
- `~/workspace/guacamayo/.sounding/telemetry/consistency.json`
- `~/workspace/guacamayo/.sounding/growth/growth.md`
- `~/workspace/guacamayo/.sounding/tooling-ledger-log.md` (`## R10 — 2026-08-15`)
