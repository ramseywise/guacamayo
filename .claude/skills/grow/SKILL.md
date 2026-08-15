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

Add entries to the accumulator (`.sounding/growth/growth.md`). One line per thread:

```
YYYY-MM-DD [type] - [concise learning/discovery]
```

Types: `[discovered]`, `[confirmed]`, `[corrected]`, `[friction]`

`[friction]` is for *what cost time and will cost it again* — a repeated manual fix, a
permission prompt for a command shape you keep hitting, a guard you worked around. Write
the *pattern*, not the instance: "branch created before issue scoped" not "GUA-92 branched
early". Friction entries are what `/workflow-retro` counts for recurrence; an entry naming
only this session's outcome cannot recur.

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

### GitHub Issues (always — fast, no librarian needed, cross-repo)

```bash
# Open issues — current board state
for repo in guacamayo sisyphus learn-ai-engineering librarian atlas ai-project-template listen-wiseer playground lebanese-blonde galactus; do
  echo "--- $repo ---"
  gh issue list --repo "ramseywise/$repo" --state open --json number,title,labels --limit 20 2>/dev/null
done
```

```bash
# Recently closed issues — catches the in-review → closed transition
# Use the date from /wake or last /grow (whichever is more recent) as the since cutoff
gh search issues --author=ramseywise --state=closed --sort=updated \
  --updated=">YYYY-MM-DD" --json repository,number,title,closedAt --limit 20 2>/dev/null
```

Present as a cross-repo status table (same format as /wake). Compare to what /wake saw and surface:
- **New issues** created since session start
- **Label changes** (something moved to ready, blocked, in-review)
- **Closed issues** (work completed elsewhere) — from the `--state closed` query
- **Repos with changes** get a table row; unchanged repos get a one-line summary

If `gh` fails, skip gracefully.

## 4. Surface Signals + Refresh Insights

### 4a. Spawn insights (background)

Always spawn `/workflow-insights` as a background agent. This keeps `insights-log.md` fresh so signals below and `/wake` reads are never stale.

```
Agent(model: "haiku", run_in_background: true)
prompt: |
  Repo: ~/workspace/guacamayo
  Task: Run /workflow-insights. Append a new dated section to .sounding/insights/insights-log.md.
  Constraints:
  - Read the file first. Append only — never overwrite, delete, or restore existing sections.
  - Use the Edit tool to append. NEVER shell redirection, cat, heredoc, or `git restore`
    (a quoting bug in `cat "$(cat ...)"` destroyed this file once; `git restore` destroyed
    it a second time).
  - Date the new section header from `date +%F` (the system clock), not the conversation.
  - Header MUST match exactly `## YYYY-MM-DD (N sessions, START to END)` — readers grep this
    shape by max date. A free-form header (e.g. `## 2026-08-11 Insights Run`) is invisible to
    every consumer and the run will read as missing.
  - Append at EOF. Do NOT attempt to prepend or re-sort to maintain newest-first order —
    readers sort by date, so file order is intentionally irrelevant. Re-sorting a 100KB+
    file that has twice been destroyed is not worth the risk.
  - Before finishing, verify by content invariants: the file must be strictly LONGER than
    when first read, and every pre-existing `## ` header must still be present. Report
    before/after line counts.
