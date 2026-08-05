# Tooling Ledger — Archive

Graduated experiments. Append-only. Active hypotheses live in `tooling-ledger.md`.

**Area tags**: `cost` (token/model), `context` (compaction/window), `friction` (manual fixes/permissions), `quality` (review/lint/test), `workflow` (skills/pipeline/ceremony), `safety` (guards/gates), `observability` (telemetry/attribution)

---

## R0 — 2026-07-22 (pre-numbered retros, batch graduation)

| Date | Change | Area | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07 (rollup) | 20 verified/failed: Bash patterns, /retro+ledger, cartographer, v2→v3, doc-artifact, akira, commands/, wake-nudge, model pairing, git-ignore .claude/docs/, shell.md safety, /grow, experiment tracking | mixed | verified/failed | >150k context 66%→37% confirmed; bash_antipattern blocking 26.4 flat failed |
| 2026-07-17 (batch) | 11/12 infra: sanyi, sync-global, zsh, skill dedupe, librarian ingest, phase-protocol, rules→refs, review-sweep, review ladder, compact-wiki, repo-security | mixed | verified | All actively working. retrieval telemetry split out (inconclusive) |

## R1 — 2026-07-24

| Date | Change | Area | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07-18 | memory_route_guard.sh | safety | verified | Hook exists, 0 misroutes across 6+ sessions |
| 2026-07-20 | Plan-doc ABANDONED status | workflow | verified | Used in 2 plans: agile-workflow-system, listen-wiseer phase7a |
| 2026-07-20 | Bash antipattern advisory→blocking | friction | failed | 26.4/session flat for 3 windows. Hook removed |
| 2026-07-20 | Spawn model guidance + default→sonnet | cost | superseded | Replaced by fable default (2026-07-22). 60% opus pre-change |
| 2026-07-22 | Ledger compressed 51→30 lines | workflow | verified | Split to active+archive format |
| 2026-07-22 | `make status/push/quick-pr` targets | workflow | verified | Used across 6 repos via make ship |

### R1 findings applied
- F1: Ledger split into active + archive (this file)
- F2: `bash_antipattern_warn.sh` deleted (failed experiment)
- F4: /dream Phase 8 independent tooling-change detection added
- F5: `PULL_STRATEGY` variable added to Makefile.common
- F6: Worktree auto-cleanup → backlog issue #27

## R8 — 2026-08-05

### Graduated rows (2 retired this retro)

| Date | Change | Area | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07-31 | Insights-report double-date path drift (R7 P4 fix) | workflow | partial-verified | Fix applied: `workflow-insights/SKILL.md:29` now passes bare `insights-report.html` (confirmed by grep). No new double-dated files since fix. Historical artifacts remain: `.sounding/insights-report-2026-08-01-2026-08-01.html` (historical), `.sounding/insights-report.html` + `.sounding/insights-report-2026-07-31.html` at root (pre-fix era). Metric `absence:writes-to-sounding-root-reports` partially failing (root artifacts not cleaned up). Graduating as partial-verified; cleanup is a one-time file operation, not a config lever. |
| 2026-08-05 | task_complete_check.sh e2e false-block fix | quality | fixed-pending-commit | Hook edited in `~/.claude/hooks/task_complete_check.sh` (new `elif [ -d tests/e2e ]` branch). Fix latent since hook was written; triggered by LIB-110 Phase C1 `tests/unit/` deletion. Uncommitted — Ramsey commits. Graduating from active ledger; metric `absence:stop-hook-e2e-false-blocks` starts now. |

### R8 findings

- F1: Config drift — model default documented but not applied to settings.json for 5 days → config-audit diff proposed
- F2: `~/.claude/` unversioned source → sync churn; fix-at-source requires design decision (dotclaude git repo)
- F3: dotclaude ref-without-commit push failure, third sighting → pre-push guard proposed
- F4: Insights-agent spawn protocol proven safe on third attempt → encode protocol in `/grow` skill
- F5: Fable leaking into non-verdict skills (17.74% vs 5% target, metric failed) → subagent model-pin audit
- Carry-forward: R7 P1 (Co-Authored-By ban) and R7 P2 (sub-issue linking) still unapplied — restate proposals

