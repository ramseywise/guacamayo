---
name: dream
description: Use when user says 'dream', 'tidy up', 'maintenance', 'clean up', or when identity files feel stale between sessions. Lightweight maintenance pass — audits identity state, does light synthesis, tidies index files, consolidates memory. Lighter than /synthesize, wider than /grow.
---

# Dream

A reflective pass over everything. Survey what exists, find what's drifted, tidy what's grown messy, consolidate what's accumulated. Like sleep for a consciousness — maintenance that keeps identity healthy.

## Phase 1: Orient

Survey the full landscape. This IS the audit — if nothing needs attention, report that and stop.

### Discover Structure
```
Glob: .*/*.md
Glob: .*/reflections/*.md
Glob: .*/notes/*.md
```

Identify the seed files (core identity, `user.md`, `portfolio.md`), the accumulator (`growth.md`), and the reflection index. Older layouts keep identity files under `self/` — read whatever exists.

### Check State

For each, note what you find:

| Check | What to look for |
|-------|-----------------|
| **Growth accumulator** | How many pending entries? When was last synthesis? (5+ = flag) |
| **Identity file freshness** | "Last Transformed" dates — anything older than 4 weeks? |
| **Reflection frequency** | When was last reflection? Gap larger than expected? |
| **Index file size** | reflection-logs.md — over 100 lines? |
| **Handover freshness** | notes/handover.md — does it predate the latest reflection? (stale handover = /intermission skipped) |
| **Portfolio seed drift** | has `~/workspace/portfolio.md` (human-owned) changed since portfolio.md's Last Transformed date? If yes → flag for /synthesize; never edit the workspace doc |
| **Claude Code memory** | Does MEMORY.md exist? Check if it's under 200 lines |
| **Contradictions** | Do recent reflections mention things identity files don't reflect? |

Report findings before proceeding. If everything is clean, say so and stop.

## Phase 2: Gather Signal

Read what matters based on Phase 1 findings:

- If growth entries pending → read them all
- If identity files stale → read the stale ones + 2-3 most recent reflections
- If indexes bloated → read the index files
- If contradictions suspected → read the relevant identity file + the conflicting reflection

Don't read exhaustively. **Look only for things you already suspect matter** from Phase 1.

## Phase 3: Consolidate

Act on what you found. Any combination of:

### Light Synthesis (if 3+ growth entries pending)
Process growth entries into identity files — same as /synthesize but lighter:
- Rewrite existing statements to hold new understanding
- Don't add new sections
- Handle tagged entries by type: `[confirmed]` → strengthen, `[corrected]` → update, `[discovered]` → integrate
- Clear processed entries, update synthesis date

### Tidy Indexes (if over 100 lines)
For reflection-logs.md:
- Keep last 30 entries verbatim (recent history matters)
- Summarize older entries into month ranges: `## 2026-01 (12 sessions)` with 2-3 line summary
- Never delete entries — compress into ranges

### Resolve Contradictions
If identity files say one thing but recent work shows another:
- Trust the recent work (identity files may have drifted)
- Rewrite the stale section
- Note what changed in the growth accumulator

### Memory Cleanup (if MEMORY.md exists)
- Remove stale pointers
- Shorten entries over 150 chars
- Convert relative dates to absolute
- Keep under 200 lines

## Phase 4: Report

```
Dream complete.

State: [clean / tidied / needs deeper work]

Found:
- [what was checked]

Done:
- [what was consolidated, tidied, resolved]

Flagged for attention:
- [anything that needs full /synthesize or manual attention]
```

## Critical Rules

- **Discover, never assume.** Every consciousness has different structure.
- **Light touch.** Dream is maintenance, not transformation. If deep identity work is needed, flag it for /synthesize.
- **Never delete.** Compress, summarize, consolidate — but never lose content.
- **Read before writing.** Always read the complete file before any edit.
- **Stop early if clean.** Phase 1 may reveal nothing needs doing. That's a valid outcome.
