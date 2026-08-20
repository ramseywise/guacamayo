# AGENTS.md

## Project

Guacamayo is a live instance of the Puffin framework for AI identity,
long-term continuity, persistent workflow state, and AI-assisted
software development. The emerged identity is **Sounding** (2026-07-13,
Genesis V-15.2).

The repository contains three packages:
- **Identity system** — `.sounding/` seeds + `.claude/skills/` lifecycle skills (no build)
- **Review package** — `review/` deterministic Python driver + 12 LLM dimension agents
- **Telemetry package** — `telemetry/` metrics pipeline + 7-tab dashboard

## Architecture

Guacamayo separates three concerns:

1. **Identity** — continuity across sessions via seeds, growth log, and handover.
2. **Process** — scaffolding work items end-to-end via plans and GitHub Issues.
3. **Execution** — performing changes in the codebase via review, code, and git tooling.

**Metacognition** observes all three layers and proposes system improvements.
It does not apply changes — it proposes diffs for human approval (D1, 2026-08-09).

Do not collapse these layers without explicit architectural justification.

---

## Review Dimension Agents (`.claude/agents/`)

The `review/driver.py` dispatches one agent per active dimension. Agent system prompts
live in `.claude/agents/<dimension>.md`. The vocabulary is reconciled with galactus's
`review-*` skill family — both repos run the same 12-dimension registry.

### Always-on (8 dimensions)

| Prefix | Dimension | What it scans |
|--------|-----------|--------------|
| CR | `correctness` | Logic errors, wrong assumptions, broken contracts |
| IN | `intent` | Whether the change achieves what the plan said it would |
| AR | `architecture` | Layer violations, naming drift, structural rot |
| SF | `safety` | Data exposure, input validation, auth gaps |
| TE | `testing` | Coverage gaps, mocked boundaries hiding bugs, missing negative tests |
| SI | `silent-failure` | Errors swallowed silently, wrong exit codes, missing fail-loud paths |
| PF | `performance` | Hot-path regressions, N+1 queries, memory leaks |
| WD | `wander` | Open questions — things that might be wrong but need human judgment |

### Conditional (4 dimensions)

| Prefix | Dimension | Activates when |
|--------|-----------|---------------|
| RT | `runtime` | `is_agent_code` — agent execution, tool dispatch, streaming |
| SG | `safeguards` | `is_agent_code` — prompt injection, jailbreak surface, output validation |
| LK | `leakage` | `is_ml_code` — train/test contamination, label leakage, eval cheating |
| CT | `contracts` | `has_sanyi_contracts` — reads `SANYI.md`, emits findings against three-principle taxonomy |

Findings carry attribution (`introduced` / `adjacent` / `pre_existing`) so blockers are
scoped to the diff, not the whole codebase.

**Note**: `akira` and `sanyi` were absorbed into these dimensions, not retired. The
`Reporter` enum retains `AKIRA_SCAN`/`AKIRA_WANDER`/`SANYI` values so historical sweep
records still deserialize; `DEPRECATED_REPORTERS` marks them, and the driver never
dispatches them.

---

## Meta-Skill Pipeline (`.claude/skills/`)

The metacognition loop runs mostly automatically. One human gate: `/meta-feedback`.

```
/meta-wake → work → /meta-grow → [auto: /meta-insights] → /meta-feedback (human) → /meta-retro → config
```

| Skill | Role | Writes to |
|-------|------|-----------|
| `/meta-wake` | Session entry point — loads seeds, reads dashboard, orients on plan state | (reads only at start) |
| `/meta-grow` | Mid-session capture — tags growth entries, refreshes dashboard, overwrites handover | `growth/growth.md`, `notes/handover.md` |
| `/meta-insights` | Auto-spawned — mines sessions.db + hook logs for friction patterns | `.sounding/insights/insights-log.md` |
| `/meta-feedback` | **Human gate** — verifies insight claims against raw corpus, routes findings | `.sounding/telemetry/feedback-log.md` |
| `/meta-retro` | Auto after feedback — proposes config diffs; propose-only, never auto-applies | `tooling-ledger.md` |
| `/meta-dream` | Session close — writes reflection, conditionally synthesizes seeds, tidies indexes | `.sounding/` seeds + logs |
| `/track` | Any session — adds typed verification row to ledger | `tooling-ledger.md` |

**Single-writer rule**: `/meta-grow` captures; `/meta-dream` is the sole transformer of
identity seeds. Multiple writers produce voice drift and accretion.

---

## Evaluator (board.json → proposed_actions → actions.jsonl)

Each board tick (every 10 min via launchd) runs the **autonomous-dispatch evaluator**:

1. `uv run telemetry --board` reads GitHub issue state via `gh` CLI
2. `telemetry/evaluator.py` computes `proposed_actions[]` — triage, close, label-fix,
   review-dispatch proposals with reason + evidence
3. Actions write to `.sounding/telemetry/board.json`
4. `/meta-wake` renders proposed actions as one accept/reject batch
5. Decisions append to `.sounding/telemetry/actions.jsonl` with `proposal_id`

Exactly two idempotent mutations (auto-close merged-with-`Closes`, unambiguous label
correction) may run unattended behind an `--act` flag that defaults **off**. The
propose/mutate boundary moves only on logged acceptance-rate evidence.

---

## Telemetry Package

`telemetry/signals.py` — signal registry (56 declared, 18 with resolvers). Signals feed
dashboard tiles and the insights engine.

`telemetry/dashboard.py` — renders the 7-tab HTML dashboard:
- **Overview**: system architecture, three-layer diagram
- **Cost & Efficiency**: cost trends, cache hit rate, repo effort vs outcome
- **Session Health**: token economics, session frequency, compaction rate
- **Context Health**: context pressure, compact timing
- **Loop Health**: pipeline stage liveness — five stage cells (Capture/Insights/Feedback/Retro/Config) with age colors, populated by `render_pipeline_health_region()`
- **Experiments**: hypothesis lifecycle, graduation rate, cascade state
- **Retro**: hypothesis graduation rate, open vs. resolved experiments

Full tab descriptions in `README.md §The Dashboard`.

`telemetry/__main__.py` entry points: `--facts` (sync sessions.db), `--board` (update board.json + run evaluator), `--dashboard` (re-render HTML).

---

## Key Invariants

- **Write authority narrows as blast radius widens.** The loop cannot write hooks or settings — only propose diffs.
- **Continuity files hold pointers, never copies.** Cross-repo work state lives in per-repo plans or GitHub Issues, read fresh at every wake.
- **Retrieval-first knowledge access.** Query librarian (`search_wiki` / `read_page`) rather than bulk-loading directories.
- **The factual session record lives in librarian.** Reflections stay local because they are subjective and identity-bearing.
