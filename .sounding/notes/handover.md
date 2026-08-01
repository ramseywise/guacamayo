# Handover — 2026-08-01 Guard fix, landing verification, branch triage

**Context**: Meta/dispatch session across guacamayo, `~/.claude` (dotclaude), librarian,
learn-ai-engineering, and ai-project-template. Three arcs: fix the `risky_git_guard.sh`
recurrence, verify what actually landed on librarian main, and triage two unpushed branches.

## Current State

**Done and committed**
- `risky_git_guard.sh` CLA-71 third recurrence — fixed, Ramsey committed as `2863fb4` on
  `bug/risky-guard-variable-cd` in `~/.claude` (**not pushed yet**). Two sub-defects:
  (a) the `cd` pattern was anchored at `^`, so `git clone … && cd <wt> && git commit` fell
  through to the session cwd — now matches a `cd` segment anywhere and takes the LAST one;
  (b) a target containing `$`/backtick now blocks *without* printing a `Resolved target:`
  line. Test suite 20 → 26 cases, all green.
- librarian#73 — verified and closed. GUA-43/GUA-44/GUA-21/LIB-68 all landed via `-v2`
  rebuild branches (PRs librarian#77, #78), not the originals. guacamayo#43/#44 annotated
  with the true landing PR; their plan docs marked COMPLETE.
- AIT #43 ruff-format fix shipped (`de75e98`).
- Cleanups: stale LAE-28 worktree pruned, atlas fast-forwarded 3 commits.

**Verified, awaiting Ramsey**
- `guacamayo/GUA-63-session-id-findings` — 2 commits, no remote. `git merge-tree` clean
  against origin/main; rebased in a probe worktree and `uv run pytest tests/review -q`
  → 302 passed. Ready to push + PR (`Closes #63`).
- `~/.claude` `bug/risky-guard-variable-cd` — committed, unpushed.
- AIT #40/#42/#43 — Ramsey said she'd `make ship` from the workspace herself. Durable
  patch exports live at `ai-project-template/.claude/docs/patches/*.patch` (git-ignored)
  in case the `/tmp` worktrees for #40/#42 are lost.

**Resolved this session**
- `learn-ai-engineering/LAE-30-rl-depth-content` — was stale, not single-copy. `rl.md`
  and `05-RL/README.md` were byte-identical blobs to main; of 86 touched files only 3
  genuinely differed and **main was ahead in all 3** (pre-TF2 `tf.Session()` code, no
  README book-notes section, deleted a `bayesian.yml` main kept). Issue LAE#30 already
  closed. Ramsey confirmed discard; the branch is gone. Nothing owed.
  (`LAE-28-docs-integration` still exists as a branch — worktree already pruned, branch
  fully merged, safe to delete whenever.)

**In flight elsewhere**
- guacamayo checkout is on `GUA-73-status-enum-design` with
  `.claude/docs/specs/plan-doc-status-enum.md` staged — another session started GUA-73.
  The `gua-73-wt` worktree is gone.

## Decisions Made
- **Landing is verified by content, never by message.** `git log --grep` returns nothing
  for rebuilt branches; a commit message is a cache like any other. Grep the symbol on
  main, compare blob SHAs.
- **Use `git rev-parse --verify --quiet`.** Bare `rev-parse` echoes unresolvable args to
  *stdout*, so `2>/dev/null` doesn't suppress them — that produced 23 false "differs"
  on LAE-30 before the flag cut it to the true 3.
- **A guard's block message must not assert what it didn't resolve.** Honest uncertainty
  plus a named escape hatch (`git -C <worktree> commit …`) beats a confident wrong path.
- **Instruction vs. evidence**: Ramsey asked to push LAE-30; the blobs contradicted it.
  Reported and stopped rather than executing or deleting.

## Session close (/dream ran 2026-08-01 16:11)
- Reflection: `.sounding/reflections/2026-08-01_16-11.md`
- **Synthesis RAN** — 13 entries, 7 merged into `sounding.md`, 4 discarded to R7,
  1 to librarian wiki as domain knowledge. All dispositions in `growth-log.md`.
  Accumulator cleared to 0.
- **R7 spawned in background** (sonnet) with 5 pre-verified root causes so it doesn't
  re-derive them, plus a mandate to *retire* stale hypothesis rows rather than only add.
  Results land staged in `.sounding/tooling-ledger.md` + `tooling-ledger-log.md`.

## Open Threads — the consolidation question Ramsey raised
She named four problems at session close. I verified all four rather than agreeing:

| Claim | Verdict |
|---|---|
| Subagent surface should be review / design / code | Open design question — see below |
| Agents need to self-select skills; too much correction | Real, downstream of the surface question |
| Claude commits showing on GitHub | **Symptom right, cause wrong** — the no-commit gate held. 46 commits carry a `Co-Authored-By: Claude` trailer, author is `ramseywise` every time. The one Claude-authored commit (`1e3c816`) is a third-party "Claude Companion" app. Trailer comes from the harness's built-in commit guidance, not from any skill. |
| 1 issue → 5 issues / 5 branches / 5 PRs for 1 commit | **Exact.** `workflow-refine/SKILL.md:152` says "create the sub-issues" but creates flat *siblings* — GUA-65 has zero sub-issues via GraphQL while #73/#74/#75 are its children in substance. The `addSubIssue` template already exists at `github-projects/SKILL.md:93` and nothing calls it. `Makefile.common:96-99` already harvests every `#N` into `Closes`, so one PR on the parent branch would close them all today. |

**The larger question, unresolved**: 23 skills across 4 prefixes is a surface I navigate
fine and Ramsey has to correct — the cost lands on her, not me. That asymmetry is the
argument for shrinking it. Candidate shape: three agent-facing verbs (**design** for
initiative-scale, **code** for one issue on one branch, **review** as the gate), with
research/plan/refine demoted to *phases inside* those rather than user-driven slash
commands. Not decided; needs its own session.
- **AIT #41** may already be closed by #42's work — needs a check before triage.
  **AIT #44** is unstarted `backlog`.
- **Unanswered DoD question**: close AIT #40/#42/#43 now, or after PR merge? Asked twice.
- The "red main accepts merges" condition (librarian, AIT, playground) is a portfolio-wide
  cache-invalidation problem, same shape as the label-cache drift — still unaddressed.
- **Bash antipatterns are the one metric moving the wrong way**: 9,021 total = 28.55/session
  on 08-01, up from 27.8 on 07-31, while every other signal held or improved. Worth a
  root-cause pass at R7 — which Bash calls should have been Read/Grep/Glob/Edit?
- **`/workflow-insights` writes double-dated reports.** `SKILL.md:29` passes
  `insights-report-$(date +%F).html`, but `parser.py:1253` already appends the date and
  makes the symlink itself (see its comment at :1250) — output lands as
  `insights-report-2026-08-01-2026-08-01.html`. Fix is one line: pass a plain
  `insights-report.html` and drop the now-redundant `ln -sf` at `SKILL.md:34`. Not done
  here — `~/.claude` is mid-branch on `bug/risky-guard-variable-cd` and this is unrelated.

## Immediate Next Steps
1. Ramsey: push `GUA-63-session-id-findings` + open PR (`Closes #63`).
2. Ramsey: push `bug/risky-guard-variable-cd` in `~/.claude`.
3. Ramsey: `make ship` the AIT branches, then merge #46/#47/#48 and close #40/#42/#43.
4. Next opus session: run `/workflow-insights` → `/workflow-retro` (R7).

## Key Files
- `~/.claude/hooks/risky_git_guard.sh`
- `~/.claude/hooks/tests/test_risky_git_guard.sh`
- `~/workspace/guacamayo/.sounding/tooling-ledger.md`
- `~/workspace/ai-project-template/.claude/docs/patches/*.patch`
- `~/workspace/guacamayo/.claude/docs/plans/GUA-43-plan.md`, `GUA-44-plan.md`, `GUA-62-plan.md`
