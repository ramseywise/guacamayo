# Review Dimensions

Structured checklists for multi-perspective code review. Consumed by akira-scan as
additional scan categories beyond its core 9. Organized into always-on dimensions
(apply to every review) and conditional dimensions (agent-system code only).

## Always-on dimensions

### 1. Intent and Correctness

- Does the change solve the intended problem or only a symptom?
- Is user-visible behavior clear and correct?
- Is scope appropriate (not too broad, not missing cases)?
- Inputs, outputs, schemas, state transitions, invariants
- Edge cases, ordering, concurrency, compatibility
- **Cross-usage consistency**: when a shared schema/type is modified, check all usages
  across the repo, not only the diff's own callers

### 2. Testing

- Unit, integration, contract, regression, end-to-end coverage
- Negative paths exercised
- Assertions are meaningful (not tautological)
- Failure-before-fix evidence (does a test prove the bug existed?)
- Mocks don't stub away the thing being tested

### 3. Reliability and Operations

**Reliability**: retries, timeouts, idempotency, partial failure, fallback,
cancellation, recovery, cleanup, consistency

**Operations**: logging, metrics, tracing, deployment readiness, rollout plan,
rollback plan, migration path, documentation, handoff

### 4. Security, Privacy and Data

**Security/Privacy**: authn, authz, tenant isolation, PII handling, secrets management,
injection vectors, unsafe writes, auditability

**Data/State**: validation at boundaries, provenance, migration safety, serialization,
stale data risk, duplicated state, source-of-truth clarity

### 5. Architecture and Documentation

**Architecture**: boundaries, dependency direction, coupling, abstraction level,
duplication, evolution path, rollback capability, long-term contracts

**Documentation accuracy**: Do existing docs (CLAUDE.md, README.md, architecture docs,
capability tables) still describe the code accurately after this diff? Do file paths
and module references still resolve? This catches pre-existing or diff-introduced
drift, not just missing updates for the current change.

## Conditional dimensions (agent-system only)

These apply only when batch files import LLM/agent frameworks or match agent-system
signals (imports from `anthropic`, `openai`, `langchain`, `langgraph`, `google.adk`,
`claude_agent_sdk`; files in `agents/`, `*_agent/`, `prompts/`).

### 6. Agent Runtime and Tooling

**Tool side effects**: read-only vs write-capable, confirmation required, retry safety,
idempotency, output validation, permission enforcement at tool boundary

**Workflow state**: graph bounded, can terminate, can resume, partial-success handling,
explicit handoffs, deterministic code where appropriate

**Retrieval and context**: scoping, provenance, permissions, stale/conflicting context,
prompt injection via retrieved content

**Memory write-back**: what is persisted (fact vs inference vs model output), correctability,
confidence stored, approval required, contamination risk from bad runs

### 7. Accountability and Safeguards

**Evaluation**: overvaluing single runs, repeated-run need, baselines, deterministic
graders, LLM judge calibration, trace + output evaluation, cost/latency consideration

**Human responsibility**: approval paths, accountability, human takeover, uncertainty
visibility, escalation availability

**Documented safeguards**: Do claimed safety behaviors (escalation paths, validation
layers, confidence gates) have actual deterministic code backing, or do they exist only
as prompt sentences? If a gap is found and no SANYI contract governs it, recommend
recording it as a candidate Buyi entry. If `SANYI.md` exists, flag for SANYI review;
if not, recommend `/sanyi init`.
