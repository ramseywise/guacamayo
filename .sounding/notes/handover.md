# Handover — 2026-08-14 GUA-109 occurrence dates, plan-status vocabulary, review of the branch

**Context**: guacamayo meta session on branch `GUA-109-occurrence-date`. Three arcs: (a) the
`occurred` vs `date` split for review findings (GUA-109 + GUA-111), (b) a plan-doc `Status:`/`Review:`
vocabulary decision plus a hook and a bulk backfill, (c) a full `/workflow-review` of the branch,
including a "git leaks" investigation Ramsey raised.

## Current State

### GUA-109 — executed, reviewed, pushed, NOT merged
Branch `GUA-109-occurrence-date`, 3 commits ahead of `origin/main` (`1c8aa7f`, `e608edf`, `9c4094b`),
0 behind. `origin/main` HEAD `88f5d7d`. **No PR exists.**

`telemetry/occurrence.py` (154 lines) resolves *when the friction landed* rather than when the sweep
ran. `date` stays immutable (it feeds `finding_uid`); `occurred` is a **last-touch** date, resolved by
blaming the cited line range — precedence blame-range → blame-file → repo HEAD → unresolved, with
`occurred_source` recording which. A per-run cache keyed `(repo, file, lines)` keeps a 40-finding sweep
from spawning 40 subprocesses.

`/workflow-review` verdict: **`comment`** → plan doc set `Status: EXECUTED` / `Review: passed`, `## Review`
section appended. 0 blockers introduced by the branch. 11 "important" findings — **all pre-existing**,
none branch-introduced. `ruff` clean, 772 tests passing.

### Plan-status vocabulary — decided and applied
- Hook lives **global** (Ramsey's call, over my guacamayo-local recommendation).
- Vocabulary: `pending` / `passed` / `failed` / `blocked`. `pending` means *no review concluded* — a
  verdict never writes it.
- Backfill was **bulk with per-doc evidence**, scoped to **guacamayo's 9 docs only**. The 27
  non-guacamayo docs are deliberately left to be "caught on write."

### The leak question — answered, and it is not the one that was asked
Two unrelated scans. The **credential** pass came back clean. The **confidentiality** pass did not:
a PUBLIC repo carries 410 lines naming dssg client projects on `main`, in files that are gitignored
*but tracked* (`git ls-files -ci --exclude-standard`). **Undecided — needs Ramsey.** dssg repos are
hands-off, but this exposure is in a repo that is not dssg.

### Working tree
Unstaged: `.sounding/telemetry/.hook-log.jsonl`, `.sounding/telemetry/.hook-pass-log.jsonl`,
`.sounding/telemetry/cascade-state.json`, `.sounding/growth/growth.md`, `.sounding/context-dashboard.html`,
`.sounding/notes/handover.md`. The three `.sounding/telemetry/` files are churn — consider dropping them
from the branch rather than shipping them.

## Decisions Made
- **Hook is global, not repo-local.** Ramsey overrode my recommendation; the rule applies in every repo.
- **Backfill rather than a `Review: blocked` sweep.** Also mine overridden — real evidence per doc beats
  a uniform "unknown" marker.
- **`occurred` is last-touch, not introduction.** Finding the introducing commit needs a `git log -S`
  pickaxe per finding: more expensive and still ambiguous for multi-line findings. For trend *shape*
  last-touch is enough, and `occurred_source` keeps the imprecision visible instead of assumed away.
- **The 11 important findings were not treated as branch defects.** Whole-file scanners produce a
  file-level census; the diff-attribution join (`git diff -U0` hunks + `git blame -L`) is what makes a
  finding a *branch* finding.
- **#109/#111 were NOT closed.** Instruction said "published, close issues"; evidence says pushed but no
  PR and not merged. Reported the evidence and stopped, per the standing rule.

## Open Threads
- **The attribution join belongs in the driver, not in my head.** Every sweep currently re-derives
  "did this branch touch the cited line?" by hand. `review/driver.py` should carry it once.
- **The dssg client-name exposure is live and undecided.** Secrets rotate; client names do not.
- **GUA-103's 5 commits are stranded** (`5d33fa0`, `15fa839`, `9ee0cd1`, `37d24ac`, `d772c4c`) — no PR.
  Same rot pattern as AIT: execute-complete is not a resting state.
- **R2 (un-ignore `.claude/docs/`) is approved but unsequenced.**
- 2 stale tracking branches both `: gone]` (nit). `spike/prototype-genesis-ml` still undecided.

## Immediate Next Steps
1. Open the PR for `GUA-109-occurrence-date` — then close #109 and #111 on merge. Both still carry stale
   labels (`refinement`, `backlog`).
2. Decide the dssg client-name exposure in the public repo.
3. Drop the 3 `.sounding/telemetry/` churn files from the branch before the PR.
4. PR or close GUA-103's 5 stranded commits.
5. **Retro is due** — `retro_due: 1`, unacked, last was R9 on 2026-08-11.

## Key Files
- `~/workspace/guacamayo/telemetry/occurrence.py`
- `~/workspace/guacamayo/.claude/docs/plans/2026-08-14-gua-109-occurrence-date.md`
- `~/workspace/guacamayo/review/driver.py` (attribution join belongs here)
- `~/workspace/guacamayo/.claude/refs/review-dod.md` (workflow-review Stage 5 cites a stale global path)
- `~/workspace/guacamayo/.sounding/telemetry/cascade-state.json`
