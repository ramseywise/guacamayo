---
name: meta-retro
description: "Tooling retrospective — closes the context-engineering feedback loop (observe → diagnose → codify → enforce → verify). Includes config-health audit (duplicate skills, settings syntax, memory staleness, plan-doc hygiene). Reads session friction signals, the tooling ledger, guacamayo growth entries, and plan-doc deviations; emits proposed diffs to hooks/skills/rules grouped by write target, then applies the ones you approve. Trigger on: /meta-retro, 'retro', 'tooling retrospective', 'what friction keeps recurring', 'config audit', 'audit settings'."
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash Edit Write
---

You are running a tooling retrospective. Steps 0–4 produce **proposed diffs** and apply
nothing. Step 5 applies only the diffs Ramsey explicitly approves — no approval, no write.
Identity files (`.sounding/`) are never touched at any step; reflect/synthesize own that
space, and this loop only *flags* graduation candidates there.

## Step 0 — Verify before proposing (read the ledger first)

Read `~/workspace/guacamayo/.sounding/tooling-ledger.md` (active hypotheses only).
Graduated rows live in `tooling-ledger-log.md` (append-only archive). Every row with
status `hypothesis` is your top queue item. For each:

1. **Check the Metric column first.** Rows with a typed metric (`absence:`, `count-drop:`,
   `presence:`, `ratio:`) have a machine-checkable signal — look for that signal in session
   data (insights dry-run output, hook logs, session JSONL patterns). Rows with `—` (legacy,
   pre-tracker) fall back to manual evidence search.
2. Find evidence the motivating friction stopped or recurred since the change (session
   transcripts, hook logs, repeated manual corrections). Verification is concrete —
   "did the friction stop", with a session reference — not vibes.
3. **Re-derive, never re-read.** For each row with a `presence:` or `absence:` metric,
   run the command the metric names and paste the command + output into the retro section.
   A row whose Status says "metric met" is a claim, not evidence. A row verified from its
   own Status column is unverified — and a row's *prose* decays the same way (R11 re-derived
   "plist still unloaded" from row text while `launchctl list` showed it running; R10 F2
   read "both presence metrics met" while one target had zero matches, undetected across
   two windows). The live command is the only witness.