### R8 config proposals (pending Ramsey approval — do not auto-apply)

**P1 (F1): Add model-claim vs settings.json diff to retro config-health Step 0.5**
Add to `~/.claude/skills/workflow-retro/SKILL.md` Step 0.5 Check B:
```
(5) CLAUDE.md model default claim (`Default session model:` line) matches `model` key in `~/.claude/settings.json`.
    Mismatch = BLOCKER (config drift can go undetected for days — see R8 F1: 5-day gap 2026-07-30→2026-08-04).
```
Eval sketch: before = Check B has 4 sub-items ending at "(4) no secrets"; after = Check B has 5 sub-items; judgement = run the check against a settings.json with `model: claude-fable-5` and CLAUDE.md claiming opus — should surface BLOCKER.

**P2 (F2): dotclaude versioning — design decision needed**
No config diff proposed. Options: (a) `git init ~/.claude` and track skills/ hooks/ explicitly, (b) keep unversioned but add a `git status`-equivalent to sync-global-skills.sh to warn on unsaved changes before sync. Option (a) is the correct fix but requires Ramsey decision. Filed as `improve` — needs design before actionable.

**P3 (F3): pre-push ref-without-commit guard**
New check in `~/.claude/hooks/risky_git_guard.sh` (or a new `pre_push_guard.sh`): if `git push` fires and `git rev-list origin/{branch}..HEAD` is empty (no commits ahead of remote), block with message:
```
[risky-git-guard] Branch has no commits ahead of remote. Did you forget to commit? Aborting push.
```
Advisory-safe: only blocks if the branch ref exists at remote AND local HEAD matches it (genuine empty push).

**P4 (F4): Encode insights-agent spawn protocol in `/grow` SKILL.md**
Add to `~/.claude/skills/grow/SKILL.md` (background-spawn section, currently step describing `/workflow-insights` spawn):
```
**Insights-agent spawn protocol** (proven after two data-destruction events):
- Content invariants: agent must verify output file is *strictly longer* (line count) than input and all prior section headers are present before accepting.
- Named tool: agent uses Edit tool directly — never shell redirection (`>`) which silently truncates on failure.
- Dispatcher verification: after agent completes, run `git diff --stat` and reject if net line count is negative.
```
Eval sketch: before = grow SKILL.md has no spawn protocol; after = protocol is visible to any session reading /grow before spawning; judgement = a fresh session reading the skill will see the three constraints without needing prior session context.

**P5 (F5): Pin subagent model in workflow-research/plan/refine**
Audit `~/.claude/skills/workflow-research/SKILL.md`, `workflow-plan/SKILL.md`, `workflow-refine/SKILL.md` for any subagent spawn instructions. Where a model is not explicitly specified, add `--model claude-opus-5` (or `claude-sonnet-5` for fan-out/extraction agents). Fable should appear only in verdict-shaped skills. Metric unchanged from R7: `ratio:fable-tokens-in-non-verdict-skills below 5% by 2026-08-13`.

**P6 (carry-forward R7 P1): Co-Authored-By ban in CLAUDE.md**
(Reproduced from R7 — still unapplied.)
Add to `~/.claude/CLAUDE.md` Communication block:
```
- Never add a `Co-Authored-By:` trailer to a drafted commit message or PR body.
  Ramsey commits and does not want Claude named as co-author.
```

