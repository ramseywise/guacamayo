# Contracts Dimension Checklist

Agent: `scan-contracts` | ID prefix: `CT-` | Conditional (SANYI.md present)

Used by: `review/scan/agents/contracts.md`

Activation: `detect-signals` returns `has_sanyi_contracts: true`

## Procedure

1. Read `SANYI.md` (or `.claude/SANYI.md`) in full before scanning any file.
2. For each Buyi (不易) contract entry, grep the diff to verify the invariant still holds.
3. Scan for Jianyi (简易) complexity violations in the diff.
4. Scan for Bianyi (变易) hardcoded values.
5. Note new patterns that should have a SANYI entry but don't (MG-1).

## 不易 Buyi — Invariants (violation codes BY-1 to BY-4)

Contracts that must hold regardless of performance, convenience, or scope:

- **BY-1** — Layer bypass: code from one layer directly calls into a layer it should
  not reach (e.g., route handler calling DB directly, skipping service layer)
- **BY-2** — Single-source violation: data modified in two places that should have
  a single canonical owner
- **BY-3** — Invariant demoted: a hard architectural guarantee (PII masking, auth check,
  rate limit) made conditional or optional by the diff
- **BY-4** — Audit/trace gap: a change removes or degrades an existing audit trail or
  observability contract

**Merge impact: blocker for all Buyi violations.**

Checklist:
- Does the diff bypass any layer boundary defined in SANYI.md?
- Does the diff create a second writer for data with a single-source contract?
- Does the diff add an env-var, feature flag, or config option that disables a contract?
- Does the diff remove logging, tracing, or audit events that the contract requires?

## 简易 Jianyi — Simplicity (violation codes JY-1 to JY-3)

The codebase should not become more complex without justification:

- **JY-1** — Duplicate abstraction: a new class/function that duplicates existing logic.
  Check if an equivalent already exists before flagging.
- **JY-2** — Logic spread: behavior that belongs in one layer is split across multiple.
- **JY-3** — Inappropriate coupling: two modules sharing state or calling each other
  when they shouldn't.

**Merge impact: important.**

Checklist:
- Does the diff introduce a new abstraction? Is there already one? (Grep first)
- Is the new logic scattered across files when it should be in one place?
- Do newly imported modules create cycles or cross-layer dependencies?

## 变易 Bianyi — Changeable Values (violation code BN-1)

Values that will need to change should live in config, not source:

- **BN-1** — Hardcoded tunable: thresholds, model names, chunk sizes, timeout values,
  feature flags hardcoded in Python/TypeScript rather than in config/env.

**Merge impact: suggestion.**

Checklist:
- Are numeric constants named? Could they be in a config file?
- Are model names / API endpoints hardcoded?
- Is there a `config.py` or env pattern the new code should use but doesn't?

## Hygiene (MG-1, UN-1, UN-2)

- **MG-1** — Missing SANYI entry: the diff introduces a new architectural pattern
  (new layer, new data ownership rule, new invariant) that should be documented
  in SANYI.md but isn't. Recommend adding an entry.
- **UN-1** — Unclassified violation: something looks like a contract violation but
  doesn't fit BY/JY/BN cleanly. Flag for human review.
- **UN-2** — Stale SANYI entry: a SANYI.md contract refers to code that no longer
  exists or behavior that has changed.

**Merge impact: nit.**

## Evidence Standard

- For Buyi violations: grep the diff AND the surrounding code. Cite the specific
  SANYI.md contract entry (title or section) being violated.
- For Jianyi: grep to confirm whether a duplicate actually exists.
- `violation_code` is **required** in the finding's `severity.violation_code` field.
- Merge impact must match the violation code — do not deviate.
