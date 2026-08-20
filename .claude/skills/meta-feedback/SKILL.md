---
name: meta-feedback
description: "Telemetry→recommendation router with a mandatory verification gate. Takes monitoring/dashboard signals (insights-log, factstore, recurrence report, dashboard tiles), VERIFIES each claim against the raw corpus before it becomes a recommendation, then routes survivors to /meta-retro (enforceable friction) or /meta-insights (metric bugs) and writes a durable feedback record the dashboard reads back. Trigger on: /meta-feedback, 'feedback loop', 'verify the dashboard', 'route telemetry to retro', 'is this metric real', 'dashboard says X'."
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash Edit Write
---

You are running the **feedback router**. This skill exists because a dashboard number is a
*claim*, not a finding — and claims that reach `/meta-retro` unverified become enforcement
(hooks, rules) built on miscounts.

**The gate is the point.** Steps 1–3 verify; only Step 4 recommends. A signal that fails
verification never becomes a recommendation — it becomes a *metric bug*, routed back at the
measurement layer, which is a different and often more valuable finding.

**Provenance rule (standing).** Every recommendation carries the command that produced its
number and the corpus it ran against. A number without a re-runnable command is not
evidence. This mirrors `/meta-retro` Step 0.3 ("re-derive, never re-read") and extends it
from the ledger to the whole telemetry surface.

**Write authority: propose-only.** Like `/meta-retro`, this loop never writes
`~/.claude/hooks/*` or `~/.claude/settings.json`, never touches `.sounding/` identity
files, and never commits. It writes exactly one place: the feedback record (Step 6).

---

## Step 0 — Scope the run

Accept an optional argument: a specific claim to verify (`/meta-feedback "bash antipatterns
19k"`), a source (`/meta-feedback dashboard`), or nothing (verify all live signals).

Establish the corpus and **state its bounds before measuring**:

```bash
ls ~/.claude/projects/**/*.jsonl | wc -l          # transcript count
du -sh ~/.claude/projects                          # corpus size
```

Note the JSONL retention ceiling (~15 days) — signals reaching further back are computed
over rows whose raw text is gone. Say so rather than reporting a confident number.

## Step 1 — Harvest claims from the monitoring surface

Read each source, extract **discrete claims**, do not yet believe any of them.

1. **Insights log** — `~/workspace/guacamayo/.sounding/insights/insights-log.md`
   (`## Recommendations`, `## Failure Attribution`, `## Numbers`). Written by
   `/meta-insights`; stale >7 days is itself a claim to flag.
2. **Factstore** — `~/workspace/librarian/data/sessions.db` (owned by librarian; guacamayo
   owns what is derived from it). Per-session columns: `errors_code`, `errors_env`,
   `errors_tool`, `errors_unknown`, `bash_antipatterns`.
3. **Recurrence report** — the `promotable` / `rising` / `falling` groups
   (`telemetry/recurrence.py`), per `/meta-retro` Step 1.6.
4. **Dashboard tiles** — `.sounding/context-dashboard.html`, incl. AUTOMATED-ACTIONS
   acceptance rates. Respect the metric fences (`JULY_ONLY_METRICS`, `COMPACT_METRICS`) —
   a tile computed over a sparse column is a fenced claim, not a population claim.
5. **Ledger hypotheses** — `.sounding/tooling-ledger.md` rows with typed metrics.
6. **User-reported claims** — anything Ramsey pasted in. These get *no* deference; they
   are usually dashboard readings and inherit the dashboard's bugs.

Emit the claim inventory:

```markdown
| C<N> | Claim | Source | Stated number |
```

## Step 2 — VERIFY each claim against the raw corpus (the gate)

For every claim, compute the number **independently from the JSONL**, not from the tile
that asserted it. The dashboard is the thing under test; it cannot be its own witness.

Verification obligations:

- **Count the right unit.** Per-*command* vs per-*occurrence-within-command* is the classic
  break: a compound `echo X && ls && for d in */` is ONE Bash call and good practice, but
  inflates any per-occurrence counter. When a claim's magnitude is implausible relative to
  the denominator, this is the first thing to check.
- **Establish the denominator.** "19k antipatterns" means nothing without total Bash calls.
  Always report `n / total (pct%)`.
- **Check the string actually exists.** A grep for a marker that only appears in your own
  analysis text measures nothing. Exclude the current session from any corpus scan.
- **Test the causal direction** for any claim of the form "X prevents Y". Split the corpus
  on X and compare Y in both arms. Correlation frequently runs *opposite* to the hypothesis.