**P7 (carry-forward R7 P2): Sub-issue linking in workflow-refine + CLAUDE.md**
(Reproduced from R7 — still unapplied.)
1. `~/.claude/skills/workflow-refine/SKILL.md:152` — replace "offer to create the sub-issues (labeled `backlog`)" with: "For `needs-split` items, offer to create real sub-issues (labeled `backlog`) linked to the parent via `addSubIssue` (template in github-projects SKILL.md:93). Sub-issues ride the parent's branch and PR — do NOT create a separate branch per sub-issue."
2. `~/.claude/CLAUDE.md` Session hygiene — add after worktree dispatch rules: "**Sub-issues ride the parent branch.** When workflow-refine splits an issue, sub-issues are linked via `addSubIssue`, land on the parent's branch, and close via `Closes #N` in the same PR."

---

## R7 — 2026-08-01

### Graduated rows (5 retired this retro)

| Date | Change | Area | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07-27 | Plan-doc Status line enforcement (F6) | workflow | dropped | Failing metric for 4 consecutive retros (R4–R7). Not a config lever — 2 specific docs need edits. Retiring as a measured hypothesis; fix is a one-time edit (see P0 below). |
| 2026-07-30 | Autocompact "no defect found" (metric confusion verdict) | context | failed | Verdict was scoped to VS Code only; terminal-mode recurrence 07-31 contradicts it. Graduated as failed. Active tracking continues in the terminal-mode row (tooling-ledger.md). |
| 2026-07-30 | R6 F1: Cross-repo dispatch rule added to CLAUDE.md | safety | verified | Confirmed present at `~/.claude/CLAUDE.md:176` ("Cross-repo dispatch rule: The worktree must be created in the target repo…"). 0 cross-repo isolation leaks since applied. |
| 2026-07-30 | R6 F2: `--no-track` branch creation rule added to CLAUDE.md | friction | verified | Confirmed present at `~/.claude/CLAUDE.md:157,160`. Convention block updated with both the flag and the rationale. |
| 2026-07-30 | R6 F3: Quota-masquerade diagnostic note added to shell.md | observability | verified | Confirmed present at `~/.claude/rules/shell.md:26` ("## Quota masquerade"). |
| 2026-07-30 | R6 F5: TodoWrite nudge hook wired (PostToolUse/Bash, advisory, exit 0) | workflow | verified | `~/.claude/hooks/todo_write_nudge.sh` exists on disk and confirmed wired in `~/.claude/settings.json:103`. Measuring effect — metric now tracking. |

### R7 findings

- F1: Co-Authored-By trailer from harness → CLAUDE.md Communication rule proposed (P1)
- F2: Flat sibling issues with no parent link → refine sub-issue convention + CLAUDE.md dispatcher rule proposed (P2)
- F3: PR titles are de-hyphenated slugs → Makefile.common fix proposed (P3)
- F4: Repo-prefix/branch-name mismatch FRICTION → enforcement hook proposed; FRICTION row converted to hypothesis in ledger
- F5: `make ship` implicit branch target → confirmation echo proposed (P6)
- F6: Work not reliably staged for review → dispatcher post-agent step made explicit in CLAUDE.md (P7)
- F7: Red main accepting merges portfolio-wide → branch protection per repo-security-setup.md; FRICTION converted to hypothesis; pending Ramsey per-repo decision
- P4: /workflow-insights double-date output → SKILL.md step 3 fix proposed (pass bare `insights-report.html`)
- P5: Bash antipatterns rising (28.55/session, 08-01) → targeted advisory hook proposed
- Closed 6 rows; 29 active → 30 active (net +7 new findings, -6 graduated)

### R7 config proposals (pending Ramsey approval — do not auto-apply)

**P0 (plan-doc fix — no issue needed)**: Edit the 2 stale plan docs. *(Paths corrected
post-retro: R7 cited `~/.claude/docs/plans/`, which does not exist — `ls` returns no such
directory. The files live in guacamayo. The finding was real; the paths were invented.)*
- `~/workspace/guacamayo/.claude/docs/plans/2026-07-22-workflow-simplification.md` line 5: change `**Status**:` → `Status:`
- `~/workspace/guacamayo/.claude/docs/plans/2026-07-24-GUA-23-review-verdict.md`: add `Status: COMPLETE` after the title line

