# Handover — 2026-07-20 Playground SANYI Cleanup + CI Fix

**Context**: Playground repo maintenance — closing SANYI contract violations (BY-2, BN-1, JY-1) and fixing a broken CI pipeline.

## Current State

**All requested work complete.** Three rounds of playground fixes:

1. **Test-runner alignment**: Added `"evals"` to `pyproject.toml` pytest pythonpath — `uv run pytest` now resolves eval imports by construction.
2. **BY-2 closed**: Removed `RAG_GUARDRAILS_ENABLED` flag from config.py, main.py, docker-compose.yml. Rag guardrail middleware is now unconditional. Test rewritten to not depend on flag.
3. **7 BN-1 fixes**: Inline prompts relocated to files (lg_agent generate, llm_classifier), model strings replaced with `resolve_model_id()` (4 ADK files), threshold made env-driven.
4. **CI rewritten**: Removed 3 jobs referencing deleted paths (support_agents, hc_rag, Dockerfiles). Fixed PYTHONPATH and uv sync args.
5. **SANYI.md v3**: Budgets updated, debt cleared/added, migration recorded.

Verification: 264 tests passed, 6 skipped, ruff clean.

**Uncommitted**: guacamayo only (this session's /grow + /dream artifacts). playground, librarian, ai-project-template all committed.

## Decisions Made

- Refused to delete `src/guardrails/language.py` — verified it's actively imported by all 3 agents via `guardrails/__init__.py`. Another agent's claim of "zero importers" was wrong.
- ADK `Agent()` takes model strings, not LangChain objects — used `resolve_model_id()` not `resolve_chat_model()`.
- BY-4 output guardrail pipeline left as standing debt (zero call sites, needs design decision).
- BY-3 history sweep left as owner decision (Ramsey).

## Open Threads

- Standing SANYI debt: BY-4 output guardrail (no call sites), BY-3 history sweep
- Playground RAG experiments E3-E6 still viable but lower priority
- ai-project-template worktree branches from earlier session need merging

## Immediate Next Steps

1. Ramsey reviews and commits playground changes
2. Ramsey reviews and commits librarian changes
3. ai-project-template worktree merge from earlier session
4. Next substantive work: DSSG or playground RAG experiments

## Key Files

- `playground/pyproject.toml`
- `playground/src/agents/rag_agent/config.py`
- `playground/src/agents/rag_agent/main.py`
- `playground/src/agents/adk_agent/agent.py`
- `playground/src/agents/adk_agent/sub_agents/direct_agent.py`
- `playground/src/agents/adk_agent/sub_agents/rag_agent.py`
- `playground/src/agents/adk_agent/app.py`
- `playground/src/agents/lg_agent/graph/nodes/generate.py`
- `playground/src/agents/lg_agent/prompts/generate.txt`
- `playground/src/guardrails/llm_classifier.py`
- `playground/src/prompts.py`
- `playground/.github/workflows/ci.yml`
- `playground/SANYI.md`
- `playground/tests/smoke/test_rag_guardrail_middleware.py`