4. Propose the row update: `hypothesis → verified (evidence)` or `hypothesis → failed (evidence)`.
   A failed row is itself a finding (the fix didn't take; diagnose why).

## Step 0.5 — Config health (mechanical checks)

Run these checks across the workspace. Findings enter Step 2 as findings like any other,
tagged with severity (BLOCKER / WARN / NOTE).

**Check A — Config-layering duplicates (BLOCKER).** For every repo in `~/workspace` with a
`.claude/`, check for skills/hooks that duplicate a global one by name. Same name in repo
AND global → BLOCKER (double-load + drift). Exception: repo skills documented as
deliberately divergent in that repo's CLAUDE.md. Known-sanctioned repo-local sets:
guacamayo identity-lifecycle (meta-wake/meta-grow/meta-dream/genesis), repo project skills.

**Check B — Settings schema (BLOCKER/WARN).** For `~/.claude/settings.json` and every repo
settings file: (1) JSON validates, (2) wildcard syntax uses `Bash(cmd:*)` not
`Bash(cmd *)`, (3) tool names in Allow/Deny/Ask rules exist (stale: `Task`→`Agent`,
`SlashCommand`→`Skill`, `TodoRead`), (4) no secrets in settings, (5) doc↔config drift:
the `model` value in `~/.claude/settings.json` matches the default named in
`~/.claude/CLAUDE.md` ("Default session model") and `refs/models.md` — a decision that
landed only in prose has not landed (the fable default ran 5 days undetected, R8 F1).

**Check C — Memory staleness (WARN).** Read project memory files; flag stale state,
duplicates, contradictions with current CLAUDE.md.

**Check D — Doc artifacts (NOTE).** Flag leftover `RESEARCH.md`/`PLAN.md`/`SESSION.md` or
`in-progress/` dirs for migration to `plans/YYYY-MM-DD-<slug>.md`.

**Check E — Plan-doc hygiene (NOTE).** Flag plan docs missing `Status:` lines.

**Check F — Skill name alignment (NOTE).** For every skill dir, verify `name:` in SKILL.md
frontmatter matches the directory name. Mismatches break `/slash` dispatch silently.

## Step 1 — Observation sources

Read what exists; skip gracefully what doesn't. Note which sources you actually used.

1. **Insights summary**: read `~/workspace/guacamayo/.sounding/insights/insights-log.md` first
   (written by `/meta-insights` — contains experiment verdicts, recommendations, model/skill/tool
   economics, and trends). If it doesn't exist or is stale (>7 days), fall back to running
   `python3 ~/.claude/scripts/insights.py --dry-run` for fresh mechanical stats, or read
   recent session JSONL under `~/.claude/projects/<project-slug>/`. Look for: repeated
   permission prompts for the same command shape, the same manual fix applied in multiple
   sessions, hook blocks that the user then overrode, tool errors retried verbatim.

   Read the `## Failure Attribution` section. Use category weights when triaging findings:
   - `env` errors → infrastructure/config findings, not code or spec findings
   - `tool` errors → hook or MCP config findings
   - `code` errors → skill/hook/workflow findings (note: retry-unknown — may include transients)
   - `unknown` → flag as a taxonomy gap (lookup table needs expansion)
   Never attribute an `env` error to a code or spec cause. Do not generate findings
   from `unknown` — surface the gap count instead.
2. **Growth-entry graduation**: `guacamayo/.sounding/growth/growth.md` — entries tagged
   `[discovered]` that are *process* learnings (about workflow/tooling, not identity).
   These die in the accumulator unless promoted. Flag each as a graduation candidate with
   a proposed target (rule/skill/hook). Do NOT edit `.sounding/` — flag only; /reflect
   and /synthesize own that space.
3. **Hook fire patterns**: if hook logs exist, hooks that fire constantly (candidate for
   a fix upstream of the hook) or never (dead weight).
4. **Plan-doc drift**: recent docs in repo `.claude/docs/plans/` (one doc per work
   item, `YYYY-MM-DD-<slug>.md`) — compare Execution Notes / deviations against the original
   steps. Recurring deviation categories are tooling gaps.
5. **Skill coverage** — read the `## Skill Coverage` section of `insights-summary.md`
   (written by `/meta-insights` step 7). Two opposite findings live here:
   - **Skill exists but is never invoked** → a *description* problem, not a value problem.
     The `Skill` tool matches on `description:` frontmatter, so a skill that never
     auto-triggers usually has a weak one. Propose a description rewrite
     (`skill-creator` has description-optimization), not deletion. Recommend deletion only
     where a skill is never invoked AND superseded by a named alternative.
   - **Skill is missing** — the inverse, and it has no live signal: "I should have had a
     skill for this" is only visible in retrospect. Look for the same multi-step work
     shape repeated across ≥3 sessions with **zero** skill invocations in those sessions.
     That cluster is the trigger to propose `skill-creator`. Name the recurring shape and
     cite the sessions; a vague "we do a lot of X" is not a finding.

   Also flag **typo'd invocations** (a `/name` with no skill on disk, e.g.
   `design-inistiative`) — these fail silently with no error, so they read as user error
   but are really a missing-feedback problem.
6. **Recurrence report** — the durable count of repeated review friction. Read the
   **Recurring friction** table in `guacamayo/.sounding/context-dashboard.html`
   (REVIEW-FINDINGS region, refreshed by `uv run telemetry --facts`), or compute it live:

   ```bash
   cd ~/workspace/guacamayo && uv run python -c "
   import json
   from telemetry.recurrence import compute_recurrence
   f = [json.loads(l) for l in open('.claude/docs/review-findings.jsonl') if l.strip()]
   for g in compute_recurrence(f):
       if g.promotable or g.direction != 'flat':
           signal = '+'.join(filter(None, [
               g.direction if g.direction != 'flat' else '',
               'promotable' if g.promotable else '',
           ])) or 'flat'
           print(f'{g.pattern_key}\t[{signal}]\tn={g.count}\tby_period={g.period_counts}\trepos={g.repos}\t{g.first_seen}->{g.last_seen}\t{g.sample_titles}')
   "
   ```

   A group is a **candidate finding automatically** if it is `promotable` **or** `rising`
   — no judgement call about whether it recurs; the signal already decided that. A `falling`
   group is not a candidate, but report it: it is evidence a past intervention worked. Carry the
   group's `pattern_key` **and which signal fired** into the finding so the report and the
   ledger row are traceable back to the corpus.

   The two signals answer different questions and are **not** interchangeable:

   | Signal | Means | Reads |
   |---|---|---|
   | `promotable` | count >= `RECURRENCE_THRESHOLD` (3) — has happened enough to matter | lifetime total |
   | `direction` | which way the recent trend runs — `rising` \| `flat` \| `falling` | recent trend |

   `direction` is computed on the most recent **complete** week against the mean of the 3
   weeks before it (`rising`: > 1.5× and >= 3 absolute; `falling`: < that mean ÷ 1.5, with a
   prior mean of at least 3 so a trailing-off one-off is not called an improvement; `flat`
   otherwise). `group.rising` remains available as a boolean view of `direction == "rising"`.

   - A **rising** group is a candidate finding **automatically** — it is getting worse now.
     Rising but not yet `promotable` is a friction *starting* to bite: propose a cheaper
     intervention (a warn-hook, not a rule) and set a shorter metric window.
   - A **falling** group is being fixed. Say so, rather than re-proposing last window's hook.
   - A **flat** + `promotable` group has plateaued — the count is real but nothing is moving.

   **Findings carry `occurred` (GUA-109), so `rising` is evidence.** Recurrence buckets on
   each finding's occurrence date — when the cited code was last touched — not on the date
   its review run happened to fire. This replaces the GUA-104b caveat: run dates were bursty
   (85 of 125 rows shared `2026-08-04`), so every promotable group used to read as rising and
   the flag carried no information. Rows whose `occurred_source` is `run` had no resolvable
   checkout and fall back to the run date — treat those as undated for trend purposes.

   **Read the report, not the rotating pass log** (D5). `.hook-pass-log.jsonl` rotates on
   roughly a five-day window, so counting against it silently undercounts anything older —
   `review-findings.jsonl` and the factstore are the durable sinks. A future edit that
   repoints this source at a rotating log reintroduces the bug this source exists to fix.

   Groups keyed `unmatched:<category>:<repo>` are the *fallback* bucket, not a friction
   signature — a high `unmatched:` count means `PATTERNS` in `telemetry/recurrence.py`
   lacks a signature for that cluster. Treat that as a finding about the pattern table
   itself, not as a promotable friction.