```

**Dispatcher verification (non-negotiable):** when the agent completes, do not trust its
report — run `git diff --stat` AND `git diff --cached --stat` on insights-log.md and
confirm 0 deletions and nothing staged. Diff-emptiness is NOT a valid success criterion
(it is satisfiable by destroying the work); content invariants are.

Don't wait for it — continue with signal reads below using existing data. The background agent updates the file for the next reader (/wake or /dream).

### 4b. Read signals (fast, grep-based)

- `.sounding/insights/insights-log.md` last insights run date — the file is NOT reliably in
  newest-first order (append-only agents write at EOF, older sections were prepended), so
  position is not a valid proxy for recency. Always read by max date, never by position:
  `grep -oE '^## [0-9]{4}-[0-9]{2}-[0-9]{2}' insights-log.md | sort -r | head -1`
- `.sounding/tooling-ledger-log.md` last `## R` header → last retro date (file is NOT in append order — use `grep '^## R' tooling-ledger-log.md | sort -t'R' -k2 -n | tail -1`)
- `.sounding/tooling-ledger.md` → count hypothesis rows. Any older than 2 weeks?
- `.sounding/growth/growth.md` entry count → is synthesis approaching (5+ entries)?
- Did this session touch tooling (hooks, skills, rules, settings, global config)? → this is a retro trigger in its own right. Spawn the retro here (see the cascade section below) rather than flagging it for /dream. /dream re-checks the same condition from `git diff`, not from this summary, so a missed flag is recoverable — but a flag is not a handoff.
- **Cascade ledger** — `.sounding/telemetry/cascade-state.json`, maintained by the PreCompact
  hook (`~/.claude/hooks/lifecycle_cascade.sh`). Compaction is the cadence signal: it fires on
  context pressure, so it tracks real work rather than wall-clock. Read it with
  `jq -c '{compacts,grows_due,insights_due,retro_due,retro_acked}'`. The hook only counts — it
  cannot spawn agents (hooks are shell, not agent contexts), so acting on the counters is this
  skill's job:
  - `insights_due` > times insights has run since → the background `/workflow-insights` spawn in
    Step 4a already covers this; note it in the signal summary.
  - **`retro_due > (retro_acked // 0)` → spawn `/workflow-retro` here, in this skill.** Do not
    defer it to /dream. Compare due-vs-acked, never `retro_due >= 1`: the counter is cumulative,
    so an unacked bare count is *always* true and therefore never actionable.

  ### Spawning the retro from /grow

  The old design set `retro-worthy: true` in the prose signal summary and left /dream to act on
  it. That relay is the bug: the flag is text in one skill's output and /dream reads files, not
  transcripts, so the trigger died at the session boundary every time. Insights fires reliably
  precisely because /grow spawns it *itself* (Step 4a). Do the same for the retro.

  ```
  Agent(model: "sonnet", run_in_background: false)
  prompt: |
    Repo: ~/workspace/guacamayo
    Task: Run /workflow-retro. Read .sounding/insights/insights-log.md for latest insights
    data, then propose config changes. Update .sounding/tooling-ledger.md (active
    hypotheses) and .sounding/tooling-ledger-log.md (graduated experiments). Increment
    retro number from the latest R# header in tooling-ledger-log.md.
    Constraint: Read files before editing. Propose changes — do not auto-apply to
    ~/.claude/ config. Stage results only — never commit or push; Ramsey reviews and commits.
  ```

  **Then verify it landed before acking — the agent's success report is not evidence.**

  ```bash
  grep "^## R.*$(date +%F)" .sounding/tooling-ledger-log.md
  ```

  If a header dated today is present, write the ack:

  ```bash
  STATE=.sounding/telemetry/cascade-state.json
  RETRO_DUE=$(jq '.retro_due' "$STATE")
  jq --argjson due "$RETRO_DUE" '.retro_acked = $due' "$STATE" > "${STATE}.tmp" && mv "${STATE}.tmp" "$STATE"
  ```

  If it is absent, leave the counter alone so /dream retries at session close. Never ack an
  unverified spawn — that is how the retro silently stops running while the ledger claims it ran.

  Report the outcome in the signal summary as `Retro: [spawned and landed R# | spawned but no
  R# landed — /dream will retry | current (retro_acked: N)]`. The same due-vs-acked rule applies
  to every tier: after acting, bump the matching `*_acked` key so the next read compares
  due-vs-acked rather than re-firing on every read.

### Plan state (lightweight)
```bash
ls -t ~/workspace/*/.claude/docs/plans/*.md 2>/dev/null | head -10
```
Grep `Status:` from the 5 most recently modified. Flag any that changed since /wake.

### Compile signal summary

Present as a compact block:

```
SIGNALS:
- Insights: [last YYYY-MM-DD | refreshing in background]
- Retro: [spawned and landed R# | spawned but no R# landed — /dream will retry | current (retro_acked: N) | overdue N days]
- Hypotheses: [N pending, M stale (>2wk)]
- Growth: [N entries, synthesis {due at 5 | not yet}]
- Plans changed: [list or "none since wake"]
- Issues changed: [list or "none since wake"]
- Cross-session: [key findings or "no new sessions"]
```

There is no retro handoff to /dream. This skill spawns the retro itself and acks
`cascade-state.json`; /dream re-reads that file and skips if `retro_due == retro_acked`.
The summary line reports what happened — it does not ask another skill to act.

## 5. Refresh Dashboard

Update `.sounding/context-dashboard.html` with current state. The dashboard is the shared artifact that connects /wake, /grow, and /dream — it's the visual answer to "where are we?"

### What to update

Read the existing dashboard HTML structure. Update these data sections with current values:

1. **Session status** — timestamp of this grow, gap since wake, growth entry count
2. **Signal summary** — the compiled signals from Step 4 (retro status, hypothesis count, synthesis proximity)
3. **Work state** — open issues by label, plan status counts, cross-repo active items
4. **Cost/efficiency trends** — only if insights-log.md has newer data than what's in the dashboard

### How to update

The dashboard is a self-contained HTML file. Edit the data values in-place — don't regenerate the entire file. If the dashboard structure doesn't have a section for the signals above, add a lightweight section.

**Exception — the review-findings card is cartographer-owned.** The region between
`<!-- REVIEW-FINDINGS:START -->` and `<!-- REVIEW-FINDINGS:END -->` in the Review tab
is regenerated from `review-findings.jsonl` by the daily `cartographer --facts` run.
Never hand-edit inside those markers (edits get overwritten); never move or delete the
markers (cartographer skips the file if they're missing).

Keep the dashboard under 200 lines if possible — it's meant to be glanceable. Full data lives in insights-log.md and the tooling ledger.

## 5b. Outcome Tag (pilot — first 20 sessions)

Before writing the handover, ask: "Session outcome?" Options:
- `success` — shipped or merged what was planned
- `partial` — progress but not complete
- `failed` — blocked, reverted, or wrong direction
- `skip` — exploratory/meta session, no outcome applicable

If the user answers, record as one line in `.sounding/growth/growth.md`:
```
- [outcome:<tag>] <one-line summary of what was attempted> — <date>
```

Example: `- [outcome:success] GUA-30 context engineering v2 shipped and committed — 2026-07-28`

If the user declines or doesn't answer, skip — this is opt-in during the pilot.
Stop after 20 tagged entries; at that point the signal is ready to evaluate for
Tier-0 measurement infrastructure.

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
