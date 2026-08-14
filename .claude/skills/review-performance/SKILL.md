---
name: review-performance
description: >
  Performance Dimension Checklist — dimension checklist read by the performance agent (.claude/agents/performance.md).
  Reference material, not invoked directly.
allowed-tools: Read
---

# Performance Dimension Checklist

Agent: `performance` | ID prefix: `PF-` | Always-on

Used by: `.claude/agents/performance.md`

Performance findings are the easiest dimension to fill with noise. The bar is not
"could this be faster" — almost anything could. The bar is **this degrades badly as
real data grows, and the diff introduced it.**

## Scan for

1. **N+1 queries** — does the diff put a query, RPC, or other external call inside a
   loop that could be batched into one call?
2. **Unbounded iteration** — can this operation load or iterate an unbounded amount of
   data: a missing `limit`, absent pagination, a full-table read that grows with usage?
3. **Hot-path complexity** — does this add an algorithm whose complexity degrades badly
   at production scale (O(n²) or worse) over data that grows with users, records, or
   time? Nested loops over the same collection are the usual tell.
4. **Blocking I/O on an async path** — does a coroutine or event-loop path make a
   synchronous filesystem, network, or subprocess call that stalls the loop?
5. **Missing indexes** — if the diff changes a query pattern, does the store have (or
   gain) an index supporting it?
6. **Repeated work** — is an expensive pure computation recomputed inside a loop when it
   could be hoisted, or a result refetched that was already in hand?

## Scale is the argument, not the smell

A finding must name **what grows**. "This is O(n²)" is not a finding; "this is O(n²)
over `facts`, which grows with every uploaded PDF" is. If you cannot identify the
growing input, you do not have a finding — you have a preference.

Fixed-size collections are not a performance concern at any complexity. A nested loop
over a 5-element template list is fine, and flagging it costs the reader more than it
saves.

## Evidence standard

Evidence here is usually incomplete without production data — query plans, load numbers,
profiles. That does not make findings unreportable; it makes them `hypothesis` rather
than `verified`. Per `review-shared`, a `hypothesis` can still carry real merge impact:
an unbounded query on a user-facing path is serious whether or not you measured it.

Never claim `verified` for a performance finding you did not measure. Reach for
`verified` only when the diff itself carries the proof — a query inside a loop is
visible in the source and needs no benchmark.

## Boundary with `review-safety`

Safety owns reliability and resource *exhaustion* as a correctness/availability concern
— an unbounded read that crashes the process is a safety finding. Performance owns
*degradation* — the same read that merely gets slower as data grows. When a single
observation supports both readings, file it once under the consequence you can evidence,
and do not duplicate it across dimensions.
