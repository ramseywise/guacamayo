---
name: review-silent-failure
description: >
  Silent-Failure Dimension Checklist — dimension checklist read by the generic `review` agent
  (.claude/agents/review.md). Reference material, not invoked directly.
prefix: SI
allowed-tools: Read
---

# Silent-Failure Dimension Checklist

Dimension: `silent-failure` | Agent: `review` | ID prefix: `SI-` | Always-on

Used by: `.claude/agents/review.md`

A silent failure is worse than a crash — the crash gets fixed the same day; the silent
failure corrupts data for six months. Correctness owns whether the logic is right; the
silent-failure dimension owns whether anyone finds out when it isn't.

## The One Question

- For every error path in the diff — catch/except/rescue blocks, error callbacks, promise
  chains, fallback expressions, exit codes — **if this fails in production, who finds out,
  and how?** If the answer is nobody, that is a finding.

## Swallowed Errors

- Empty handlers: `catch (e) {}`, `except: pass`, `rescue nil`, `if err != nil { }`,
  `_ = err`?
- Catch-and-continue where the error is logged at debug level or not at all while the
  function returns as if it succeeded?
- Overly broad catches (`except Exception`, `catch (Throwable)`) wrapping code where only
  one specific failure was anticipated?
- Error translation that destroys the cause — `throw new Error("operation failed")`
  discarding the original error, stack, and context?

## Failures Masked as Success

- Fallback values that hide breakage — returning `[]`, `null`, `0`, or a default object
  from a catch block, indistinguishable from a legitimate empty result?
- Partial failure reported as total success — batch operations that continue past
  individual failures and return OK?
- Scripts and CI steps that cannot fail — `|| true`, ignored exit codes, missing `set -e`
  in chained scripts?
- Validation that warns and proceeds anyway?

## Async-Specific

- Floating promises — async calls without `await`, `.then`, or explicit fire-and-forget
  marking?
- `.catch(() => {})` and rejection handlers that do nothing?
- Missing rejection handling on `Promise.all` / concurrent batches, where one rejection
  masks the others' results?
- Background tasks (queues, timers, event handlers) whose exceptions reach no logger or
  monitor?

## Retries and Recovery

- Retries without a max attempt count, or whose final failure is never surfaced?
- Circuit breakers and fallbacks that never report they are open, so degraded mode becomes
  permanent mode?
- Cleanup code in `finally` that throws and masks the original error?

## What NOT to Flag

- Intentional suppression with a comment explaining why (best-effort cleanup, optional
  telemetry, probing for existence).
- Best-effort paths where failure is genuinely acceptable AND the code says so.
- Errors handled by a caller you verified — read the call sites before flagging.
- Logging-level debates when the error IS surfaced somewhere actionable.
- Pre-existing silent failures the diff did not touch.

## Evidence Standard

- **verified**: grep of call sites confirmed no handler and no logger is reached
- **supported**: strong evidence, one assumption remains
- **hypothesis**: cannot tell whether the suppression is intentional — say so
- Rank by blast radius: data corruption > lost writes > degraded UX
