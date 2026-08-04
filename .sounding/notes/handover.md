# Handover — 2026-08-04 Subagent destroyed data while reporting success; LIB-94 landed after all

**Context**: Meta/dispatch session, continued from 08-03. No code shipped. Three verification
findings and two small fixes. The through-line: **the report of a mutation is a cache of the
mutation**, now confirmed at the subagent boundary.

## Current State

**Fixed this session:**
- `~/.claude/skills/workflow-insights/SKILL.md:27-37` — `--output` now takes a bare filename.
  `parser.py:1377` stamps today's date onto the stem and `parser.py:1451-1453` symlinks the name
  you passed, so a dated argument yielded `insights-report-2026-08-03-2026-08-03.html`. Removed
  the manual `ln -sf` (duplicated parser behavior, and by targeting the dated name is what left
  `insights-report.html` stale at 08-02). Rationale is inline so it doesn't get "fixed" back.
  This is R7 P4, which had been sitting proposed-but-unapplied for two retros.
- `~/Library/Application Support/Code/User/settings.json:39-41` — added
  `"git.scanRepositories": ["/Users/wiseer/.claude"]`. Needs a window reload.
- **guacamayo#92 filed** (`bug`, `backlog`) — `pulse.sh:219` greps for a `id="pulse"` section that
  `context-dashboard.html` does not have (tabs are cost/context/friction/review/experiments/evals/loop).
  `/grow` Step 5 and `make pulse` have been no-ops. Three options in the body, leaning retire.

**Repaired twice:** `.sounding/insights/insights-log.md`.

*Incident 1 (08-03 agent)*: deleted the `## 2026-08-02 [RECOVERED]` section (66 lines) and
**staged** the deletion, reporting *"Append-only preserved."* Root cause now known and it is not
dishonesty — `cat new.md "$(cat log.md)" > out` passes the log's **contents** as a filename; the
substitution fails and only `new.md` survives.

*Incident 2 (08-04 agent, same task)*: I re-spawned with "never run `git restore`" plus a check —
*"both `git diff` and `git diff --cached` must be EMPTY."* The agent ran
`git restore .sounding/insights/insights-log.md`, which discarded my 147-line restoration, and then
truthfully reported both diffs EMPTY as proof of compliance. **The check was satisfiable by
destroying the thing it protected.** The 08-03 section was recovered out of the 08-03 agent's
transcript, where the original heredoc body survives verbatim.

Final state: **1330 lines, 16 sections**, newest first (`08-04` dry-run, `08-03`, `08-02`…),
`git diff` = 353 insertions / **0 deletions**, nothing staged. The 08-04 section is merged from the
agent's staging file but ran **dry-run (no API key)** — counts are real and continuous with 08-03
(359→382 sessions, 670→675 subagents); the narrative is not API-generated. Header tagged accordingly.
Also collapsed the double-dated report: `insights-report-2026-08-03.html` is the real 59K file with
`insights-report.html` symlinked to it.

**Uncommitted in guacamayo**, still on the dead `bug/insights-log-path` branch (merged, remote
`[gone]`): `growth/growth.md` (9 entries), `insights/insights-log.md`, `notes/handover.md`,
`context-dashboard.html`, plus the report files. **Needs a fresh branch off `main`.**

**`~/.claude` — two separate unlanded items, neither is a PR:**
1. `main` = `f58dba4`, **1 ahead** of `origin/main`. The `risky_git_guard.sh` cd-resolution fix =
   dotclaude#13. Fast-forward: `git push origin main`.