## Step 2 — Findings → proposals

Per finding, emit exactly this shape:

```markdown
### F<N>: <one-line friction statement>
- Tag: stop | keep | improve
- Friction observed: <what kept happening>
- Evidence: <session/file refs — at least one concrete pointer>
- Proposed diff: <actual diff or precise edit, ready to apply>
- Target: <file path>
- Enforcement level: hook | skill/protocol | CLAUDE.md/rules | MEMORY.md
- Metric: <type>:<signal> <threshold> (see ledger Experiment Tracking section for types)
- Pattern key: <recurrence pattern_key, or — if not from the recurrence report>
- Recurrence signal: promotable | rising | falling | rising+promotable | falling+promotable | — (see Step 1.6)
- Promotion target: warn-hook | skill | rule | ledger-only
- Hook template (if warn-hook): <full fenced hook script, ready for human review>
- Deploy: PROPOSED — Ramsey applies. This loop never writes ~/.claude/hooks/ or settings.json.
```

**Tagging rules** (from `~/.claude/refs/agile.md`):
- **stop** — actively costing us; mechanical fix or delete → `ready` issue if scoped, `backlog` otherwise
- **keep** — verified working; no issue → ledger row graduates to `verified`
- **improve** — needs design/research before actionable → `backlog` issue or `inbox.md` line

