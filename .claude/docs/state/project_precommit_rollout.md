---
name: project-precommit-rollout
description: "Workspace-wide pre-commit standardization (2026-07-16, board green across 11 repos) — durable config baseline + remaining verifications"
metadata:
  node_type: memory
  type: project
  originSessionId: ca6248ff-a1e8-41d2-aa22-88a6feca99bb
---

Pre-commit (ruff + ruff-format + gitleaks + eslint local hooks) standardized across 11 repos on
2026-07-16 — board fully green; canonical base in `ai-project-template/template/_scaffold/.pre-commit-config.yaml`.
black fully removed (ruff-format replaces it). Fixes were left uncommitted for Ramsey.

**Durable config (apply to new repos):**
- ruff baseline: `select = ["E","W","F","I","N","UP","B","C4","SIM","RUF"]`,
  `ignore = ["E501","RUF001","RUF002","RUF003","N803","N806"]`; Marimo nbks add per-file `F841,N807,B018`.
- Manual runs: `make precommit` (playground/librarian/listen-wiseer/atlas, or workspace root for the
  full board, grouped output via RUFF_OUTPUT_FORMAT=grouped); `pre-commit run --all-files` anywhere.
- eslint: flat configs (`eslint.config.mjs` + `eslint .` in atlas/web; Vite react-ts in librarian/app/ui).

**Exclusions (user decisions):** FOIA-Fluent out of REPOS; hackathon-agent + SmartMeetOS (embedded in
project-mgmt-ai) are example code — never lint, hooks uninstalled, gitignored in outer repo.

**Still open:**
- listen-wiseer: history was restored from origin/main 2026-07-16 (orphan branch reset; lint mods
  uncommitted). Recheck `from etl.db import init_schema` resolves now that etl lives at src/etl/.
  Note: infrastructure/db/listen_wiseer.db has a pre-existing git-lfs pointer warning from remote.
- librarian: 14 pre-existing test failures (e2e need a server; wiki YAML parse issues) — unrelated to lint.
- User to verify dssg-volunteer-dash `.streamlit/secrets.toml.example` holds a placeholder (Claude
  can't read it; excluded from hook on that assumption).
- ai-project-template branch is master on BOTH local and remote (in sync, deliberate).
