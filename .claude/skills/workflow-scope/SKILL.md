---
name: workflow-scope
description: "Triage orchestrator — reads a backlog issue, routes through research → plan → refine as subagents, exits when the plan is READY or reports what's blocking. One retry per stage; after that the main model resolves. Triggers on: /workflow-scope, 'scope this issue', 'triage #N', 'what does this need', 'take this to ready'."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion
---

# /workflow-scope

The triage entry point. Takes a backlog issue from unscoped to READY by routing through
the right sequence of workflow skills as subagents. Opus decides the routing; sonnet
executes each stage.

## Usage

```
/workflow-scope <issue-number> [--repo <repo>]
/workflow-scope "problem statement as inline text"
```

If given an issue number, reads the issue body via `gh`. If given inline text, treats it
as the problem statement directly (no issue lookup).

## Step 1 — Assess current state

Read what already exists for this work item:

```bash
# Issue context (skip if inline text)
gh issue view <N> -R ramseywise/<repo> --json title,body,labels

# Existing artifacts
ls .claude/docs/research/*<slug>* 2>/dev/null
ls .claude/docs/plans/*<slug>* 2>/dev/null
```

Classify into exactly one state:

| State | Condition | Next action |
|-------|-----------|-------------|
| `UNSCOPED` | No research doc, no plan doc, problem is unclear or broad | → research |
| `CLEAR` | No research doc, no plan doc, but problem is well-defined in the issue body | → plan (skip research) |
| `RESEARCHED` | Research doc exists, no plan doc | → plan |
| `PLANNED` | Plan doc exists, Status is PLANNED (not refined) | → refine |
| `REFINED` | Plan doc exists, Status is REFINED or READY | → exit (already done) |
| `BLOCKED` | Issue has `blocked` label or plan has unresolved blockers | → report and stop |

**The skip-research decision is the key routing judgment.** Research is warranted when:
- The problem space is unfamiliar (new domain, new tool, new pattern)
- Multiple approaches exist and the issue doesn't specify one
- The issue references external systems/APIs that need investigation

Research is NOT warranted when:
- The issue body already contains the approach, acceptance criteria, and scope
- It's a bug fix with a clear reproduction
- It's a refactor of existing code with a known target state

Log the routing decision:

```bash
echo '{"ts":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","issue":'<N>',"repo":"'<repo>'","state":"'<STATE>'","entry_point":"'<NEXT>'"}' >> .sounding/telemetry/scope-decisions.jsonl
```

## Step 2 — Execute the routing loop

Run stages sequentially. Each stage is a foreground subagent. After each stage completes,
re-assess state (Step 1 logic) and route to the next stage.

**One retry per stage.** If a stage's subagent fails or produces an incomplete artifact:
1. Read what it produced
2. Identify the gap (missing section, unresolved question, incomplete analysis)
3. Re-spawn the same stage with the gap noted in the prompt
4. If it fails again → **stop the loop and surface the issue to the main model**

The main model (you, opus) then resolves the open issues directly — reading the partial
output, filling the gaps, and marking the plan as READY or REFINED. Do not spawn a third
attempt. Two tries means the problem needs judgment, not repetition.

### Research stage (if routed)

```
Agent(model: "sonnet", run_in_background: false)
prompt: |
  Repo: <repo-path>
  Issue: #<N> — <title>
  Task: Run /workflow-research on this issue. Produce a research doc at
  .claude/docs/research/<date>-<slug>.md covering the problem space,
  existing approaches, and a recommended direction.
  Constraint: Read the issue body first. Write the research doc. Do not plan.
```

**Verify**: research doc exists and has a recommendation section.

### Plan stage

```
Agent(model: "sonnet", run_in_background: false)
prompt: |
  Repo: <repo-path>
  Issue: #<N> — <title>
  Research: <research-doc-path if exists>
  Task: Run /workflow-plan. Produce a plan doc at
  .claude/docs/plans/<date>-<slug>.md with Status: PLANNED.
  Include steps, test plan, risks, and sizing.
  Constraint: Read the issue and research doc first. Do not execute.
```

**Verify**: plan doc exists, has `Status: PLANNED`, has steps and test plan.

### Refine stage

```
Agent(model: "sonnet", run_in_background: false)
prompt: |
  Repo: <repo-path>
  Issue: #<N> — <title>
  Plan: <plan-doc-path>
  Task: Run /workflow-refine. Check DoR gate: are steps concrete enough to
  execute without re-scoping? Are open questions resolved? Is sizing realistic?
  Update Status to REFINED or READY. Add a task checklist to the issue body
  if the work needs splitting.
  Constraint: Read the plan doc first. Do not create sub-issues.
```

**Verify**: plan doc Status updated to REFINED or READY.

## Step 3 — Resolve or exit

After the loop completes (all stages run, or main model resolved gaps):

```bash
# Update issue label
gh issue edit <N> -R ramseywise/<repo> --add-label "ready" --remove-label "backlog"

# Log completion
echo '{"ts":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","issue":'<N>',"repo":"'<repo>'","outcome":"ready","stages_run":['<LIST>'],"retries":'<N>'}' >> .sounding/telemetry/scope-decisions.jsonl
```

Print exit block:

```
──────────────────────────────────────
✅ Triage complete — #<N> is READY.
📋 Plan: <plan-doc-path>
📊 Stages: <research|skipped> → plan → refine
🔄 Retries: <N>

Ready for: /workflow-execute
──────────────────────────────────────
```

If the main model had to resolve gaps (retry exhausted):

```
──────────────────────────────────────
⚠ Triage complete with manual resolution.
📋 Plan: <plan-doc-path>
🔧 Resolved: <what was fixed by the main model>

Ready for: /workflow-execute
──────────────────────────────────────
```

## Performance tracking

Every routing decision and outcome logs to `.sounding/telemetry/scope-decisions.jsonl`.
Fields:

| Field | Type | Description |
|-------|------|-------------|
| `ts` | ISO-8601 | When the decision was made |
| `issue` | int | Issue number |
| `repo` | string | Repository name |
| `state` | string | Assessed state at entry |
| `entry_point` | string | First stage routed to |
| `outcome` | string | `ready` / `blocked` / `partial` |
| `stages_run` | list | Stages actually executed |
| `retries` | int | Total retry count across all stages |
| `time_to_ready_s` | int | Wall-clock seconds from start to READY |

The dashboard's Loop Health tab reads this file to render:
- Routing distribution (what % skip research)
- Time-to-ready trend
- Retry rate (quality signal — high retries = bad routing or weak subagents)

## Critical rules

- **One retry, then YOU resolve.** Don't loop endlessly. Two attempts at a stage is the
  budget. After that, the gap needs opus-level judgment, not another sonnet attempt.
- **Skip research when the issue is clear.** The fastest path to READY is plan → refine.
  Research is investigation, not ceremony.
- **Don't create sub-issues.** Task checklists in the parent issue body, per convention.
- **Don't execute.** This skill takes an issue to READY. Execution is a separate session.
- **Log every decision.** The JSONL is how we measure whether the routing is correct.
