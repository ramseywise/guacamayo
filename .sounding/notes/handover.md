# Handover — 2026-08-07 Branch cleanup + issue closure sweep

**Context**: Housekeeping session — swept branch debt across all main repos, closed orphaned issues, surfaced squash-merge detection pattern.

## Current State

**Completed:**
- 14 merged local branches deleted (librarian 10, AIT 2, LAE 2)
- 5 stale remote-tracking refs pruned (guacamayo 2, librarian 2, LAE 1)
- Issues closed: GUA-93, GUA-96, LIB-110, LIB-114 (all had merged PRs)
- LAE: new branch `bug/librarian-sync-cleanup` created from old `LAE-115-code-test-formats` HEAD

**Waiting on Ramsey (push-guarded):**
- Remote branch deletions across guacamayo, AIT, job-system, lebanese-blonde, playground (commands in chat)
- Local `-D` for 3 squash-merged guacamayo branches (GUA-93, GUA-96, bug/insights-log-path)
- Playground cord/* bulk delete (~50 Devin branches)
- `JOB-31-fix-stale-paths` local delete (contained in JOB-32)

**Still open:**
- GUA-92 (current branch, no PR yet)
- JOB-32 (superset of JOB-31, needs PR — close both #31 and #32)
- AIT-56-drop-temperature-param (local only, no PR, relevance unclear)
- Dotclaude CLA-8/CLA-15 merge still pending from prior session

## Decisions Made

- Squash-merge detection: `merge-base --is-ancestor` + `gh pr list --state all` (not `--merged`)
- JOB-31 redundant — JOB-32 is superset, one PR covers both
- Branch hygiene friction flagged for retro — no post-merge cleanup ritual exists

## Open Threads

- Post-merge cleanup ritual: candidate for retro proposal (`make branch-clean`, post-merge Action, or /wake sweep)
- Issue scoping tighter before branching (JOB-31/32 lesson)
- 2 new playground dependabot branches arrived during fetch

## Immediate Next Steps

1. Run the staged remote delete + local `-D` commands
2. PR JOB-32, close #31 and #32
3. Decide AIT-56 fate
4. GUA-92 retire-pulse PR when ready

## Key Files

- `.sounding/growth/growth.md:20-21` (2 friction entries)
- `.sounding/reflections/2026-08-07_18-50.md`
