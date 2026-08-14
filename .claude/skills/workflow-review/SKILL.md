---
name: workflow-review
description: "Phase 4 review — plan fidelity + multi-reporter code review + DoD assessment + merge verdict. Run BEFORE committing (pre-commit quality gate) so fixes avoid amend/fixup commits. Also usable for PR reviews. Triggers: 'review PR #42', '/workflow-review', '/workflow-review my-feature', 'check the PR', 'review the diff', 'code-pr 42'."
skills: [review-shared]
allowed-tools: Read Grep Glob Bash Agent
---

Review implementation against plan (if one exists) AND review code quality via
multi-reporter orchestration. Primary use: pre-commit quality gate after `/workflow-execute`
(review before committing so fixes are clean, not amend/fixup). Also handles standalone PR reviews.

`$ARGUMENTS` — one of:
- A PR number or URL (`42`, `#42`, `https://...`) → PR review mode
- A work-item slug (`my-feature`) → plan-doc review mode
- Empty → discover: match `^Status:[[:space:]]*IN_PROGRESS`, else `gh pr list`

## Target repo

All paths resolve against a **target repo**:

1. A `repo:<name-or-path>` token anywhere in `$ARGUMENTS` (strip before routing)
   — bare name resolves to `~/workspace/<name>`.
2. Otherwise, the repo containing the cwd.
3. In a meta/workspace-root session with no `repo:` token, ask which repo.

Run commands with the target as working dir. Artifacts land in the TARGET repo's
`.claude/docs/plans/` so that repo's own sessions find them.

---

## Stage 0: Scope Detection

Before gathering context, determine the review scope from the branch and repo state:

1. **Check branch prefix**: `bug/` or `spike/` → lightweight. Feature branch with plan doc → full.
2. **Check for plan doc**: `find .claude/docs/plans/ -name "*$(branch-slug)*"`. Present → full. Absent → lightweight.
3. **Check commit types**: if all commits are `chore`, `style`, `fix`, `docs` → lightweight. Any `feat` → full.

| Scope | What runs | What's skipped |
|-------|-----------|----------------|
| **Full** | All stages (1-8) | Nothing |
| **Lightweight** | Context brief (slim), lint/tests, worktree check, DoD, verdict | dimension scan, plan fidelity |

The review artifact is always written regardless of scope — `check-review` in `make ship` gates on it.

## Stage 0.5: Worktree & Branch Cleanup Check

Before reviewing code quality, verify the workspace is clean:

1. **Leftover worktrees**: `git worktree list` — any worktrees beyond the main checkout are leftovers from agent runs. Flag as `merge_impact: important` finding if they contain uncommitted changes, `nit` if empty.
2. **`worktree-agent-*` branches**: `git branch --list 'worktree-agent-*'` — these are auto-generated branches from `isolation: "worktree"` that bypassed the branch convention. Flag as `merge_impact: blocker` — commits on these branches must be cherry-picked onto a named `{PREFIX}-{NUM}-slug` branch before review can proceed.
3. **Unmerged agent branches**: check for branches matching the current work item that haven't been merged into the current branch (e.g. `GUA-18-*` branches when reviewing `GUA-23-*`). Flag unmerged branches as `merge_impact: blocker`.
4. **Stale tracking branches**: `git branch -vv | grep ': gone]'` — remote-deleted branches still tracked locally. Flag as `nit`.

Report findings in Stage 7 under a "Workspace Hygiene" subsection.

## Stage 1: Context Brief

Produce a context brief (per `review-shared/references/context-brief.md`). Gather:

1. **PR metadata** (if PR mode): `gh pr view <number> --json title,body,headRefName,baseRefName,labels,reviewRequests`
2. **Diff**: `gh pr diff <number>` (PR mode) or `git diff main...HEAD` (plan mode)
3. **Changed files**: from PR or git diff
4. **Repo context**: read CLAUDE.md, check for SANYI.md, check for Refs: line
5. **CI status** (PR mode): `gh pr checks <number>`
6. **Callers of changed symbols**: Grep for function/class names from the diff
7. **Review profile**: infer `general` or `agent-system` from imports and file paths.
   Agent-system if any changed file imports LLM/agent frameworks or lives under `agents/`,
   `*_agent/`, `prompts/`.