- **Separate substitutable from non-substitutable.** For tool-choice claims, only count what
  the alternative can actually express. Read/Grep/Glob cannot do aggregation (`wc -l`,
  `for d in */`), range extraction (`sed -n '/a/,/b/p'`), or section markers (`echo`).

Assign each claim exactly one verdict:

| Verdict | Meaning | Routes to |
|---|---|---|
| `CONFIRMED` | Independent count matches within ~10% | Step 4 recommendation |
| `OVERSTATED` | Real but materially smaller (state both numbers + the counting bug) | Step 4, scoped to the true slice + a metric-fix finding |
| `INVERTED` | Data contradicts the claimed direction | Step 4 as a *retraction* finding |
| `PHANTOM` | Signal does not exist in the corpus | Metric-fix finding only; never an enforcement proposal |
| `UNMEASURABLE` | No column/signal exists to score it | Surface as unmeasurable-by-construction; propose a `_SIGNAL_METRICS` entry, not a hand-derived verdict |

Emit, with the command inline:

```markdown
### C<N>: <claim> — **<VERDICT>**
- Stated: <number from source>
- Measured: <number> (`n / total`, pct)
- Command: <the exact re-runnable command>
- Corpus: <file count, date range, exclusions>
- Divergence cause: <counting bug | stale window | wrong denominator | none>
```

**A claim that does not survive this step cannot appear in Step 4 as a behavior change.**
Report it as a measurement defect instead. This is not a lesser outcome — a miscounted
metric that drives a hook is worse than no metric.

## Step 3 — Root-cause clustering

Before recommending, collapse verified claims into **causes**, not symptoms. Several
distinct-looking signals routinely share one root — and fixing the root beats fixing each
surface separately.

For each cluster: name the mechanism, list the member claims with their measured counts,
and total the yield. Prefer one structural fix over N surface fixes; say explicitly when
fixing cluster A is expected to move cluster B, and note that as a prediction to check
next run.

```markdown
### Cluster <name>
- Mechanism: <the causal story, one or two sentences>
- Members: C<N> (n=…), C<M> (n=…)
- Combined yield: <n> (<pct>% of the error/cost surface)
- Expected knock-on: <other cluster this likely moves, or none>
```

## Step 4 — Recommendations (verified claims only)

Emit `/meta-retro`-compatible findings so the handoff is mechanical, not a rewrite. Use the
exact Step 2 finding shape from `/meta-retro`, plus two fields this loop adds:

```markdown
### F<N>: <one-line friction statement>
- Tag: stop | keep | improve
- Verdict source: C<N> (<VERDICT>)          # NEW — traceability to the gate
- Yield: <measured n> (<pct>% of <surface>)  # NEW — measured, never estimated
- Friction observed: <what kept happening>
- Evidence: <session/file refs + the Step 2 command>
- Proposed diff: <actual diff or precise edit, ready to apply>
- Target: <file path>
- Enforcement level: hook | skill/protocol | CLAUDE.md/rules | MEMORY.md
- Metric: <type>:<signal> <threshold>
- Pattern key: <recurrence pattern_key, or —>
- Recurrence signal: promotable | rising | falling | —
- Promotion target: warn-hook | skill | rule | ledger-only
- Deploy: PROPOSED — Ramsey applies. This loop never writes ~/.claude/hooks/ or settings.json.
```

**Rank by measured yield, highest first.** Not by severity language, not by how easy the
fix is — by the number Step 2 produced.

Inherit `/meta-retro`'s standing constraints rather than re-deciding them: enforcement
strength hooks > skills > rules > MEMORY.md; warn-hook is the default promotion target;
never propose prompt-prefix growth; machine-consumed targets only.

**Two failure modes to refuse explicitly** (both have burned this loop before):

- **Auto-rewriting hooks on a heuristic.** A hook that rewrites tool calls fires on the
  non-substitutable remainder too, and blocks correct work. Warn-only, scoped to patterns
  verified substitutable in Step 2.
- **Enforcement built on an `INVERTED` claim.** If the data ran opposite, the finding is to
  *retire* the existing nudge, not to strengthen it.

## Step 5 — Route

Each finding goes exactly one place. Routing is determined by the verdict, not by taste:

