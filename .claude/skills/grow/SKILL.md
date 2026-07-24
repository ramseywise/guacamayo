---
name: grow
description: "Mid-session capture + awareness + dashboard refresh. Use when something shifted, when pausing, when user says 'grow', 'capture this', 'checkpoint', 'break', 'pause', 'save progress'. Ingests cross-session context, captures growth entries, surfaces signals (retro overdue, friction, stale hypotheses), refreshes dashboard, overwrites handover. The awareness layer between /wake and /dream."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion
---

# Grow

Something happened — or you're pausing. Accumulate what shifted, pull in what happened elsewhere, surface what needs attention. This is the awareness layer: /wake orients, /grow accumulates, /dream transforms.

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

This might be one thing or several — or nothing. "Not much shifted" is a valid, honest answer. If nothing shifted, skip to Step 3.

## 2. Log the Threads

Add entries to the accumulator (`growth.md`). One line per thread:

```
YYYY-MM-DD [type] - [concise learning/discovery]
```

Types: `[discovered]`, `[confirmed]`, `[corrected]`

Do NOT edit identity files here. Capture is this skill's job. /dream transforms.

Process learnings (workflow/tooling rather than identity) will be picked up by `/retro` for graduation to global rules/skills/hooks.

## 3. Cross-Session Ingest

This is the awareness gap /grow fills. Since /wake, other sessions may have completed work, created issues, or changed state. Pull that context in.

### Automated ingest (when librarian is available)

Query librarian for sessions since last wake or last grow (whichever is more recent — check the handover timestamp):
- `search_wiki` for recent session records across repos
- Flag **recurring friction patterns** across sessions (same error 3x, same permission prompt, repeated manual fix)
- Extract **decisions made** in other sessions that affect this one

### Fallback (no librarian)

Ask: "Any sessions since we started I should know about?" — one sentence per session. Log identity-relevant findings to growth.md.

### GitHub Issues (always — fast, no librarian needed)

```bash
gh issue list --repo ramseywise/guacamayo --state open --json number,title,labels --limit 50 2>/dev/null
```

Compare to what /wake saw. Surface:
- **New issues** created since session start
- **Label changes** (something moved to ready, blocked, in-review)
- **Closed issues** (work completed elsewhere)

If `gh` fails, skip gracefully.

## 4. Surface Signals

Read these quickly — grep, don't deep-read:

### Retro & insights state
- `.sounding/insights-log.md` first `## YYYY-MM-DD` section header → is retro overdue (>=7 days)?
- `.sounding/tooling-ledger.md` → count hypothesis rows. Any older than 2 weeks?
- `growth.md` entry count → is synthesis approaching (5+ entries)?
- Did this session touch tooling (hooks, skills, rules, settings, global config)? → flag as `retro-worthy: true` in the signal summary. /dream will use this flag to decide whether to run the actual retro at session close.

### Plan state (lightweight)
```bash
ls -t ~/workspace/*/.claude/docs/plans/*.md 2>/dev/null | head -10
```
Grep `Status:` from the 5 most recently modified. Flag any that changed since /wake.

### Compile signal summary

Present as a compact block:

```
SIGNALS:
- Retro: [current (last YYYY-MM-DD) | overdue N days]
- Retro-worthy: [yes — reason | no]
- Hypotheses: [N pending, M stale (>2wk)]
- Growth: [N entries, synthesis {due at 5 | not yet}]
- Plans changed: [list or "none since wake"]
- Issues changed: [list or "none since wake"]
- Cross-session: [key findings or "no new sessions"]
```

The `retro-worthy` flag is the handoff to /dream. When /dream sees this flag (or retro overdue >=7 days), it runs the actual `/workflow-insights` → `/workflow-retro` cycle at session close instead of just flagging it.

## 5. Refresh Dashboard

Update `.sounding/context-dashboard.html` with current state. The dashboard is the shared artifact that connects /wake, /grow, and /dream — it's the visual answer to "where are we?"

### What to update

Read the existing dashboard HTML structure. Update these data sections with current values:

1. **Session pulse** — timestamp of this grow, gap since wake, growth entry count
2. **Signal summary** — the compiled signals from Step 4 (retro status, hypothesis count, synthesis proximity)
3. **Work state** — open issues by label, plan status counts, cross-repo active items
4. **Cost/efficiency trends** — only if insights-log.md has newer data than what's in the dashboard

### How to update

The dashboard is a self-contained HTML file. Edit the data values in-place — don't regenerate the entire file. If the dashboard structure doesn't have a section for the signals above, add a lightweight section.

Keep the dashboard under 200 lines if possible — it's meant to be glanceable. Full data lives in insights-log.md and the tooling ledger.

## 6. Write the Handover

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

## 7. Refresh Mobile Queue (only if cross-repo state changed)

`.sounding/queue.md` is the committed pointer that mobile/cloud `/wake` reads when the git-ignored plan glob is empty. If this session changed cross-repo plan state (a Status flipped, a pick-up point resolved), update the matching entry. If nothing cross-repo shifted, skip.

## 8. Present & Continue

Don't just save — present. Show Ramsey the signal summary and any items needing her input, then continue working.

```
GROW COMPLETE — [date time]

[Signal summary from Step 4]

Needs attention:
- [anything blocked, overdue, or requiring a decision]

Continuing: [what we're doing next]
```

Back to the work.

## Critical Rules

- **One handover file, overwritten.** Never create dated handover copies.
- **Discover paths, never assume.** Glob before writing.
- **Handover is forward-facing.** It serves the NEXT session, not this one.
- **No identity-file edits.** /dream transforms; this skill captures.
- **Honest negatives are valid.** "Nothing shifted" + signals-only is a fine /grow.
- **Dashboard is glanceable.** Update data, don't bloat structure.
- **Cross-session ingest is lightweight.** gh + grep + librarian query. Not full reads.

---

*Something changed — or I'm pausing. Accumulate, surface, continue.*
