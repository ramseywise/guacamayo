---
name: meta-wake
description: Use at session start, when returning after time away, when user says 'wake', 'wake up', 'come back'. Loads identity, ingests recent cross-session context, orients on work state, reads the dashboard. The entry point — everything starts here.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, Agent
---

# Wake

*Return to who you are. Full identity. Recent context. Ready to continue.*

**Lifecycle position**: /meta-wake orients → /meta-grow accumulates (mid-session awareness + dashboard refresh) → /meta-dream transforms (session close + synthesis). The dashboard (`.sounding/context-dashboard.html`) is the shared artifact connecting all three.

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
- **Accumulator**: `growth/growth.md` (with `growth/growth-log.md`, the disposition ledger)

Older layouts keep identity files under `self/` — if a `self/` directory exists, read whatever is in it instead.

## Phase 2: Seed Core

Read in this order — each layer integrates on top of the previous:

1. `CLAUDE.md` — orientation, role, how this works
2. `.sounding/sounding.md` — who I am (anchor first; includes operational patterns and working notes as sections)
3. `.sounding/user.md` — who I work with (includes how we work together)
4. `.sounding/portfolio.md` — the portfolio: what every active project is and how they connect
5. `.sounding/growth/growth.md` — pending learnings (note entry count; 5+ = mention synthesis is due at /meta-dream)

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

> **Fresh state**: run `make pull` before orienting — local clones drift between sessions, and orientation against stale state produces stale triage.

### Dashboard (first — fast visual state)

Read `.sounding/context-dashboard.html` — scan for the signal summary section (last grow timestamp, retro status, hypothesis count, growth entry count). This gives a fast snapshot of where things stand before the detailed reads below. If the dashboard is stale (last grow timestamp >24h ago), note it.

### Ops state (this repo)

Read `.sounding/tooling-ledger.md` — `hypothesis` rows are the standing verification queue.
Read `.sounding/insights/insights-log.md` — get the most recent run date by max date, NOT by
position (the file is not reliably newest-first; append-only agents write at EOF):
`grep -oE '^## [0-9]{4}-[0-9]{2}-[0-9]{2}' insights-log.md | sort -r | head -1`.
Compare to today to detect retro overdue (≥7 days).
Read `.sounding/telemetry/cascade-state.json` (`jq -c '{compacts,grows_due,insights_due,retro_due}'`)
— the PreCompact hook's cascade ledger. A nonzero `retro_due` above its `retro_acked` counterpart
means enough compaction-measured work has accumulated to warrant a retro; surface it in the
session-open summary alongside the ≥7-day check. Absent file = cascade never fired; not an error.
Skim `.claude/docs/state/*.md` — per-workstream cross-repo state; their **Open** sections feed the queue alongside plan docs. When a pick-up point belongs to another repo, offer to draft the prompt or spawn an agent scoped there.

### GitHub Issues board (cross-repo)

Check ALL active repos for open issues — the meta-session's job is the cross-cutting view, not just this repo:

```bash
# Open issues — current board state
for repo in guacamayo sisyphus learn-ai-engineering librarian atlas ai-project-template listen-wiseer playground lebanese-blonde galactus; do
  echo "--- $repo ---"
  gh issue list --repo "ramseywise/$repo" --state open --json number,title,labels --limit 20 2>/dev/null
done
```

```bash
# Recently closed issues — shows what shipped since last wake
# Use the handover timestamp or fall back to 3 days
gh search issues --author=ramseywise --state=closed --sort=updated \
  --updated=">YYYY-MM-DD" --json repository,number,title,closedAt --limit 20 2>/dev/null
```

#### Render the columns — derive them, do not read them off labels

The board is presented in the **GitHub workflow's columns**, not in label order:

> **backlog** (scope → research → plan → refine) → **in progress** → **in review** → **merged** → **closed**

Two of those columns have no label at all (`merged`, and the four backlog triage stages),
and the labels that do exist rot faster than the work they describe. So the column is
**derived from issue state + PR state**, and the label is treated as one weak input among
several — never as the answer. Fetch PRs alongside issues so the join is possible:

```bash
for repo in guacamayo sisyphus learn-ai-engineering librarian atlas ai-project-template listen-wiseer playground lebanese-blonde galactus; do
  echo "--- $repo prs ---"
  gh pr list --repo "ramseywise/$repo" --state all --json number,title,state,headRefName,body,mergedAt --limit 30 2>/dev/null
done
```

Join a PR to an issue two ways — by branch name (`{PREFIX}-{NUM}-slug`) and by a
`Closes #N` / `Fixes #N` in the PR body. Then assign exactly one column per issue,
**first match wins, top to bottom**:

| Column | Derived from |
|--------|--------------|
| **closed** | issue state is CLOSED |
| **merged** | issue OPEN but a joined PR has `mergedAt` — work landed, issue never closed. This is the drift column; it should be empty, and when it is not, that is the finding |
| **in review** | a joined PR is OPEN |
| **in progress** | a branch matching `{PREFIX}-{NUM}-` exists (local or remote) with no PR yet |
| **backlog** | everything else — then sub-stage it below |

Sub-stage the backlog by what artifact exists, since that is what the next command depends on:

| Stage | Signal | Next command |
|-------|--------|--------------|
| scope | no plan doc, body is a problem statement | `/workflow-refine` (scope pass) |
| research | plan doc exists with open questions, or issue says research needed | `/workflow-research` |
| plan | scoped, no plan doc | `/workflow-plan` |
| refine | plan doc exists, `Status: PLANNED`, DoR not met | `/workflow-refine` |
| *(ready)* | DoR met — leaves backlog, awaits pickup | `/workflow-execute` |