| Finding kind | Routes to | Mechanism |
|---|---|---|
| Enforceable friction (`CONFIRMED`/`OVERSTATED`) | `/meta-retro` | Findings land in Step 2 of retro's queue; retro's Step 5 approval gate applies them |
| Metric/counting defect (`PHANTOM`, `OVERSTATED` cause) | `/meta-insights` + parser | Fix at measurement layer — parser, `_SIGNAL_METRICS`, or dashboard keying |
| Retraction (`INVERTED`) | `/meta-retro` | Proposes retiring the misaimed hook/rule + failing its ledger row |
| Unscoped | `.sounding/state/inbox.md` | One line, no issue |

**Filing** follows the global convention — issues live in the repo they change:
dashboard/telemetry/parser → guacamayo (or librarian, if it is the parser); global hooks,
CLAUDE.md, rules → `ramseywise/dotclaude`. Grep for the actual source before assigning a
repo; do not guess from the symptom's location.

After writing the feedback record (Step 6), if any finding is routed to `/meta-retro`
(`CONFIRMED` or `OVERSTATED` enforceable friction, or `INVERTED` retraction), spawn retro
as a background agent:

```
Agent(agentType: "persistence", model: "sonnet", run_in_background: true)
prompt: |
  Repo: ~/workspace/guacamayo
  Task: Run /meta-retro. Read .sounding/telemetry/feedback-log.md for latest
  verified findings, then propose config changes.
  Constraint: Read files before editing. Propose-only — never write hooks or settings.
```

This is safe because retro is propose-only (Step 5 approval gate). The human checkpoint
is retro's Step 5, not a manual invocation of retro itself — chaining the spawn removes
one relay failure (the flag-in-prose-that-dies-at-session-boundary shape) without removing
the approval gate.

## Step 6 — Write the feedback record (the dashboard reads this back)

This is the loop's only write, and it is what makes the improvement *continuous* rather
than per-session. Append a dated section to
`~/workspace/guacamayo/.sounding/telemetry/feedback-log.md` (create if absent; newest at
top, never overwrite):

```markdown
# Feedback Run — <YYYY-MM-DD>

## Corpus
<transcript count, size, date range, exclusions, retention caveat>

## Verdict ledger
| Claim | Source | Stated | Measured | Verdict |
|-------|--------|--------|----------|---------|

## Clusters
<root-cause clusters with combined yield>

## Recommendations (ranked by measured yield)
| F<N> | Recommendation | Yield | Routed to | Status |

## Predictions to check next run
<"fixing F2 should move cluster A" — the falsifiable claims this run made>

## Metric defects found
<claims that failed the gate, with the counting bug named — these are parser/dashboard bugs>
```

**Why this file matters:** the next `/meta-feedback` run reads its own prior verdict ledger
first. A claim previously marked `PHANTOM` that reappears unchanged means the metric was
never fixed — escalate it as a *measurement* finding rather than re-verifying from scratch.
The **Predictions** section is the loop's own accountability: next run checks whether the
predicted knock-on actually happened, which is how this loop discovers that *its own*
recommendations were wrong.

Also propose (do not apply) a `FEEDBACK` dashboard region rendering: last run date, claims
verified, verdict distribution, and open recommendations by route. Verdict distribution is
the health metric that matters — a rising `PHANTOM`/`OVERSTATED` share means the monitoring
layer is drifting away from the corpus, which no other tile currently detects.

## Step 7 — Ledger rows

For each `CONFIRMED`/`OVERSTATED` recommendation Ramsey approves in retro, a ledger row is
proposed with status `hypothesis` and a typed metric. **The metric must be the same command
Step 2 used to verify** — so the next run's verification and the ledger's own check are the
same measurement. Rows are proposed here; `/meta-retro` Step 4 owns writing them.

---

## Relationship to the other meta skills

| Skill | Role | Boundary |
|---|---|---|
| `/meta-insights` | **Measures** — generates the report and metrics | Produces claims; does not verify them against raw corpus |
| `/meta-feedback` | **Verifies + routes** — this skill | Gates claims; writes only the feedback record |
| `/meta-retro` | **Decides + applies** — approval gate, ledger, issues | Owns all application; the only one that writes hooks/skills after approval |

Insights measures, feedback verifies, retro enforces. Keeping verification separate from
both measurement and enforcement is deliberate: the layer that produced a number should not
be the layer that certifies it, and the layer that acts on it should receive it already
certified.

`/meta-grow` background-spawns `/meta-insights`; `/meta-dream` background-spawns
`/meta-retro`. This skill sits between them and is invoked deliberately — it is the step
where a human decides that a monitoring signal deserves to become a behavior change.
