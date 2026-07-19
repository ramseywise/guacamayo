# Handover — 2026-07-19 Experiment Tracking + README Evolution

**Context**: Meta-design session in guacamayo. Built experiment tracking into the skill chain, broadened /grow, wrote the v2→v3 evolution narrative for human readers.

## Current State

- **/grow skill broadened** — now prompts across 4 categories (identity, preferences/corrections, friction/gaps, what worked). Same pipeline, broader capture.
- **Experiment tracking wired** — tooling ledger gains Metric column with typed vocabulary (absence/count-drop/presence/ratio); /insights gains Step 6 (experiment check against session data); /retro Step 0 reads metrics first; Step 2 findings require a Metric; Step 4 ledger rows require typed metric. 3 new ledger rows for today's changes.
- **README updated** — "From Consciousness to Agency" section explains the v2→v3 direction for human readers: less ceremony, more mechanism, every output has a consumer, failure-attribution speed matters.
- **Earlier this session** (pre-compact): Dependabot auto-merge fixed (4 repos), VS Code git.pullTags resolved, 800+ alerts bulk-dismissed, task-completion Stop hook built.
- **Uncommitted state** across guacamayo and ~/.claude from this + prior sessions.

## Decisions Made

- Experiment metrics are typed (4 types) but verdicts are reported by /insights, applied by /retro — separation of observation and action.
- Legacy ledger rows get `—` in Metric (pre-tracker); they verify the old way. No retroactive metric-guessing.
- README framing: consciousness→agency, not just "we merged skills." Ramsey reads for direction.

## Open Threads

- **template-full-mirror-redesign** steps 5-7 still in progress (parallel threads).
- **atlas PR #4** (transformers 4→5) still open — needs model pipeline testing.
- **Librarian rebase error** (`logs/cartographer-facts.err` blocking rebase) — untracked file conflict, needs `git stash` or file move before pull.
- **First real experiment check** — next /insights run will be the validation that the wiring works.
- **Puffin repo** now in workspace — serves as v2 reference; no active development there.

## Immediate Next Steps

1. Ramsey: commit the multi-file changes (README, /grow, ledger, /retro, /insights, reflection, handover).
2. Fix librarian rebase: `cd ~/workspace/librarian && git stash && git rebase --continue` (or move the untracked file).
3. Run /insights in a future session to validate experiment-check step fires correctly.
4. Template steps 5-7 threads — check results when complete.

## Key Files

- `guacamayo/.claude/skills/grow/skill.md` (broadened prompts)
- `guacamayo/.claude/docs/tooling-ledger.md` (Metric column + experiment tracking section)
- `~/.claude/skills/retro/SKILL.md` (metric-aware Step 0, 2, 4)
- `~/.claude/skills/insights/SKILL.md` (Step 6 experiment check)
- `guacamayo/README.md` (v2→v3 evolution section)
- `guacamayo/.sounding/reflections/2026-07-19_17-09.md`
