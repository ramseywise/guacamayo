---
name: project-contracts-rollout
description: SANYI/akira dev-tools rollout state (2026-07-17) — sanyi global + contracts drafted in 3 repos + review-skill enforcement + template seeding; akira blocked on hardcoded scan roots; Buyi interviews owed
metadata: 
  node_type: memory
  type: project
  originSessionId: 73f6b61f-286a-46fc-bc5b-a18d1d260fff
---

Executed 2026-07-17 (ledger row: sanyi promotion, 2026-07-17):
sanyi skill promoted to `~/.claude/skills/sanyi` (repo copies deleted in librarian/playground/atlas;
template vendored copy synced via sync-global-skills.sh — reverses rustling-squishing-pine's
"template-only" decision, user-approved). `SANYI.md` contracts drafted at playground/librarian/atlas
roots from declared conventions. review-pr + code-review reservoir skills now run the sanyi-review
protocol on diffs when SANYI.md exists (BY-* blocking, Debt silent, report-only). Template scaffolds
seeded `SANYI.md.jinja` (staged in `_scaffold/`, full renders only; ADK schema/tool-signature Jianyi
entries when adk_agent chosen). Librarian: SANYI wiki conflict resolved (Claim B/violations.md wins),
scraper repos.txt now lists 4 repos + akira-findings glob, 5 new wiki pages (rollout decision record,
3 system-design interview pages, code-review drill), learn-ai-engineering README points to them.

**Open:**
1. Buyi confirmation interviews — **playground DONE 2026-07-19** (ratified v2). Librarian + atlas
   still owed (drafted autonomously from CLAUDE.md rules; each file's header comment says so).
   Playground's interview found v1 was **false on arrival**, not merely unconfirmed: both guardrail
   pipelines had zero call sites (vendored via a template commit, never wired), three divergent
   per-agent reimplementations, `evidence: tests/smoke/` overstated (covered lg_agent only), and
   `RAG_GUARDRAILS_ENABLED` defaulted False. Also surfaced a BY-1 the contract hadn't looked for:
   accounting-domain strings in 4 files incl. shipped code (`adk_agent/gateway/main.py:115`).
   **Expect the same class of finding in librarian/atlas** — all three were drafted the same way,
   from declarations. Run their interviews with the fixed `/sanyi init` (step 2 verification,
   added 2026-07-20 — ledger row same date).
2. **Akira rollout blocked**: subagents hardcode `src/agents/*` scaffold paths
   (safeguard/schema_check jinja templates) — cannot scan librarian's app/etl/tools layout.
   Fix upstream: settings-driven scan roots in `template/_scaffold/{{ source_root }}/agents/akira/`,
   then re-pilot. Atlas has a dangling `.claude/skills/akira` (skill, no agent code).
3. Bulk ingest of the 241 scraped raw/repos files deferred to normal /ingest cadence.

**How to apply:** don't re-add sanyi copies to repo `.claude/skills/`; when asked to "review" in a
repo with SANYI.md, the contract check is part of the review protocol now. Link: [[project-librarian-dssg-extension]], [[project-config-layering]].
