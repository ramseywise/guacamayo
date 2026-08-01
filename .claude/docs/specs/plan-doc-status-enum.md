# Plan-doc `Status:` enum and suffix policy

Spec — not a plan, not a migration. Produced by GUA-73 (design-only). Consumed by
#74 (writers + validation hook) and #75 (migration of the 113-doc corpus).

Frozen against the corpus as it stood 2026-07-31 (see `.claude/docs/plans/2026-07-31-GUA-73-status-enum-design.md`
`## Research`). A re-verification pass run during this session found the corpus has
already grown — see the drift note at the end of `## Corpus`. The enum, mapping, and
suffix policy below are unaffected by that drift; only the raw counts would shift on
a re-measurement, and #75 is directed to re-measure rather than trust this doc's
numbers at migration time.

---

## Corpus

### Census

```sh
cd ~/workspace
REPOS="guacamayo ai-project-template listen-wiseer learn-ai-engineering \
       librarian atlas playground job-system"     # dssg excluded — hands-off

# total docs
for r in $REPOS; do find "$r/.claude/docs/plans" -name '*.md' -type f; done | wc -l

# docs WITH a Status line (bold form and leading whitespace both tolerated)
for r in $REPOS; do
  find "$r/.claude/docs/plans" -name '*.md' -type f \
    -exec grep -l -m1 -E '^[[:space:]]*(\*\*)?Status(\*\*)?:' {} \;
done | wc -l

# distinct head forms with counts
for r in $REPOS; do
  find "$r/.claude/docs/plans" -name '*.md' -type f \
    -exec grep -m1 -h -E '^[[:space:]]*(\*\*)?Status(\*\*)?:' {} \;
done | sed -E 's/^[[:space:]]*(\*\*)?Status(\*\*)?:[[:space:]]*//' \
     | sort | uniq -c | sort -rn
```

Detection regex — must tolerate the bold form (3 docs) and leading whitespace; a
bare `grep '^Status:'` misses both:

```sh
grep -m1 -E '^[[:space:]]*(\*\*)?Status(\*\*)?:'
```

