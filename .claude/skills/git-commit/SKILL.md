---
name: git-commit
description: "Create a branch, stage changes, and commit — without opening a PR."
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash
---

Create a branch and commit current changes.

`$ARGUMENTS` — required. Format: `<slug> [commit message]`

## Branch naming

Per `~/.claude/refs/agile.md`:

| Type | Format | Example |
|------|--------|---------|
| Planned (has issue) | `{PREFIX}-{NUM}-{slug}` | `GUA-9-workflow-simplification` |
| Bug fix | `bug/{slug}` | `bug/fix-broken-links` |
| Spike | `spike/{slug}` | `spike/explore-supabase` |

- If current branch already matches one of these formats → stay on it
- Planned work requires a GitHub issue — if none exists, ask whether to create one
  or use a `bug/`/`spike/` branch. Prefix = repo being changed (prefix table in agile.md).

## Flow

1. `git status` — if tree is clean, stop
2. Create/switch to branch per naming table above (never commit on main)
3. Extract issue number from branch name (e.g. `9` from `GUA-9-workflow-simplification`);
   `bug/` and `spike/` branches have none
4. List files to stage (`git diff --name-only` + `git diff --cached --name-only`)
5. Skip: `.env`, `*.pem`, `models/*.pkl`, files >10 MB
6. Show file list → ask **"Stage these files and commit? (y/n)"**
7. Commit message in **Conventional Commits** format:
   - `{type}({scope}): {description} (#{num})` — e.g. `feat(review): merge code-pr (#9)`
   - Types: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `style`
   - If `$ARGUMENTS` provided, use as description; infer type from diff
   - On `bug/`/`spike/` branches, omit the issue ref: `fix(links): repair broken anchors`

## Safety

- Never force-push or amend published commits
- Never skip hooks (`--no-verify`)
- Never commit secrets or large binaries
- Never commit on `worktree-agent-*` branches — check out a named branch first (`{PREFIX}-{NUM}-{slug}`)

To push and open a PR: `/git-pr`.
