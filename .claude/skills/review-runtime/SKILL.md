---
name: review-runtime
description: >
  Runtime Dimension Checklist — dimension checklist read by the runtime agent (.claude/agents/runtime.md).
  Conditional dimension (agent-system code only). Reference material, not invoked directly.
allowed-tools: Read
---

# Runtime Dimension Checklist

Agent: `runtime` | ID prefix: `RT-` | Conditional (`is_agent_code`)

Used by: `.claude/agents/runtime.md`

Activation: dispatched only when `detect-signals` reports `is_agent_code: true` — files
import an LLM/agent framework or match agent-system path signals.

The runtime dimension owns how the agent system *behaves* at execution time. Evaluation
rigor, human responsibility, and whether a documented safeguard has real code backing
belong to `safeguards`.

## Prompt / LLM Smells

- Are prompt strings hardcoded inline instead of living in a `prompts/` directory?
  `[Non-blocking]`; cite SANYI BN-1 if applicable.
- Is LLM output fed downstream without validation — no structured-output schema, no output
  bound, no Pydantic/JSON schema check?
- Are model names or versions hardcoded rather than read from config?
- Is the token budget ignored — no context-length guard, no truncation strategy?

## Tool Side Effects and Safety

- Are write-capable tools (write files, send messages, mutate DB) dispatched without user
  confirmation or a dry-run mode?
- Is a non-idempotent tool retried without an idempotency guard?
- Are tool return values used without a schema check?
- Is tool permission enforced only in prose instructions rather than in the tool
  implementation itself?

## Workflow State and Partial Failure

- Is the agent loop unbounded — no termination condition, no iteration cap? Can it
  terminate? Can it resume?
- Does a multi-step workflow fail silently on step N with no indication of what completed
  before the failure?
- Does an agent hand off to another agent without explicit state serialization or a
  handoff contract?
- Is a model deciding something deterministic code could and should settle?

## Retrieval and Context

- Is retrieved content used without a freshness check or provenance tracking, risking
  stale or conflicting context?
- Can user-controlled or external content reach a sensitive sink without sanitization
  (prompt injection via retrieval)?
- Is the retrieval query scoped to authorized data, and are permissions respected on
  retrieved content?

## Memory Write-Back

- Is model output persisted as fact without confidence tracking or an approval gate?
- Is there any way to correct a bad memory entry?

## Evidence Standard

- **verified**: grep confirmed the missing guard in code (e.g. no iteration cap present)
- **supported**: strong evidence, one assumption remains
- **hypothesis**: pattern looks wrong, couldn't fully confirm
- Verify a claimed guard exists in code before accepting it
