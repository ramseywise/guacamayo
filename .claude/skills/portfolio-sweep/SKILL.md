---
name: portfolio-sweep
description: Sweep every repo guacamayo governs (repos.toml) — git/PR state plus a code review of what changed on each default branch — and summarise the digest. Report only. Triggers on: '/portfolio-sweep', 'sweep the portfolio', 'check all the repos', 'are the repos up to date', 'what changed across the repos'.
allowed-tools: Read, Bash
---

# Portfolio sweep

*One look across every governed repo. Reports; never acts.*

The work is done by `uv run telemetry --sweep` (`src/telemetry/sweep.py`); this skill runs it
and reads the result. The same command runs weekly from launchd (`telemetry-cron.sh sweep`),
so a fresh digest may already exist — check before re-running.

## 1. Fresh digest or new run

```bash
ls ~/workspace/guacamayo/.sounding/sweeps/????-??-??.md 2>/dev/null | sort | tail -1
```

If today's digest exists, read it and skip to step 2. Otherwise run:

```bash
uv run --project ~/workspace/guacamayo telemetry --sweep            # state + review
uv run --project ~/workspace/guacamayo telemetry --sweep --no-review   # state only, ~30s
```

The review pass runs the review driver on the plan (no API key) and takes a few minutes per
repo with new commits. Use `--repos a,b` to narrow it, `--days N` for a first-run lookback.
Ask before a full review run if the user only asked "are the repos up to date".

## 2. Summarise

Read `.sounding/sweeps/<date>.md` and report, in this order:

1. **Errors** — `not cloned`, `fetch_failed`, failed `gh` calls, incomplete reviews. A repo with
   errors was only partly checked; say so before anything else.
2. **Drift** — local default behind origin, uncommitted work, `gone upstream` and `merged, not
   deleted` branches, external worktrees.
3. **Findings** — unticked **blocker** and **important** first, with `file:line`; then counts of
   the rest and of carried-over items.
4. **Open PRs / dependabot / board actions** — one line per repo that has any.

`preserve/*` branches are rescued work kept on purpose — count them, never suggest deleting them.

## Boundaries

- No issue creation, no branch or worktree deletion, no `Status:` edits, no commits. Point at
  `scripts/hygiene.sh` or the owning repo for cleanup and let the user run it.
- The digest and `findings.json` live in `.sounding/` (git-ignored) because they cover private
  repos. Never copy private-repo findings into a public repo, an issue, or a PR.
- To acknowledge a finding, the user ticks `[x]` in the digest; the next sweep records it.
