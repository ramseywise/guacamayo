# Handover — 2026-07-19 Interview Rounds Restructure

**Context**: Restructuring `learn-ai-engineering/interviewing/rounds/` from flat `.md` files into folder-per-round format with README, questions, sources, study-guide, and examples.

## Current State

All 10 interview rounds are now structured folders. 78 markdown files across 19 directories. No flat files remain.

- **code-review-round** and **system-design-round** — done in prior session, including portfolio case study examples (support-agent, forecasting-agent, meeting-processor, accounting-assistant)
- **behavioral, case-study, coding-challenge, customer-simulation, leadership-rounds, project-deep-dive, recruiter-screen, technical-questions** — done this session via 8-way sonnet agent fan-out
- Two rounds intentionally have no `examples/`: recruiter-screen (too light) and technical-questions (questions.md IS the worked content)
- Earlier today (prior session, pre-compact): experiment tracking wired into skills chain, /grow broadened, README updated with v2→v3 narrative

## Decisions Made

- Examples = real systems / realistic walkthroughs; topics = study-guide + questions + sources
- Sonnet agents for bounded execution — each got full source content in prompt, no discovery needed
- No `-round` suffix on the 8 new folders (only code-review-round and system-design-round have it from prior session)

## Open Threads

- Naming inconsistency: `code-review-round`/`system-design-round` vs `behavioral`/`case-study`/etc. — rename for consistency?
- Cross-references between rounds may still use old flat-file paths
- Content quality review of agent-generated material not yet done
- `interviewing/rounds/` parent README may need updating for new folder structure
- **From earlier today**: librarian rebase error still pending; atlas PR #4 still open; template steps 5-7 threads

## Immediate Next Steps

1. Spot-check 2-3 agent-generated files for quality/voice consistency
2. Fix any broken cross-references between rounds (old `.md` paths → new folder paths)
3. Update `interviewing/` parent README if it references the old flat files
4. Consider renaming `code-review-round` → `code-review` and `system-design-round` → `system-design`

## Key Files

- `~/workspace/learn-ai-engineering/interviewing/rounds/` — all 10 round folders
- `~/workspace/learn-ai-engineering/interviewing/README.md` — parent index
- `guacamayo/.sounding/growth.md` — 4 entries pending (including fan-out pattern confirmation)