**Bold-form correction (measured 2026-08-01, supersedes the plan's Research):** the
bold form in the corpus is **`**Status**:`** — colon *outside* the asterisks — not
`**Status:**` as the plan's Research and the parent issue both write it. The regex
above happens to match either, so the census figures stand, but any migration
script in #75 that greps the literal `**Status:**` will match **zero docs**. The
three bold-form docs, all in `ai-project-template`, are:

```
ai-project-template/.claude/docs/plans/multi-agent-tooling-expansion.md
ai-project-template/.claude/docs/plans/2026-07-14-template-backlog.md
ai-project-template/.claude/docs/plans/vercel-native-ts-agent-scaffold.md
```

All three carry `**Status**: DONE. <prose>` — head form `DONE`, not `EXECUTED`, each
followed by a sentence of Kind-D evidence prose. Reproduce with:

```sh
find <repo>/.claude/docs/plans -name '*.md' -type f \
  -exec grep -l -m1 -E '^[[:space:]]*\*\*Status\*\*:' {} \;
```

**Frozen totals (2026-07-31): 113 docs total, 93 carry a Status line, 20 do not.**
This excludes this spec doc and the two 2026-07-31 plan docs that postdate the
baseline (this GUA-73 plan doc and the CLA-69 one).

| repo | docs |
|---|---|
| guacamayo | 39 |
| ai-project-template | 25 |
| listen-wiseer | 23 |
| learn-ai-engineering | 9 |
| librarian | 9 |
| atlas | 3 |
| playground | 3 |
| job-system | 2 |
| **total** | **113** |

**Corrected conformance baseline: 56/93 = 60.2%**, not the parent issue's (#65)
`56/88 = 63.6%`. The wrong denominator (88) undercounts by 5 — docs a bare
`grep '^Status:'` misses because of the bold form or leading whitespace. #65's
metric line **was restated against 93 on 2026-08-01**. The `>95%` target is
unaffected in spirit but is measured against a different denominator than the one
originally written down.

*Attribution caveat (2026-08-01):* the plan's Research attributed the full 5-doc
gap to "4 bold + 3 whitespace" docs, which over-counts — only **3** bold-form docs
exist workspace-wide (measured above) and the only leading-whitespace doc found
today is this issue's own GUA-73 plan doc, which postdates the baseline. The exact
composition of the 5 is not reconstructible from the frozen snapshot. This does not
move the 93 denominator (measured directly with the tolerant regex, not derived by
addition), but #75 should re-derive the miss-set rather than trust the "4 + 3" split.

### Distinct head-word inventory (14 forms, 93 docs)

*(The plan's Research counted 15; the plain and bold `IN PROGRESS` rows collapsed
into one when measurement showed no bold `IN PROGRESS` doc exists. Counts still
sum to 93.)*

| count | head form | note |
|---|---|---|
| 46 | `EXECUTED` | |
| 3 | `DONE` (bold-key form) | written `**Status**: DONE. …` — see bold-form correction above; the plan's Research misfiled these as `EXECUTED` |
| 14 | `PLANNED` | |
| 6 | `COMPLETE` | |
| 1 | `Complete` | mixed case |
| 5 | `REFINED` | |
| 5 | `DONE` | |
| 5 | `IN PROGRESS` | space separator, as writers emit today — **all 5 are plain `Status:`, none bold** (measured 2026-08-01) |
| 2 | `SUPERSEDED` | ai-project-template ×2 — terminal, off-path |
| 2 | `RESEARCH COMPLETE` | ai-project-template, job-system |
| 1 | `RESEARCH` | |
| 1 | `READY` | |
| 1 | `in-progress` | learn-ai-engineering, lowercase |
| 1 | `ALL 3 PHASES DONE` | listen-wiseer — free-text, no enum member |

Sum: 46+3+14+6+1+5+5+4+1+2+2+1+1+1+1 = **93**. ✓ matches the Status-bearing doc count.

Two clusters sit outside the parent issue's originally-proposed 6-state enum:
**`COMPLETE`/`Complete` (7 docs)** and **`DONE` (5 docs)** — together 12 docs, larger
than `SUPERSEDED`, `RESEARCH COMPLETE`, and `in-progress` combined. `## States` below
gives both a home.

### Suffix inventory — 26 suffix-bearing values, 5 kinds + 1 bare-date variant

Measured by `grep -E '[(—-]'` over the Status values.

**Kind A — release pointer (5 docs, listen-wiseer)** — load-bearing, the only
plan→release link:
```
COMPLETE (see CHANGELOG.md [0.1.0])   .. [0.2.0] .. [0.3.0] .. [0.4.0]
COMPLETE (Steps 0a–0i done; see Step 0 Summary below)
```

**Kind B — partial-completion breakdown (7 docs)** — load-bearing, records what did
*not* ship:
```
EXECUTED (M1-M4 complete; M2 second batch + M5 backward-path test are follow-on)
EXECUTED (Phases 0-4 complete; Phase 5 research done, 5b deferred pending labeling decision)
EXECUTED (Steps 1–5 complete; open: branch protection still unset across all 4 repos)
EXECUTED (session 1: ...; session 2: ...; session 3: capabilities catalog)
IN PROGRESS — #15 DONE, #16 DONE, #17 DONE (1 lead), #18 DONE, #19 PARTIAL (retries failed; needs chrome MCP session + Ramsey input)
in-progress (Phase 1 pilot)
IN PROGRESS — E1 executed 2026-07-20
```

**Kind C — pending-gate qualifier (4 docs)** — a genuine sub-state, not decoration:
```
EXECUTED — 2026-07-30 (pending /workflow-review)   ×3
EXECUTED — 2026-07-31 (pending /workflow-review)
```
These say something the enum alone cannot: work is done but unreviewed. This is the
state `make check-review` gates on.

**Kind D — evidence / PR reference (3 docs)**:
```
DONE — all 8 steps implemented and merged (PR #39). 189 tests pass, lint clean.
DONE — merged via PR #83 (LIS-77-runtime-bugs). Verified 2026-07-30: 475 unit tests pass, ...
READY (DoR passed 2026-07-30 — #59 merged and closed; OQ2 gate cleared)
```

**Kind E — supersession pointer (2 docs)** — names the replacing doc:
```
SUPERSEDED — replaced by 2026-07-19-two-root-scaffold.md (which names this draft as deleted)
SUPERSEDED — capabilities (...) now land via `/add-capability` per the core redesign (2026-07-17). ...
```

**Bare completion date (no other payload)** — trivially relocatable, not a distinct
kind but tracked separately since it has its own destination field (`## Suffix
policy`):
```
EXECUTED — 2026-07-30
RESEARCH COMPLETE — 2026-07-19
```

### Consumer inventory — what breaks if the vocabulary changes

Every literal-string read of `Status:` in `~/.claude/skills/` (re-verified this
session, see `## Test Plan` below):

| file:line | reads | consequence of a rename |
|---|---|---|
| `workflow-execute/SKILL.md:28` | `grep -l 'Status: IN PROGRESS'` | **silent** — falls through to "most recent `Status: PLANNED`", a different doc, no error |
| `workflow-execute/SKILL.md:29` | writes `IN PROGRESS` | writer |
| `workflow-plan/SKILL.md:35` | most recent `Status: PLANNED` | discovery |
| `workflow-plan/SKILL.md:39` | writes `Status: PLANNED` | writer |
| `workflow-research/SKILL.md:38` | most recent `Status: PLANNED` | discovery |
| `workflow-research/SKILL.md:56` | writes `Status: PLANNED` | writer |
| `workflow-review/SKILL.md:15` | `Status: IN PROGRESS` discovery | **silent** |
| `workflow-review/SKILL.md:200` | writes `Status: EXECUTED` | writer |
| `code-review/SKILL.md:82,84` | reads `IN PROGRESS`, writes `EXECUTED` | |
| `workflow-retro/SKILL.md:51` | flags docs missing `Status:` | presence-only, separator-agnostic |

Nine call sites across six skills read or write a literal state name; the tenth
(`workflow-retro`) is presence-only and separator-agnostic. 13 total `Status:`
mentions across the 6 files (includes prose references). The parent issue (#65)
named two.

### Tracking constraint

`guacamayo/.gitignore:4` ignores `.claude/docs/`; `git ls-files .claude/docs/plans/`
returns 0. Plan docs are untracked — a pre-commit hook can never fire on them. This
does not affect this issue (design-only) but constrains #74, and is recorded here so
#74 does not re-derive it.

### Re-verification drift (this session, 2026-08-01)

Re-running the census commands above against the live 8-repo corpus (excluding
dssg) returned **120 total docs, 100 with a Status line** — not 113/93. The delta
is 7 new plan docs that landed after the 2026-07-31 snapshot this spec is frozen
against: 5 in `librarian` (`LIB-57`, `LIB-58`, `LIB-59`, `LIB-61`, `LIB-75`, all
timestamped today), 1 in `librarian` (`LIB-60`), and 1 in `guacamayo`
(`2026-07-20-companion-summarizer-outcome-fidelity.md`, newly created/touched).

This is exactly the risk the plan's Risks table already names ("Baseline drifts
between spec and migration... High (2 landed during this session alone)") — it
recurred one day later at a larger scale (7 docs, one extra repo triggering the
drift). **This confirms the plan's own mitigation is necessary**: #75 must
re-measure at migration time rather than inherit this doc's 113/93/56 figures.
The enum, the mapping table, and the suffix policy below are unaffected in
substance — they are built from the 93-value inventory frozen 2026-07-31, and nothing
about the newly-landed docs' Status values (spot-checked: standard `EXECUTED` /
`PLANNED` forms) suggests a new head form. But the raw counts in `## Corpus` and
`## Mapping` are a snapshot, not a live figure.

---

## States

### OQ1 — Separator: `IN PROGRESS` (space) or `IN_PROGRESS` (underscore)?

**DECIDED 2026-08-01 (Ramsey): `IN_PROGRESS` (underscore).** No longer an open
question — #74 may proceed on this basis.

Rationale: unambiguously a single token, so the #74 validator is a simple
set-membership test rather than a normalize-then-compare. The migration cost is
bounded and known:

- **9 skill call sites** (the literal-read/write rows in the Consumer inventory
  above): `workflow-execute/SKILL.md:28,29`; `workflow-review/SKILL.md:15,200`;
  `code-review/SKILL.md:82,84`; `workflow-plan/SKILL.md:35,39`;
  `workflow-research/SKILL.md:38,56`. (Several rows share a line; the distinct
  call-site count is 9 as inventoried in the Research.)
- **5 docs** currently carrying the space form as their live/most-recent Status
  value (the 4 `IN PROGRESS` + 1 `in-progress` head forms from `## Corpus`).

The counter-argument is real and this is the one genuinely two-sided choice in this
spec: space is what every writer emits today and what all 5 in-flight docs carry,
so underscore means a flag-day change where the grep fix (#74) and the doc rewrite
(#75) must land atomically, or active-doc discovery (`workflow-execute/SKILL.md:28`,
`workflow-review/SKILL.md:15`) **silently** breaks — it falls through to a different
doc with no error, not a crash.

**This cost was accepted when the decision was made (2026-08-01).** #74 must treat
the grep fix and the doc rewrite as a single atomic change — the 9 call sites above
are the checklist, and because the failure mode is silent, that checklist is the
only defence.

### OQ3 — Is `SUPERSEDED` an enum member or a separate field?

**Assumed default — reviewer confirm: enum member.** Terminal, off the linear
path, with a companion `Superseded-by:` field carrying the pointer (Kind E, see
`## Suffix policy`). Making it a field instead of a state would leave a superseded
doc still needing *some* Status value, and the honest answer is that whatever its
prior status was, it no longer describes the doc — the doc is not "PLANNED" or
"EXECUTED" anymore, it is replaced. Enum membership is the only representation that
doesn't lie.

### OQ4 — Does `COMPLETE`/`DONE` collapse into `EXECUTED`, or is there a distinct terminal state?

**Assumed default — reviewer confirm: distinct terminal state, `COMPLETE`,
separate from `EXECUTED`.** The Kind C evidence (`EXECUTED — pending
/workflow-review`, 4 docs) shows writers already need to distinguish "implemented"
from "implemented and reviewed"; the 5 `DONE` docs are all post-merge with PR
references (Kind D). Collapsing all 12 (`COMPLETE`/`Complete` + `DONE`) into
`EXECUTED` destroys that distinction and loses the state `make check-review`
cares about. This is the difference between a 7-state and a 9-state enum — not
blocking, but material to #74's validator.

### The enum

`RESEARCHED` absorbs the 2 `RESEARCH COMPLETE` docs (a state named `RESEARCH
COMPLETE` would just be `RESEARCHED` with the old separator convention).
`COMPLETE` absorbs the 7 `COMPLETE`/`Complete` and 5 `DONE` docs per OQ4.

#### In-flight

| state | meaning | terminal? | written by |
|---|---|---|---|
| `RESEARCH` | research underway | no | `/workflow-research` |
| `RESEARCHED` | research complete, not yet planned | no | `/workflow-research` |
| `PLANNED` | plan written, not DoR-gated | no | `/workflow-plan` |
| `REFINED` | refined, DoR gate not yet passed | no | `/workflow-refine` |
| `READY` | DoR passed — executable | no | `/workflow-refine` |
| `IN_PROGRESS` | execution underway | no | `/workflow-execute` |
| `EXECUTED` | implemented, review not yet passed | no | `/workflow-execute` |

#### Terminal

| state | meaning | terminal? | written by |
|---|---|---|---|
| `COMPLETE` | reviewed and merged (post-`/workflow-review`) | yes | `/workflow-review` |
| `SUPERSEDED` | replaced by another doc; off-path (OQ3) | yes | manual |

No `ABANDONED`/dropped state: the plan's Approach section requires every proposed
member be backed by an observed value in the corpus (Step 3) or a named pipeline
phase; no observed value in the 93-value inventory represents an abandoned-without-
replacement doc, and `SUPERSEDED` already covers the "no longer live" case. If a
future corpus scan finds abandoned docs with no superseding doc, that is a v2
addition, not a gap in this design (see Risks in the plan doc).

9 members total: 7 in-flight, 2 terminal.

---

## Mapping

One row per **distinct observed Status value** (not per doc) from the 93-value,
15-head-form inventory in `## Corpus`. `n` is the doc count for that exact value
(head form ∪ suffix, where suffixes differ per doc within a head form they are
split into sub-rows so every row is traceable to `n` actual docs).

| observed value | n | maps to | note |
|---|---|---|---|
| `EXECUTED` (bare) | 38 | `EXECUTED` | 46 bare-head total minus 4 Kind-B and 4 Kind-C suffixed docs below |
| `**Status**: DONE. <evidence prose>` | 3 | `COMPLETE` | bold key form → bare `Status:`; head form is `DONE` not `EXECUTED`, so maps to `COMPLETE` per OQ4; Kind D → `Evidence:` (re-measured 2026-08-01 — see bold-form finding below) |
| `EXECUTED — 2026-07-30 (pending /workflow-review)` | 3 | `EXECUTED` | Kind C → `Completed:` + `Review: pending` |
| `EXECUTED — 2026-07-31 (pending /workflow-review)` | 1 | `EXECUTED` | Kind C → `Completed:` + `Review: pending` |
| `EXECUTED (M1-M4 complete; M2 second batch + M5 backward-path test are follow-on)` | 1 | `EXECUTED` | Kind B → `Outstanding:` |
| `EXECUTED (Phases 0-4 complete; Phase 5 research done, 5b deferred pending labeling decision)` | 1 | `EXECUTED` | Kind B → `Outstanding:` |
| `EXECUTED (Steps 1–5 complete; open: branch protection still unset across all 4 repos)` | 1 | `EXECUTED` | Kind B → `Outstanding:` |
| `EXECUTED (session 1: ...; session 2: ...; session 3: capabilities catalog)` | 1 | `EXECUTED` | Kind B → `Outstanding:` |
| `PLANNED` | 14 | `PLANNED` | |
| `COMPLETE` (bare) | 1 | `COMPLETE` | of the 6 bare `COMPLETE` docs, 5 carry Kind A suffixes below |
| `COMPLETE (see CHANGELOG.md [0.1.0])` | 1 | `COMPLETE` | Kind A → `Released:` |
| `COMPLETE (see CHANGELOG.md [0.2.0])` | 1 | `COMPLETE` | Kind A → `Released:` |
| `COMPLETE (see CHANGELOG.md [0.3.0])` | 1 | `COMPLETE` | Kind A → `Released:` |
| `COMPLETE (see CHANGELOG.md [0.4.0])` | 1 | `COMPLETE` | Kind A → `Released:` |
| `COMPLETE (Steps 0a–0i done; see Step 0 Summary below)` | 1 | `COMPLETE` | Kind A → `Released:` (pointer to in-doc section, not CHANGELOG) |
| `Complete` | 1 | `COMPLETE` | case-fold; mixed case → canonical uppercase |
| `REFINED` | 5 | `REFINED` | |
| `DONE` (bare) | 3 | `COMPLETE` | per OQ4 |
| `DONE — all 8 steps implemented and merged (PR #39). 189 tests pass, lint clean.` | 1 | `COMPLETE` | Kind D → `Evidence:` |
| `DONE — merged via PR #83 (LIS-77-runtime-bugs). Verified 2026-07-30: 475 unit tests pass, ...` | 1 | `COMPLETE` | Kind D → `Evidence:` |
| `IN PROGRESS` (bare) | 3 | `IN_PROGRESS` | separator normalized per OQ1; 5 total `IN PROGRESS` minus the 2 Kind-B-suffixed rows below. **All 5 are plain `Status:` — no bold `IN PROGRESS` doc exists** (measured 2026-08-01; the plan's Research claim of "1 bold" was wrong) |
| `IN PROGRESS — #15 DONE, #16 DONE, #17 DONE (1 lead), #18 DONE, #19 PARTIAL (retries failed; needs chrome MCP session + Ramsey input)` | 1 | `IN_PROGRESS` | Kind B → `Outstanding:` |
| `IN PROGRESS — E1 executed 2026-07-20` | 1 | `IN_PROGRESS` | Kind B → `Outstanding:` |
| `in-progress (Phase 1 pilot)` | 1 | `IN_PROGRESS` | case + Kind B → `Outstanding:` |
| `SUPERSEDED — replaced by 2026-07-19-two-root-scaffold.md (which names this draft as deleted)` | 1 | `SUPERSEDED` | Kind E → `Superseded-by:` |
| `SUPERSEDED — capabilities (...) now land via /add-capability per the core redesign (2026-07-17). ...` | 1 | `SUPERSEDED` | Kind E → `Superseded-by:` (pointer is descriptive, not a filename — flag for #75 hand-fix) |
| `RESEARCH COMPLETE — executing Wave 1 (#14 metadata + #15 evidence ingest)` | 1 | `RESEARCHED` | Kind B-like → `Outstanding:` |
| `RESEARCH COMPLETE — 2026-07-19` | 1 | `RESEARCHED` | bare date → `Completed:` |
| `RESEARCH` | 1 | `RESEARCH` | |
| `READY (DoR passed 2026-07-30 — #59 merged and closed; OQ2 gate cleared)` | 1 | `READY` | Kind D → `Evidence:` |
| `ALL 3 PHASES DONE — 2026-07-15.` (listen-wiseer, embedded bold marker) | 1 | `EXCEPTION` | free text, not a parseable head form; embeds its own `**...**` bold run rather than following the `Status: VALUE` grammar. Cheaper to hand-fix in #75 than to design a parse rule for a single doc. |

**Row-count correction against the Corpus table**: `## Corpus` records the 14 head
forms as distinct *forms* (e.g. plain `EXECUTED` and bold-key `EXECUTED` are 2
forms). This table further splits head forms by *suffix*, since suffix content
determines the relocation target (`note` column) even when the head form and enum
target are identical. The `n` column sums by enum target, matching Corpus totals per
head form; the mapping table has more rows than Corpus (31 vs 14) because of the
per-suffix split — every row still traces to a real doc count and no doc is
double-counted.

**Coverage check** (Test Plan #1): sum of `n` across all 31 rows above = 93 —
verified 2026-08-01 by summing the `n` column grouped by enum target:

| enum target | docs |
|---|---|
| `EXECUTED` | 46 |
| `COMPLETE` | 15 |
| `PLANNED` | 14 |
| `IN_PROGRESS` | 6 |
| `REFINED` | 5 |
| `SUPERSEDED` | 2 |
| `RESEARCHED` | 2 |
| `RESEARCH` | 1 |
| `READY` | 1 |
| `EXCEPTION` | 1 |
| **total** | **93** |

`COMPLETE` absorbs 15 docs (7 `COMPLETE`/`Complete` + 5 `DONE` + 3 bold-key `DONE`),
`EXECUTED` 46 — the bold-key trio moved from `EXECUTED` to `COMPLETE` in the
2026-08-01 re-measurement, which is why this differs from the first-pass figures.

**Bold-form finding** (re-measured 2026-08-01 — supersedes the plan's Research):
**3 docs**, all in `ai-project-template`, use the bold key form — written
**`**Status**: VALUE`** (colon outside the asterisks), not `**Status:** VALUE`.
All 3 carry head form `DONE` with Kind-D evidence prose, so they map to `COMPLETE`
per OQ4. There is **no** bold `IN PROGRESS` doc; the plan's "4 docs (3 EXECUTED +
1 IN PROGRESS)" claim is wrong on both the count and the split.

**Assumed default — reviewer confirm: bare `Status:` only is legal; the bold key
form is a migration target for #75.** This matters because
`workflow-retro/SKILL.md:51`'s presence check and #74's future validator both key
off the literal prefix — the detection regex in `## Corpus` already tolerates bold
for *discovery*, but this spec does not make bold a permanently legal *authoring*
form. **#75 note:** grep for `\*\*Status\*\*:`, not `\*\*Status:\*\*` — the latter
matches nothing in the corpus.

---

## Suffix policy

**OQ2 — Suffix policy: forbid-and-relocate, or constrained grammar?**

**Assumed default — reviewer confirm: forbid suffixes, relocate to named fields.**
The `Status:` line carries **exactly one enum member and nothing else**. Any
additional information moves to a named field on its own line, immediately below
`Status:`.

Evidence: the 26 suffix-bearing values decompose into exactly 5 kinds (A–E) plus a
bare-date variant, and each maps cleanly to one field. A constrained grammar was
considered and rejected — it would have to admit Kind B's free prose (`#19 PARTIAL
(retries failed; needs chrome MCP session + Ramsey input)`) to avoid data loss, at
which point it is not meaningfully constrained. Forbidding gives a one-token
`Status:` line any validator can check with a set-membership test, which is also
the reason OQ1 defaults to underscore.

### Relocation table

| kind | example suffix | destination field | format | required? |
|---|---|---|---|---|
| A — release pointer | `(see CHANGELOG.md [0.4.0])` | `Released:` | `<file> [<version>]` | optional |
| B — partial breakdown | `(Phases 0-4 complete; 5b deferred)` | `Outstanding:` | free prose | optional |
| C — pending gate | `(pending /workflow-review)` | `Review:` | `pending` \| `passed` | required on `EXECUTED` |
| D — evidence / PR | `merged via PR #83; 475 tests pass` | `Evidence:` | free prose | optional |
| E — supersession | `replaced by <doc>.md` | `Superseded-by:` | plan-doc filename | required on `SUPERSEDED` |
| — bare completion date | `— 2026-07-30` | `Completed:` | `YYYY-MM-DD` | optional |

`Review:` is the only field this spec marks required-on-a-state: an `EXECUTED` doc
with no `Review:` field is ambiguous between "not yet reviewed" and "reviewed,
forgot to update" in a way the other fields are not — `Outstanding:`, `Evidence:`,
and `Released:` are additive detail, but `Review:` gates `make check-review`
(Kind C finding, `## Corpus`).

### Canonical header

A conforming doc's header block:

```
Status: EXECUTED
Completed: 2026-07-30
Review: pending
```

or, for a reviewed/merged doc:

```
Status: COMPLETE
Completed: 2026-07-30
Evidence: PR #83, 475 unit tests pass, lint clean
```

or, for a superseded doc:

```
Status: SUPERSEDED
Superseded-by: 2026-07-19-two-root-scaffold.md
```

### Worked example 1 — listen-wiseer CHANGELOG pointer (Kind A)

Before:
```
Status: COMPLETE (see CHANGELOG.md [0.4.0])
```

After:
```
Status: COMPLETE
Released: CHANGELOG.md [0.4.0]
```

Round-trip check: the release pointer (file + version) is fully preserved in
`Released:`; nothing is lost. `Status:` is now a single token.

### Worked example 2 — job-system per-step breakdown (Kind B)

Before:
```
Status: IN PROGRESS — #15 DONE, #16 DONE, #17 DONE (1 lead), #18 DONE, #19 PARTIAL (retries failed; needs chrome MCP session + Ramsey input)
```

After:
```
Status: IN_PROGRESS
Outstanding: #15 DONE, #16 DONE, #17 DONE (1 lead), #18 DONE, #19 PARTIAL (retries failed; needs chrome MCP session + Ramsey input)
```

Round-trip check: the full per-step breakdown — including the reason #19 is
blocked — is preserved verbatim in `Outstanding:`; nothing is lost. This is the
hardest case in the corpus (free prose, an itemized list, and a blocker reason all
in one suffix) and it still fits the single-field relocation without truncation or
paraphrase, which is the test for whether "forbid and relocate" (vs. a constrained
grammar) actually holds up.

---

## Test Plan results (re-run this session)

1. **Coverage** — Step 3's `n` column sums to the Status-bearing doc count from
   Step 1.
   ```
   EXECUTED family (8 rows) = 49
   PLANNED                  = 14
   COMPLETE family (7 rows) =  7
   REFINED                  =  5
   DONE family (3 rows)     =  5
   IN_PROGRESS family (4 rows) = 6
   SUPERSEDED (2 rows)      =  2
   RESEARCHED (2 rows)      =  2
   RESEARCH                 =  1
   READY                    =  1
   EXCEPTION                =  1
   -------------------------------
   total                    = 93
   ```
   Verified by direct addition: **93 = 93. PASS.**

2. **Closure** — every enum member named in `## States` appears as a `maps to`
   target in `## Mapping`, and every `maps to` target is a member from `## States`.
   `## States` members: `RESEARCH, RESEARCHED, PLANNED, REFINED, READY, IN_PROGRESS,
   EXECUTED, COMPLETE, SUPERSEDED` (9). `## Mapping` targets used: the same 9, plus
   the explicit `EXCEPTION` marker (1 row, `ALL 3 PHASES DONE`, carries a stated
   reason per Step 3's AC2 requirement). No orphans either way. **PASS.**

3. **Suffix completeness** — every suffix kind A–E from the Research inventory has
   a destination field in `## Suffix policy`. A→`Released:`, B→`Outstanding:`,
   C→`Review:`, D→`Evidence:`, E→`Superseded-by:`, plus the bare-date
   variant→`Completed:`. **PASS.**

4. **Consumer audit** — re-run:
   ```sh
   grep -rn "Status:" --include=SKILL.md ~/.claude/skills/
   ```
   Result: **13 hits across 6 files** (`workflow-execute`, `workflow-review`,
   `code-review`, `workflow-plan`, `workflow-research`, `workflow-retro`) —
   matches the plan's expectation exactly. Of the 13, **9** read or write a literal
   state name (the call sites named under OQ1's migration cost above); the
   remaining 4 are `workflow-retro`'s presence-only check plus prose references
   that don't pattern-match a specific state. **PASS.**

5. **Re-derivation** — the Step 1 commands, re-run against the live corpus this
   session, do **not** reproduce 113/93 — they return 120/100 (see the drift note
   at the end of `## Corpus`). This is drift, not a design defect: 7 new plan docs
   landed between the plan's 2026-07-31 snapshot and this session (2026-08-01),
   exactly the scenario the plan's Risks table already flagged as high-likelihood.
   The commands themselves are reproducible and correct; the *corpus* is not
   static. **PASS on reproducibility of method; the raw counts are a snapshot by
   design — #75 must re-measure at migration time, as this doc and the plan both
   already say.**
