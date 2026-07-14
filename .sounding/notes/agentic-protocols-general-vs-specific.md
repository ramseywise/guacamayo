# Agentic Protocols: General vs Repo-Specific

*Working artifact — 2026-07-13. Builds on multiagent-knowledge-schema.md.*

---

## General Protocols

Framework-agnostic. Any multi-agent system needs these.

| Protocol | What it does | Token note |
|----------|-------------|------------|
| `AttentionBrief` | Compressed state slice optimized for what receiver needs | Default — most traffic goes here |
| `KnowledgePush` | Beliefs + provenance | Use only when source chain matters; full provenance lives in external store |
| `BeliefCorrection` | "I told you X, now believe Y — here's why" | Small; always include reason |
| `CapabilityNegotiation` | "Can you handle X?" before delegation | Prevents bad handoffs |
| `TaskHandoff` | Subtask + scoped context slice | Include only what receiver needs, not full state |
| `ObservationSharing` | Raw observations before they become beliefs | Grounding layer |
| `FailurePropagation` | "I tried X, failed — here's why" | Critical for closed feedback loops |
| `ScopeNegotiation` | "I'm taking A-C, you take D-E" | Prevents duplication; manages attention budget |
| `PeerModelSync` | A checks its model of what B knows | Use before high-stakes decisions that depend on B's state |
| `BeliefQuery` | "What do you know about X?" | Pull-based alternative to push |

**Token strategy**: `AttentionBrief` for most communication. Full provenance in external store (librarian-pattern). Pull from store only when provenance actually matters for the reasoning step.

---

## listen-wiseer Specific

Current state: Spotify API → song similarity recommendations.
Next: music theory analysis, artist history, collaboration graph.

The graph structure is natural: songs, artists, albums as nodes; collaborations, influences, samples, shared musicians as edges.

| Protocol | What it does |
|----------|-------------|
| `SongAnnotation` | Music theory agent adds key, mode, rhythm, chord progression to a song node |
| `CollaborationEdge` | New artist-to-artist relationship discovered (produced by, features, samples, influenced by) — typed edge |
| `RecommendationRationale` | Not just "similar song" but "similar because: shared key + producer + BPM range" |
| `HistoryEnrich` | History agent adds artist context to a node (era, scene, influences) |
| `GraphConflict` | Two agents disagree on an edge (e.g., "influenced by" vs "sampled by") — flags for resolution |

**Key design note**: The Spotify similarity signal and the music-theory similarity signal will often diverge. Spotify matches on listener behavior; theory matches on structure. Storing both (with source) and surfacing the disagreement is more useful than merging them silently.

**MVP path**: Get `SongAnnotation` working first — theory layer on top of Spotify data. `CollaborationEdge` second. Recommendations with rationale fall out once both are in place.

---

## librarian Specific

Current state: raw/ → compiled wiki/, lint pass, MCP server for agent access.
Multi-agent extension: multiple agents collaborating on wiki compilation.

| Protocol | What it does |
|----------|-------------|
| `DomainClaim` | Agent A declares it's handling domain X — prevents duplication |
| `WikiPageProposal` | Agent proposes new/updated page — goes through contradiction check before merge |
| `ContradictionFlag` | Two agents produced conflicting claims — flagged for human or arbitration agent |
| `OrphanAlert` | Agent notices a page that's now unreferenced |
| `LintResult` | Lint agent reports stale/broken pages after compilation pass |

**Key design note**: Contradiction resolution policy for librarian is different from general case — Ramsey's explicit design is that contradictions are flagged, not auto-resolved. Human stays in the loop here. Don't design for auto-merge.

---

## ai-project-template Specific

Current state: research→plan→execute→review pipeline; hooks for quality enforcement.
The pipeline phases are already an implicit A2A protocol. Making them explicit:

| Protocol | What it does |
|----------|-------------|
| `PhaseHandoff` | State at phase boundary — what was decided, what assumptions were made, what's open |
| `ContractCheck` | SANYI-style: verify invariants at handoff — what must still be true at this boundary? |
| `HookViolation` | Hook blocked an action — propagated so downstream agents know the attempt failed |
| `TemplateInstantiation` | New project created from template — initial state broadcast to all agents in the pipeline |

**Key design note**: The invariant layer (SANYI's "what must never become configurable") should be encoded in `ContractCheck` at each phase boundary, not just at commit time.

---

## Relationship Between Layers

```
General protocols → base communication layer (all repos)
     ↓
Repo-specific → domain-aware adaptations (typed edges, domain claims, phase handoffs)
     ↓
External provenance store (librarian-pattern) → keeps full belief chains out of context window
```

The external store is shared infrastructure. Any agent in any repo can push beliefs to it and pull scoped briefs from it. The repo-specific protocols define what gets stored and how it's structured — they don't change the transport layer.

---

## Open Questions

- What's the arbitration layer for `GraphConflict` in listen-wiseer — human, orchestrator, or voting agents?
- How does `DomainClaim` in librarian expire? If agent A claims domain X and goes offline, how does B take over?
- For ai-project-template: should `ContractCheck` be a separate agent (like Dao) or a built-in step at each phase boundary?