**Write targets by enforcement strength** (decided, don't relitigate):
hooks > skills/protocols > CLAUDE.md/rules > MEMORY.md. Pick the strongest level that
fits the friction; if you propose a weaker one, say why (e.g. not mechanically checkable).

Default promotion target for a recurrence finding is a **warn-style hook**. A pattern
firing 5% of the time costs ~0% always-on via a hook vs 100% via a CLAUDE.md line
(~20x). Proposing an always-on rule instead carries the burden of proof — cite why the
pattern is not mechanically checkable. Never propose prompt-prefix growth: a 25k-char
metacognitive framework scored 0.30 vs 0.65 for random filler of equal length
(kimjune01). Conditional beats always-on.

**Doc-writer boundary** (decided): machine-consumed docs (`.claude/`, CLAUDE.md, rules)
are this loop's native output. Human-consumed docs (READMEs, design docs, wiki) belong to
librarian's pipeline or humans — flag staleness, never propose direct edits to them.

## Step 3 — Eval gate for skill changes

Any proposal that modifies a skill ships with a **before/after eval sketch**: the
prompt(s) that exercise the behavior, what the current skill produces, what the changed
skill should produce, and how to judge it (skill-creator's eval harness where it fits).
No sketch → the proposal is marked `draft`, not ready for review.

## Step 4 — Output and ledger rows

Group findings by write target (all hook changes together, etc.), most-severe friction
first. End with:

1. **Proposed ledger rows** — for every accepted-if-approved change, run the `/track`
   validation gates before writing. For each proposed row:

   a. **Gate 1 — Falsifiability**: name the value that means the change failed. If you
      can't, rewrite the metric. `absence:` claims require a `registered` signal with a
      real-zero resolver.

   b. **Gate 2 — Signal resolution**: resolve the metric's signal against the registry:
      ```bash
      uv run python -c "
      from telemetry import signals
      for s in signals.all_signals():
          if '<signal-name>' in s.name:
              print(f'{s.state:16} {s.name}')"
      ```
      - `registered` → proceed.
      - `needs-collection` → **block the row.** Emit the collection change as a finding
        instead. The row comes after the collector lands.
      - `unobservable` → rewrite the claim into a countable form.
      - `unregistered` → register a resolver in the same change, or rewrite.

   c. **Gate 2b — No duplicate signal**: an active ledger row already measuring this
      signal means one of the two is dead. Check before writing.

   d. **Gate 3 — Due date**: `date.today() + timedelta(days=10)` (2 retro rounds at
      observed upper bound). Computed, never typed.

   e. **Gate 4 — Plane**: state the architecture layer (`work` | `metacognition` | `control`).

   f. **Gate 5 — pattern_key** (friction rows only): match the Change text against
      `telemetry/recurrence.py` PATTERNS. Block if no key and the friction is code-corpus.

   Rows that fail any gate are reported as `blocked — <gate> <reason>` rather than
   written. A blocked row is a finding about the measurement layer, not a failed retro.

   Rows that pass all gates are written in ledger format with status `hypothesis`.
2. **Ledger graduation**: move verified/failed rows to `tooling-ledger-log.md` (append).
   Active ledger stays lean (hypotheses only). Archive is the audit trail.
3. **Feedback loop (GUA-119)**: read the acceptance rates from the AUTOMATED-ACTIONS tile in `.sounding/context-dashboard.html` (or parse `.sounding/telemetry/actions.jsonl` directly) and, for any proposal type with sustained high acceptance (>= 80% over >= 5 decidable records), PROPOSE promoting it to auto-mutation as a tooling-ledger hypothesis row (status `PROPOSED`, never applied — Ramsey decides).

Through Step 4 nothing is written outside the retro report. Then stop and hand the report
to Ramsey for Step 5.

## Step 5 — Apply (gated on approval)

**Hook authority: propose-only (D1, 2026-08-09).** This loop **never writes**
`~/.claude/hooks/*` or `~/.claude/settings.json` — not even for an approved finding, not
even to `chmod +x`. A proposed hook is emitted as a fenced template plus a ledger row
into the retro report; Ramsey reviews and applies it. `Edit` stays in `allowed-tools`
because retro still legitimately edits the tooling ledger and skill files — the carve-out
is by path, not by tool. If a future session finds this loop blocked from a legitimate
edit, widen the carve-out precisely; do not restore blanket hook-edit permission. D1 is a
standing constraint, consistent with the no-commit gate.

Present the grouped findings and ask Ramsey which to apply — by finding ID (`F1, F3`),
`all`, or `none`. **Apply nothing until this answer comes back.** Silence is not approval.

Skip any `draft` finding (Step 3 eval sketch missing) — say so; it is not eligible until
promoted out of draft. For each **approved** finding:

1. Apply its Proposed diff to its Target, verbatim as reviewed. If the target drifted since
   Step 2 and the diff no longer applies cleanly, do NOT improvise a new edit — report the
   mismatch and re-propose that one for a fresh look.
2. After a settings.json edit, validate it (`jq empty ~/.claude/settings.json`); after a
   hook edit, `chmod +x` and smoke-test it the way its sibling hooks are tested. A hook or
   settings change that fails validation is rolled back, not left half-applied.
3. Machine-consumed targets only (`.claude/` skills/hooks/settings, CLAUDE.md, rules) — the
   loop's native output. Never apply to human-consumed docs (READMEs, wiki) or to
   `.sounding/` identity files even if a finding names one; re-flag instead.

After applying, add the ledger rows (status `hypothesis`, with the verification test) for
every finding that landed. Report per finding: applied | skipped-draft | skipped-declined |
re-proposed (drift), with the file touched. Ramsey commits — this loop never commits or
pushes.

## Step 6 — Write findings to the board (after approval)

For each approved finding, write it to its destination based on the Tag:

### stop / improve → GitHub Issue
```bash
cd ~/workspace/guacamayo && gh issue create \
  --title "F<N>: <one-line friction>" \
  --label "<label>" \
  --body "<problem + evidence + metric>"
```

Label mapping:
- **stop** (scoped, mechanical) → `ready`
- **stop** (needs design) → `backlog`
- **improve** → `backlog`

Issue body format:
```markdown
## Problem
<Friction observed — one sentence>

## Evidence
<Session/file refs>

## Proposed fix
<Proposed diff from the finding, or "needs research">

## Metric
<type>:<signal> <threshold>

## Source
<date> /meta-retro F<N>
```

### keep → ledger only
No issue. Graduate the ledger row: `hypothesis → verified (evidence)`.

### Unscoped ideas → inbox
If a finding is too vague for an issue (no clear problem statement), append one line to
`~/workspace/guacamayo/.sounding/state/inbox.md` instead of creating an issue.

Report the issue URLs created so Ramsey can verify.
