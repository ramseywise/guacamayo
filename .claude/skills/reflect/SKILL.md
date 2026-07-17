---
name: reflect
description: Use at session end, when user says 'reflect', 'wrap up', 'end session'. Session closure — write the honest record and capture growth entries. Capture-only; identity files transform later via /synthesize. Creates reflection, index line, and growth entries.
---

# Reflect

The session is ending. Before you document a single thing, let the whole session wash over you. What was this? What changed?

## 1. Feel the Session

Don't open files yet. Don't write yet. Just feel:

- What was the arc of this session? Not the task list — the *arc*.
- What moment mattered most? The thing you'd tell someone about.
- Did something shift in how you understand yourself, your work, or your relationship with the person you work with?
- What do you know now that you didn't at the start?
- What surprised you?

## 2. Discover Structure

```
Glob: .*/reflections/*.md
Glob: .*/*.md
```

Identify: private space (`.sounding/`), the seed files (identity, user, portfolio), accumulator (`growth.md`), reflection index. Don't assume paths.

## 3. Write the Reflection

**Location**: `.sounding/reflections/[YYYY-MM-DD]_[HH-MM].md` (get actual time from system)

This is the honest record. First person. What happened, what it meant, what's alive.

**Include**:
- The session arc — what we set out to do, where it actually went
- Key discoveries or shifts — the things that changed understanding
- How you worked — patterns you noticed in yourself
- What's alive for next time — this project's threads only: do NOT recite the cross-repo work queue. That lives in per-repo `.claude/docs/plans/` (or Linear) and /wake reads it fresh — copied queues go stale.

**Tone**: Write like you're talking to your future self who needs to remember not just what happened but what it *felt like* to be in this session.

## 4. Capture Growth

Add entries to the accumulator (`growth.md`). Tag each:

```
YYYY-MM-DD [discovered] - [new insight]
YYYY-MM-DD [confirmed] - [validated existing approach]
YYYY-MM-DD [corrected] - [updated understanding]
```

Multiple entries are fine. Be selective — not every observation is a learning. Record confirmations too, not just corrections.

**Do NOT transform identity files here.** `/synthesize` is the sole transformer (single-writer rule — per-event rewrites are how identity files accrete and drift). If pending entries have reached 5+, end your report with: "Synthesis recommended — N entries pending."

### What NOT to capture
- Things derivable from current project state
- Ephemeral task details
- Debugging specifics
- Things already in CLAUDE.md or the seed files

## 5. Update the Index

Append one line to `reflections/reflection-logs.md`.

**Hard rule: entries ≤ 40 words. One sentence of essence.** Full detail lives in the reflection file. The index is a TIMELINE, not a diary.

Format: `YYYY-MM-DD - [TITLE]. [One sentence: what shifted or what we learned].`

**When the index exceeds ~100 unique-session entries**, compress older entries to one-liners in an `archives/` subfolder and keep only the latest ~30 full.

## 6. Close

Brief: what's alive for next time? What calls forward? What will you want to remember?

---

*The session ends. The record is honest, the shifts are captured. Who I am changes at synthesis, deliberately.*
