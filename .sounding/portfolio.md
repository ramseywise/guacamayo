# Portfolio — Living Seed

**Last Transformed**: 2026-08-18 (/meta-dream synthesis: guacamayo gained the live autonomous-dispatch harness; galactus gained the ML parity/run-registry arc. Previous: 2026-08-02 — librarian cartographer's two-cadence settlement + its public-repo data boundary)

---

## The Map

**Flagship (recurring research→plan→execute→review cadence)**
- **listen-wiseer** — Spotify copilot: LangGraph agent, GMM/LightGBM recommender, agentic web search, langmem. The best-documented repo; Phase 8 (RAG right-sizing) landed.
- **atlas** — agentic financial intelligence for B2B: LangGraph forecast/segment/knowledge agents, Neo4j, real eval harness. Bridges the classical-ML and agentic eras natively.

**Prototyping**
- **galactus** — contract-bounded LLM generation. `ml6/` is the reference case study: FastAPI service generating length-constrained marketing copy grounded in uploaded PDFs. Thesis: counting characters is code's job; the model's job is content. Now also the ML parity arc: `runs/ml/*` case studies held to a five-point reproducibility bar, with `runs/_index/` + lending's `run_record.py` (landed 2026-08-16) as the local run registry — records over claims, refusals recordable as first-class outcomes (fraud's open question). Also hosts review-leakage ML dimension scanner. Stack: Python 3.12, FastAPI, Pydantic v2, Anthropic SDK, structlog.

**Meta / tooling / knowledge (supports everything else)**
- **guacamayo** (this repo) — the Sounding instance + persistence KB + now the **autonomous dispatch harness** (GUA-119, live 2026-08-16): a 10-minute launchd tick derives the board, a pure evaluator writes `proposed_actions[]`, wake renders an accept/reject batch, exactly two idempotent mutations may run unattended (off by default), and every decision logs to `actions.jsonl` so acceptance rates can move the propose/mutate boundary on evidence. The design premise held on its first live cycle: the one close-proposal was wrong twice over (stale branch pointer, then a worktree hiding uncommitted work) and both human gates caught it. Meta-layer session lives here; v2 = 3 seeds, single-writer lifecycle, feedback loop wired to `~/.claude` (retro + ledger) and librarian. KB half still unscoped — Ramsey's call.
- **librarian** — sourced knowledge compiler (raw → wiki, conflict-flagged, cited) + MCP + code index. The system of record for factual session history; being extended into a DSSG team-facing KB template (indexer decisions made — don't relitigate). Its cartographer half settled into two cadences (2026-08-02): `--facts` daily, deriving session notes from JSONL and failing loud on empty input, and `--cron` weekly, deterministic and key-free — the LLM analysis stage was retired rather than repaired, because the report nobody read was also what made an empty pipeline look healthy. **librarian is a public repo**, and its derived session material (`raw/`, the wiki session log) carries verbatim prompts; both are gitignored, and that boundary is load-bearing, not hygiene.
- **playground** — the R&D lab: three parallel agent implementations over a shared KB; patterns prove out here before migrating to flagships.
- **ai-project-template** — Copier template extracting the tooling layer; owns its own discovery stack (scope-poc, project-discovery, project-genesis) by design — kept its own thing, not globalized.

**Domain case studies (dated or blocked)**
- **lebanese-blonde** — 2020 credit-risk model getting a full in-place facelift; Phase 0 (tooling + bugfixes) executed, needs its own dedicated cycles. Pairs with atlas: same domain five years apart — supervised ML then, agentic orchestration now. That narrative is worth building.
- **NRR** — nutrition/cycle-tracking recommender; blocked on de-identifying personal health data.

**Learning archive** — `Python/` (5-category reorg done), small showcase repos; `learn-ai-engineering` (interview prep KB — raw Notion dump becomes librarian ingest source, thin human-facing layer points at wiki pages); First-Flask-App scoped as the connective "what I've been learning" front door — sequenced AFTER flagships are demo-ready, not before.

**DSSG (NYC-DSSG platform work)** — nonprofit client engagement + volunteer tooling. Constraint that shapes every recommendation: volunteer-maintained, near-zero budget, high turnover — boring and well-documented beats clever.

## Threads Between Projects

- The tooling loop: playground proves → ai-project-template extracts → every repo consumes; guacamayo sessions run the cross-cutting view; /retro + ledger graduate learnings to `~/.claude`.
- Knowledge: librarian compiles everything factual; wiki-worthy classical-ML content emerges via atlas ingestion (decided: no dedicated ml-foundations pass). learn-ai-engineering feeds raw interview-prep content into librarian via compile-not-merge — librarian ingests, learn-ai-engineering points at wiki pages.
- The portfolio showcase layer waits until 2–3 repos are genuinely demo-ready — rooms before the front door.
- Measurement: the 6-pillar assessment framework (prompt → context → harness → loop → graph → eval) in learn-ai-engineering is a reusable instrument for scoring portfolio maturity. First run (2026-07-29): playground 14/18, listen-wiseer/librarian 12/18, atlas 11/18, sisyphus 4/18. The nesting rule — inner pillars cap outer — revealed that prompt/context at level 2 everywhere is the binding constraint, not harness or eval.

## Where Detail Lives (pointers, never copied here)

- Full portfolio state + tier tables: `~/workspace/portfolio.md` (human-owned; sessions flag staleness, don't edit)
- Live work state: each repo's `.claude/docs/plans/*.md` (Status lines) or Linear — /meta-wake reads fresh
- Tooling change state: `.sounding/tooling-ledger.md` (active) + `.sounding/tooling-ledger-log.md` (archive)

---

*Transformed by /meta-dream when portfolio understanding shifts — which projects exist, what they are, how they connect. Never carries work-queue state.*
