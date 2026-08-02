# Handover — 2026-08-01 (late) Ingest-only /grow — landing verification sweep

**Context**: No work was performed this session. `/grow` was the first and only invocation,
so this handover carries **cross-session ingest findings**, not task progress. Everything
below was verified against git and `gh`, not read off labels.

## Current State

**The previous handover's four "awaiting Ramsey" items — resolved, except one**

| Item | Verdict |
|---|---|
| guacamayo GUA-63 | **LANDED.** PR #76 merged; tip is an ancestor of origin/main |
| guacamayo GUA-73 | **LANDED.** PR #77 merged; tip is an ancestor of origin/main |
| AIT #40/#41/#42/#43/#44 | **ALL CLOSED** 2026-08-01 21:17 |
| `~/.claude` guard fix `2863fb4` | **STILL UNLANDED** — not an ancestor of origin/main |

**The one thing actually owed**: `~/.claude` CLA-71 guard fix. It sits on **two branches
with an identical tree** — `bug/risky-guard-variable-cd` and `CLA-8-insights-computed-columns`,
both at `2863fb4`, `git diff` between them empty, neither with an upstream. The checkout is
on the CLA-8 one. `~/.claude` main is behind 40. Pick one branch, delete the other, ship.

**New this ingest**
- guacamayo local `main` is behind 4; both feature branches are safe to delete (fully landed).
- AIT opened #49 (60-min LLM starter kit, plan doc written), #50 (security/guards called by
  nothing), #51 (extend unimported-module guard to Python render).
- learn-ai-engineering has an **empty live worktree** at `/private/tmp/.../wt-lae-115` holding
  `LAE-115-case-study-code-test` under a `+` lock, zero commits ahead of origin/main.
- librarian is the deepest queue: 8 open, four `ready` with 07-31 plan docs.

## Decisions Made

- **Verified by ancestry and content, never by label.** `gh issue list` said #63 `ready` and
  #73 `in-review`; `git merge-base --is-ancestor` said both were already on main. The board
  was wrong in the safe direction, but it was wrong.
- **Did not close #63/#73.** Both are genuinely complete, but closing issues is a
  shared-state action and Ramsey owns the DoD call. Flagged instead.
- **Did not prune the LAE-115 worktree or delete any duplicate branch.** A live worktree may
  hold an active session; unfamiliar state gets investigated, not deleted.
- **Told the background insights agent to pass a bare `insights-report.html`** — and it did not.
  It wrote `insights-report-2026-08-01-2026-08-01.html` anyway and reported success without
  flagging the conflict. SKILL.md's literal step beat the dispatch instruction. Conclusion:
  hand a subagent a workaround and you get the defect; fix the skill text instead.
- **Confirmed R7 P4's diagnosis by reading the source**, not by trusting the agent:
  `librarian/tools/cartographer/parser.py:1253` appends `date.today()` to the stem
  unconditionally, so any dated `--output` double-dates. The one-line fix is sound, unapplied.

## Open Threads

- **CLA-67's hypothesis failed twice in one day.** `absence:merged-PRs-without-closing-links`
  — PRs #76 and #77 both merged with empty bodies and zero `closingIssuesReferences`. The
  cause is already filed as **guacamayo#69** (`quick-pr` exits 0 on an existing PR, so any
  PR created outside `make ship` escapes issue-linking) and is sitting at `ready`. Until #69
  lands, every externally-opened PR re-opens the hole. This is the highest-leverage open fix
  on the board — it is the mechanism behind the label drift, not a separate problem.
- **R7 F3 confirmed in permanent history.** Merged PR titles are de-hyphenated branch slugs:
  "Gua 63 session id findings", "Gua 73 status enum design". The slug is what the repo shows
  forever, not just in the PR list.
- **Artifact sprawl has a stable signature**: N branches, one tree, no upstream. Seen at AIT
  #40/#42 (three branches each) and now in `~/.claude`. Worth a detector — `git diff` between
  same-tip branches is cheap and unambiguous.
- **Unchanged from last session, still unaddressed**: the 23-skills-across-4-prefixes
  consolidation question (candidate shape: design / code / review as the three agent-facing
  verbs, with research/plan/refine demoted to phases); red-main-accepts-merges portfolio-wide;
  Bash antipatterns at 28.55/session, the one metric moving the wrong way.

## Immediate Next Steps

1. Ramsey: close guacamayo **#63** and **#73** — work is on main, issues drifted open.
2. Ramsey: in `~/.claude`, pick one of the two identical guard-fix branches, delete the other,
   push + ship `2863fb4`. It is the only genuinely unlanded work in the portfolio.
3. Prioritize **guacamayo#69** — it is the root cause of items 1 and of the CLA-67 metric miss.
4. Decide on the LAE-115 worktree (empty, holding a branch lock) — prune or claim.
5. Apply R7 P4 (one line): `/workflow-insights` SKILL.md step 3 passes bare
   `insights-report.html`, drop the redundant `ln -sf` at step 34. Verified correct against
   `parser.py:1253`. Cheapest open fix on the list.
6. Next /dream will synthesize: accumulator is at 9, well over the threshold of 5.

## Key Files

- `~/workspace/guacamayo/.sounding/queue.md`
- `~/workspace/guacamayo/.sounding/growth/growth.md`
- `~/workspace/guacamayo/.sounding/tooling-ledger.md`
- `~/workspace/ai-project-template/.claude/docs/plans/2026-08-01-49-llm-starter-kit.md`
- `~/.claude/hooks/risky_git_guard.sh`
