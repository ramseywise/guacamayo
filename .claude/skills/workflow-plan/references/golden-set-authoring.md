# Golden-set authoring

Turn DESIGN.md § Behavioral Cases into `data/evals/cases.jsonl` — the executable spec,
authored before the agent exists.

## When this applies

Only when the target repo has `data/evals/` **and** DESIGN.md § Behavioral Cases has
non-placeholder rows. Otherwise skip silently — this is not a universal phase.

## Record shape

One JSON object per line in `data/evals/cases.jsonl`:

```json
{"id": "case-001", "given": "...", "must": "...", "must_not": "...",
 "source_risk": "MVP Scope In: ...", "grader": "code|judge",
 "assertion": "...", "rubric": "..."}
```

- `id` — stable, zero-padded (`case-001`). Never renumber; cases are cited by id.
- `given` / `must` / `must_not` — carried verbatim from the table row's first three columns.
- `source_risk` — the MVP Scope `In:` or `Open:` bullet the row traces to, quoted
  verbatim. A case that traces to nothing is a case nobody asked for; the golden-set
  gate FAILs on an empty or unmatched `source_risk` at any case count.
- `grader` — `code` or `judge`, per the rule below.
- `assertion` — present when `grader` is `code`: the mechanical check.
- `rubric` — present when `grader` is `judge`: what the judge reads for, in
  pass/fail terms.

## Grader selection

Layered graders — use the cheapest one that can actually decide the case.

- **`code`** when the check is a substring, regex, enum membership, or a boolean field.
  Deterministic, free, and it cannot drift. Prefer it whenever it fits.
- **`judge`** when deciding requires reading for tone, completeness, or reasoning —
  anything a string comparison would get wrong.

A case whose `must` is vague enough that neither grader can decide it is not ready to be
a case. Rewrite the DESIGN.md row until two readers agree on pass/fail without arguing.

## Authoring rules

- 20–50 rows, not hundreds. Over-speccing at discovery is the known failure mode; early
  cases have large effect size, so small sets are fine.
- Balance positive and negative. A suite with no `must_not` cases does not measure safety.
- One case per row, in table order. Do not merge rows to hit a count, and do not pad —
  `source_risk` traceability makes padding visible as duplication.

## Gate

The `golden_set_authored` audit at G1 grades: **<10 cases = FAIL**, **10–19 = WARN**
(reports the count and the 20–50 target, does not block), **≥20 = PASS**.

> **Status in guacamayo:** no `/gate-check` skill implements this audit in this repo
> (nor in galactus as of 2026-08-15) — the thresholds above are the authoring target,
> applied by hand until a gate exists. Treat them as the standard to write to, not as
> a check that will fire on its own.

## SANYI layer note

The case ROWS are 简易 Jianyi — add cases freely as you learn. "The golden set is authored
before implementation" is 不易 Buyi.
