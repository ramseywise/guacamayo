# Growth - Learning Accumulator

**Last Synthesis**: 2026-08-01 16:11 (/dream — 7 merged into sounding.md (stale-cache generalized to "everything that summarizes state is a cache", negative-evidence verification, honest-uncertainty-in-tooling, artifact sprawl, checking-her-claims, instruction-vs-evidence), 4 discarded → /retro R7 (repo-prefix enforcement, staging default, make ship target, autocompact), 1 discarded as domain knowledge (lifespan/lazy-import → librarian wiki); all 13 dispositions logged)
**Entries Since**: 9

*One-line entries added by /reflect and /grow. Processed and cleared by /synthesize.*

---

- [outcome:partial] AIT-33 executed + verified on stacked branch (uncommitted); GUA-60 driver smoke 4/5, live re-run deferred to post-7pm — 2026-07-30
- [outcome:success] CLA-71 guard fix committed (2863fb4), librarian#73 verified + closed, GUA-63 verified merge-clean, LAE-30 triaged and discarded — 2026-08-01
- [discovered] Worktree agents: tear down each worktree the moment its agent commits, not at session end — a lingering worktree locks its branch (`+` in `git branch -vv`) and hides the files from the main checkout, so finished work reads as "I don't see anything"; report branch+SHA+push-state, never a table implying files sit in her tree — 2026-08-01
- [confirmed] CLA-67's closing-link hypothesis failed again, twice the same day: guacamayo PRs #76 (GUA-63) and #77 (GUA-73) merged with **empty bodies and zero `closingIssuesReferences`**, leaving #63 stuck at `ready` and #73 at `in-review` after their work was fully on main. Root cause is the already-filed guacamayo#69 (`quick-pr` exits 0 on an existing PR, so externally-created PRs escape issue-linking) — the fix exists as an issue, not as code, and every PR opened outside `make ship` re-opens the hole — 2026-08-01
- [confirmed] R7 F3 observed live in merged history: PR titles are de-hyphenated branch slugs — "Gua 63 session id findings", "Gua 73 status enum design". The Makefile-derived title survives to the permanent record, so the slug is what the repo shows forever — 2026-08-01
- [confirmed] Label state is a cache, again — `gh issue list` reported #63 `ready` / #73 `in-review` while `git merge-base --is-ancestor` proved both tips already on origin/main. Drift was in the safe direction (work done, issue open), but the board still disagreed with the repo — 2026-08-01
- [confirmed] Duplicate-branch sprawl recurs in `~/.claude`: `bug/risky-guard-variable-cd` and `CLA-8-insights-computed-columns` both sit at `2863fb4` with an **empty diff between them** and neither has an upstream — the same shape as AIT #40/#42's three-branches-one-tree. A branch named for one issue now carries another issue's only copy of the guard fix, which is still unlanded on origin/main — 2026-08-01
- [discovered] The lingering-worktree cost has a second form: an **empty** one. `LAE-115-case-study-code-test` holds a live worktree in `/private/tmp/.../wt-lae-115` and a `+` branch lock while being **zero commits ahead of origin/main**. Checking "is the branch ahead" is the cheap way to tell an in-progress worktree from an abandoned one before deciding to prune — 2026-08-01
- [discovered] A subagent silently preferred SKILL.md over its own prompt: I spawned /workflow-insights with an explicit "pass the BARE filename, the parser double-dates" instruction, and it wrote `insights-report-2026-08-01-2026-08-01.html` anyway — the skill's literal step won over the dispatch instruction, and the agent's summary reported success without mentioning the conflict. Corollary: a workaround handed to a subagent is not a fix; fix the skill text or expect the defect — 2026-08-01
- [confirmed] R7 P4's diagnosis is correct — `librarian/tools/cartographer/parser.py:1253` appends `date.today()` to the stem unconditionally, so a dated `--output` always double-dates. The one-line fix (skill passes bare `insights-report.html`) is sound and still unapplied — 2026-08-01
- [corrected] Bash antipatterns did NOT hold — 9,363 = **28.99/session**, up again from 28.55 the same day. I committed one mid-session myself: a `grep --include=*.py` Bash call that died on zsh nomatch, where the Grep tool was correct and would not have failed. The metric and the cause are the same thing — 2026-08-01

*Format: YYYY-MM-DD [type] - [concise learning/discovery]*
*Types: [discovered] = new insight, [confirmed] = validated existing approach, [corrected] = updated understanding*
*Outcome tags persist across synthesis (pilot measurement — first 20 sessions)*
*Processed and cleared by /synthesize*