**P0b (config drift R7's audit pass missed)**: `~/.claude/docs/` exists again, containing
`insights/` (2026-07-27.md, latest.json) and `state/insights-report.html`. Global
CLAUDE.md states it is "deliberately deleted; do not recreate it" and that cross-repo
state belongs in `guacamayo/.claude/docs/state/`. Something in the insights tooling
recreates it. Decide: re-delete and fix the writer, or amend CLAUDE.md to permit it.

**P1 (F1): Forbid Co-Authored-By in CLAUDE.md Communication block**
Add one bullet under Communication:
```
- Never add a `Co-Authored-By:` trailer to a drafted commit message or PR body.
  Ramsey commits and does not want Claude named as co-author.
```
*(Rationale corrected post-retro: R7's draft said "the harness appends them
automatically; adding them in prose duplicates the trailer." It does not append them —
the built-in commit guidance instructs Claude to write the trailer, which is why all 46
appear on commits authored by ramseywise. The trailer is unwanted outright, not merely
duplicated, so the bullet must forbid it rather than warn about duplication.)*

**P2 (F2): Fix flat-sibling-issue explosion in workflow-refine + CLAUDE.md**
Two changes:
1. `~/.claude/skills/workflow-refine/SKILL.md:152` — replace "offer to create the sub-issues (labeled `backlog`)" with:
   ```
   For `needs-split` items, offer to create real sub-issues (labeled `backlog`) linked
   to the parent via `addSubIssue` (template in github-projects SKILL.md:93). Sub-issues
   ride the parent's branch and PR — do NOT create a separate branch per sub-issue.
   ```
2. `~/.claude/CLAUDE.md` Session hygiene, after the worktree dispatch rules, add:
   ```
   **Sub-issues ride the parent branch.** When workflow-refine splits an issue, sub-issues
   are linked via `addSubIssue`, land on the parent's branch, and close via `Closes #N`
   in the same PR. One PR per parent issue, not one per sub-issue.
   ```

**P3 (F3): PR titles from issue title in Makefile.common**
Replace `Makefile.common:110` block (the `TITLE=` assignment for `[A-Z]{2,4}-[0-9]+-` branches):
```make
	ISSUE_NUM=$$(echo "$$BRANCH" | grep -oE '^[A-Z]{2,4}-[0-9]+' | grep -oE '[0-9]+$$'); \
	ISSUE_TITLE=$$(gh issue view "$$ISSUE_NUM" --repo "${ISSUE_REPO:-$(shell git remote get-url origin | sed 's/.*github.com[:/]//' | sed 's/.git$$//')}" --json title --jq '.title' 2>/dev/null); \
	PREFIX=$$(echo "$$BRANCH" | grep -oE '^[A-Z]{2,4}-[0-9]+'); \
	TITLE=$${ISSUE_TITLE:+$$PREFIX $$ISSUE_TITLE}; \
	TITLE=$${TITLE:-$$PREFIX $$(echo "$$BRANCH" | sed -E 's/^[A-Z]{2,4}-[0-9]+-//' | tr '-' ' ')}; \
```

**P4 (double-date fix): workflow-insights SKILL.md step 3**
Change `~/.claude/skills/workflow-insights/SKILL.md:29` from:
```
   python3 ~/.claude/scripts/insights.py --output ~/workspace/guacamayo/.sounding/insights/insights-report-$(date +%F).html
```
to:
```
   python3 ~/.claude/scripts/insights.py --output ~/workspace/guacamayo/.sounding/insights/insights-report.html
```
And change line 34 from:
```
   ln -sf insights-report-$(date +%F).html ~/workspace/guacamayo/.sounding/insights/insights-report.html
```
to:
```
   ln -sf insights-report-$(date +%F).html ~/workspace/guacamayo/.sounding/insights/insights-report.html
```
(The symlink step stays, but the `--output` arg is now bare so the parser stamps the date once, not twice. The symlink then points the stable alias at the dated file — parser creates it, symlink aliases it.)

**P5 (Bash antipatterns): targeted advisory hook**
New hook `~/.claude/hooks/bash_substitution_nudge.sh` — fires on PostToolUse/Bash when the command matches one of the substitutable patterns (`\bcat\b`, `\bhead\b`, `\btail\b`, `\bgrep\b`, `\brg\b`, `\bfind\b`, `\bsed\b`, `\bawk\b`). Emits to stderr:
```
[bash-substitution] Use Read/Grep/Glob/Edit instead of <matched_command> — see CLAUDE.md Bash tool section.
```
Advisory only (exit 0). Add to settings.json PostToolUse/Bash block alongside todo_write_nudge. Metric: `count-drop:bash-antipatterns below 25/session by 2026-08-31`.

**P6 (F5 / make ship): confirmation echo before push**
In `~/.claude/Makefile.common` `ship` target, before `git push`, insert:
```make
	@BRANCH=$$(git branch --show-current); \
	ISSUE=$$(echo "$$BRANCH" | grep -oE '^[A-Z]{2,4}-[0-9]+' || echo "(no issue)"); \
	echo "About to push: branch=$$BRANCH  issue=$$ISSUE"; \
	echo "Press Enter to confirm or Ctrl-C to abort."; \
	read _CONFIRM;
```

**P7 (F6 / staged handoff): CLAUDE.md dispatcher convention clarification**
In `~/.claude/CLAUDE.md` Session hygiene, step 4 (after completion), replace current text with:
```
4. **After completion**: dispatcher soft-resets the branch to staged:
   ```
   git checkout {branch} && git reset --soft origin/main
   ```
   This is the **required handoff step** — not optional. Worktree directories are cleaned
   after the agent finishes and staged-only changes are destroyed with them; the soft-reset
   moves the agent's committed work back to staged so Ramsey reviews the diff and commits herself.
   After review she may instead keep the agent's commits as-is. Ramsey — not the dispatcher —
   runs `make ship`. Claude never pushes.
```

---

## R6 — 2026-07-30

| Date | Change | Area | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07-20 | growth-log.md + dream gate hook | workflow | verified | growth-log persisting across 3+ synthesis runs; /dream 2026-07-30 logged 6 cleared entries with full audit trail |
| 2026-07-24 | /dream Phase 8 independent tooling-change check | workflow | verified | 3/3 sessions triggered retro correctly (2/3 at R5 + this R6 session = threshold met) |
| 2026-07-28 | Insights placement settled: engine+data in librarian, rendered artifacts in guacamayo/.sounding | observability | verified | 3 retro windows (R4+R5+R6): artifacts confirmed in .sounding/; no outliers |
| 2026-07-29 | Review-findings persistence: required-field list inlined in workflow-review Stage 4b | observability | verified | 7/7 rows schema-conformant on day 1; graduated R5 |

### R6 findings applied
- F1: Cross-repo worktree isolation leak → CLAUDE.md rule proposed (pending approval)
- F2: `--no-track` branch creation rule → CLAUDE.md Conventions proposed (pending approval)
- F3: Quota-masquerades-as-agent-failure → shell.md diagnostic note proposed (pending approval)
- F4: Plan-doc Status line fix (2 stale docs) → doc edits proposed (pending approval)
- F5: TodoWrite nudge hook → new hook + settings.json proposed (pending approval)
- F6: design-* skill retirement decision → pending Ramsey's choice (a=retire/b=consolidate/c=document)
- F7: MEMORY.md retro number → stale, update to R6

### R6 config proposals (pending Ramsey approval — do not auto-apply)

**P1 (F1): Add cross-repo dispatch rule to CLAUDE.md** — in the "Worktree agents follow the branch convention" block, after step 4, add:
```
**Cross-repo dispatch rule**: The worktree must be created in the **target repo**, not the
dispatcher's repo. A worktree in guacamayo does not sandbox writes to ai-project-template —
the agent follows the `Repo:` path in its prompt, which is the live checkout. Create the
worktree with `git -C ~/workspace/<target-repo> worktree add ...`.
```

**P2 (F2): Add `--no-track` rule to CLAUDE.md** — update branch creation example in step 1 of worktree convention block: `git checkout -b {PREFIX}-{NUM}-slug}` → `git checkout -b {PREFIX}-{NUM}-slug} --no-track`. Add note under Conventions table: "`git checkout -b NAME origin/main` silently sets upstream to origin/main, breaking push flow — always use `--no-track`."

**P3 (F3): Add quota-masquerade note to shell.md** — new section:
```markdown
## Quota masquerade
Account usage exhaustion surfaces as `error_max_turns` or silent empty results from the Agent
SDK — indistinguishable from agent logic failures at the API level. Before debugging agent
behavior, check quota state. SDK-level `error_max_turns` in a low-turn session is a quota
signal, not a turns signal.
```

**P4 (F4): Fix Status lines in 2 stale plan docs** — `2026-07-22-workflow-simplification.md` line 5: change `**Status**:` to `Status:`. `2026-07-24-GUA-23-review-verdict.md`: add `Status: COMPLETE` after the title line.

**P5 (F5): Wire TodoWrite nudge hook** — new advisory hook `~/.claude/hooks/todo_write_nudge.sh` that fires a stderr warning at 100 bash calls in a session if no TodoWrite invoked. Add to settings.json PostToolUse/Bash block (exit 0, advisory only). Eval: `grep "HEAVY SESSION" ~/.claude/.hook-pass-log.jsonl` shows entries after wiring.

**P6 (F6): Decide on design-* skills** — three options: (a) retire all 4 (recommended — 3 retro windows zero invocations after description rewrite), (b) consolidate into `/design` dispatch, (c) keep + add trigger examples to CLAUDE.md. Decision required before R7.

---

## R5 — 2026-07-29

| Date | Change | Area | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07-29 | Review-findings persistence: required-field list inlined in workflow-review Stage 4b + finding-schema example | observability | verified | 7 rows in review-findings.jsonl, all 7 pass full-schema validation (id, source, date, repo, file, title, merge_impact, evidence_state present); day-1 conformance met |
| 2026-07-28 | Insights placement settled: engine+data in librarian, rendered artifacts in guacamayo/.sounding | observability | verified | 2 retros (R4+R5): context-dashboard.html, insights-log.md, insights-report.html confirmed in .sounding/; no artifacts found outside .sounding/; state doc authoritative |

### R5 findings applied
- F1: Review-findings persistence graduated verified — 7/7 rows schema-conformant on day 1
- F2: Insights artifact placement graduated verified — 2 retro windows clean
- F3: Plan-doc Status enforcement still failing — `2026-07-24-GUA-23-review-verdict.md` has no Status line; `2026-07-22-workflow-simplification.md` uses `**Status**:` (bold) not bare `Status:` prefix — both need fixup
- F4: p90 output tokens unchanged at 956/msg (latest insights: 22% >150k, no trend improvement) — verbosity cap hypothesis active, due 08-24
- F5: TodoWrite enforcement: 69+ long sessions still run without TodoWrite across R4+R5 window — hook not yet wired, hypothesis active
- F6: Bash error stratification still in cartographer backlog — no signal in R5 insights; hypothesis active, due 08-17

### R5 config proposals (pending Ramsey approval — do not auto-apply)

**P1: Fix Status line format in 2 stale plan docs** — `2026-07-24-GUA-23-review-verdict.md` needs `Status: COMPLETE` (merge verdict = approve; merged). `2026-07-22-workflow-simplification.md` already has `**Status**: EXECUTED` but grep for `^Status:` misses it — either normalize to bare `Status:` prefix or update the enforcement check to match bold variant.

**P2: Wire TodoWrite hook** — PostToolUse/Bash: if cumulative bash_calls > 100 and no TodoWrite in session, emit structured warning. Pattern persists across R4+R5 (69+ sessions blind). Metric: `ratio:TodoWrite-in-heavy-sessions above 50% by 2026-08-09`. See R4 P1 for draft mechanism.

**P3: Add ≤400-token output budget to wake/grow/dream prompts** — p90 at 956 tokens/msg unchanged across 2 retros. Quick change: add one instruction line to each identity skill prompt. Metric: `p90:output-tokens-per-msg below 700 by 2026-08-24`.

**P4: Retire or redesign design-* skills** — 0 invocations across 3 retro windows (227+ sessions). Options: (a) add invoke examples to CLAUDE.md, (b) consolidate to `/design` dispatch, (c) close backlog and remove. Decision needed before R6.

## R4 — 2026-07-28

| Date | Change | Area | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07-24 | PULL_STRATEGY variable in Makefile.common | friction | verified | 0 rebase-conflict-abort events across 227 sessions (5-session threshold met) |
| 2026-07-27 | Remove bash_antipattern_warn.sh from settings+disk (F1) | friction | verified | Hook absent from disk and settings.json at R4 check; R3 approved action confirmed applied |
| 2026-07-27 | Investigate/change model default fable vs opus (F2) | cost | verified | settings.json model = `claude-fable-5[1m]`; fable is default, opus = escalation only; 87%+ opus cost-weighted is justified escalation pattern not default mismatch |
| 2026-07-24 | FRICTION: label extraction + dashboard panel | observability | failed | Not present in insights-log 2026-07-27 or 2026-07-29 (2 consecutive runs). Cartographer parser gap, not a config lever |
| 2026-07-24 | Agent spawn extraction + type attribution table | observability | failed | No signal in insights-log 2026-07-27 or 2026-07-29 (2 consecutive runs). Subagent cost attribution requires parser work (cartographer) |
| 2026-07-26 | Design skill description optimization (via skill-creator) | workflow | failed | 0 invocations across 227 sessions; 2 retro windows. Descriptions not the blocker — skills are workflow-fit gap. Retire or redesign |

### R4 findings applied
- F1: PULL_STRATEGY graduated verified
- F2: bash_antipattern_warn.sh removal graduated verified
- F3: Model default fable graduated verified
- F4: FRICTION label + agent attribution graduated failed → cartographer parser backlog
- F5: Design skill optimization graduated failed → skill-creator retirement audit backlog
- F6: 4 new hypotheses added (TodoWrite hook, bash stratification, verbosity cap, session breakpoints)
- F7: Plan-doc Status enforcement remains active (failing — 2 docs missing Status)

### R4 config proposals (pending Ramsey approval — do not auto-apply)

**P1: Add TodoWrite enforcement hook** — PostToolUse/Bash: if cumulative bash_calls > 100 and no TodoWrite logged, emit structured warning. Target: reduce context drift in 30% of heavy sessions.

**P2: Retire design-* skills or rewrite as invoke-on-demand** — `/design-sprint`, `/design-initiative`, `/design-milestones`, `/design-prototype` show zero invocations across 2 retro windows (227 sessions). Options: (a) add to `make help` output + CLAUDE.md examples, (b) consolidate into `/design` dispatch, (c) close backlog issues and remove.

**P3: Add ≤400-token output budget line to identity skills** — wake/grow/dream prompts. p90 output tokens 956/msg; 5× cost multiplier at that range. Mechanism: add `Keep output under 400 tokens` to each skill's instruction block.

**P4: Add Status: line to 2 stale plan docs** — `/Users/wiseer/workspace/guacamayo/.claude/docs/plans/2026-07-22-workflow-simplification.md` and `2026-07-24-GUA-23-review-verdict.md` missing `Status:` header. Quick fix: prepend `Status: ABANDONED` or `Status: COMPLETE` to each.

## R3 — 2026-07-27

| Date | Change | Area | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07-20 | sync-global-skills.sh guards | safety | verified | 3/3 retros: 0 unaccounted reservoir skills — threshold met |
| 2026-07-20 | Duplicate skill deletion (listen-wiseer + Parallax/sanyi) | workflow | verified | 3/3 retros: 0 duplicate skill names in active repos |
| 2026-07-22 | Worktree timing guidance in CLAUDE.md | friction | verified | 0 stale-state errors across 222 sessions (5-session threshold met) |
| 2026-07-22 | Worktree agent commit convention in agile.md | safety | verified | 0 data-loss events across 222 sessions (5-session threshold met) |
| 2026-07-19 | task_complete_check.sh Stop hook | quality | inconclusive | R3 deadline: no lint errors on commit triggered in any window |
| 2026-07-19 | mcp-builder refs/→skills/ | workflow | inconclusive | R3 deadline: no MCP sessions in 3 retro windows |
| 2026-07-19 | /docs-check + docs_drift_warn.sh | quality | inconclusive | R3 deadline: no L2 reviews triggered in window |
| 2026-07-20 | /sanyi init verify-before-write | quality | inconclusive | R3 deadline: no SANYI inits in 3 retro windows |
| 2026-07-20 | ci_drift_warn.sh advisory hook | quality | inconclusive | R3 deadline: no broken CI paths in 3 retro windows |
| 2026-07-22 | PR body `Closes #N` convention + quick-pr auto-gen | workflow | inconclusive | R3 deadline: mixed evidence, no clean signal |
| 2026-07-26 | Hook telemetry wiring audit (hooks call log_event) | observability | failed | Hook log: 1 entry (test_hook only). All hooks DO call log_event — wiring correct. Issue is trigger rate: conditions rarely met. Threshold `count-drop:unique-hooks-in-log above 5` not met at R3 |

