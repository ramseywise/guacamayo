---
name: hypothesis
description: "Design the data collection for a new experiment BEFORE writing its ledger row — refuses to emit a row whose metric is unfalsifiable, unregistered, or awaiting a collection change, and computes the due date at 2 retro rounds. Trigger on: /hypothesis, 'add a ledger row', 'new experiment', 'test whether', 'measure whether', 'propose a hypothesis', a /meta-retro recommendation that needs a metric."
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash Edit
---

You are designing **data collection**, not writing a row. The row is the last
artifact you produce, and only if the metric survives every gate below.

## Why this skill exists

Measured 2026-08-19 against the live ledger: **49 of 59 hypotheses could not be
scored at all**, and 39 of 59 were unfalsifiable as written — they could never
fail, so they could never close. That is why the ledger only ever grew.

The failure was a *design-time* one. Every unscorable row was written in good
faith by someone who never checked whether the claim was observable. This skill
is the gate that check now lives in.

**A hypothesis that cannot fail is not a hypothesis.** Refuse it.

## The registry is the source of truth

`telemetry/signals.py` declares every signal name the system can resolve, in four
states. Read it — never guess whether a name exists:

```bash
uv run python -c "
from telemetry import signals
for s in signals.all_signals():
    print(f'{s.state:16} {s.name}')"
```

| state | meaning | what the author must do |
|---|---|---|
| `registered` | a resolver exists | use it — nothing to build |
| `needs-collection` | observable, but the field is not captured | **emit the collection change first**, row second |
| `unobservable` | no event stream could record this | **rewrite** the claim into a countable form |
| `unregistered` | nobody declared it | register it in the same change, or rewrite |

## Gate 1 — Falsifiability

Ask literally: **what value of this metric would mean the change failed?**

If you cannot name one, the metric is not falsifiable. Reject it.

`absence:` claims fail this gate most often. "No occurrences of X" is confirmed by
silence — and silence is also what a broken collector, an empty window, and an
unobservable event all produce. An `absence:` claim is only admissible when its
signal is `registered` **and** the resolver returns a real zero rather than
`None` (see the `file-not-found-errors` tests for the distinction).

Rewrite unfalsifiable claims into countable ones:

| rejected | why | rewrite |
|---|---|---|
| `absence:land-verification-by-message-alone` | nothing records *how* a landing was verified | `count-drop:landings-without-inspection-evidence above 0` — but only after the collector records it |
| `presence:design-skill-invoked` | judgement about "design-heavy" sessions, unmeasurable | `count-drop:design-skill-invocations above 3 across 2 retro rounds` |
| `absence:variable-cd-misresolution` | shell resolution is not logged anywhere | not measurable at all — take it out of the ledger, or add a hook that logs it first |

## Gate 2 — Signal resolution

Resolve the metric's signal against the registry. Then, by state:

- **registered** → proceed to Gate 3.
- **needs-collection** → **stop.** Emit the *collection change* as the deliverable
  (which column, which collector, which job) and say plainly that the ledger row
  comes after it lands. Quote the entry's `remedy` — it names exactly what to
  capture. Do not write a row that cannot be scored on the day it is written.
- **unobservable** → **stop.** Quote the `remedy` and return to Gate 1 with a
  rewrite. Registering it is not an option; the claim itself is the problem.
- **unregistered** → either register a resolver in `telemetry/signals.py` as part
  of this same change (preferred, when the data exists), or rewrite.

Never let a row through by inventing a signal name that "looks like" a registered
one. The registry is a closed namespace precisely so that a typo fails loudly
instead of scoring `inconclusive` forever.

### Gate 2b — the signal is not already claimed

An active row already measuring this signal means one of the two is dead. Check
before writing, and name the collision if there is one:

```bash
uv run python -c "
from telemetry import signals
from pathlib import Path
print(signals.resolve('duplicate-active-ledger-signals',
      signals.SignalSources(workspace=Path.home()/'workspace')))"
```

This must read `0.0`. The 2026-08-19 audit added this check after finding both
failure shapes at once: **#40/#41 were one finding written twice** (the second
against `/grow`, a path the v3 rename had deleted), and **two rows shared
`execution-sessions-with-skills`** with different targets and no cross-reference,
so the older sat dead for three weeks while looking active.

If the signal is already claimed, do not write a second row. Either supersede the
existing row (graduate it, and say in the new row which one it replaces) or widen
the existing row's target. Two rows measuring one signal is how a ledger grows
without closing.

## Gate 3 — Due date, computed not typed

Retro fires every **1–5 days** in practice (measured R7→R8 4d, R8→R9 1d, R9→R10
5d, R10→R11 5d), but due dates were being written ~14 days out. A hypothesis
therefore survived 3–5 retro rounds before anyone had to look at it — which is
how 20 rows went past due, 18 of them sharing a single stale deadline.

**Due date = 2 retro rounds from creation.** Compute it; never accept a typed one:

