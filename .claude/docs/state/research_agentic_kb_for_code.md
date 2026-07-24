---
name: research-agentic-kb-for-code
description: "2025-2026 patterns for agentic knowledge bases over live source repos (AST chunking, code graphs, agentic retrieval, incremental indexing) — researched while evaluating librarian repo for DSSG use"
metadata:
  node_type: memory
  type: reference
  originSessionId: 375f1cfb-f126-468e-890b-e09a210aa4cf
---

Research pulled 2026-07-15 while assessing [[librarian-repo-engineering]] and scoping a DSSG-facing knowledge base template. Full agent report preserved below since the user flagged it as important to keep.

## Why this matters for librarian/DSSG

Librarian's ingest model (raw/ → Claude compiles → wiki/ prose pages) is well-suited to curated design knowledge (decisions, patterns) but is the **wrong model for live source code** — you don't want an LLM paraphrasing source into wiki prose; you want structural, precise, always-current retrieval. This split is validated by where the field moved in 2025-2026, not just a hunch — see point 3 below on Anthropic pulling vector search out of Claude Code itself in favor of grep/glob loops.

## Summary by area

**1. Code-aware chunking & indexing** — Fixed-size/line chunking breaks functions mid-body. 2025 consensus: AST-based structural chunking. **cAST** (CMU, EMNLP Findings 2025, `astchunk` on PyPI) recursively splits large AST nodes, merges siblings within a token budget. **Tree-sitter** is the near-universal parser backbone (multi-language, incremental). Symbol-level indexing — function/class as the retrieval unit, with signature + docstring + byte/line range + scope chain — is standard practice now. Call-graph/import-graph extraction is a separate pass on top of the AST.

**2. Knowledge graph vs vector DB vs hybrid for code** — Pure vector search underperforms on code: semantic similarity doesn't capture structural relevance (caller/callee can be textually dissimilar). **RepoGraph** builds a repo-level code graph, retrieves k-hop ego-graphs around key symbols, combines with BM25. **CodexGraph** / **Code Graph Model (CGM)** bridge LLMs to graph DBs for repo-level SWE tasks. **Sourcegraph Cody** historically combined embeddings + SCIP (successor to LSIF) precise def/ref lookups + reranking, though Sourcegraph has been de-emphasizing embeddings for code-graph/search signals. **Aider's repo-map** is the lightweight pattern worth emulating at small-team scale: tree-sitter tag extraction → directed multigraph of file-to-file symbol references → personalized PageRank (weighted by chat-mentioned identifiers) → top-ranked defs rendered as an elided map within a token budget. Verdict: full property graphs (Neo4j etc.) pay off at large multi-repo/monorepo scale or when precise "what calls this" queries matter a lot; below that, a lightweight symbol graph (Aider-style, in SQLite) plus FTS/embeddings hybrid is sufficient.

**3. Agentic retrieval patterns** — Dominant 2025-2026 shift: away from pre-built vector indexes, toward agentic/tool-based search. **Anthropic removed vector search from Claude Code in 2025** in favor of grep/glob-driven iterative exploration — reported to outperform on precision (exact match vs fuzzy embeddings), freshness (no index drift during active edits), and simplicity. An Amazon Science AAAI 2026 paper found agentic keyword search reaches ~94.5% of RAG faithfulness with zero vector store. Pattern: agent issues grep/glob/read calls, follows imports/call edges for multi-hop reasoning, self-corrects by re-querying (CRAG-style, implemented via tool loops not a trained evaluator). Aider/Continue.dev/Cursor still combine embedding search with keyword/exact-match tools and reranking. Query decomposition and multi-hop over call graphs matter most for repo-level tasks (cross-file refactors, "what breaks if I change X") — single-file Q&A rarely needs it.

**4. Freshness/incremental indexing** — Key divergence from doc/wiki ingestion (append-only, human-curated cadence): code indexes must track fast-moving git history. **Cursor** computes a Merkle tree over the workspace; syncs walk only branches whose hashes differ, re-embedding only changed files (~5 min periodic resync). **Continue.dev** uses content-hashed incremental indexing with a debounced file watcher. General pattern: git post-commit hook or file-watcher → targeted re-chunk (AST) → re-embed only changed chunks → delete/upsert into vector index (not full rebuild) → update graph edges for changed imports. "Staleness envelopes" (metadata flagging index drift from HEAD) are an emerging practice. Full reindex reserved for schema/parser changes.

**5. Practical stack for a small team** — Don't reach for Neo4j/full graph DB unless multi-repo blast-radius queries or CodeQL-style structural analysis is needed — complexity rarely pays off below that scale. Reasonable stack: **tree-sitter** parsing → **cAST/astchunk** structural chunking → **SQLite or DuckDB** for symbol metadata + FTS5/BM25 → **local embedding model** (all-MiniLM-L6-v2, nomic-embed-text via Ollama) into a lightweight vector store (LanceDB, sqlite-vec, DuckDB VSS) for semantic fallback → simple file/symbol-level reference graph (Aider-style PageRank, stored as edges in SQLite) rather than a full graph DB → git hook/watcher for incremental re-chunk/re-embed on changed files only. Wrap retrieval in an agent loop that prefers grep/symbol-graph lookups first, falls back to embedding search for fuzzy/conceptual queries.

## Sources
- cAST: Structural Chunking via AST (EMNLP Findings 2025) — https://aclanthology.org/2025.findings-emnlp.430/ , arXiv https://arxiv.org/abs/2506.15655
- astchunk toolkit — https://github.com/yilinjz/astchunk
- Supermemory code-chunk: AST-Aware Chunking — https://supermemory.ai/blog/building-code-chunk-ast-aware-code-chunking/
- Retrieval-Augmented Code Generation Survey (repo-level) — https://arxiv.org/pdf/2510.04905
- RepoGraph — https://arxiv.org/html/2410.14684v1
- CodexGraph — https://arxiv.org/pdf/2408.03910
- Code Graph Model (CGM), OpenReview — https://openreview.net/forum?id=b98ODdeYq5
- How Cody understands your codebase (Sourcegraph) — https://sourcegraph.com/blog/how-cody-understands-your-codebase
- Aider: Building a better repo map with tree-sitter — https://aider.chat/2023/10/22/repomap.html
- Aider repository map docs — https://aider.chat/docs/repomap.html
- How Cursor Indexes Codebases Fast — https://read.engineerscodex.com/p/how-cursor-indexes-codebases-fast
- Securely indexing large codebases (Cursor) — https://cursor.com/blog/secure-codebase-indexing
- Claude Code Doesn't Index Your Codebase — https://vadim.blog/claude-code-no-indexing/
- Agentic Search Over Vector Embeddings pattern — https://github.com/nibzard/awesome-agentic-patterns/blob/main/patterns/agentic-search-over-vector-embeddings.md
- Corrective RAG (CRAG) overview — https://www.emergentmind.com/topics/corrective-retrieval-augmented-generation-crag
- Continue.dev Codebase Indexing docs — https://docs.continue.dev/features/codebase-embeddings
- Codebase-Memory: Tree-Sitter Knowledge Graphs via MCP — https://arxiv.org/pdf/2603.27277
- RAG Freshness Problem: Stale Embeddings — https://tianpan.co/blog/2026-04-10-rag-freshness-problem-stale-embeddings-silent-failure
- Incremental Indexing Strategies for RAG — https://medium.com/@vasanthancomrads/incremental-indexing-strategies-for-large-rag-systems-e3e5a9e2ced7
