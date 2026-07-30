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

Orchestration: `review-cli run` is the single entry point — it owns the full pipeline
from signal detection through report rendering. Skills (`/akira`, `/workflow-review`)
call `review-cli run` and present the result; they no longer orchestrate individual
CLI subcommands. Agents preload the global `review-shared` skill via frontmatter.

## Package layout

- `driver.py` — **pipeline owner**: `run_review(config, scan_fn)` orchestrates all stages end-to-end; `sdk_scan` is the real Agent SDK implementation; injectable `scan_fn` for testing
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
  → review-cli run                     # single entry point (the deterministic driver)
      ├─ detect-signals                # which dimensions activate (no LLM)
      ├─ sdk_scan × N dimensions       # Claude Agent SDK, concurrent, output_format json_schema
      │   └─ validate_finding          # Pydantic gate; one repair round-trip then hard fail
      ├─ find_duplicate_clusters       # union-find dedup; deterministic cluster merge
      ├─ fingerprint + save_sweep      # SweepRecord → .claude/docs/reviews/
      ├─ build_trend_report            # diff vs previous sweep
      └─ render_report                 # deterministic Markdown output → stdout
```

Ad-hoc subcommands (still available for standalone use):
```
  review-cli detect-signals            # standalone signal detection
  review-cli validate-finding          # validate a single finding JSON
  review-cli dedup                     # cluster a findings list
  review-cli fingerprint --save        # fingerprint and save sweep
  review-cli trends                    # trend diff between two sweeps
  review-cli render-report             # render Markdown from findings JSON
```

## Usage

```bash
uv run review-cli --help
uv run pytest tests/review -q
uv run ruff check review tests
bash review/setup.sh        # after moving/renaming anything under docs/
```
