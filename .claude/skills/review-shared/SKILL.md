---
name: review-shared
description: >
  Shared Scan Rules — cross-scanner finding format, evidence model, and severity
  mapping for the dimension agents. Reference material, not invoked directly.
allowed-tools: Read
---

# Shared Scan Rules

Loaded by all dimension agents. Defines cross-scanner rules: the evidence model,
finding format, severity mapping, and shared operational constraints.

## Finding Format (canonical)

Every finding — regardless of dimension — uses this format:

```
**[merge_impact:evidence_state]** `<PREFIX>-<NNN>` `file:line` — claim title
Evidence: basis summary (what was found, what confirms it)
Merge impact: merge_impact
```

Fields:
- `merge_impact`: blocker | important | question | suggestion | nit
- `evidence_state`: verified | supported | hypothesis | question
- `<PREFIX>-<NNN>`: dimension prefix + 3-digit number (e.g. `CR-001`, `SF-002`)
- `file:line`: path and line number from the file scanned

Full schema: `review/docs/finding-schema.md`

## Dimension ID Prefixes

| Dimension | Prefix | Agent |
|-----------|--------|-------|
| correctness | CR- | correctness |
| intent | IN- | intent |
| architecture | AR- | architecture |
| safety | SF- | safety |
| testing | TE- | testing |
| silent-failure | SI- | silent-failure |
| contracts | CT- | contracts (conditional: SANYI.md present) |
| runtime | RT- | runtime (conditional: agent code) |
| safeguards | SG- | safeguards (conditional: agent code) |
| leakage | LK- | leakage (conditional: ML code) |
| wander | WD- | wander (questions, not findings) |

## Evidence Model

Four states — pick the most honest one:

| State | Meaning | When to use |
|-------|---------|-------------|
| `verified` | Fully confirmed by code inspection + grep | You read the call chain, ran grep, saw no counter-evidence |
| `supported` | Strong evidence, one gap remains | You traced most of the path; one link is inferred |
| `hypothesis` | Pattern matches a known smell | You see the shape but can't confirm the impact without more context |
| `question` | Open question, not a defect | You don't have enough information to decide |

**Rule**: `question` cannot carry `merge_impact: blocker` or `important` (schema-enforced).
Evidence state and merge impact are otherwise orthogonal — a plausible safety concern with
insufficient evidence is `hypothesis` + `blocker`, phrased as a hypothesis ("this appears
to..."), never downgraded to `nit`.

**Rule**: When in doubt, downgrade to `hypothesis`. Never bluff `verified`.

## Severity Mapping

| Finding tier | merge_impact | evidence constraint |
|---|---|---|
| [Blocking] | blocker | any state except question |
| [Non-blocking] | important or suggestion | important: any state except question |
| [Nit] | nit | any state |

## Shared Operational Rules

1. **Read before reporting.** Read every file in your batch in full.
2. **Grep callers** before flagging anything as unused, unreachable, or removable.
3. **Respect CLAUDE.md**. Do not flag deliberate, documented architectural choices.
4. **Self-verify**. Inspect the code path end-to-end before claiming `verified`.
5. **READ-ONLY**. Never edit, create, or delete files. Return text only.
6. **Rank findings** — most impactful first (blockers before nits).
7. **Separate findings from hypotheses** in your output section headings.
8. **Language lenses**: for language-specific smells, read the relevant ref first:
   - Python: `~/.claude/refs/python.md`
   - TypeScript: `~/.claude/refs/typescript.md`
   - SQL: `~/.claude/refs/sql.md`

## Output Structure (per dimension)

```
### <Dimension> Findings (ranked, most important first)

- **[blocker:verified]** `<PREFIX>-001` `path/file:line` — title
  Evidence: ...
  Merge impact: blocker

### <Dimension> Hypotheses (unverified)

- **[suggestion:hypothesis]** `<PREFIX>-002` `path/file:line` — this appears to ...
  Evidence: ...
  Merge impact: suggestion

(or: "No <dimension> findings — files scanned: N")
```
