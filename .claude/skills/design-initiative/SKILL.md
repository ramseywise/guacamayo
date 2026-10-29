---
name: design-initiative
description: "PM + EM role — initiative → milestones → task backlog in one pass. Use when an initiative is named and agreed: 'break this down into tickets' or 'define milestones for X'. Runs: milestone checkpoints first, then failure modes, HMWs, task backlog (t-shirt sized, acceptance criteria), dependency map, Linear hierarchy. Triggers on: 'scope this initiative', 'break this down into tasks', 'generate a backlog for X', 'what are the tickets for X', 'define milestones', 'what are the phases for X', 'initiative backlog'. Aliases: /initiative, /scope-initiative."
disable-model-invocation: true
allowed-tools: Read Bash Grep Glob WebSearch Write
---

## Target repo

Same convention as the phase protocols (research/plan/execute/code-review): a
`repo:<name-or-path>` token in `$ARGUMENTS` targets another workspace repo (bare name
resolves to `~/workspace/<name>`); all repo-relative paths and git/test commands resolve
against it, and artifacts land in the TARGET repo. No token → the cwd's repo; in a
meta/workspace-root session, ask rather than defaulting.

Scope the following initiative into milestones and a Linear-ready backlog: `$ARGUMENTS`

## Inputs (ask if not provided)

1. **Initiative name + one-line goal**
2. **Known failure modes** — 3-5 distinct ways the system currently fails (patterns, not symptoms)
3. **Brief or requirements doc**
4. **Existing assets** — prototypes, research, analogous systems
5. **Team roles available**
6. **MVP scope** — in vs out
7. **Hard constraints** — decision gates, external deadlines, capacity
8. **Dependencies on other initiatives** — what must exist elsewhere before this initiative can ship

## Phase 0 — Read the tree before the docs

**Do this first, before Phase 1, and before trusting any source doc's state claims.**
Source documents describe intent; the working tree is the only evidence of state.
Evidence: a PRD inherited green markers from feasibility docs written before anyone read
the code — six of eight were wrong. Ranking, intake, the review gate and the snapshot
store were all marked shipped and did not exist; one capability that was built appeared
in no document. A wrong done-marker removes work from the plan that then never gets
planned. (See `~/.claude/refs/verification.md` §2.)

For every capability a source doc claims exists, find the file. Record it as:

| Capability | Doc says | Tree says | File path or ABSENT |
|---|---|---|---|

Rules:

- **A capability with no file path is `ABSENT`, whatever the doc says.** Not partial,
  not "in progress" — absent. "Shipped" claims decay silently; a path is the only claim
  that can be checked by the next reader.
- **`BUILT` means "the module exists and is tested", never "the deliverable is accepted."**
  Keep those two states in separate columns — a module can be built and simultaneously
  violate its own acceptance criteria.
- **Anything you could not verify is `UNVERIFIED`, never an optimistic partial.**
  Write `🔍 UNVERIFIED — go and look`, not a hopeful middle ground.
- **The audit is the first deliverable, not a preamble.** Where it contradicts a source
  doc, the contradiction is a finding with an ID (e.g. `AUDIT-1: PRD claims ranking
  shipped; tree has no ranking module`) — not a silent correction, and not a reason to
  re-derive the doc.
- **A wrong build-state marker is more expensive than a missing one.** It removes work
  from the plan that then never gets planned, and every downstream sequencing decision
  inherits the error.

### Phase 0 output

The audit table is included at the top of the milestone doc (Phase 1 output) under a
`## Capability audit` heading. Findings carry IDs and are referenced from milestone
done-conditions where relevant — a milestone gated on a capability marked ABSENT must
name the finding.

---

## Phase 1 — Milestones (run first)

Define 2–6 phase-level checkpoints before task breakdown. A milestone is a verifiable system
state, not a bundle of work. Hierarchy (matches Linear): **Initiative → Project → Milestone → Issue.**

### Before starting milestones

Check for an existing milestone doc at `.claude/docs/milestones/<initiative-slug>.md`. If one
exists and is current, skip Phase 1 and proceed to Phase 2 using it.

### Milestone process

1. **Initiative goal statement** — one sentence: what does this initiative deliver and for whom?
2. **Milestones (2–6)** — each is a named system state, ordered. Per milestone:
   - **Done-condition** — a verifiable observation ("a service key returns real rows from
     `GET /kb/search`"), never activity ("API built")
   - **Gates** — decisions or external dependencies that block it, marked ⛔
   - **Target** — date or sequence position; only pin dates driven by real external events
3. **Cross-initiative dependencies** — which milestones here unblock or wait on milestones in
   other initiatives
4. **Out of scope** — what this initiative explicitly does not cover, with reasons

### Milestone output

Write `.claude/docs/milestones/<initiative-slug>.md`:

```markdown
# Initiative: <name>
Date: <today>
Goal: <one sentence>
Source plan: <path to the plan/roadmap section this formalizes>

## Milestones

### M1 — <named system state>
- **Done when:** <verifiable condition>
- **Gates:** <⛔ decision/dependency, or "none">
- **Target:** <date if externally driven, else "after M0" / "sequence only">

### M2 — ...

## Cross-initiative dependencies
- <this M unblocks / waits on <initiative>:<milestone>>

## Out of scope
- <item with reason>
```

### Milestone rules

- A milestone is a state, not a workstream — if it names ongoing activity, it's an initiative
  or a project, not a milestone
- One verifiable done-condition per milestone — if you need two unrelated ones, split it
- Milestones inherit the source plan's phase boundaries unless there's a stated reason to re-cut
- Only externally-driven milestones get calendar dates; the rest get sequence positions —
  fake dates on gated work hide the real critical path (the gate)
- Defer rather than stretch — fewer verifiable milestones beat many vague ones

---

## Phase 2 — Task Backlog

With milestones defined (Phase 1 output or existing doc), produce the full task backlog.

## Sections

1. **Failure modes & HMWs** — table: # | Failure mode (`root cause -> symptom`) | Pain point | HMW. Every subsequent task traces to at least one failure mode.
2. **Research** — existing assets (reuse/adapt/reference), libraries per layer, technical unknowns (what each blocks), roadblocks + dependencies table.
3. **Task backlog** — initiative goal + MVP definition of done. Per task: goal, deliverable (concrete, not "implement X"), key work bullets, risks/questions, size (S/M/L/XL).
4. **Summary table + critical path** — # | Task | Failure mode | Size | Key dep | Owner | MVP? Plus: week-1 decisions, highest-risk dependency, tasks that must be designed together.
5. **Open questions** — numbered, each names who must answer. Categories: data access, infra, product, ownership, policy, phasing.
6. **Linear hierarchy** — Initiative → Project → Milestone → Issues (tasks): every task attaches to one of the initiative's milestones (Phase 1), with acceptance criteria (Given/When/Then + metric + integration criterion) and blocking relationships. A task that fits no milestone means either the backlog has scope creep or the milestone list is missing a checkpoint — resolve, don't orphan.

## Task constraints

- Every deliverable is concrete (running system, document, dataset) — not "implement X"
- Every task traces to at least one failure mode
- T-shirt sizes: S (<1wk, few unknowns), M (1-2wk, some unknowns), L (2-4wk, significant unknowns), XL (>sprint, major decisions)
- Day-one decisions (embedding model, schema, vector store) appear first in critical path

---

**Upstream**: `/design-sprint` if still ideating what to build — run that first to get named initiatives and workstream clusters.

**Next step**: `/doc-to-linear-tickets` to push the task backlog (Section 6 Linear hierarchy) into actual Linear issues once the scope is reviewed and agreed.
