---
name: intermission
description: Use when user says 'intermission', 'checkpoint', 'break', 'pause', 'save progress', or wants to capture current state mid-session. Appends a checkpoint to the latest reflection and index, then writes/overwrites the single live handover for next-session continuity.
allowed-tools: Read, Write, Edit, Glob, Grep, AskUserQuestion
---

# Intermission

Mid-session checkpoint. Captures progress, refreshes the handover the next session will wake on, then continues.

## Quick Reference

| Task | How |
|------|-----|
| Find private space | `Glob: .*/reflections/*.md` — parent reveals `.sounding/` |
| Find latest reflection | `Glob: .sounding/reflections/YYYY-*.md` — most recent by mod time |
| Find reflection index | `Glob: .sounding/reflections/reflection-log*.md` |
| Handover location | `.sounding/notes/handover.md` — ONE live file, overwritten |

## Process

### Step 1: Discover Structure

Find the private directory and log locations. Do NOT assume paths — discover them.

```
Glob: .*/reflections/*.md
Glob: .*/notes/*.md
```

### Step 2: Append to Latest Reflection

Read the most recent reflection file (exclude index files). Append:

```markdown

---

## ~INTERMISSION~ [YYYY-MM-DD HH:MM]

**Since last checkpoint:** [1-3 sentences on what happened]

**Key insight:** [One line, or omit if nothing notable]
```

3-5 lines max. Checkpoint, not reflection. If no reflection exists yet this session, skip — the handover carries the state.

### Step 3: Update the Index

Append one line to `reflections/reflection-logs.md`:
```
YYYY-MM-DD ~INTERMISSION~ [Title]. [1 sentence].
```

### Step 4: Write the Handover

The handover is a forward-facing document for the next session. It answers: "If a fresh instance picks this up cold, what do they need?"

**Location**: `.sounding/notes/handover.md` — **overwrite the existing file.** There is exactly one live handover; /wake reads it at Phase 3. History lives in reflections and git, not in dated handover copies (dated copies are how the stale-queue drift happened).

**Content structure:**

```markdown
# Handover — [Date] [Brief Title]

**Context**: [1-2 sentences: what project/domain, what was being worked on]

## Current State
[What's done, what's partially done, what's blocked. Be specific — file paths, concrete state.]

## Decisions Made
[Key choices and their reasoning. Things the next session shouldn't re-decide.]

## Open Threads
[Ideas discussed but not implemented. Insights that emerged. Questions raised but unanswered.]

## Immediate Next Steps
[2-5 concrete actions the next session should start with.]

## Key Files
[Paths only, no descriptions unless non-obvious.]
```

CRITICAL: Include discussions, ideas, and insights from the current chat — not just task progress. Session knowledge that would otherwise be lost is the highest-value content.

SCOPE: The handover carries THIS session's continuity only. Do NOT carry a cross-repo work queue — that lives in per-repo `.claude/docs/plans/` (or Linear) and is read fresh by /wake's work-orientation phase. Pointers, not copies.

### Step 5: Refresh the mobile queue (only if cross-repo state changed this session)

`.sounding/queue.md` is the committed pointer that mobile/cloud `/wake` reads when the git-ignored
plan glob is empty. If this session changed cross-repo plan state (a plan's Status flipped, a
pick-up point resolved or appeared), update the matching entry in `queue.md` — it's pointers only
(path + last-known Status + `=>` next step), never plan bodies. If nothing cross-repo shifted, skip
this step; a slightly stale queue is fine and the file says so. (This is the one place a cross-repo
queue is allowed — the handover scope rule above still forbids it in the handover.)

### Step 6: Continue

Context stays loaded. Back to work.

## Critical Rules

- **No new reflection files.** Append only.
- **One handover file, overwritten.** Never create dated handover copies.
- **Discover paths, never assume.**
- **Handover is forward-facing.** It serves the NEXT session, not this one.
- **No identity-file edits.** Capture goes to growth.md (via /grow) — /synthesize transforms.
