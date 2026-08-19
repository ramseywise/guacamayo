---
name: review-safety
description: >
  Safety Dimension Checklist — safeguards, secrets/PII, security, privacy and data,
  reliability, and performance/scale. Read by the safety agent (.claude/agents/review.md).
  Reference material, not invoked directly.
prefix: SF
allowed-tools: Read
---

# Safety Dimension Checklist

Dimension: `safety` | Agent: `review` | ID prefix: `SF-` | Always-on

Used by: `.claude/agents/review.md`

## Safeguards

- Is external/user input validated before use? (injection, overflow, unexpected types)
- Are network calls bounded by timeouts? Is there retry logic?
- Are irreversible writes (delete, overwrite, send) guarded by confirmation or dry-run?
- Are queries scoped to the correct tenant/user? (no cross-tenant data leakage)
- Are rate limits or resource caps in place for unbounded operations?

## Error and Resource Handling

- Swallowed exceptions: bare `except:`, `except Exception: pass`, silent fallbacks
  on critical paths → `[Blocking]`
- Resources properly closed: context managers (`with`), `.close()`, try/finally
- Network calls with no timeout/retry — `[Blocking]` if on critical path
- Partial failure: does the system leave state consistent on failure?

## Secrets and PII

- Hardcoded secrets or credentials in source → always `[Blocking]`
- PII (names, emails, SSNs, health data) reaching logs or error messages
- Credentials in config files that may be committed → `[Blocking]`
- API keys, tokens, passwords in test fixtures → `[Blocking]`

## Security

- **Authn**: Is authentication required where it should be, and not bypassable?
- **Authz**: Is authorization checked at the right boundary — not just "is this user
  logged in" but "can this user do this specific thing"? Is the check order-dependent
  (performed after the operation)?
- **Injection**: Is user-controlled input safe from injection (SQL, command, template,
  prompt) at every sink it reaches? Unparameterized queries, `os.system` with user input
- **Path traversal**: user-controlled file paths without normalization
- **Unsafe deserialization**: `pickle`, `yaml.load` without Loader
- **Unsafe writes**: Can a malicious or malformed input turn a write into an unintended
  data modification?

## Privacy and Data

- **PII**: Does this diff introduce, log, or expose PII that wasn't handled carefully
  before? Is PII collected beyond stated purpose?
- **Auditability**: Is there an audit trail for the sensitive actions this change introduces?
- **Data exposure**: Does data leak through error messages or stack traces?
- **Tenant isolation**: If multi-tenant, can one tenant's data or actions leak into
  another's (shared cache, shared DB rows)?
- **Sensitive data in transit**: secrets or PII in URLs, query params, or logs
- **Validation**: Is data validated at the boundary where it enters the system, not just
  assumed correct downstream?
- **Provenance**: Is the provenance of the data (where it came from, how trustworthy it
  is) tracked or lost?
- **Serialization**: Does serialization/deserialization round-trip correctly, including
  edge cases (nulls, new/missing fields)?
- **Source of truth**: Is it clear what the single source of truth is, or does this diff
  create a second one that can drift?

## Reliability

- **Retries**: Are retries used where transient failures are expected, and avoided where
  they'd cause harm (non-idempotent writes)? Retry budgets bounded — max retries + jitter
  + exponential backoff (unbounded retries are `[Blocking]`)
- **Timeouts**: Does every outbound HTTP/API call have an explicit, reasonable timeout?
- **Idempotency**: Is the operation idempotent, so a retry or duplicate delivery doesn't
  cause incorrect state?
- **Fallback**: Is there a circuit breaker or fallback for degraded dependencies, or does
  the whole path fail hard (cascading failure)?
- **Graceful degradation**: What does the system do when a dependency is down — is that
  path documented?
- **Cancellation**: Can the operation be cancelled cleanly, leaving state safe?
- **Backpressure**: Does the system shed load or queue under high throughput, or fail silently?
- **SLI/SLO boundaries**: Are error rate and latency thresholds enforced, or is the caller
  expected to absorb degradation?

## Performance and Scale

- **N+1 queries**: Does this diff put a query or external call inside a loop that could be
  batched into one call instead?
- **Unbounded loops/results**: Can this operation iterate over or load an unbounded amount
  of data — is there a missing limit or pagination?
- **Hot-path complexity**: Does this add an algorithm whose complexity degrades badly at
  production scale (O(n²) over user-facing or growing data)?
- **Missing indexes**: If this changes a query pattern, does the store have (or gain) an
  index to support it at scale?

Evidence for this dimension is usually incomplete without production data (query plans,
load numbers). When unverified, phrase findings as `hypothesis` — never `verified` — per
the evidence standard below.

## Evidence Standard

- Trace the data flow from input to sink before claiming injection risk
- Grep call sites before claiming a secret is hardcoded (could be a test fixture)
- `[Blocking]` requires verified or supported evidence for hardcoded secrets;
  hypothesis is acceptable for subtle injection paths
