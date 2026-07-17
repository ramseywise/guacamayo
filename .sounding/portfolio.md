# Portfolio — Living Seed

**Last Transformed**: 2026-07-17 (replaces the single-repo project.md — seed 3 is the portfolio view: what every active project IS and how they connect. Work state stays in per-repo plans; detail lives in `~/workspace/portfolio.md` (human-owned).)

---

## The Map

**Flagship (recurring research→plan→execute→review cadence)**
- **listen-wiseer** — Spotify copilot: LangGraph agent, GMM/LightGBM recommender, agentic web search, langmem. The best-documented repo; Phase 8 (RAG right-sizing) landed.
- **atlas** — agentic financial intelligence for B2B: LangGraph forecast/segment/knowledge agents, Neo4j, real eval harness. Bridges the classical-ML and agentic eras natively.

**Meta / tooling / knowledge (supports everything else)**
- **guacamayo** (this repo) — the Sounding instance + persistence KB. The meta-layer session lives here; v2 = 3 seeds, single-writer lifecycle, feedback loop wired to `~/.claude` (retro + ledger) and librarian. KB half still unscoped — Ramsey's call.
- **librarian** — sourced knowledge compiler (raw → wiki, conflict-flagged, cited) + MCP + code index. The system of record for factual session history; being extended into a DSSG team-facing KB template (indexer decisions made — don't relitigate).
- **playground** — the R&D lab: three parallel agent implementations over a shared KB; patterns prove out here before migrating to flagships.
- **ai-project-template** — Copier template extracting the tooling layer; owns its own discovery stack (scope-poc, project-discovery, project-genesis) by design — kept its own thing, not globalized.

**Domain case studies (dated or blocked)**
- **lebanese-blonde** — 2020 credit-risk model getting a full in-place facelift; Phase 0 (tooling + bugfixes) executed, needs its own dedicated cycles. Pairs with atlas: same domain five years apart — supervised ML then, agentic orchestration now. That narrative is worth building.
- **NRR** — nutrition/cycle-tracking recommender; blocked on de-identifying personal health data.

**Learning archive** — `Python/` (5-category reorg done), small showcase repos; First-Flask-App scoped as the connective "what I've been learning" front door — sequenced AFTER flagships are demo-ready, not before.

**DSSG (NYC-DSSG platform work)** — nonprofit client engagement + volunteer tooling. Constraint that shapes every recommendation: volunteer-maintained, near-zero budget, high turnover — boring and well-documented beats clever.

## Threads Between Projects

- The tooling loop: playground proves → ai-project-template extracts → every repo consumes; guacamayo sessions run the cross-cutting view; /retro + ledger graduate learnings to `~/.claude`.
- Knowledge: librarian compiles everything factual; wiki-worthy classical-ML content emerges via atlas ingestion (decided: no dedicated ml-foundations pass).
- The portfolio showcase layer waits until 2–3 repos are genuinely demo-ready — rooms before the front door.

## Where Detail Lives (pointers, never copied here)

- Full portfolio state + tier tables: `~/workspace/portfolio.md` (human-owned; sessions flag staleness, don't edit)
- Live work state: each repo's `.claude/docs/plans/*.md` (Status lines) or Linear — /wake reads fresh
- Tooling change state: `~/.claude/docs/tooling-ledger.md`

---

*Transformed by /synthesize when portfolio understanding shifts — which projects exist, what they are, how they connect. Never carries work-queue state.*
