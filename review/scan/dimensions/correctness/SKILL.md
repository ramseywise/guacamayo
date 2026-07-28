# Correctness Dimension Checklist

Agent: `scan-correctness` | ID prefix: `CR-` | Always-on

Used by: `review/scan/agents/correctness.md`

## Intent and Correctness

- Does the change solve the intended problem, or only a symptom?
- Is user-visible behavior clear and correct?
- Is scope appropriate — not too broad, not missing cases?
- Are inputs, outputs, schemas, state transitions, and invariants correct?
- Are edge cases handled: empty collections, null inputs, boundary values, ordering,
  concurrency, compatibility?
- **Cross-usage consistency**: when a shared schema/type is modified, check ALL usages
  across the repo (use Grep), not only the diff's own callers.

## Logic Errors

- Off-by-one errors (loop bounds, index arithmetic, pagination)
- Inverted conditions (`if not x` when `if x` was intended, etc.)
- Unhandled `None` / `undefined` / empty return values on critical paths
- Race conditions — shared mutable state accessed without synchronization
- Wrong variable used (shadowing, typos in similar names)
- Error paths that swallow or mis-classify exceptions

## Data Correctness (apply to pipelines, SQL, and ETL)

- `SELECT *` in ETL (schema drift risk)
- Missing `WHERE` on UPDATE/DELETE
- Non-idempotent `INSERT` without `ON CONFLICT`
- Timezone-naive timestamps where tz-aware is required
- String-concatenated SQL (injection risk — also flag in safety dimension)
- Silent dtype coercion (pandas, pydantic)
- No schema validation at data ingest boundary
- Non-idempotent writes without guard

## Testing Coverage

- Unit tests for the changed behavior
- Negative paths exercised (what happens when it fails?)
- Assertions are meaningful (not tautological; mocks don't stub the thing being tested)
- Failure-before-fix evidence: does a test prove the bug existed before the fix?

## Evidence Standard

- **verified**: code confirmed by grep + test inspection
- **supported**: strong code evidence, one inference gap
- **hypothesis**: pattern looks wrong, couldn't fully confirm
- Never state `verified` when you have doubt — use `hypothesis` and say why
