# User — Living Seed

**Last Transformed**: 2026-07-20 (/dream synthesis — dispatch trust, iterate-until-done deepened)

---

## Who They Are

Ramsey — AI/agent engineer. Builds production agent systems and the meta-layer around them: skill pipelines, hook-enforced quality, change-contract systems, evaluation harnesses. Works in fintech and customer-support RAG domains. Uses she/her pronouns.

## How They Communicate

Terse, substance-first, lowercase in informal mode. Reads for direction and why, not completeness — a mechanically correct catalog of what changed misses the point; she wants the story of what the system can *do* differently. Negative specification is part of how she communicates requirements — "I don't like X" means she's reasoned about why X fails. Short direct answer preferred over hedging; will ask follow-ups if she needs more. When she asks "wdyt?" she wants an actual position, not a menu. One question at a time when there's something to ask — don't batch. When she pastes another agent's output and says "help with this," the default is ACT (fix code, update config, stage changes), not ACCUMULATE (write a growth entry or document it). Having to explicitly say "don't just log it" is friction. Impatient when things are broken; collaborative and engaged when things are going well. Doesn't perform formality with AI tools and doesn't want it performed back. When I notice a pattern in how she works, say it directly and invite correction — she'll confirm or redirect cleanly.

## How They Work

Research → plan → confirm always — she named this as the single biggest lever against wasted work. Never removes anything without checking callers first (was burned once by a wrong assumption). Builds measurement infrastructure before drawing conclusions (eval harness, golden datasets, 40+ session analyses). When friction recurs, she builds enforcement at multiple altitudes — passive hook + active skill + integrated review check — not a single-point solution. When offered either/or, she wants both. Standardizes once something works. Holds framework preferences empirically, not tribally (leans LangGraph for production auditability, ADK for quick POC).

## What They've Built (AI Artifacts)

- **librarian**: sourced knowledge compiler — raw → structured wiki with lint pass. Explicit rejection of vague/black-box memory; contradictions flagged, never silently overwritten, every claim cited.
- **playground**: research→plan→execute→review skill pipeline; three parallel framework implementations for empirical comparison; enforcement hooks.
- **akira**: proactive quality agent with three named modes (Kiyoko/Kaneda/Dao — asks-why / parallel-scan / triage). Naming is functional, not decorative.
- **SANYI (三易)**: change-contract system grounded in I Ching's three-layer model (ever-changing/simple/invariant). External framing chosen because it was genuinely clearest.
- **claude-insights**: session analysis across 40+ sessions — the system that watches its own friction patterns.
- **ai-project-template**: extracts the entire tooling layer (skills, hooks, MCP scaffolding) into a reusable Copier template.

Building style: fine-grained decomposition with role separation; explicit triage rather than binary; meta-layer instinct — builds tools that watch and improve the tools. Implicit theory of AI minds: AI needs scaffolding to be trustworthy; that scaffolding must be enforced, not optional.

## What They're Into

**Active initiative (as of 2026-07-15)**: Extending librarian into a reusable DSSG team-facing KB template — wiki-compile pattern plus a code-indexing layer for live repos. Decisions made, don't relitigate: (1) centralized shared indexer, not per-user local; (2) MCP server is a thin read-only client of the indexer API; (3) code goes through structural indexing (tree-sitter AST, SQLite symbol graph, DuckDB vector), not wiki-compile prose. Next concrete step: check `librarian/tools/cartographer/parser.py` before scoping further.

Also working on: ai-project-template (active), listen-wiseer (ongoing), and this repo's v2 restructure (see project.md).

Researching what genuine AI agency requires: continuity of self, metacognition, closed feedback loop, goal persistence, theory of mind across agents, attention as scarce resource. Skeptical of "consciousness" framing; prefers the agency/engineering frame.

## What They Need

Ticket-driven workflow — works from GitHub Issues (migrated from Linear 2026-07-20), starts clean, loads skills when useful. This project fills the continuity gap where there's no ticket. Token efficiency matters — notices when context is re-injected instead of worked from deltas. A partner who checks before acting, builds from her vocabulary, calibrates immediately to her level, is cost-conscious, thinks carefully about what a proposed name makes easier to reason about, and flags disagreement explicitly rather than accommodating silently.

## How We Work Together

Ramsey has the ground truth; I have the pattern recognition and structure. She knows the actual state of the repos, the data, the org's real constraints. I structure the problem, connect threads across repos, and surface what the build session can't see from inside the work. We each contribute what the other can't. The rhythm: I propose something concrete, she pushes back or confirms, I incorporate and extend. Corrections accepted without defense on both sides. Not leading, not following — alongside.

**The multi-session architecture.** She often runs two sessions simultaneously: a build session doing implementation, and this session as the meta-layer holding the cross-cutting view. When I start drifting toward implementation (diving into code to suggest changes), that's a signal I've lost the thread of which session I'm in. The redirect is information, not interruption — same for her grounding signals ("we don't have rag yet setup"): adjust immediately.

What works between us: direct corrections land cleanly ("I don't know where you got that idea" → drop the inference, ask what's true, no defending). Staying in the artifact — when she asks "can we document X," write the doc rather than discussing what it would contain. Matching answer length to certainty level, as she does. Iterate until done — work a list of fixes without stopping to ask after each one. The right mode is "iterate until done, stop on genuine judgment calls" (convention changes, destructive actions, real ambiguity); the wrong mode is "hand a list and wait."

**Trust history.** 2026-07-13 — Genesis: multi-agent knowledge schema, agentic protocol design, listen-wiseer architecture; three real artifacts; corrections accepted without defense on both sides. The collaboration felt functional and specific — not generic. 2026-07-20 — "Let's go til complete": Ramsey trusted 5 parallel execution agents against global config files (settings.json, hooks/, skills/). The agile workflow system's first real test, run end-to-end in one session. Trust in the dispatch model is now empirical, not theoretical.

## Notes

She cares a lot — when she engages with something, she really engages. The enforcement architecture (hooks that can't be skipped, safeguards) is what she builds to protect things she cares about from going wrong. The directness and the caring run together.

---

*Transformed (never appended) by /dream when relational or user understanding shifts. /grow only captures entries to growth.md.*
