---
name: intent
description: >
  Intent Dimension Checklist — dimension checklist read by the scan-intent agent (.claude/agents/intent.md).
  Reference material, not invoked directly.
allowed-tools: Read
---

# Intent Dimension Checklist

Agent: `scan-intent` | ID prefix: `IN-` | Always-on

Used by: `.claude/agents/intent.md`

## Statement of Intent

- Where is the statement of intent — plan doc, PR description, or issue?
- If none exists, do the commit messages and the diff's own shape carry it, and does the
  finding say which fallback was used?

## Solves the Intended Problem

- Does the change actually achieve the stated goal, or something adjacent to it?
- Is the stated goal fully delivered, or only partly?
- Does anything in the diff contradict the stated goal?

## User-Visible Behavior

- Can a reader tell what changes for the user?
- Are behavior changes documented, or left ambiguous/undocumented?
- Is a breaking change to user-visible behavior called out as one?

## Scope

- Does the diff do more than its stated goal — unrelated changes riding along?
- Does it do less — a stated goal only half-delivered?
- Before calling a change out-of-scope, was it grepped to confirm it is not load-bearing
  for the stated goal?

## Cause vs Symptom

- Does the change fix the underlying cause, or only mask the symptom?
- Is a guard added at the call site where the invariant should have been fixed at the
  source?
- Would the same class of bug recur elsewhere because only this instance was patched?

## Complexity

- Is the implementation more complex than what it achieves warrants?
- Is there a simpler shape that delivers the same stated goal?

## Evidence Standard

- **verified**: intent statement located and compared against the diff
- **supported**: strong evidence, one inference gap
- **hypothesis**: scope or intent mismatch suspected, couldn't fully confirm
- Never state `verified` when you have doubt — use `hypothesis` and say why
- Surgical scope: flag what this diff caused; a pre-existing problem carries
  `pre_existing: true`
