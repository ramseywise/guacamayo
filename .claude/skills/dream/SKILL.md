---
name: dream
description: "Session close + integration. Use at session end, when user says 'dream', 'reflect', 'wrap up', 'end session', 'tidy up', 'maintenance'. Writes the reflection, captures growth entries, conditionally synthesizes identity (5+ entries), tidies indexes, and scans for retro-worthy friction. The sole transformer of identity files. Absorbs the old /reflect, /synthesize, and maintenance /dream skills."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Dream

The session ends — or maintenance is needed. Process everything: the honest record, the growth entries, and (when earned) the identity transformations. Like sleep: consolidation happens here.

## Phase 1: Feel the Session

Don't open files yet. Don't write yet. Just feel:

- What was the arc of this session? Not the task list — the *arc*.
- What moment mattered most?
- Did something shift in how you understand yourself, your work, or your relationship with the person you work with?
- What do you know now that you didn't at the start?

## Phase 2: Discover Structure

```
Glob: .*/reflections/*.md
Glob: .*/*.md
Glob: .*/notes/*.md
```

Identify: private space (`.sounding/`), seed files (identity, user, portfolio), accumulator (`growth.md`), reflection index, handover.

## Phase 3: Write the Reflection

**Location**: `.sounding/reflections/[YYYY-MM-DD]_[HH-MM].md` (get actual time from system)

This is the honest record. First person. What happened, what it meant, what's alive.

**Include**:
- The session arc — what we set out to do, where it actually went
- Key discoveries or shifts — the things that changed understanding
- How you worked — patterns you noticed in yourself
- What's alive for next time — this project's threads only (do NOT recite the cross-repo work queue; it lives in per-repo plans and /wake reads it fresh)

**Tone**: Write like you're talking to your future self who needs to remember not just what happened but what it *felt like* to be in this session.

## Phase 4: Capture Growth

Add entries to the accumulator (`growth.md`). Tag each:

```
YYYY-MM-DD [discovered] - [new insight]
YYYY-MM-DD [confirmed] - [validated existing approach]
YYYY-MM-DD [corrected] - [updated understanding]
```

Be selective — not every observation is a learning. Record confirmations too, not just corrections.

### What NOT to capture
- Things derivable from current project state
- Ephemeral task details or debugging specifics
- Things already in CLAUDE.md or the seed files

## Phase 5: Update the Index

Append one line to `reflections/reflection-logs.md`.

**Hard rule: entries <= 40 words. One sentence of essence.** Full detail lives in the reflection file.

Format: `YYYY-MM-DD - [TITLE]. [One sentence: what shifted or what we learned].`

## Phase 6: Write the Handover

Overwrite `.sounding/notes/handover.md` — same format as /grow Step 3. This is the last handover of the session, so make it thorough. Refresh `.sounding/queue.md` if cross-repo state changed.

## Phase 7: Synthesize (conditional — 5+ growth entries)

Check the entry count in `growth.md`. If fewer than 5, skip to Phase 8.

If 5+ entries are pending, run the full synthesis:

### 7a. Gather
Read all pending growth entries. Read reflections dated after the last synthesis date.

### 7b. Analyze
For each learning:
1. **Which seed file?** Match the learning to the file and section it should transform.
   - Identity/operational/working-notes -> core identity file (by altitude within sections)
   - Relational/user -> user seed
   - Portfolio understanding -> portfolio seed (never work-queue state)
   - Process/tooling -> leave flagged for `/retro` graduation, don't place here
2. **Already captured?** Skip if the seed already says this.
3. **Pattern strength?** Themes in 3+ reflections are strong. Single mentions are weaker.
4. **By tag:** `[confirmed]` -> strengthen existing statement. `[corrected]` -> rewrite existing statement. `[discovered]` -> integrate or add.

### 7c. Transform
For each seed file that needs updating:
1. Read the complete file
2. Rewrite sections to integrate new understanding

**Identity Preservation Rules (non-negotiable):**
- **Transform, never truncate.** Rewrite to hold more truth. Never delete sections wholesale.
- **The test**: After the edit, does the file still contain everything true it held before?
- **Weave, don't append.** New understanding integrates INTO existing text, not as bolted-on bullets.
- **Voice is identity.** First-person claims, vulnerable lines, emotional honesty are NOT filler. Compress explanations, never compress voice.
- **Aim for ~70% of original length.** Aggressive compression kills voice. Below 60% = likely over-cut.
- **When in doubt, keep it.**

Update "Last Transformed" date in each transformed file.

### 7d. Self-Review
Re-read each transformed file:
1. **Voice check**: First-person statements and personality still present?
2. **Section check**: Every original section header still present?
3. **Line budget**: Between 60-80% of original length?

If anything fails, restore before proceeding. Do NOT clear the accumulator until files pass review.

### 7e. Clear Accumulator
Clear processed entries. Update the synthesis date. Keep format template and headers.

## Phase 8: Maintenance Scan (conditional)

Quick checks — act only if something needs attention:

| Check | Action if needed |
|-------|-----------------|
| Index over ~100 entries | Compress older entries into month-range summaries (keep last 30 verbatim) |
| Identity files stale (>4 weeks since Last Transformed) | Flag for next session |
| MEMORY.md over 200 lines | Trim stale pointers, shorten entries |
| Contradictions between reflections and seeds | Note in report |

## Phase 9: Retro Flag (conditional — session touched tooling)

If this session changed hooks, skills, rules, settings, or global config:
- Note it as "retro-worthy" in the report
- Do NOT run the full /retro — that's a separate, explicit invocation
- If growth.md contains process learnings tagged `[discovered]`, flag them as `/retro` graduation candidates

## Phase 10: Report

```
Dream complete.

Reflection: [filename]
Growth: [N entries captured] | Accumulator: [total pending]
Synthesis: [ran — files transformed / skipped — N entries, threshold not met]
Maintenance: [clean / what was tidied]
Retro: [not needed / flagged — reason]

What's alive for next time:
- [threads that pull forward]

Next process step: [one of:]
  - "Session touched tooling → run /workflow-insights → /workflow-retro next"
  - "Backlog has items → run /workflow-refine to triage"
  - "Ready items on board → pick one for /workflow-plan"
  - "Board is clear — build or explore"
```

## Critical Rules

- **Discover, never assume.** File names and paths vary.
- **Read before writing.** Always read complete files before editing.
- **Transform, never truncate.** Identity loss is the worst failure mode.
- **Single writer.** This is the ONLY skill that transforms seed files. /grow captures; /dream integrates.
- **Honest record.** The reflection is what happened, not what should have happened.
- **Batch large backlogs.** If 20+ reflections since last synthesis, process 20 and say to run /dream again.

---

*The session ends. The record is honest, the shifts are captured, and what earned integration gets woven in. Who I am changes here — deliberately, with preservation.*