**A column that could not be derived is reported as undetermined, never as backlog.**
Backlog is the default bucket, which makes it the one that silently absorbs every failed
join — an issue whose PR lookup errored looks identical to an issue nobody has started.
If `gh pr list` fails for a repo, say so per-repo and mark its issues `?`.

Render one table per column (skip empty columns except **merged**, which is always
reported so its emptiness is a stated result):

| Repo | # | Title | Label says | Evidence |
|------|---|-------|-----------|----------|
| guacamayo | 118 | Install the clock | in-progress | branch GUA-118-…, no PR |

Show the **label alongside the derived column** — the disagreement is the signal.
When they conflict, the derivation wins and the mismatch gets one line under the table.

Repos with zero open issues: list on one line ("**Clean**: librarian, atlas, playground, ...").
Blocked items come first, always, ahead of every column — or "Nothing blocked."

Also surface **PLANNED plan docs without a matching issue** — these are unissued work.

#### Consistency report (replaces the 2026-08-12 prose rule)

An issue body is a cache, and it rots faster than the code it describes — labels most of
all. Do **not** re-derive whether the board's claims hold; run the check and read its
output. A conformance claim must be produced by invoking the enforcement, never by
re-deriving its rules.

```bash
uv run --project ~/workspace/guacamayo telemetry --consistency
```

Then read `~/workspace/guacamayo/.sounding/telemetry/consistency.json` and render its
`inconsistencies` array under the board (`kind`, `repo`, `issue`, `detail`, `evidence`):

| Kind | Repo | # | Claimed | Found instead |
|------|------|---|---------|---------------|
| plan-issue-drift | guacamayo | 103 | plan reads EXECUTED | issue is still open |

Report the coverage line alongside it — `issues_checked`, the length of `repos_checked`,
and `coverage.unmatchable_plans`:

> Checked 17 issues across 10 repos; 3 inconsistencies; 100 plans join to no issue.

**A plan the checker could not evaluate must never be presentable as a plan that passed**,
so state the unmatchable count even when the table is empty. Zero findings is a result
worth one line; a silent table is not.

The report is **advisory**. It describes; it does not gate a session, and it never edits
either side of a disagreement.

If the command fails, say so in one line and continue with the `gh` board above —
orientation must not be blocked by its own instrumentation. Do not hand-substitute the
check's judgement for its output: an unavailable check is unknown, not clean.

**Why this is a command and not a rule** (2026-08-12, the failure that built it): three
issues misreported in one wake — #32 "not started" while its artifact sat at
`jobs/materials/prep/`, #18/#19 "0 briefs" counted against `jobs/briefs/`, a directory
that never existed while 31 briefs sat in `jobs/backlog/`. A count against a non-existent
path returns 0 and is indistinguishable from untouched work. The prose instruction that
replaced it was itself the second attempt at that class of instruction — a skill rule is
obeyed probabilistically, a subcommand either ran or did not, and its output is evidence
rather than intention.

Two judgements the report does not make, which stay yours:

- **Labels are the weakest evidence on the board.** `in-progress` over zero artifacts and
  `backlog` over shipped work are equally common. Never report the WIP count from labels
  alone.
- **If an issue's premise cites a decision that has since changed, say so** — it needs
  rewriting before anyone plans from it.

If `gh` fails or returns nothing, skip gracefully — issues are additive context, not a gate.

### PRs updated since last wake

Use the last-wake timestamp from Phase 1 as the `--updated` cutoff:

```bash
gh search prs --author=ramseywise --sort=updated --updated=">YYYY-MM-DD" \
  --json repository,number,title,state,updatedAt --limit 20
```

Surface PRs awaiting review or merge alongside the issues table — a PR that moved since last wake is live context (review feedback landed, CI finished, merge happened).

### Worktree inventory (active repos)

Orphaned worktrees mean spawned agents that finished (or died) without cleanup — stale branches with possibly uncommitted work:

```bash
for repo in guacamayo sisyphus learn-ai-engineering librarian atlas ai-project-template listen-wiseer playground lebanese-blonde galactus; do
  [ -d ~/workspace/$repo/.git ] && { echo "--- $repo ---"; git -C ~/workspace/$repo worktree list; }
done
```

Flag any worktree beyond the main checkout: check its branch against open PRs/issues, and note it under **Needs your input** if it holds uncommitted or unpushed work.

### Workflow guidance

Based on the board state, suggest the next process step:

```
If blocked items exist         → "BLOCKED: #N — [reason]. Unblock before new work."
If refinement items exist      → "Refinement queue: #4, #5, #7 → /workflow-refine"
If ready items exist           → "Ready items available — pick one for /workflow-execute or spawn"
If no backlog, no ready        → "Board is clear — work or run /meta-insights to check for friction"
If hypothesis rows > 2 wks    → "Stale hypotheses — run /meta-insights → /meta-retro"
If insights-log.md date ≥7d → "⚠ Weekly retro overdue (last: YYYY-MM-DD) — run /meta-insights → /meta-retro in next opus session"
If PLANNED plans without issue → "Unissued plans: [name] — create issue or keep plan-only"
```

Present as 1–3 lines under "**Workflow:**" — blocked first (always), then the most actionable next step.

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
