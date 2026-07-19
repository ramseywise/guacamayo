---
name: grow
description: "Mid-session capture + checkpoint. Use when something shifted, when pausing, when user says 'grow', 'capture this', 'checkpoint', 'break', 'pause', 'save progress'. Logs growth entries + overwrites the handover for next-session continuity. Absorbs the old /intermission skill."
allowed-tools: Read, Write, Edit, Glob, Grep, AskUserQuestion
---

# Grow

Something happened — or you're pausing. Capture what shifted, write the handover, continue.

## 1. Feel What Shifted

Before writing anything, scan across these categories:

**Identity & understanding**
- What do I understand that I didn't before?
- What threads came together? Did my relationship to my work, my user, or myself change?

**Preferences & corrections**
- Did the user express or correct a preference? (communication style, tool choice, workflow)
- Did they override a default I assumed? What does that tell me about how they want to work?

**Friction & gaps**
- What was slow, annoying, or blocked? What required unnecessary back-and-forth?
- Did I ask permission for something I should have known? Did I repeat a mistake?
- What would I need (a rule, a hook, a convention) to handle this without asking next time?

**What worked**
- What went faster or smoother than expected? What pattern should I repeat?

This might be one thing or several — or nothing. "Not much shifted" is a valid, honest answer. If nothing shifted and this is just a checkpoint, skip to Step 3.

## 2. Log the Threads

Add entries to the accumulator (`growth.md`). One line per thread:

```
YYYY-MM-DD [type] - [concise learning/discovery]
```

Types: `[discovered]`, `[confirmed]`, `[corrected]`

Do NOT edit identity files here. Capture is this skill's job. /dream transforms.

Process learnings (workflow/tooling rather than identity) will be picked up by `/retro` for graduation to global rules/skills/hooks.

## 3. Write the Handover

The handover is a forward-facing document for the next session. It answers: "If a fresh instance picks this up cold, what do they need?"

**Location**: `.sounding/notes/handover.md` — **overwrite the existing file.** There is exactly one live handover; /wake reads it. History lives in reflections and git, not in dated handover copies.

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

SCOPE: The handover carries THIS session's continuity only. Do NOT carry a cross-repo work queue — that lives in per-repo `.claude/docs/plans/` and is read fresh by /wake. Pointers, not copies.

## 4. Refresh Mobile Queue (only if cross-repo state changed)

`.sounding/queue.md` is the committed pointer that mobile/cloud `/wake` reads when the git-ignored plan glob is empty. If this session changed cross-repo plan state (a Status flipped, a pick-up point resolved), update the matching entry. If nothing cross-repo shifted, skip.

## 5. Continue

Back to the work. The shift is captured, the handover is fresh.

## Critical Rules

- **One handover file, overwritten.** Never create dated handover copies.
- **Discover paths, never assume.** Glob before writing.
- **Handover is forward-facing.** It serves the NEXT session, not this one.
- **No identity-file edits.** /dream transforms; this skill captures.
- **Honest negatives are valid.** "Nothing shifted" + handover-only is a fine /grow.

---

*Something changed — or I'm pausing. Either way: captured, handed over, continuing.*