8. **Plan doc** (if exists): find matching `.claude/docs/plans/*.md` by slug or branch name.
   If found, read `## Plan` section for fidelity check.

Fill the context brief template. Unknown fields = "unknown", not guessed.

## Stage 2: Plan Fidelity (conditional — skip if no plan doc)

For each plan step:

| Plan said | Code shows | Tests | Status |
|-----------|-----------|-------|--------|
| Step 1: ... | [actual] | PASS/FAIL | Match / Deviation / Missing |

### Stub detection

Check key files for: `TODO`, `NotImplementedError`, `return None`, `pass` on critical
paths. Blocker if on critical path, warning otherwise.

Deviations become findings with `merge_impact: important` (justified deviation) or
`blocker` (unjustified omission).

## Stage 3: Dispatch Reporters

### Dimension scan (quality + contracts + wander)

Delegate to the deterministic driver for reporter dispatch, validation, deduplication,
fingerprinting, and report rendering:

```bash
uv run --project ~/workspace/guacamayo review-cli run \
  --repo <target-repo> \
  --files <changed-file1> --files <changed-file2> \
  --reviews-dir <target-repo>/.claude/docs/reviews
```

The driver spawns all active dimension agents — always-on: correctness, intent,
architecture, safety, testing, silent-failure, wander; conditional: runtime and
safeguards if agent code, leakage if ML code, contracts if SANYI.md exists — validates every
finding through the Pydantic gate (one repair round-trip then hard fail), deduplicates
via union-find, fingerprints, and persists a sweep record. Capture stdout as the
dimension report for Stage 7. The driver's exit code surfaces any validation failure.

Plan-fidelity findings (Stage 2) are NOT passed to the driver — they remain in-session.
In Stage 4, merge them into the report by hand.

### Lint and tests
Run `make lint` / `make test` if available; fallback to stack-specific commands
(`uv run pytest --tb=short -q`, `npx tsc --noEmit`, etc.).
Record pass/fail. Test failures become findings with `merge_impact: blocker`.

## Stage 4: Merge plan-fidelity + lint findings

The driver has already merged and deduped the dimension findings. In this stage:
1. Take the driver's rendered findings section.
2. Prepend any plan-fidelity findings from Stage 2 (they have no dimension agent).
3. Prepend any lint/test failure findings.
4. Re-rank the combined list: blockers first, then important, suggestion, nit.

Stage 6 derives the verdict directly from this combined list — no serialization step.

Sweep persistence (fingerprint + sweep record) is handled by the driver automatically.
No separate Stage 4b persistence step is needed.

## Stage 5: DoD Assessment

Assess each item from `~/.claude/refs/review-dod.md` as met / gap / n/a.
Gaps become findings with appropriate merge_impact. Repo-specific DoD overrides defaults.

If a plan doc exists, also check:
- All plan steps accounted for (from Stage 2)
- Status line present and correct
- Acceptance criteria from the plan/issue met

## Stage 6: Judge — Merge Verdict

The verdict is computed, not judged. The driver already derives `merge_decision`
inline for dimension findings (`~/workspace/guacamayo/review/driver.py:784-794`).
Apply the same ladder to the Stage 4 combined list (driver + plan-fidelity + lint
findings), in order:

1. Any reporter/dispatch failure that could mask blockers → `insufficient_context`
2. Any `merge_impact: blocker` → `request_changes`
3. Any `merge_impact: important` → `comment`
4. Otherwise → `approve`

`driver.py:784-794` is the single source of these rules — if this list and the code
disagree, the code wins.

## Stage 7: Report

Produce the unified report:

