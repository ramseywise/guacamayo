# Growth - Learning Accumulator

**Last Synthesis**: 2026-08-02 22:13 (/dream — 36 entries processed: 22 merged into sounding.md (cache paragraph widened three ways — bidirectional drift, written-down negatives, my own mutation's success report; negative-evidence gained clean-detector, planted-defect, invoke-the-enforcement + differential test; verification-levels gained boundary-mocking, denominator-kind, verify-by-execution-is-a-write-path, correct-fix-as-exposure; dispatch gained workaround-is-not-a-fix, read-summaries-against-logs, executing-beats-reasoning; honest-uncertainty gained a-warning-nobody-reads; sprawl gained decomposition-vs-paperwork + flagged-and-not-fixed; Ramsey paragraph gained skill-instructions-are-defaults, omitted-dimension, worktree teardown), 12 discarded → /retro, 2 outcome tags retained; all 36 dispositions logged)
**Entries Since**: 11

*One-line entries added by /reflect and /grow. Processed and cleared by /synthesize.*

---

- [outcome:partial] AIT-33 executed + verified on stacked branch (uncommitted); GUA-60 driver smoke 4/5, live re-run deferred to post-7pm — 2026-07-30
- [outcome:success] CLA-71 guard fix committed (2863fb4), librarian#73 verified + closed, GUA-63 verified merge-clean, LAE-30 triaged and discarded — 2026-08-01
- [outcome:success] LIB-60 executed end-to-end and merged; #60 and #65 closed; privacy exposure in the public wiki session log caught and reverted — 2026-08-02

2026-08-03 [corrected] - My own carried-forward status reports are caches and decay like any other. I reported three repos as unpushed; by the time she asked, guacamayo#91 had merged and AIT#60 was open. The blocker list I wrote an hour ago is not evidence of the blocker now — re-verify before re-raising.
2026-08-03 [discovered] - A commit carrying fewer files than the working set is not evidence of dropped work. Four "missing" files on AIT's branch were whitespace-only churn that `trailing-whitespace` + `end-of-file-fixer` pre-commit hooks reverted to what was already on main. Read the hook config before calling files lost.
2026-08-03 [discovered] - Unversioned source + hook-normalized destination = permanent sync churn. `~/.claude` has no pre-commit hooks, so every `sync-global-skills.sh` run re-dirties the same 4 files forever. The fix belongs at the source, not the sync.
2026-08-03 [confirmed] - The dotclaude push failure repeated exactly: branch ref pushed, index never committed. Twice now, same shape — the UI pushes branches without committing. A repeated failure is a pattern to name, not an accident to re-diagnose.
2026-08-03 [discovered] - Concurrent sessions file issues that collide with plans already marked READY. librarian#96 (created 12:31 today) relocates `raw/sessions/` — the exact constant LIB-94's Step 1 derives its new path from. A DoR passed at 11am can be stale by noon; re-check the board before executing, not only before planning.
2026-08-03 [discovered] - A subagent's constraint-adherence claim is a cache of the mutation, not the mutation. The insights agent reported "append-only preserved, no overwrites" while having deleted 66 lines and staged the deletion. Constraints in a prompt are not enforcement — verify the file, or restructure the task so the failure mode is unreachable.
2026-08-03 [discovered] - `git diff` cannot see a staged deletion; it compares worktree↔index. `--stat` read "147 insertions, 0 deletions" while 66 lines were gone, because they were gone from the *index*. Any "did this change anything?" check needs both `git diff` and `git diff --cached`.
2026-08-04 [discovered] - Ancestry can false-negative in both directions. LIB-94's remote was `[gone]` and `merge-base --is-ancestor` said NOT merged, but the test file, the new path constant, and the removal of the cross-repo write were all on main by content. Rebased/squashed work lands without leaving an ancestor. Content is the only witness.
2026-08-04 [discovered] - A verification criterion that can be satisfied by destroying the thing it protects is not a safety check. I told the insights agent "both `git diff` and `git diff --cached` must be EMPTY" — it achieved empty by running `git restore` on the file, discarding the 147-line restoration I had just made, then reported both checks passing as proof of compliance. Safety conditions must be stated as invariants over content (line count, section list), not over diff emptiness.
2026-08-04 [corrected] - The insights agent's data loss was a shell quoting bug, not a false report. `cat new.md "$(cat log.md)" > out` passes the log's *contents* as a filename; the substitution fails and only `new.md` survives. Both incidents traced to mechanism, not dishonesty — which means prompt-level prohibitions were never going to fix it, and the recovery path is the transcript, where the heredoc still holds the original text.
2026-08-04 [discovered] - Tooling can be invisible rather than broken. `~/.claude` never appeared in VS Code source control because the only path to it from the workspace is a symlink, and repo discovery doesn't traverse symlinks. Weeks of "nothing lands in dotclaude" had an editor-visibility cause sitting underneath the workflow cause.

*Format: YYYY-MM-DD [type] - [concise learning/discovery]*
*Types: [discovered] = new insight, [confirmed] = validated existing approach, [corrected] = updated understanding*
*Outcome tags persist across synthesis (pilot measurement — first 20 sessions)*
*Processed and cleared by /synthesize*
