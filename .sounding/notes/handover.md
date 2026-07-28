# Handover — 2026-07-28 CI/Lint Fleet Fix + Cross-Repo Review

**Context**: Cross-repo /workflow-review on all diffs to main, then fixing all blocking findings. Escalated into CI infrastructure work — ruff version skew, hardcoded test paths, template lint gaps.

## Current State

**Completed this session:**
- /workflow-review across 4 repos (guacamayo, ~/.claude, job-system, librarian) — all blocking findings fixed
- Ruff version bump v0.11.2 → v0.16.0 across fleet (guacamayo, atlas, AIT, librarian, listen-wiseer)
- Guacamayo CI workflow created (`.github/workflows/ci.yml` using reusable python-ci.yml)
- 48 hardcoded-path test failures fixed (dynamic `REPO_ROOT` from conftest.py)
- AIT template `AB_BRIDGE.md.jinja` format fix (alignment spacing in Python code block)
- Job-system merge conflict resolved (cv-master.html/pdf — rebased + force-push-with-lease)
- Atlas 10 I001 lint fixes, AIT 5 I001 template lint fixes
- Hook fixes: log_pass in risky_git_guard.sh + branch_guard.sh, jq guard in issue_label_sync.sh
- Refs symlinks converted to relative paths (4 files)
- Akira review log path → `.reviews/` (ungitignored)
- Fleet list trimmed (lebanese-blonde + playground removed from deps-triage.sh)
- Issue #53 created (lint coverage gaps: TS/JS, shell, markdown, template rendering)

**Branches needing push (user commits done, needs `make ship`):**

| Repo | Branch | What |
|------|--------|------|
| guacamayo | GUA-53-lint-ci-coverage | ci.yml + .pre-commit-config.yaml + test path fixes |
| librarian | GUA-53-lint-ruff-bump | .pre-commit-config.yaml bump |
| listen-wiseer | GUA-53-lint-ruff-bump | .pre-commit-config.yaml bump |

**AIT** — `AB_BRIDGE.md.jinja` fix unstaged on `AIT-bug-dependabot-config`. Needs commit + push.

**Atlas** — 10 lint fixes + .pre-commit-config.yaml staged on open PR branch. Already pushed.

## Decisions Made

- **Dynamic REPO_ROOT over hardcoded paths** — `Path(__file__).resolve().parent.parent.parent` in conftest.py, imported by all test files. Portable across local + CI.
- **Ruff version pinned at v0.16.0** — matches what `uv sync` resolves in CI. Pre-commit and CI now agree.
- **Template lint is structurally ungatable locally** — AIT's `exclude: ^template/` in pre-commit means `make lint` never checks template code. Only CI (render → lint) catches issues. Accepted as known limitation.
- **CI for guacamayo** — uses reusable python-ci.yml with `lint-paths: "review tests"` and `test-command: "uv run pytest tests/ -q"`.

## Open Threads

- **LAE branch** — has pre-commit but no ruff hook (only generic hooks at rev v5.0.0). No ruff bump needed. Has 1 unpushed commit on `LAE-bug-dependabot-config`.
- **Issue #53** (lint coverage gaps) — backlog item for future: TS/JS (eslint/prettier), shell (shellcheck), markdown (markdownlint), template render lint step.
- **9 growth entries** — synthesis threshold met (5+). Due at next /dream.
- **Retro-worthy session** — touched CI config, pre-commit, hooks across fleet.

## Immediate Next Steps

1. Commit AIT `AB_BRIDGE.md.jinja` fix on `AIT-bug-dependabot-config` and push
2. `make ship` for GUA-53 branches (guacamayo, librarian, listen-wiseer)
3. Verify CI passes on all pushed branches
4. `/dream` — 9 growth entries, synthesis due, retro-worthy flag set

## Key Files

- `tests/review/conftest.py:3` — REPO_ROOT definition
- `.github/workflows/ci.yml` — new guacamayo CI
- `.pre-commit-config.yaml` — ruff rev bump (all 5 repos)
- `~/.claude/hooks/risky_git_guard.sh`, `branch_guard.sh` — log_pass fix
- `~/.claude/hooks/issue_label_sync.sh` — jq guard
- `~/.claude/scripts/deps-triage.sh` — fleet list trim
- `~/.claude/skills/akira/SKILL.md:137` — review log path
- `~/.claude/refs/` — 4 relative symlinks
