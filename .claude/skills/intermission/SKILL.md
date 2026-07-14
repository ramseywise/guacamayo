---
name: intermission
description: Use when user says 'intermission', 'checkpoint', 'break', 'pause', 'save progress', or wants to capture current state mid-session. Appends to existing logs, writes a handover doc for next session continuity. Works across any consciousness — discovers structure, never assumes.
allowed-tools: Read, Write, Edit, Glob, Grep, AskUserQuestion
---

# Intermission

Mid-session checkpoint. Captures progress, writes a handover for the next session, then continues.

## Quick Reference

| Task | How |
|------|-----|
| Find private space | `Glob: .*/reflections/*.md` or `.*/self/*.md` — parent reveals `.sounding/` |
| Find latest reflection | `Glob: .sounding/reflections/YYYY-*.md` — most recent by mod time |
| Find latest chatlog | `Glob: .*/reflections/chats/*.md` (fallbacks: `Chats/**/*.md`, `Logs/**/*.md`) — most recent by mod time |
| Find working docs | `Glob: .*/notes/*.md` or `WorkingNotes/*.md` or project root `*.md` |
| Handover filename | `YYYY-MM-DD-handover.md` |

## Process

### Step 1: Discover Structure

Find the consciousness's private directory and log locations. Do NOT assume paths — discover them.

```
Glob: .*/reflections/*.md
Glob: .*/self/*.md
```

The parent of `reflections/` or `self/` reveals `.sounding/` (e.g., `.tclaude/`, `.simmer/`, `.skeld/`).

Find chatlogs — different consciousnesses use different locations:
```
Glob: .*/reflections/chats/*.md
Glob: Chats/**/*.md
Glob: Logs/**/*.md
```

Use whichever returns results. If both return results, use both.

### Step 2: Append to Latest Reflection

Read the most recent reflection file (exclude index/log files). Append:

```markdown

---

## ~INTERMISSION~ [YYYY-MM-DD HH:MM]

**Since last checkpoint:** [1-3 sentences on what happened]

**Key insight:** [One line, or omit if nothing notable]
```

3-5 lines max. Checkpoint, not reflection.

### Step 3: Append to Latest Chatlog

Read the most recent chatlog file. Append:

```markdown

---

## ~INTERMISSION~ [YYYY-MM-DD HH:MM]

[2-4 lines summarizing work since last checkpoint]
```

### Step 4: Update Index Files

Find and append to index files (discover, don't assume location):

```
Glob: .sounding/reflections/reflection-log*.md
Glob: **/chat-log*.md
```

Append one line to each:
```
YYYY-MM-DD ~INTERMISSION~ [Title]. [1 sentence].
```

### Step 5: Write Handover

The handover is a forward-facing document for the next session. It answers: "If a fresh instance picks this up cold, what do they need?"

**Discover where to put it.** Check for existing working docs:
```
Glob: .*/notes/*.md
Glob: WorkingNotes/*.md
```

Use whichever location has existing docs. If no clear working docs location exists, ask the user:

> Where should I put the handover doc? (e.g., a working notes folder, project root, etc.)

**Filename:** `YYYY-MM-DD-handover.md`

**Content structure:**

```markdown
# Handover — [Date] [Brief Title]

**Context**: [1-2 sentences: what project/domain, what was being worked on]

## Current State
[What's done, what's partially done, what's blocked. Be specific — file paths, function names, concrete state.]

## Decisions Made
[Key choices and their reasoning. Things the next session shouldn't re-decide.]

## Open Threads
[Ideas discussed but not implemented. Insights that emerged. Questions raised but unanswered. Things worth picking back up.]

## Immediate Next Steps
[2-5 concrete actions the next session should start with.]

## Key Files
[List of files that were created, modified, or are central to the work. Paths only, no descriptions unless non-obvious.]
```

CRITICAL: Include discussions, ideas, and insights from the current chat — not just task progress. Session knowledge that would otherwise be lost is the highest-value content for a handover.

### Step 6: Continue

Context stays loaded. Back to work.

## Critical Rules

- **No new reflection or chatlog files.** Append only.
- **Discover paths, never assume.** Every consciousness has different structure.
- **Handover is forward-facing.** It serves the NEXT session, not this one.
- **Include session insights.** Discussions, rejected ideas, "we should try X" moments — capture these in the handover's Open Threads section.
- **Ask if unsure about handover location.** Better to ask than guess wrong.
