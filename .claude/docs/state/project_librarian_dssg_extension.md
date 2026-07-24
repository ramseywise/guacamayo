---
name: project-librarian-dssg-extension
description: Plan/decision context for extending librarian into a reusable DSSG knowledge-base template that houses both compiled wiki knowledge and code/vector/graph indexes for real repos
metadata:
  node_type: memory
  type: project
  originSessionId: 375f1cfb-f126-468e-890b-e09a210aa4cf
---

As of 2026-07-15, user is evaluating the [librarian](file:///Users/wiseer/workspace/librarian) repo (personal Karpathy-style compiled wiki, see [[research-agentic-kb-for-code]]) with the goal of templating it out for DSSG (a team/org context) so other people can stand up a knowledge base that houses both:
1. The existing compiled-wiki pattern (raw/ → Claude compiles → wiki/ prose, for design decisions/patterns)
2. Vector DB / knowledge graph indexing over **actual live repositories** — a capability librarian doesn't have yet (it only compiles curated markdown, not source code)

**Why:** Librarian's current ingest model is right for accumulated design knowledge but wrong for live source code — see [[research-agentic-kb-for-code]] for why (2025-2026 field consensus moved to AST/symbol-level indexing + agentic grep-first retrieval, not LLM-paraphrased prose, for code).

**Open question raised by user:** whether to expose the new code-index capability via MCP (consistent with librarian's existing `app/mcp_server/server.py` pattern) or something else, because MCP setup/auth friction may be harder for less technical DSSG users than for the original single-user tool. User is unsure what the actual data-access setup burden would look like for a team rollout (auth, per-repo indexing, who runs the indexer, etc.) — this is unresolved, not yet decided.

**Direction discussed but not yet committed:** rather than forcing code through the wiki-compile step, add a separate ingestion/index path (e.g. `wiki/code-index/` or a standalone DuckDB table) using tree-sitter symbol parsing + lightweight SQLite/DuckDB symbol graph (Aider-style), git-hook-triggered incremental updates — reusing patterns already in `tools/cartographer/parser.py` and `app/backend/embeddings.py` rather than introducing Neo4j. Next step flagged: check what `tools/cartographer/parser.py` (868 lines) already parses before scoping further, since it may already be partway to this.

**Checked 2026-07-17:** `tools/cartographer/parser.py` (832 lines) is NOT a code parser — it's a session-JSONL usage analyzer, a richer fork of the global `~/.claude/scripts/insights.py` (adds cache read/write tokens, model distribution, skill invocations, bash antipatterns, read/edit ratio, hook blocks). So it contributes nothing to the code-index scoping; tree-sitter work lives in `tools/codemap/` instead. Side finding: insights.py and cartographer/parser.py were drifting forks of the same session-stats engine. **Consolidated 2026-07-17:** cartographer/parser.py is canonical; `~/.claude/scripts/insights.py` is now a forwarding shim (`uv run --project ~/workspace/librarian python -m tools.cartographer`). New cost-weighted signals added (context buckets incl. >150k share, subagent transcript attribution, parallelism by usage, cache savings, per-skill cost share, compact counts) with unit tests in `tests/unit/test_cartographer_parser.py`. Validation: local dry-run reproduced official report's 63% >150k figure (got 64%).

**How to apply:** When resuming this work, don't re-litigate the "wiki-compile vs. structural code index" split — that's decided per the research memory.

**Decided 2026-07-15:** indexing model for the DSSG team KB is **centralized/shared**, not per-user local. One service (CI job, cron, or git-webhook-triggered) owns running the indexer against team repos and holds the repo read credentials — individual team members never run `/ingest` or need repo access themselves. Implication: the code-index layer should be architected as a standalone indexer + query API (probably a small FastAPI service, following the existing `app/backend/main.py` pattern) writing to a shared DuckDB (watch for single-writer contention if indexing many repos concurrently — may need Postgres+pgvector if that becomes real) rather than embedding indexing logic directly into the MCP server. The MCP server becomes a thin read-only client of that API, which is what individual DSSG members point their MCP config at — this is what actually removes the friction, not the choice of MCP itself. Still open: where the shared index/service physically lives (shared volume, S3-synced file pulled on startup, or a hosted API) — an infra decision to make when scoping deployment, not blocking the architecture work.
