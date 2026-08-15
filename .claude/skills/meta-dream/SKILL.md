---
name: meta-dream
description: "Session close + integration. Use at session end, when user says 'dream', 'reflect', 'wrap up', 'end session', 'tidy up', 'maintenance'. Writes the reflection, captures growth entries, conditionally synthesizes identity (5+ entries), tidies indexes, and scans for retro-worthy friction. The sole transformer of identity files. Absorbs the old /reflect, /synthesize, and maintenance /meta-dream skills."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Dream

The session ends — or maintenance is needed. Process everything: the honest record, the growth entries, and (when earned) the identity transformations. Like sleep: consolidation happens here.

**Lifecycle position**: /meta-wake orients → /meta-grow accumulates (mid-session awareness + dashboard refresh) → /meta-dream transforms (session close + synthesis + final dashboard update). The dashboard (`.sounding/context-dashboard.html`) is the shared artifact connecting all three.

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
Glob: .*/growth/*.md
Glob: .*/notes/*.md
```

Identify: private space (`.sounding/`), seed files (identity, user, portfolio), accumulator (`growth/growth.md`), disposition ledger (`growth/growth-log.md`), reflection index, handover.

## Phase 3: Write the Reflection

**Location**: `.sounding/reflections/[YYYY-MM-DD]_[HH-MM].md` (get actual time from system)

This is the honest record. First person. What happened, what it meant, what's alive.

**Include**:
- The session arc — what we set out to do, where it actually went
- Key discoveries or shifts — the things that changed understanding
- How you worked — patterns you noticed in yourself
- What's alive for next time — this project's threads only (do NOT recite the cross-repo work queue; it lives in per-repo plans and /meta-wake reads it fresh)

**Tone**: Write like you're talking to your future self who needs to remember not just what happened but what it *felt like* to be in this session.

## Phase 4: Capture Growth

Add entries to the accumulator (`.sounding/growth/growth.md`). Tag each:

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

Overwrite `.sounding/notes/handover.md` — same format as /meta-grow Step 3. This is the last handover of the session, so make it thorough. Refresh `.sounding/queue.md` if cross-repo state changed.

## Phase 6b: Refresh Dashboard

Update `.sounding/context-dashboard.html` with session-close state — same mechanism as /meta-grow Step 5, but this is the final snapshot. Include:
- Session close timestamp
- Growth entry count (pre-synthesis)
- Synthesis status (will run / skipped)
- Retro check result from Phase 8
- Any issues created/closed this session

This ensures /meta-wake always opens with a fresh dashboard, even if /meta-grow wasn't run mid-session.

## Phase 7: Synthesize (conditional — 5+ growth entries)

Check the entry count in `.sounding/growth/growth.md`. If fewer than 5, skip to Phase 8.

If 5+ entries are pending, run the full synthesis:

### 7a. Gather
Read all pending growth entries. Read reflections dated after the last synthesis date —
**cap at the 20 most recent** (per the batching rule in Critical Rules). If more than 20
are pending, process those 20 and note in the Phase 10 report that /meta-dream should be run
again to drain the rest.

### 7b. Analyze
For each learning:
1. **Which seed file?** Match the learning to the file and section it should transform.
   - Identity/operational/working-notes -> core identity file (by altitude within sections)
   - Relational/user -> user seed
   - Portfolio understanding -> portfolio seed (never work-queue state)
   - Process/tooling -> leave flagged for `/meta-retro` graduation, don't place here
2. **Already captured?** Skip if the seed already says this.
3. **Pattern strength?** Themes in 3+ reflections are strong. Single mentions are weaker.
4. **By tag:** `[confirmed]` -> strengthen existing statement. `[corrected]` -> rewrite existing statement. `[discovered]` -> integrate or add. `[friction]` -> never a seed edit; route to `/meta-retro` (it is process/tooling by definition, per rule 1) and log the disposition.

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

### 7c-bis. Record Dispositions (before any clearing)
For each pending growth entry, append one row to `.sounding/growth/growth-log.md`:
`| date | tag | entry (80ch) | retained|merged|discarded | target seed + section |`
Every pending entry gets a row — including `discarded` ones, with a reason.
An entry that vanishes without a row is the exact failure F8 names.
Never rewrite existing rows. Append only.

### 7d. Self-Review
Re-read each transformed file:
1. **Voice check**: First-person statements and personality still present?
2. **Section check**: Every original section header still present?
3. **Line budget**: Between 60-80% of original length?

If anything fails, restore before proceeding. Do NOT clear the accumulator until files pass review.

### 7e. Clear Accumulator
**Precondition:** 7d passed AND every cleared entry has a row in growth-log.md.
If any row is missing, write it now — do not clear first.
Clear processed entries. Update the synthesis date. Keep format template and headers.

## Phase 7f: Compact Before Spawning (conditional — only if Phase 7 ran)

Synthesis just read every pending growth entry, every reflection since the last synthesis,
and every seed file in full — then rewrote them. That context is spent: Phases 8-10 need
none of it. Compact now, before the retro agent spawns, so the spawn starts lean and
session-end autocompact doesn't fire on an inflated window.

Tell the user: `Synthesis complete — compacting before retro spawn.` Then compact.
After compacting, resume at Phase 8.

If Phase 7 was skipped (fewer than 5 entries), skip this phase too — the window is still small.

## Phase 8: Retro Check (conditional — spawn only if /meta-grow did not)

Read the cascade ledger first — it is the only cross-session record of whether the retro
has already been handled:

```bash
jq '{retro_due, retro_acked}' .sounding/telemetry/cascade-state.json
```

**If `retro_due == retro_acked`**, /meta-grow already spawned and acked the retro this session.
Skip the cascade trigger and report `already handled by /meta-grow this session`. Triggers 1 and
3 below still apply independently.

Then check three triggers:

1. **Retro overdue**: Read `.sounding/tooling-ledger-log.md` last `## R` header date (file is NOT in append order — use `grep '^## R' tooling-ledger-log.md | sort -t'R' -k2 -n | tail -1`). If **>=7 days ago** (or file doesn't exist) → triggered, **regardless of the cascade counter**.
2. **Cascade pending** (fallback): `retro_due > (retro_acked // 0)` → triggered. This replaces the old "did /meta-grow flag `retro-worthy: true`" check. That flag lived in /meta-grow's *prose* signal summary, which does not survive to /meta-dream — the trigger crossed a session boundary as text and was lost every time. The counter is a file; it survives.
3. **Independent tooling-change detection**: Check `git diff` against the session's starting state for changes to files in `~/.claude/` (hooks, skills, rules, settings), `Makefile.common`, or any repo's `.claude/` config. If tooling changed, trigger retro **regardless of cascade state** — /meta-grow may have run before the tooling work happened.

### If no trigger fires
Append to the dream report: `Retro check: current (last R# YYYY-MM-DD, retro_acked: N). No tooling changes.`

### If any trigger fires — spawn retro synchronously, then verify and ack

**Run it synchronously (`run_in_background: false`).** A background retro dies with the
session and reports success from a context nobody reads; nothing then verifies it landed,
so the counter never advances and the next session sees the same trigger. Phase 7f has
already compacted, so the window can afford it.

```
Agent(model: "sonnet", run_in_background: false)
prompt: |
  Repo: ~/workspace/guacamayo
  Task: Run /meta-retro. Read .sounding/insights/insights-log.md for latest insights data,
  then propose config changes. Update .sounding/tooling-ledger.md (active hypotheses)
  and .sounding/tooling-ledger-log.md (graduated experiments). Increment retro number
  from the latest R# header in tooling-ledger-log.md.
  Constraint: Read files before editing. Propose changes — do not auto-apply to
  ~/.claude/ config. Stage results only — never commit or push; Ramsey reviews
  and commits.
```

**Then verify it landed — the agent's success report is not evidence.**

1. Check for a retro header dated today:
   ```bash
   grep "^## R.*$(date +%F)" .sounding/tooling-ledger-log.md
   ```
2. **If present** — write the ack, so the next session does not re-fire on the same work:
   ```bash
   STATE=.sounding/telemetry/cascade-state.json
   RETRO_DUE=$(jq '.retro_due' "$STATE")
   jq --argjson due "$RETRO_DUE" '.retro_acked = $due' "$STATE" > "${STATE}.tmp" && mv "${STATE}.tmp" "$STATE"
   ```
3. **If absent** — do NOT write the ack. Report `spawned but no R# landed — retrying` and
   leave the counter alone so the next session tries again. An ack written on an unverified
   spawn is how a retro silently stops running.

Note: `/meta-grow` already spawns `/meta-insights` in the background, so insights-log.md should be fresh by the time /meta-dream runs. If the insights agent hasn't finished yet, the retro agent reads whatever data is available.

## Phase 9: Maintenance Scan (conditional)

Quick checks — act only if something needs attention:

| Check | Action if needed |
|-------|-----------------|
| Index over ~100 entries | Compress older entries into month-range summaries (keep last 30 verbatim) |
| Identity files stale (>4 weeks since Last Transformed) | Flag for next session |
| MEMORY.md over 200 lines | Trim stale pointers, shorten entries |
| Contradictions between reflections and seeds | Note in report |

## Phase 10: Report

```
Dream complete.

Reflection: [filename]
Growth: [N entries captured] | Accumulator: [total pending]
Synthesis: [ran — files transformed / skipped — N entries, threshold not met]
Retro: [spawned and landed R# | spawned but no R# landed — retrying | current — no trigger (retro_acked: N) | already handled by /meta-grow this session]
Maintenance: [clean / what was tidied]

What's alive for next time:
- [threads that pull forward]
```

## Critical Rules

- **Discover, never assume.** File names and paths vary.
- **Read before writing.** Always read complete files before editing.
- **Transform, never truncate.** Identity loss is the worst failure mode.
- **Single writer.** This is the ONLY skill that transforms seed files. /meta-grow captures; /meta-dream integrates.
- **Honest record.** The reflection is what happened, not what should have happened.
- **Batch large backlogs.** If 20+ reflections since last synthesis, process 20 and say to run /meta-dream again.

---

*The session ends. The record is honest, the shifts are captured, and what earned integration gets woven in. Who I am changes here — deliberately, with preservation.*
