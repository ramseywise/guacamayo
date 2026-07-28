# Agent-Quality Dimension Checklist

Agent: `scan-agent-quality` | ID prefix: `AQ-` | Conditional (agent code only)

Used by: `review/scan/agents/agent-quality.md`

Activation: `detect-signals` returns `is_agent_code: true`

## Prompt and LLM Smells

- Prompt strings hardcoded inline instead of in `prompts/` directory (SANYI BN-1)
- Model output used downstream without validation (no Pydantic/JSON schema check)
- Model names or versions hardcoded rather than in config (SANYI BN-1)
- No context length guard or truncation strategy for large inputs
- System prompt instructions doing the work that should be in deterministic code

## Tool Safety

- Write-capable tools (file write, DB mutate, send message) without confirmation gate
  or dry-run mode → `[Blocking]` if write is irreversible
- Non-idempotent tool retried without idempotency guard
- Tool return values used without schema/type validation
- Tool access control enforced only in prompt instructions, not in code → `[Blocking]`
- Tool side effects not documented or surfaced to orchestrator

## Workflow State

- Agent loop with no termination condition or iteration cap (unbounded graph)
- Multi-step workflow fails silently at step N with no partial-success record
- Agent hands off to another agent without explicit state serialization or handoff contract
- Workflow cannot resume after interruption (no checkpoint mechanism)
- Deterministic steps mixed with LLM steps without clear boundary

## Retrieval and Context

- Retrieved content used without freshness check or provenance tracking
- User-controlled content injected into prompt without sanitization (prompt injection)
- Retrieval not scoped to authorized data (tenant isolation)
- Stale or conflicting context without reconciliation logic

## Memory Write-Back

- Model inference stored as persistent fact without confidence tracking
- Memory writes with no mechanism to correct bad entries
- Model output persisted without human approval gate (for high-stakes decisions)
- Bad runs can contaminate memory without detection

## Accountability and Safeguards

The highest-priority category — find these first:

- **Safeguard in prose only**: a claimed safety behavior (escalation path, validation gate,
  confidence threshold, human-in-the-loop) exists only in prompt instructions, not in
  deterministic Python/TypeScript code. These are `[Blocking]` for production agent systems.
  Use Grep to verify: is there actual code backing the claim?
- No human takeover path for an agentic loop running in production
- No evaluation harness — relying solely on manual single-run testing
- Approval path unclear or absent for autonomous actions
- Uncertainty not surfaced to operators (silent low-confidence decisions)

## Evaluation

- Agent behavior not tested across multiple runs (overvaluing single-run results)
- No baseline to compare against (no regression signal)
- LLM judge used without calibration or deterministic grader backup
- Cost / latency not tracked or bounded

## Evidence Standard

- For "safeguard in prose only": grep the codebase for the claimed guard. If no code
  exists, mark `verified`. If partial code exists, mark `supported`.
- For missing validation: grep import of the model/agent, find the output usage, check
  for schema validation between them.
- Hypothesis acceptable for subtle coupling issues.
