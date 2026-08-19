---
name: review-testing
description: >
  Testing Dimension Checklist — dimension checklist read by the generic `review` agent (.claude/agents/review.md).
  Reference material, not invoked directly.
prefix: TE
allowed-tools: Read
---

# Testing Dimension Checklist

Dimension: `testing` | Agent: `review` | ID prefix: `TE-` | Always-on

Used by: `.claude/agents/review.md`

This dimension owns whether anything would *catch* the bug. The bug itself belongs to
correctness or silent-failure.

## Coverage by Level

- **Unit** — do unit tests cover the new/changed logic in isolation?
- **Integration** — do tests cover how this interacts with the components it depends on?
- **Contract** — if a contract (API, schema, interface) changed, is there a contract test
  guarding it?
- **Regression** — for a bug fix, does a regression test exist for that specific bug?
- **End-to-end** — is there end-to-end coverage exercising this change through a
  realistic path?

## Negative Paths

- Are failure paths exercised, not just the success case?
- Are error branches, timeouts, and rejected inputs covered?
- Are boundary and empty-collection cases tested?

## Assertion Quality

- Do assertions verify the behavior that matters, or only that the code ran without
  throwing?
- Are any assertions tautological (asserting the mock's own return value)?
- Do mocks stub the thing under test, making the test unable to fail?
- **A test that cannot fail is worse than a missing test** — it reports coverage it does
  not provide. Is any test here in that shape?
- **Conservation**: where a function transforms a collection, does a test assert nothing
  is silently lost or duplicated?

## Failure-Before-Fix Evidence

- For a bug fix, is there evidence the test failed before the fix and passes after?
- Would the new test pass against the unfixed code? If so, that is a finding, not
  coverage.

## Reporting Discipline

- Was the test tree grepped by symbol name (not only file path) before claiming a gap?
- For a missing test, does the finding cite and quote the **untested code** rather than an
  absent test file? A finding whose only location is a nonexistent file cannot be
  validated.

## Evidence Standard

- **verified**: grep of test tree plus assertion inspection confirmed the gap
- **supported**: strong evidence, one assumption remains
- **hypothesis**: coverage gap suspected, couldn't fully confirm
- Surgical scope: flag gaps this diff created; an already-untested module is reportable
  only when the change extends it, carrying `pre_existing: true`