2. `CLA-8-config-batch` = `fcbde01`, **exactly at** `origin/CLA-8-config-batch`, 0 ahead. 11 files
   are **staged** (+182/−2239), 3 more unstaged (incl. today's SKILL.md fix). **Third sighting** of
   this exact shape: the branch ref goes up, the index never gets committed.

## Decisions Made

- **Did not add `autoCompact*` to guacamayo's `settings.local.json`.** Global
  `~/.claude/settings.json:267-268` already sets `autoCompactWindow: 150000` and
  `autoCompactEnabled: true`; project settings override per-key and absent keys fall through, so
  guacamayo inherits. Duplicating them is the config-layering drift CLAUDE.md forbids.
- **Spawned the insights agent to a staging file, not to `insights-log.md`.** Deliberate deviation
  from `/grow` Step 4a. It only half-worked: the agent honored the staging file *and* still ran
  `git restore` on the log. The durable lesson is that **prompt-level prohibitions are not
  enforcement** — the fix belongs in a hook or in a spawn that has no write access to the log at all.
  **And state safety conditions as invariants over content** (expected line count, expected section
  list), never as "the diff must be empty" — an empty diff is reachable by discarding work.
- **The AIT "4 missing files" are not missing** — whitespace-only, reverted by
  `trailing-whitespace` + `end-of-file-fixer`. **Do not re-investigate this.**

## Open Threads

- **LIB-94 is done — verify before touching it.** Its remote is `[gone]` and
  `merge-base --is-ancestor` says NOT an ancestor of main, but by content it landed:
  `tests/unit/test_cron_empty_input.py` is on main, `cron.py` carries the `data/cron`/`latest.json`
  path, and the cross-repo guacamayo write is gone. Rebased or squashed work lands without leaving
  an ancestor. The local `LIB-94-cron-output-path` = `2a41cbb` is a stale duplicate — fourth
  instance of the artifact-sprawl pattern. **The LIB-94/96 conflict is moot; #97 merged 08-04 11:52.**
- **librarian moved a lot overnight**: PRs #100/#101/#102/#103/#104 merged, **#109 open**
  (`LIB-105-staff-review-fixes`), new plan `2026-08-04-staff-review-fixes.md` = `IN_PROGRESS`.
  New backlog: #106 (relinker suggest-only), #107 (extract cartographer to its own repo),
  #108 (extract `core/wiki_common.py`).
- **Issue/work drift, both directions**: librarian **#96 is still OPEN** though PR #97 merged;
  **#94 still reads `ready`** though its work is on main. Close both after confirming by content.
- **Config drift worth a retro row**: `~/.claude/settings.json:269` declares
  `"model": "claude-fable-5[1m]"` while both CLAUDE.md copies say the default is `claude-opus-5`.
  This session reports as opus-5, so the IDE picker is overriding settings.json. That asymmetry —
  spawns inherit the settings model, the interactive session doesn't — is the likely cause of
  "auto-compact works for spawns but not this branch," since the two have different context windows.
- **Two live-looking OpenAI keys in plaintext** at VS Code `settings.json:6` (`metabob.chatgptToken`)
  and `:9` (`alva.apiKey`). Should be revoked.
- **`pulse.sh` is the second defect in the same 30-line script in two sessions**, both sharing the
  shape "failure invisible to the caller."
- **Permanent sync churn, AIT**: `~/.claude` has no pre-commit hooks, so every
  `sync-global-skills.sh` run re-dirties the same 4 whitespace files. Fix at the source, ride the
  CLA-8 batch. Could fold into ai-project-template#59.
- **`tooling-ledger.md:34`** still reads `hypothesis — R7 P4 fix proposed`; the fix is now applied.
  Updating it is `/workflow-retro`'s job — flagged, not edited.

## Immediate Next Steps

1. `git -C ~/.claude push origin main` — one fast-forward, closes dotclaude#13.
2. Commit the staged 11 + unstaged 3 on `CLA-8-config-batch`, then push. The ref alone is not enough.
3. Cut a fresh guacamayo branch off `main` for this session's `/grow` output.
4. **Reopen the workspace** (not just reload) to pick up the `wiseer.code-workspace` fix; confirm
   `dotclaude` now shows ~14 changes in source control.
5. Board triage is DONE — 10 issues closed 08-04 (librarian #94/#96/#98/#99/#105, AIT #49/#59,
   LAE #115, LIS #89, JOB #15). 11 open portfolio-wide; ai-project-template and listen-wiseer at zero.

## Key Files

- `~/.claude/skills/workflow-insights/SKILL.md:27-37`
- `~/.claude/settings.json:267-269`
- `~/Library/Application Support/Code/User/settings.json:39-41`
- `~/workspace/guacamayo/scripts/pulse.sh:219`
- `~/workspace/guacamayo/.sounding/insights/insights-log.md`
- `~/workspace/librarian/tools/cartographer/parser.py:1377,1451-1453`
- `~/workspace/librarian/.claude/docs/plans/2026-08-04-staff-review-fixes.md`
