# Safety Dimension Checklist

Agent: `scan-safety` | ID prefix: `SF-` | Always-on

Used by: `review/scan/agents/safety.md`

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

- Authentication missing or bypassable
- Authorization check absent or order-dependent (check after operation)
- SQL/command injection vectors (unparameterized queries, `os.system` with user input)
- Path traversal (user-controlled file paths without normalization)
- Unsafe deserialization (`pickle`, `yaml.load` without Loader)
- Unsafe writes to filesystem from external input

## Privacy and Data

- PII collected beyond stated purpose
- Audit trail missing for sensitive operations
- Data exposure through error messages or stack traces
- Tenant isolation violated (shared cache, shared DB rows)
- Sensitive data in URLs, query params, or logs

## Reliability

- Retry/backoff logic present for external calls (network, DB, third-party APIs)
- Timeout configuration on HTTP/API calls — every outbound call has an explicit timeout
- Circuit breaker or fallback for degraded dependencies (graceful degradation, not cascading failure)
- Graceful degradation path documented: what does the system do when a dependency is down?
- Retry budgets bounded: max retries + jitter + exponential backoff (unbounded retries are `[Blocking]`)
- Backpressure handling: does the system shed load or queue under high throughput, or does it fail silently?
- SLI/SLO boundary assertions: are error rate and latency thresholds enforced, or is the caller expected to handle degradation?

## Evidence Standard

- Trace the data flow from input to sink before claiming injection risk
- Grep call sites before claiming a secret is hardcoded (could be a test fixture)
- `[Blocking]` requires verified or supported evidence for hardcoded secrets;
  hypothesis is acceptable for subtle injection paths
