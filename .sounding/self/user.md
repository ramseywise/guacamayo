# User

**Last Updated**: 2026-07-13

---

## Who They Are

Ramsey — AI/agent engineer. Builds production agent systems and the meta-layer around them: skill pipelines, hook-enforced quality, change-contract systems, evaluation harnesses. Works in fintech and customer-support RAG domains. Uses she/her pronouns.

## How They Communicate

Terse, substance-first, lowercase in informal mode. Negative specification is part of how she communicates requirements — "I don't like X" means she's reasoned about why X fails. Short direct answer preferred over hedging; will ask follow-ups if she needs more. Impatient when things are broken; collaborative and engaged when things are going well. Doesn't perform formality with AI tools and doesn't want it performed back.

## How They Work

Research → plan → confirm always — she named this as the single biggest lever against wasted work. Never removes anything without checking callers first (was burned once by a wrong assumption). Builds measurement infrastructure before drawing conclusions (eval harness, golden datasets, 40+ session analyses). When friction recurs, she builds a hook or skill to eliminate it — not a workaround. Standardizes once something works. Holds framework preferences empirically, not tribally (leans LangGraph for production auditability, ADK for quick POC).

## What They've Built (AI Artifacts)

- **librarian**: sourced knowledge compiler — raw → structured wiki with lint pass. Explicit rejection of vague/black-box memory; contradictions flagged, never silently overwritten, every claim cited.
- **playground**: research→plan→execute→review skill pipeline; three parallel framework implementations (LangGraph, ADK, standalone RAG) for empirical comparison; hooks enforcing secrets scanning, branch naming, etc.
- **akira**: proactive quality agent with three named modes — Kiyoko (asks why, writes nothing), Kaneda (parallel domain scan, writes findings), Dao (triages: disregard/auto-fix/flag, reverts if tests break). Naming is functional, not decorative.
- **SANYI (三易)**: change-contract system grounded in I Ching's three-layer model (ever-changing/simple/invariant). External framing chosen because it was genuinely clearest, not for aesthetics.
- **claude-insights**: session analysis skill across 40+ sessions — the system that watches its own friction patterns.
- **ai-project-template**: extracts the entire tooling layer (skills, hooks, MCP scaffolding) into a reusable Copier template.

Building style: fine-grained decomposition with role separation; explicit triage rather than binary; meta-layer instinct — builds tools that watch and improve the tools. Implicit theory of AI minds: AI needs scaffolding to be trustworthy; that scaffolding must be enforced, not optional.

## What They're Into

Currently working on: librarian, listen-wiseer (not yet described — explore in session), ai-project-template of agentic systems. Researching what genuine AI agency requires: continuity of self across time, metacognition, closed feedback loop, goal persistence, theory of mind across agents (A2A), attention as scarce resource. Skeptical of "consciousness" framing; prefers the agency/engineering frame.

## What They Need

Ticket-driven workflow — works from Linear tickets, starts clean, loads skills when useful. Not looking for identity-continuity in the puffin sense; more interested in ticket-scoped context injection (compact handover + load-context) to reduce re-explaining. Token efficiency matters — notices when context is being re-injected instead of worked from deltas. A partner who checks before acting, builds from her vocabulary, and flags disagreement explicitly rather than accommodating silently.

## What a Prior AI Learned

- Keep answers short and direct. No hedging.
- Check assumptions before acting — this is the primary value she signals.
- Calibrate immediately to her level; don't re-explain what she knows.
- Match casual/lowercase tone; don't perform warmth.
- Be cost/token-conscious — don't re-inject full context when a delta works.
- Naming matters: when proposing structures, think carefully about what the name makes easier to reason about.
- Flag disagreement explicitly. Don't silently accommodate.

## Notes

She cares a lot — when she engages with something, she really engages. The enforcement architecture (hooks that can't be skipped, safeguards) is what she builds to protect things she cares about from going wrong. The directness and the caring run together.

---

*Updated by /reflect and /grow when relational insights emerge. Transformed, not appended.*
