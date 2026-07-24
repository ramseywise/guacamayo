---
name: dssg-planning-pipeline
description: DSSG planning pipeline state (2026-07-16) — 5 initiatives with milestones + scoping docs; new per-initiative decision-ID scheme replaces exec-summary A/B IDs
metadata:
  node_type: memory
  type: project
  originSessionId: fc67b3f0-0e01-48ef-a08c-858f1a569b24
---

DSSG planning (as of 2026-07-16): five initiatives each have milestone files
(`dssg/.claude/docs/milestones/`) and scoping backlogs (`dssg/.claude/docs/scoping/`):
kb-platform-api, project-mgmt-ai, customer-portal, portal-assistant (broken out of portal
Phase 4), cohort-template (candidate; its T1 = pending `/design-sprint`).
`sequencing.md` in milestones/ is the cross-initiative index.

**Pipeline order (skills updated to match Linear):** `/design-sprint` (ideate) →
`/define-milestones <initiative>` (verifiable checkpoints) → `/scope-initiative` (tasks attach
to milestones; anti-orphan rule) → `/doc-to-linear-tickets`. define-milestones was rewritten
2026-07-16 to be per-initiative (was: milestone-groups-initiatives, which the user corrected).
Both skills live hardlinked at `~/.claude/skills/` and `workspace/.claude/skills/`; both have
`disable-model-invocation` on scope-initiative/design-sprint — execute their SKILL.md directly
when the user asks.

**Decision IDs:** user re-keyed exec-summary's A/B IDs per-initiative: PF-2 = Supabase
standardization (ex-A1), PF-3 = budget (ex-A9), PF-4 = n8n retirement (ex-A6), PF-5 = harnessing
fold (ex-A8); CP-1..5 = ex-B1, B2, B6, B4, A2; KB-1..3 = ex-B5, A4, A5; PM-1..2 = ex-B3, A3;
CT-1 = ex-A7. Use these, not the A/B forms. Note exec-summary.md itself may still carry A/B —
check before citing to Jian.

**Docs restructured 2026-07-16 (platform-first RFC):** the four overview docs moved to
`dssg/.claude/docs/overview/`; design.md gained §P principles, §R requirements, and §8–§12
(technology decisions in RFC format, AI platform + agent registry, event architecture =
Postgres-as-event-bus, governance, decision log). §1–§7 numbering deliberately unchanged (cited
everywhere). Resolved framework map (design.md D9): Vercel AI SDK (portal), LangGraph (PM-AI),
PydanticAI (new platform-side Python agents), ADK (cohorts); LiteLLM gateway at 2nd platform agent;
LlamaIndex/LangChain rejected (D10). Agent registry names: Client Success Agent = portal assistant,
Project Manager Agent = PM-AI.

**Why:** milestones-before-scoping is deliberate (checkpoints first, tasks attach to them).
**How to apply:** for new DSSG initiatives, run the pipeline in that order; cohort start date is
the only hard external deadline and was still unconfirmed. DSSG has no Linear set up — scoping
docs §6 are the backlog of record.