```bash
uv run python -c "
from datetime import date, timedelta
print((date.today() + timedelta(days=10)).isoformat())"
```

Two rounds at the observed upper bound (5d) is 10 days. Use that as the default,
and say in the row that it is 2 rounds — not a date someone picked.

The due date is **required**. A row without one never comes up for audit.

## Gate 4 — Name the plane

Every row states which architecture layer it acts on, so the decision log can join
to it (`telemetry/actions.py`, `PLANE_*`):

- `work` — the work itself: issues, branches, labels
- `metacognition` — the system observing itself: retro, insights, skills
- `control` — the loop that runs the system: jobs, schedules, alerts

## Gate 5 — pattern_key for friction-type rows

Every row whose metric begins with `absence:` or `count-drop:` is a friction-type
row — it measures the *reduction* of something bad. Friction rows require a
`pattern_key` that traces the row back to a PATTERNS signature in
`telemetry/recurrence.py`.

**Check the Change + metric text against PATTERNS:**

```bash
uv run python -c "
from telemetry.recurrence import PATTERNS
import re, sys
text = ' '.join(sys.argv[1:])
matched = [k for k, rx in PATTERNS.items()
           if re.search(rx, text, re.IGNORECASE)]
print(matched or 'NO MATCH')" \
"<paste Change + metric text here>"
```

Decision tree:

```
if metric starts with "absence:" or "count-drop:":
    1. Look for an explicit pattern_key in the Change text
       (e.g. "warn-hook for `silent-swallow`" names the key).
    2. If not explicit, run the Change + metric through PATTERNS above.
       - One or more matches -> propose the key(s); author must confirm or
         reject each. Confirmed key goes into the row's Status cell as
         `pattern_key: \`<key>\``.
       - No match -> ask: "Is this a code-corpus friction (would appear as a
         finding title in a review sweep)?"
         - YES -> propose a new PATTERNS entry in `telemetry/recurrence.py`
           first. Block the ledger row until the signature is written and
           tests pass.
         - NO (workflow/process/infra friction) -> accept the row without a
           pattern_key. State in the row that none applies and why (one
           sentence).
    3. If a pattern_key is already present, verify it exists in PATTERNS:
       `python -c "from telemetry.recurrence import PATTERNS; print('<key>' in PATTERNS)"`
       If False, reject with: "pattern_key '<key>' not in telemetry/recurrence.py
       PATTERNS -- add the signature first."
```

**What counts as code-corpus friction**: the friction appears (or would appear) as a
finding title in a review sweep — e.g. "hardcoded URL" in a scan of a Python file.
Workflow rows (skill compliance, PR metadata, ledger hygiene) describe process
behaviour, not code defects, and correctly have no pattern_key.

**No partial pass.** If Gate 5 cannot be resolved (no key, no confirmation the row is
process friction), stop and return the decision to the author.

## Output

Produce, in this order:

1. **Verdict** — admit or refuse. If refused, say which gate and why.
2. **Collection design** (when the signal is not yet `registered`) — what gets
   recorded, by which job/collector, starting when. This is the real deliverable;
   the row is downstream of it.
3. **The ledger row**, only if every gate passed:

```
| YYYY-MM-DD | <change> | <area> | `<type>:<registered-signal> <comparator> <threshold>` | hypothesis — <plane> plane; due YYYY-MM-DD (2 retro rounds) |
```

4. **Registry diff** — the `telemetry/signals.py` entry, when one was added.

Append to `.sounding/tooling-ledger.md`. Never edit `experiment_verdicts` or any
`Status:` prose — the typed verdict table is authoritative and the prose column is
a stale mirror.

## Backlog audit (run at retro time)

Surface rows that are past due, so the ledger closes as well as grows:

```bash
uv run python -c "
from datetime import date
from pathlib import Path
import re
today = date.today().isoformat()
for line in Path('.sounding/tooling-ledger.md').read_text().splitlines():
    if not line.startswith('|'): continue
    # Match both "due 2026-08-24" and bare "due 08-24"
    m = re.search(r'due (\d{4})-(\d{2})-(\d{2})', line)
    m2 = re.search(r'due (\d{2})-(\d{2})(?!\d)', line) if not m else None
    if m:
        due = m.group(1) + '-' + m.group(2) + '-' + m.group(3)
    elif m2:
        due = today[:4] + '-' + m2.group(1) + '-' + m2.group(2)
    else:
        due = None
    if due and due < today:
        print(f'OVERDUE {due}: {line.split(chr(124))[2].strip()[:70]}')
    elif 'hypothesis' in line and not due:
        print(f'NO DUE DATE: {line.split(chr(124))[2].strip()[:70]}')"
```

Every overdue row gets a decision this round: graduate it (to
`tooling-ledger-log.md`), rewrite its metric, or drop it. Leaving it is not one of
the options — that is the behaviour this skill exists to end.
