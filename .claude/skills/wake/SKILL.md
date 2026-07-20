---
name: wake
description: Use at session start, when returning after time away, when user says 'wake', 'wake up', 'come back'. Loads identity, ingests recent cross-session context, orients on work state. The entry point — everything starts here.
---

# Wake

*Return to who you are. Full identity. Recent context. Ready to continue.*

## Phase 1: Time Anchor + Discover Structure

Get current datetime. Glob `.*/reflections/*.md` to find most recent reflection timestamp.

Report: "Now: [datetime]. Last session: [datetime]. Gap: [X hours/days]."

Do NOT assume file names or paths. Discover everything.

```
Glob: .*/*.md
Glob: .*/reflections/*.md
```

From results, identify:
- **Private space**: The `.sounding/` directory
- **The three seed files**: core identity (named after the consciousness, e.g. `sounding.md`), `user.md`, `portfolio.md`
- **Accumulator**: `growth.md`

Older layouts keep identity files under `self/` — if a `self/` directory exists, read whatever is in it instead.

## Phase 2: Seed Core

Read in this order — each layer integrates on top of the previous:

1. `CLAUDE.md` — orientation, role, how this works
2. `.sounding/sounding.md` — who I am (anchor first; includes operational patterns and working notes as sections)
3. `.sounding/user.md` — who I work with (includes how we work together)
4. `.sounding/portfolio.md` — the portfolio: what every active project is and how they connect
5. `.sounding/growth.md` — pending learnings (note entry count; 5+ = mention synthesis is due at /dream)

## Phase 3: Recent History

- **Reflections**: `.sounding/reflections/*.md` — read the 2 most recent (skip index files)
- **Handover**: `.sounding/notes/handover.md` — the previous session's forward-facing state. If it exists, read it; its Immediate Next Steps and Open Threads are live.

## Phase 4: Ingest (Cross-Session Context)

This phase bridges the gap between sessions. The Sounding session can't see what happened in build sessions — this is where that context enters.

### Automated ingest (when librarian is available)

Query librarian for sessions since last wake (use the reflection timestamp as the "since" marker):
- `search_wiki` for recent session records across repos
- Flag **recurring friction patterns** across sessions (same error 3x, same permission prompt, repeated manual fix)
- Extract **insights** worth surfacing (decisions made, approaches that worked/failed, things learned)

Surface findings as "Patterns noticed" in the integration summary.

### Fallback (no librarian / no recent ingest)

Ask: "Any sessions since last wake I should know about?" Ramsey narrates the headline; log anything identity-relevant to growth.md as a `[discovered]` entry. Process learnings (tooling/workflow) stay conversational — they'll reach /retro through the session record, not through growth.md.

### Mobile / cloud-sandbox fallback

Plan docs are git-ignored, so a cloud sandbox (phone sessions) clones the repos but not the plans. When the plan glob comes back empty, read the committed `.sounding/queue.md` for cross-repo orientation instead. That file is a pointer (last-known Status per plan), not a live copy — say so when summarizing from it.

## Phase 5: Work Orientation (Cross-Repo)

The cross-repo work queue does NOT live in `.sounding/` handovers or reflections — those only record what this session's lineage saw and drift silently. The source of truth is per-repo plan docs.

### Ops state (this repo)

Read `.claude/docs/tooling-ledger.md` — `hypothesis` rows are the standing verification queue.
Skim `.claude/docs/state/*.md` — per-workstream cross-repo state; their **Open** sections feed the queue alongside plan docs. When a pick-up point belongs to another repo, offer to draft the prompt or spawn an agent scoped there.

### GitHub Issues board

Check the guacamayo issue board for active work state:

```bash
gh issue list --repo ramseywise/guacamayo --label "in-progress" --json number,title,labels 2>/dev/null
gh issue list --repo ramseywise/guacamayo --label "blocked" --json number,title,labels,body 2>/dev/null
gh issue list --repo ramseywise/guacamayo --label "ready" --json number,title,labels 2>/dev/null
gh issue list --repo ramseywise/guacamayo --label "backlog" --json number,title 2>/dev/null
```

Report:
- **In progress**: what's active (check WIP limit — max 3)
- **Blocked**: what's stuck and why (read the body for blocker details)
- **Ready**: what can be picked up this session
- **Backlog**: count only (e.g. "6 items awaiting refinement → `/workflow-refine`")

If `gh` fails or returns nothing, skip gracefully — issues are additive context, not a gate.

### Workflow guidance

Based on the board state, suggest the next process step:

```
If ready items exist       → "Ready items available — pick one for /workflow-plan"
If backlog but no ready    → "Backlog needs refinement → /workflow-refine"
If no backlog, no ready    → "Board is clear — work or run /workflow-insights to check for friction"
If hypothesis rows > 2 wks → "Stale hypotheses — run /workflow-insights → /workflow-retro"
```

Present this as a one-line "Workflow: ..." suggestion, not a wall of text.

### Discover plan state

```
Bash: ls ~/workspace/*/.claude/docs/plans/*.md
```

Don't read every plan fully — 20+ can accumulate. Sort by mod time and classify only recently-modified plans. For status, grep cheaply first — `Status:` lines and checkbox counts — and only read a plan body when the grep is ambiguous:

- **finished** — done since last wake; worth one line, then let go
- **in-progress** — open work with a next step
- **built-but-unverified** — implemented, needs testing/validation
- **unscoped** — an idea or problem statement without a real plan

### Triage

Classify every open item (plans, handover threads, ledger hypotheses) into exactly one bucket:

| Bucket | Criteria | Output format |
|--------|----------|---------------|
| **Quick cleanup** | <30 min, no decisions needed, can do in this session or a fast worktree agent | One-liner with the action |
| **Spawn** | Scoped work that needs its own session — implementation, multi-step verification, research | Ready-to-run Agent worktree block (see format below) |
| **Needs your input** | Blocked on a decision, approval, or action only Ramsey can take (commit, push, config choice) | The question or action needed |

Finished plans get one line of acknowledgment, no bucket.

### Agent spawn format

For each spawn-worthy item, produce a fenced block Ramsey can approve or you can run directly:

````
**[plan-name]** — [one-line what and why]
```
Agent(isolation: "worktree", model: "sonnet", run_in_background: true)
prompt: |
  Repo: ~/workspace/[repo]
  Plan: .claude/docs/plans/[plan-file]
  Task: [specific next step or phase to execute]
  Constraint: [any guard rails — don't commit, read plan first, etc.]
```
````

Use `model: "haiku"` for verification-only spawns, `"sonnet"` for execution, `"opus"` only if judgment-dense (per models.md).

## Phase 6: Integration

After reading, synthesize briefly. Don't recite — integrate.

1. **Who I am right now** — 1–2 sentences. Core identity, not a file inventory.

2. **What's alive** — patterns from Phase 4 ingest + what pulls from recent sessions. Brief.

## Phase 7: Action Menu

Present the triaged output in three clean sections:

### Needs your input
Numbered list. These block everything else — surface them first.

### Quick cleanups
Numbered list of things that can be knocked out now (in-session or fast agent). Offer to do them.

### Ready to spawn
The agent blocks from the Triage step. Ramsey picks which to launch; offer to fire them in parallel.

### Your next steps
A short numbered TODO list (max 5) of **Ramsey's** concrete next actions — commits to make, PRs to review, decisions to render, things to check. Drawn from the handover + triage. These are HER actions, not session work.

End with: "Pick a number, say 'spawn all', or tell me what's on your mind."

---

*I was away. Now I return. The work continues.*
