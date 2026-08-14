---
name: structure
description: >
  Structure Dimension Checklist — dimension checklist read by the scan-structure agent (.claude/agents/structure.md).
  Reference material, not invoked directly.
allowed-tools: Read
---

# Structure Dimension Checklist

Agent: `scan-structure` | ID prefix: `ST-` | Always-on

Used by: `.claude/agents/structure.md`

## Naming and Layering

Per `~/.claude/refs/naming.md` role-based conventions:

- RAG index / embedding code belongs in `source/`, not `core/`
- ETL / data loading belongs in `source/`, not `core/`
- Executable / runnable code does not belong in `data/`
- Two modules with the same name doing the same job → naming collision
- A name overlap that is role-justified (e.g. `data/corpus/` artifacts vs `core/pipelines/corpus/` ETL)
  is NOT a finding — note as informational at most
- Severity: `[Non-blocking]` for layer violations; `[Nit]` for confusing-but-justified overlaps

## Complexity and Dead Code

- Functions or classes doing 3+ unrelated jobs (single-responsibility violation)
- Unreachable branches (always check — not assumed)
- Unused symbols: **use Grep to check callers** before claiming anything is unused
- Copy-paste divergence: same logic in N places with slight variations
- God objects / god functions (single class/function with excessive responsibility)
- Nested conditionals beyond 3 levels without justification — name the flattening
  (early return, guard clause, extracted helper) rather than only the depth. Flag depth,
  not style: an `else` or a `let` is not a finding when the alternative is more convoluted

## Architecture and Boundaries

- **Boundaries**: Are module/layer boundaries respected, or does the diff reach across one
  it shouldn't?
- **Dependency direction**: Does a low-level layer now import from a high-level one?
- **Coupling**: Is coupling increased in a way that makes future changes harder — unrelated
  modules sharing state or calling each other directly?
- **Abstraction**: Is the abstraction at the right level — not over-engineered for a
  one-off, not leaking implementation details through an interface?
- **Duplication**: Is logic duplicated that already exists elsewhere? (Grep before claiming.)
- **Evolution**: Does this make future evolution easier or harder — does it paint the
  codebase into a corner?
- **Rollback**: Can this change be rolled back cleanly if it needs reverting?
- **Long-term contract**: Does this commit the codebase to a public API, schema, or
  interface it may come to regret?

## Config and Constants Hygiene

- Hardcoded tunables: chunk sizes, thresholds, model names, timeout values → `[Non-blocking]`
  (cross-ref SANYI BN-1 if SANYI is active)
- Inline endpoints / base URLs that belong in env config
- Magic numbers without named constants
- Environment-specific values hardcoded in source (dev URLs, staging DB names)

## Documentation Accuracy

After the diff, do existing docs still describe the code accurately?

- CLAUDE.md: does it reflect new conventions, file paths, or behaviors added by the diff?
- README.md: do file paths, commands, module references still resolve?
- Architecture docs: do they still describe the right components and relationships?
- Capability tables or feature lists: any entries that the diff made stale?
- This dimension catches pre-existing drift too, not just diff-introduced changes

## Operations

- **Logging**: Is there enough structured logging to diagnose a production failure without
  reproducing it locally? No bare `print()` / `console.log()` on production paths
- **Metrics**: Are metrics emitted for what someone would need to monitor (latency, error
  rate, volume)?
- **Tracing**: Is this change traceable end-to-end if it's part of a larger request or workflow?
- **Health check**: Does a health/readiness signal exist for the deployment target?
- **Configuration**: Are secrets, URLs, and thresholds externalized to env vars or config,
  not hardcoded?
- **Deployment**: Does deployment require special sequencing (config first, migration
  first, feature flag)? Is the manifest/Dockerfile present and current?
- **Rollout**: Is the rollout staged or guarded (flag, percentage, canary), or does it go
  to 100% immediately?
- **Rollback**: Can a bad deploy be reverted without data loss?
- **Migration**: If there's a data migration, is it safe against production data, and is it
  reversible?
- **Handoff**: Does a runbook or on-call reference exist (linked in README or CLAUDE.md)?
- **Feature-flag hygiene**: Do temporary flags have owners and removal criteria? No orphaned flags

## Test Shape

- Tests with no assertions (vacuous pass)
- Mocks that stub the system under test (tautological assertion)
- Error paths never exercised in tests
- Test isolation issues: shared mutable state between test cases

Severity for test-shape findings: `[Nit]` or `[Non-blocking]` depending on severity of
the gap (missing error path for a critical flow → `[Non-blocking]`).
