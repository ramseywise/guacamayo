# Structure Dimension Checklist

Agent: `scan-structure` | ID prefix: `ST-` | Always-on

Used by: `review/scan/agents/structure.md`

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
- Nested conditionals beyond 3 levels without justification

## Architecture and Boundaries

- Dependency direction violations: low-level layer importing from high-level
- Inappropriate coupling: unrelated modules sharing state or calling each other directly
- Wrong abstraction level: concrete implementation detail leaking through an interface
- Duplication of existing utility or abstraction (check if it already exists)
- Long-term contract concerns: public APIs that will be hard to evolve

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

## Test Shape

- Tests with no assertions (vacuous pass)
- Mocks that stub the system under test (tautological assertion)
- Error paths never exercised in tests
- Test isolation issues: shared mutable state between test cases

Severity for test-shape findings: `[Nit]` or `[Non-blocking]` depending on severity of
the gap (missing error path for a critical flow → `[Non-blocking]`).