### R3 findings proposed (pending Ramsey approval)
- F1: Remove bash_antipattern_warn.sh from settings.json + delete hook file (config-ledger divergence: recorded as removed in R1 but still wired)
- F2: Investigate model default field (settings.json model: opus-4-6, not fable — fable-default experiment may not have landed)
- F3: Add log_pass() to lib.sh for exit-0 hook fire-rate visibility
- F4: Graduate 6 untestable + 4 verified rows (this section)
- F5: Plan-doc Status line enforcement for 2 docs missing Status
- F6: Create GitHub issue for unknown-error taxonomy gap (35.3%, 3 retros flat)

## R2 — 2026-07-26

| Date | Change | Area | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07-18 | memory_route_guard.sh | safety | duplicate | Already graduated in R1; row left in active ledger by mistake |
| 2026-07-22 | Default model → fable; opus = escalation only | cost | verified | 88%+ fable+opus share (target ≥60%) — insights-log 2026-07-27 |
| 2026-07-20 | Design skill descriptions rewritten | workflow | failed | 0 invocations across 219 sessions; insights-log R4 flags zero-invoked design skills |
| 2026-07-20 | Hook telemetry (log_event, .hook-log.jsonl) | observability | failed | 89 log entries, only test_hook fires; hooks don't call log_event consistently |
| 2026-07-20 | Skill name mismatches fixed; typo aliases | workflow | verified | 0 mismatches across 2 retros (threshold: 2) |
| 2026-07-20 | Parallax integration plan (5 phases) | quality | inconclusive | Plan executed but review-shared never invoked — no L2+ reviews occurred to test |

### R2 findings applied
- F1: Duplicate memory_route_guard.sh row removed from active ledger
- F2: Fable model default graduated as verified
- F3: Design skill descriptions graduated as failed → backlog issue for skill-creator optimization
- F4: Hook telemetry graduated as failed → new hypothesis for wiring audit
- F5: Skill name mismatches graduated as verified
- F6: Parallax review-shared graduated as inconclusive
- F7: 6 untestable rows annotated with R3 graduation deadline
- 2 new hypothesis rows added (design skill optimization, hook telemetry wiring)