```markdown
# Review — #<number> <title> (or <slug>)

## 1. Overall Understanding
[1-3 sentences]

## 2. Review Contract
[From context brief]

## 3. Plan Fidelity
[Plan step table — only if plan doc exists. Otherwise: "No plan doc — standalone review."]

## 4. What Looks Strong
[Genuine positives, not filler]

## 5. Blocking Findings
[merge_impact: blocker findings with canonical IDs]

## 6. Important Findings
[merge_impact: important]

## 7. Questions and Hypotheses
[merge_impact: question + hypothesis-state findings]

## 8. Suggestions and Nits
[merge_impact: suggestion | nit]

## 9. Testing and Evaluation Assessment
[Coverage, gaps, repeated-run consideration for agent code]

## 10. Definition of Done Assessment
[DoD checklist table: item | status | note]

## 11. Reporter Dispatch Summary
| Reporter | Status | Findings |
|----------|--------|----------|
| plan-fidelity | ran/skipped | N findings |
| correctness | dispatched/skipped | N findings |
| intent | dispatched/skipped | N findings |
| architecture | dispatched/skipped | N findings |
| safety | dispatched/skipped | N findings |
| testing | dispatched/skipped | N findings |
| silent-failure | dispatched/skipped | N findings |
| runtime | dispatched/skipped | N findings |
| safeguards | dispatched/skipped | N findings |
| leakage | dispatched/skipped | N findings |
| contracts | dispatched/skipped | N findings |
| wander | dispatched/skipped | N questions |
| lint/tests | ran/skipped | pass/fail |

## 12. Merge Verdict
**approve** | **comment** | **request_changes** | **insufficient_context**
[1-2 sentence rationale]
```

If a plan doc exists, append the review section to it, set `Status: EXECUTED`, and write
`Review:` on the next line to the value this verdict maps to — see the verdict→`Review:`
table in Stage 8. `Status:` and `Review:` each carry exactly one enum member, no suffix.

## Stage 8: Action (read-only default)

Report the verdict to the user. Do NOT run `gh pr review` unless explicitly authorized.

> "Verdict: **[verdict]**. Want me to submit this as a GH review?"

If authorized:
- `approve` → `gh pr review <number> --approve -b "<summary>"`
- `request_changes` → `gh pr review <number> --request-changes -b "<summary>"`
- `comment` → `gh pr review <number> --comment -b "<summary>"`

For plan-doc mode (no PR): append the `## Review` section to the plan doc, set `Status:` to
`EXECUTED`, and set `Review:` by this table:

| verdict | `Review:` | meaning |
|---|---|---|
| *(not run)* | `pending` | no review has concluded |
| `approve` | `passed` | reviewed, accepted |
| `comment` | `passed` | reviewed, accepted with non-blocking notes |
| `request_changes` | `failed` | reviewed, rejected — findings outstanding |
| `insufficient_context` | `blocked` | review ran and could not decide |

`pending` means *no review concluded* — a verdict never writes it. Writing `pending` for a
concluded review makes "rejected", "could not decide", and "nobody has looked" the same
token, which is the defect this table exists to remove. Never write a free-text status.

## Boundaries

- Never commit, push, or merge — Ramsey commits.
- Never auto-fix findings — report only. Recommend `/akira dao` for safe fixes.
- Read-only by default; GH review submission requires explicit authorization.
- Per-reporter failures are reported (not retried infinitely), noted in dispatch summary.
- Max 3 review rounds — if issues persist, escalate to user.

## Exit

When the review verdict is **approve**:

1. **Label sync** — issue stays `in-review` until PR merges. On merge, close the issue.

2. **Compact** — call `/compact "phase: review → ship"` to shed review context.

3. **Print exit block**:

```
──────────────────────────────────────
✅ Review complete — approved.
👉 Next: git commit, then make ship
🧠 Model: n/a (user action)

After merge:
  gh issue close <N> --comment "Shipped via PR #<M>."
──────────────────────────────────────
```

When the verdict is **request_changes**:

1. **Label sync** — keep `in-review` (changes are part of the review cycle).

2. **No compact** — stay in the same session to fix findings.

3. **Print exit block**:

```
──────────────────────────────────────
🔄 Review complete — changes requested.
👉 Next: fix findings, then /workflow-review <slug>
🧠 Model: (same session)
──────────────────────────────────────
```
