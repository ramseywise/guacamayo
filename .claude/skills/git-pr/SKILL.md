---
name: git-pr
description: "Stage, commit, push, and open a PR — resolving rebase conflicts along the way. Never merges."
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash Write
---

PR flow for the current working tree: stage → commit → push → open PR. Merging is out of
scope — Ramsey reviews and merges.

`$ARGUMENTS` — optional commit message. If omitted, derive from diff.

## Flow

1. **Check**: `git status` + `git diff main...HEAD --stat` — if clean and no unpushed commits, stop.
   Branch must match `{PREFIX}-{NUM}-{slug}`, `bug/{slug}`, or `spike/{slug}`
   (see `~/.claude/refs/agile.md`) — never main; offer to create one if needed
2. **Commit** (if needed): list files, skip secrets/`.env`/large binaries, show list + message,
   confirm before `git commit`
3. **Push**: `git push -u origin HEAD` — if rejected, `git fetch origin main && git rebase origin/main`,
   resolve conflicts, retry
4. **Draft PR**: read active plan if present, write title + body per conventions below,
   show full content, confirm before `gh pr create`

## PR conventions

- Title: `{PREFIX}-{NUM} {description}`, under 60 chars — issue number from branch name
  (e.g. `GUA-9-workflow-simplification` → `GUA-9 Workflow simplification`).
  `bug/`/`spike/` branches: `{type}: {description}` instead
- Commits: `{type}({scope}): {description} (#{num})` — types: `feat`, `fix`, `refactor`,
  `docs`, `chore`, `test`, `style`
- Body must include `Closes #N` (skip for `bug/`/`spike/` branches with no issue) and
  follows `.github/pull_request_template.md`:

```markdown
## Overview
[Derive from diff: what this PR accomplishes and why]

## Related Issue(s)
- Closes #[NUM from branch name, or prompt user]

## Changes Made
[Summarize from `git diff --stat` and commit messages]

## Impact
- [x] [Infer: Low/Medium/High from scope of changes]

## Priority
- [x] [Infer: Low/Medium/High from context]

## Testing
- [x] [Check applicable: unit/integration tests from test output]
- [ ] Manual testing performed

## Type of Change
- [x] [Infer from diff: New feature / Bug fix / Refactoring / Documentation update]

## Documentation
- [Check if docs were modified in diff]

## Deployment Considerations
- [Check if infra/ files were modified in diff]
```

Auto-fill what you can infer from the diff and test results. Leave unchecked boxes for the user to verify.

## Conflict resolution

`git diff --name-only --diff-filter=U` → read each → resolve → `git add` → `git rebase --continue` → retry push.

## Safety

- Never merge the PR — that's Ramsey's call after review
- Never force-push or skip hooks
- Never commit `.env`, `*.pem`, `models/*.pkl`, or files >10 MB
