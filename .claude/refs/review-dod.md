# Review Definition of Done

Checklist for assessing whether a PR is ready to merge. Distinct from the agile
Definition of Done in `~/.claude/refs/agile.md` — that defines when a *work item*
is complete (acceptance criteria met, tests pass, human committed, ledger row added);
this defines when a *PR's code changes* are merge-ready from a review perspective.

## Priority chain

```
Repository-specific DoD (CONTRIBUTING.md, PR template, repo CLAUDE.md)
  → Team/project DoD
    → This default checklist
```

Check the target repo for its own DoD before falling back to defaults below.
A repository-specific DoD always wins.

## Default checklist

- [ ] Intended behavior complete — the change does what it claims
- [ ] Important edge cases handled — not every edge case, but the ones that matter
- [ ] Tests sufficient — coverage proportional to risk, not arbitrary percentage
- [ ] Evaluation sufficient — for judgment-shaped code, N>1 runs considered
- [ ] Documentation updated — if behavior visible to users/operators changed
- [ ] Observability present — logging/metrics for new failure paths
- [ ] Migration handled — if data/schema changed, migration path exists
- [ ] Rollout understood — deployment sequence clear
- [ ] Rollback understood — revert path exists and is safe
- [ ] Security reviewed — auth, input validation, secrets at boundaries
- [ ] Handoff complete — next operator can understand the change
- [ ] Limitations recorded — known gaps documented, not hidden

## Usage in review

The orchestrator (`/workflow-review`, `/code-review`) assesses each item as:

- **met** — evidence exists (test, code, doc)
- **not applicable** — doesn't apply to this change
- **gap** — missing, becomes a finding with appropriate merge_impact

Not every item applies to every PR. A documentation-only PR skips most of
the checklist. The reviewer's judgment determines applicability.
