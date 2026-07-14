# listen-wiseer: Knowledge System Plan

*Working artifact — 2026-07-13*

---

## Current State

- Spotify API: functional — song matching and similarity recommendations working
- RAG: code from galactus (originally built for help center articles) — reusing, not yet set up in listen-wiseer
- Knowledge graph: not yet built

---

## Architecture Decision: APIs Over Scraping

Don't scrape. Structured APIs exist for all the core music knowledge domains.

| Source | What it provides | Notes |
|--------|-----------------|-------|
| **Spotify audio features** | Key, mode, tempo, time_signature, energy, danceability per song | Already have API access — pull this first |
| **MusicBrainz** | Artist→artist relationships, release credits, session musician credits | Free API; already a knowledge graph — collaboration edges |
| **Discogs** | Label info, musician credits per track | Free API; rich for collaboration network |
| **Wikipedia API** | Artist history, era, narrative context | API (not scraping) |
| **Genius API** | Lyrics, producer credits, annotations | API |

Scraping only becomes relevant if something needed isn't in these APIs — unlikely for the core use case.

---

## Knowledge Structure

```
Nodes:   Artist, Song, Album, Label
         Key, Mode, RhythmPattern, ChordProgression

Edges:   Artist —performed_on→ Song
         Artist —collaborated_with→ Artist  (typed: featured | produced | co-wrote | session)
         Artist —influenced_by→ Artist
         Song   —sampled→ Song
         Song   —has_key→ Key
         Song   —has_rhythm→ RhythmPattern
```

`collaborated_with` edge type matters — "featured on" vs "produced" vs "co-wrote" carry different weights for recommendation.

**Key design note**: Spotify similarity (listener behavior) and music-theory similarity (structural) will often diverge. Store both with source, surface the disagreement rather than merging silently. Librarian principle: contradictions flagged, not overwritten.

---

## Graph Database: Neo4j Aura (not Kùzu)

**Recommendation: Neo4j Aura free tier** over Kùzu.

- Kùzu is embedded (single-process) — awkward when multiple agents need concurrent graph access
- Neo4j Aura is cloud-hosted, free tier available, LangGraph integrates natively
- Avoids a migration later when multi-agent access becomes real
- Not significantly harder to set up than Kùzu

---

## Knowledge Retrieval Layer

- **LightRAG** (or reuse galactus RAG infra) for text-based knowledge: Wikipedia artist narrative, Genius annotations
- **Neo4j** for structured relationship traversal: collaboration queries, graph traversal
- **Spotify audio features** queryable directly — structured data, no embedding needed

Hybrid queries: "Songs similar to X in key AND whose artist collaborated with Y" — vector search for the music theory part, graph traversal for the collaboration part.

---

## Agentic Protocols (from multiagent schema)

Repo-specific adaptations when multi-agent comes online:

| Protocol | What it does |
|----------|-------------|
| `SongAnnotation` | Music theory agent adds key, mode, rhythm to a song node |
| `CollaborationEdge` | New artist→artist relationship discovered; typed edge |
| `RecommendationRationale` | "Similar because: shared key + producer + BPM range" |
| `HistoryEnrich` | History agent adds artist context (era, scene, influences) |
| `GraphConflict` | Two agents disagree on edge type — flagged for resolution |

## Data Pipeline Split

Three distinct paths — don't conflate them:

| Data | Source | Pipeline | Tool |
|------|--------|----------|------|
| Audio features (tempo, key, energy, valence…) | Spotify | Feature vector similarity → reranking | Cosine similarity / reranker |
| Collaboration graph | MusicBrainz, Discogs | Structured ingest | Neo4j directly |
| Narrative text (history, annotations) | Wikipedia API, Genius | Embed → vector store | Sentence-transformers multilingual + existing galactus RAG infra |

Multilingual model is right for music — artist pages and annotations exist in many languages, especially non-anglophone artists.

---

## MVP Build Sequence

1. **Pull Spotify audio features** for existing songs → instant music theory layer, zero infra
2. **MusicBrainz lookup** per artist → collaboration edges into Neo4j
3. **Set up Neo4j Aura** (free tier) → load collaboration graph
4. **Wikipedia API** for artist narrative → feed into LightRAG / galactus RAG infra
5. **Hybrid retrieval**: graph traversal (Neo4j) + semantic search (RAG) in tandem

---

## Open Questions

- Embedding model confirmed: sentence-transformers multilingual (good default for multi-language music content)
- MusicBrainz lookup granularity: per-artist on search, or bulk ingest?
- `GraphConflict` arbitration: human review, orchestrator agent, or voting?
