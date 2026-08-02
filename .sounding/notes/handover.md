# Handover — 2026-08-02 Status-enum arc phase 1 + three librarian branches + insights outage

**Context**: Started as an ingest-only `/grow`; became a close-out session on the guacamayo
board. All landing claims below were verified by SHA ancestry against `origin/main`, not by
label, commit message, or plan `Status:` line.

## Shipped this session

**GUA-75 phase 1** — guacamayo plan-doc Status corpus migrated **32/43 → 43/43 conforming**.
11 docs edited under `.claude/docs/plans/`. Two were *corrected*, not mechanically migrated:
`2026-07-31-CLA-69-*.md` went `IN PROGRESS → COMPLETE` with an `Evidence:` line citing
`19e2c39`'s verified ancestry. Phases 2-3 are a **per-repo checklist inside #75** — the
12-point mechanics block lives once in #75's body.

**Board made hierarchical** — `addSubIssue` called for the first time (R7 F2 said the template
existed at `github-projects/SKILL.md:93` and nothing called it; confirmed). #65 now has 4
sub-issues (#73/#74/#75/#79). The durable fix — `workflow-refine` calling it on split — is
still **not** wired.

**Board hygiene correction (Ramsey's, mid-session).** I had taken the board 8 → 16 while
calling it a cleanup: filed #81-#87 (one flat sibling per repo) plus #88, closed zero.
Collapsed #81-#87 back into a checklist in #75 and transferred #88 to **librarian#86**
(cross-repo issues belong in the target repo, not on the guacamayo board). **Back to 8 open.**
Standing correction: decomposition and paperwork look identical at the moment you do them —
the test is whether each piece gets *worked*, not whether each piece is well-formed.

**librarian#86 (ex-#88) FIXED and verified** — see "insights outage" below. Branch
`LIB-86-section-contract-wiring`, **uncommitted**, 2 files. 471 pass / 2 skip, ruff clean,
real end-to-end run produced a 63,916-byte report with all nine section IDs.

**Three librarian branches**, one commit each, base `5a67d71`, worktrees torn down:

| Issue | Branch / commit | Result |
|---|---|---|
| #41 | `LIB-41-error-taxonomy` `acd9a65` | `other` bucket 42.0% → **3.1%**; 480 tests pass |
| #50 | `LIB-50-findings-table` `5019e52` | findings SQLite projection, 3/3 gates, `parse_findings()` byte-identical |
| #64 | `LIB-64-eval-tab` `1579df8` | `SKILL-EVALS` region; **363 pass / 0 fail / 3 skip** verified end-to-end |

#64's guacamayo half is done here too (nav + `#evals` section + markers in
`context-dashboard.html`, uncommitted). Safe to land before librarian merges — main's
`inject_regions` skips unknown markers with a warning rather than crashing.

## Current State

### What moved since the last handover (2026-08-01 late)

| Item | Then | Now |
|---|---|---|
| guacamayo **#69** (`quick-pr` escapes issue-linking) | `ready`, called "highest-leverage open fix" | **CLOSED + LANDED** — `19e2c39` is an ancestor of `~/.claude` origin/main |
| guacamayo **#78** (lint parity) | not yet filed | **CLOSED + LANDED** — `36be12e` on origin/main |
| librarian #57/#58/#59/#61/#75 | 8 open, deepest queue | **all closed** — librarian down to 3 open |
| guacamayo #63 / #73 | drifted open after merge | **closed** |
| `~/.claude` **`2863fb4`** guard fix | unlanded, two identical branches | **STILL UNLANDED**, still two identical branches |

### The one thing still owed (unchanged, 24h)

`~/.claude` `2863fb4` — the CLA-71 guard fix. Sits on `bug/risky-guard-variable-cd` **and**
`CLA-8-insights-computed-columns`, empty diff between them, neither with an upstream.
`~/.claude` local main is behind 42. Pick one branch, delete the other, ship.

### New drift found this ingest

1. **Cache drift, inverse direction.** Yesterday: issues open while work was on main.
   Today: `#69` and `#78` are **closed** while their plan docs still read
   `Status: IN PROGRESS` and `Status: EXECUTED`. Neither artifact is authoritative — the
   pair disagreeing is the signal. This is exactly what the GUA-65/74/75 status-enum
   workstream exists to fix, which makes it that workstream's own best test case.
2. **Artifact sprawl, third sighting, now cross-issue.** `CLA-78-lint-parity` tip
   `92649ba` is **unlanded**, but a byte-equivalent commit `36be12e` reached origin/main
   from the `CLA-74-status-writers` branch. Same shape as `2863fb4`-on-two-branches: a
   branch named for one issue carries another issue's landed copy. `CLA-74-status-writers`
   is locally ahead 2 of its own remote while both those commits are already on main.
3. guacamayo local `main` is **behind 12**; checkout is on `GUA-73-status-enum-design`
   (PR #80 merged). `GUA-63-session-id-findings` has a `gone` upstream — safe to delete.
4. **`/workflow-insights` was totally down since librarian#61 landed** — **now FIXED**
   (librarian#86, branch `LIB-86-section-contract-wiring`, uncommitted).
   Not flaky, not a timeout: `_SYSTEM_PROMPT` in `librarian/tools/cartographer/parser.py`
   held the entire nine-section-ID contract and was **referenced nowhere**; `call_claude`
   hardcoded a one-line system string; `build_prompt` never mentioned sections. The
   validator enforced IDs the model was never asked for. Attempt 1 got 0/9; the retry
   recovered exactly 2 because it names the missing IDs inline in the *user* message. All 3
   tests passed because they patch `call_claude` with canned HTML that already has the IDs.
   **Two further failures only executing could reveal**: a conforming report is ~17.2k
   tokens, so it truncated at `max_tokens=8192` **and** at `16384` (the old ~6.2k reports
   were the model writing freely — never evidence about a *conforming* report's size); then
   at `32768` the SDK refused non-streaming ("Streaming is required for operations that may
   take longer than 10 minutes"). Fix is: wire `system=_SYSTEM_PROMPT`, `_MAX_REPORT_TOKENS
   = 32768`, `client.messages.stream()` + `get_final_message()`, and a distinct
   `ReportTruncatedError` so truncation never again reads as a contract failure.
   New tests patch `anthropic.Anthropic`, not `call_claude`, and assert the section IDs
   reach the **outgoing payload** — including on the retry. Negative test executed: reverting
   `system=` fails exactly those 2 tests.
5. **Warn-mode hooks are invisible.** `plan_status_validate.sh` surfaces nothing in the tool
   result; the text exists only in `~/.claude/.hook-log.jsonl`. Every phase-1 "verified
   conforming" claim was checked against a hook that could have been disagreeing silently.
   This reframes **#79** from a strictness preference to fixing a no-op.

## Decisions Made

- **Verified landing by SHA ancestry, not by any summary artifact.** `git merge-base
  --is-ancestor` for each of `19e2c39`, `36be12e`, `2863fb4`, `92649ba`. Two landed, two not.
  The "ahead 2" branch status was misleading — those commits were already on main.
- **Did not delete any branch, prune any worktree, or close any issue.** Shared/destructive
  state is Ramsey's call; flagged instead.
- **Did not fix the stale plan `Status:` lines.** They are evidence for the GUA-74/75
  workstream; correcting them by hand would erase the test case before the validation hook
  is proven against it.
- **Spawned `/workflow-insights` in background** with an explicit bare-filename instruction.
  Noted from yesterday: that instruction alone did **not** hold — SKILL.md's literal step
  wins. R7 P4 (the one-line skill fix) is still unapplied and is still the cheapest open fix.

## Open Threads

- **CLA-67's hypothesis now has a real fix in code**, not just an issue. `absence:merged-PRs-without-closing-links`
  should be re-measured at the next retro — this is the first cycle where the mechanism is
  actually closed. If it fails again post-`19e2c39`, the diagnosis was wrong.
- **Nothing escalates a flagged-and-unfixed item.** `2863fb4` was called "the only genuinely
  unlanded work in the portfolio" 24h ago and is unchanged. Flagging is not a mechanism.
- **Duplicate-branch detector is still worth building.** The signature is stable and cheap:
  N branches, one tree, no upstream, or a tip whose content is already on main under a
  different SHA. Three confirmed instances now (AIT #40/#42, `~/.claude` guard, CLA-78).
- **Bash antipatterns — I contributed another one this session** (`grep ... scripts/quick-pr*`,
  zsh nomatch, mid-compound-command). One day after logging it as the metric moving the
  wrong way. Knowing the rule and holding the tool preference are different things.
- **Nothing on the board distinguishes decomposition from paperwork.** Filing #81-#87 passed
  every convention check (parented, literal AC, one per repo) and still added six rows and
  zero work. A candidate guardrail: a close-out session may not end with more open issues
  than it started with, unless the new ones are being worked *this* session.
- **AskUserQuestion needs a location dimension for cross-repo work.** I offered granularity
  (seven vs two) and never placement; the guacamayo-vs-target-repo call was my silent
  default surfacing as her decision. Cross-repo issues go in the **target repo**.
- **Unchanged, still unaddressed**: the 23-skills-across-4-prefixes consolidation question;
  red-main-accepts-merges portfolio-wide.

## Immediate Next Steps

1. **Commit + push librarian `LIB-86-section-contract-wiring`** — the insights fix is
   uncommitted (2 modified files). Closes librarian#86 and unblocks `/workflow-insights`.
2. **Ramsey pushes the three librarian branches** (`acd9a65`, `5019e52`, `1579df8`) — all
   commits are provisional; nothing was pushed. Then commit guacamayo's `#evals` dashboard
   half plus the `.sounding/` changes on `GUA-75-migrate-status-corpus`. #41/#50/#64 close
   on merge.
3. **Commit `#74`'s staged work in `~/.claude`** (branch `CLA-74-status-writers`: hook + 41
   tests + `settings.json` + 3 SKILL.md files). It is the last thing blocking #74.
4. `~/.claude`: pick one of the two identical `2863fb4` branches, delete the other, ship.
   Still the only genuinely unlanded work — flagged 48h now.
5. `~/.claude`: reconcile `CLA-78-lint-parity` (`92649ba`) — its content is on main under
   `36be12e`; delete or rebase, don't leave it as a third sprawl artifact.
6. Fast-forward guacamayo `main` (behind 12); delete `GUA-63-session-id-findings` (upstream gone).
7. Phases 2-3 of the status arc are the **per-repo checklist in #75** — one session per repo,
   mechanics block in #75's body. **Do not** tighten the transitional dual-separator grep
   (`IN[ _-]PROGRESS`) in workflow-execute/workflow-review/code-review until the corpus is
   migrated; that tightening is #79.
8. Next `/dream` **must synthesize** — accumulator is at **23**, threshold is 5.

## Key Files

- `~/workspace/guacamayo/.sounding/growth/growth.md`
- `~/workspace/guacamayo/.sounding/tooling-ledger.md`
- `~/workspace/guacamayo/.claude/docs/plans/2026-08-01-CLA-74-status-writers-validation.md`
- `~/workspace/guacamayo/.claude/docs/plans/2026-08-02-CLA-78-lint-parity.md`
- `~/.claude/hooks/risky_git_guard.sh`
- `~/.claude/scripts/lint-parity.sh`
