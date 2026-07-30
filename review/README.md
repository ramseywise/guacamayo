# review — deterministic backbone for the review pipeline

Python package + CLI that enforces the structural invariants of the multi-agent review
system. The split (see `.claude/docs/plans/2026-07-27-review-agent-architecture.md`):
**markdown tells agents what to think about; Python enforces that the output is
structurally sound.** LLM judgment lives in the dimension agents; everything checkable
without a model call lives here.

## The three parts

| Part | Where | Role |
|------|-------|------|
| Deterministic backbone | `review/` (this package) | Schemas, validation, dedup, fingerprints, trends, routing signals, report rendering |
| Dimension agents | `.claude/agents/` | LLM judgment: `correctness` (CR-), `safety` (SF-), `structure` (ST-), `agent-quality` (AQ-), `contracts` (CT-), `wander` (WD-) |
| Checklists | `.claude/skills/` | Per-dimension checklists + `shared` scan rules, read by the agents; not invoked directly |

Orchestration is global: `/akira`, `/code-review`, and `/workflow-review` (in
`~/.claude/skills/`) dispatch the agents and pipe their output through this CLI.
Agents preload the global `review-shared` skill via frontmatter.

## Package layout

- `schemas/models.py` — Pydantic models: `ReviewFinding`, `ReviewReport`, `SweepRecord`, reporter/severity/category enums, ID-prefix validation
- `validation.py` — finding/report validators (evidence-state vs merge-impact consistency, dispatch coverage)
- `signals.py` — regex file-signal detection → which dimensions activate (no LLM call)
- `deduplication.py` — union-find clustering of overlapping findings across dimensions
- `fingerprint.py` — stable finding fingerprints + sweep persistence (`.claude/docs/reviews/`)
- `trends.py` — sweep-over-sweep diff: new / resolved / recurring findings per dimension
- `render.py` — deterministic Markdown report from merged findings
- `commit_verification.py` — plan-step → commit verification (`verify-commits`)
- `sanyi.py` — sanyi violation → merge-impact mapping
- `docs/` — canonical refs (finding-schema, evidence-model, review-dimensions, review-dod, models) — **machine-consumed**, symlinked into `~/.claude/refs/` for the global skills
- `setup.sh` — idempotent symlink setup for those refs

## Pipeline flow

```
files/diff
  → review-cli detect-signals          # which dimensions activate
  → dispatch .claude/agents/*          # LLM scan (orchestrated by skills)
  → review-cli validate-finding        # schema gate per finding
  → review-cli dedup                   # cross-dimension clustering
  → review-cli fingerprint --save      # persist sweep record
  → review-cli trends                  # diff vs previous sweep
  → review-cli render-report           # deterministic Markdown output
```

## Usage

```bash
uv run review-cli --help
uv run pytest tests/review -q
uv run ruff check review tests
bash review/setup.sh        # after moving/renaming anything under docs/
```
