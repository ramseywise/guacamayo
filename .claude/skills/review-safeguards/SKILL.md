---
name: review-safeguards
description: >
  Safeguards Dimension Checklist — dimension checklist read by the scan-safeguards agent
  (.claude/agents/safeguards.md). Conditional dimension (agent-system code only).
  Reference material, not invoked directly.
allowed-tools: Read
---

# Safeguards Dimension Checklist

Agent: `scan-safeguards` | ID prefix: `SG-` | Conditional (`is_agent_code`)

Used by: `.claude/agents/safeguards.md`

Activation: dispatched only when `detect-signals` reports `is_agent_code: true`.

The safeguards dimension owns whether the system can be trusted and held accountable.
Tool side effects, workflow state, and retrieval boundaries belong to `scan-runtime`.

## Documented Safeguards (highest-value class)

- Is a claimed safety or guardrail behavior — escalation path, input/output validation
  layer, confidence gate — present only in documentation, a system prompt, or config, with
  no deterministic code path behind it? **Always flag these.** Models are probabilistic, so
  a constraint implemented only in a prompt is soft.
- Were both halves confirmed: the claim in prose AND the absence in code?
- If the repo has a `SANYI.md`, was it noted that the contracts dimension should carry this
  as `BY-4`? (Do not attempt the contract draft in this dimension.)

## Evaluation

- Is there an eval harness for the agent behavior, or is the change relying on single-run
  manual testing?
- Is one successful run being treated as evidence — no repeated runs, no baseline to
  compare against?
- Is an LLM judge used where a deterministic grader is possible, or is the judge
  uncalibrated?
- Is only the final output graded, never the intermediate trace? Are cost and latency
  considered at all?

## Human Responsibility

- Does the agentic loop have a mechanism for a human to interrupt or take over?
- Is it clear who approves and who is accountable for the agent's actions?
- Does the system surface when it is unsure, so there is something to escalate on?
- Where uncertainty is surfaced, is there an escalation path for it to go to?

## Evidence Standard

- **verified**: grep showed no deterministic gate, only a prose instruction
- **supported**: strong evidence, one assumption remains
- **hypothesis**: safeguard gap suspected, couldn't fully confirm
- Severity note: safeguard-in-prose-only is often **Blocking** for production agent code
