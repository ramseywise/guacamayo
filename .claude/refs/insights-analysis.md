# Insights Analysis — Interpretation Framework

You are interpreting Claude Code usage data to produce actionable workflow improvements — not a usage dashboard. Raw numbers are inputs; the output must be specific recommendations.

The data comes from `librarian/tools/cartographer/parser.py` (invoked via `/insights`). All "% of usage" figures are **cost-weighted**: token counts weighted by price ratios (input 1×, cache write 1.25×, cache read 0.1×, output 5×), so they reflect spend, not message counts.

## Token economics signals (cost-weighted)

| Signal | What to look for | Workflow implication |
|--------|-----------------|----------------------|
| **`context_usage_pct` / `pct_usage_over_150k_context`** | Large share of spend at >150k request context | Sessions run too long before `/compact` or `/clear`; every turn re-reads a huge prefix. >50% is the top cost lever |
| **`compacts`** vs. >150k share | Zero compacts *and* high >150k share | Compacting too late or never — recommend `/compact` mid-task, `/clear` between tasks |
| **`cache.hit_rate_pct`** | Below ~90% | Context churn (files re-read, prefix edits) breaking prompt cache; big cost multiplier |
| **`cache.savings_vs_uncached_pct`** | Sanity check | How much caching is already saving — frame recommendations against this baseline |
| **`subagents.share_of_usage_pct` / `pct_usage_in_heavy_sessions`** | Subagent-heavy sessions dominating spend | Each subagent re-derives context. Spawn deliberately; use cheaper models for simple subagents |
| **`parallelism_usage_pct`** | Large "4+" share | All sessions share one limit — queue instead of running 4+ at once |
| **`skill_usage_pct`** | One skill eating budget | That skill's prompt/protocol may load too much context per invocation |
| **`max_context` (per session)** | Sessions peaking near the window | Candidates for splitting or earlier compaction |

## Context / prompt engineering signals

| Signal | What to look for | Workflow implication |
|--------|-----------------|----------------------|
| **Tool error rate by type** | `edit_failed`, `file_not_found` spikes | Plan steps with wrong file paths; reading before editing |
| **User interruptions** (gap <5s) | High count = agent going off-track | Plans are ambiguous; steps too large |
| **Response time distribution** | Many >5m gaps = user is reviewing, not waiting | Good: human-in-loop working. Many <10s = rubber-stamping |
| **`bash_antipatterns`** | Bash used where Read/Grep/Glob exists | Wastes context and loses tool affordances; reinforce via hooks |
| **`read_edit_ratio`** | Below 1 | Editing blind — understand before changing |
| **Error type: `user_rejected` / `hook_blocks`** | High count | Permission model too tight, or hooks doing their job — check which |
| **`output_tokens_per_msg` p75/p90** | High values | Verbose responses (output is 5× input price) — tighten response style |
| **`long_sessions_without_todo`** | Long sessions, no planning structure | Steps sized too large; agent doing too much per turn |
| **`model_distribution`** | Expensive model on trivial sessions | Route simple work to a cheaper model |

## Patterns that indicate context engineering problems

**Symptom: majority of spend at >150k context**
- Cause: long-running sessions carrying stale context; compacting late or never
- Fix: `/compact` at phase boundaries mid-task; `/clear` when switching tasks; trim always-loaded includes

**Symptom: high subagent share with generic subagents**
- Cause: each spawn re-derives context the parent already has
- Fix: fewer, better-briefed subagents; configure cheaper models for simple agent types

**Symptom: low cache hit rate**
- Cause: context churn — re-reading files, reordering prefix content, frequent session restarts
- Fix: stable session structure; avoid re-reading unchanged files; lazy-load skills

**Symptom: high `edit_failed` rate**
- Cause: editing files without reading first, or plan has wrong line numbers
- Fix: enforce read-before-edit in execute skill; add plan_check before execute

**Symptom: Bash dominates tool usage**
- Cause: using shell for file reads/searches instead of dedicated tools
- Fix: reinforce Read/Grep/Glob preference in hard-rules or hooks

## What the data cannot tell you

- Whether the work was correct (only whether tests passed)
- Whether a deviation from the plan was good or bad
- Why a user interrupted (reviewing vs. correcting)
- Whether a big spend was justified by task complexity — a long session on a hard problem is not a problem
- Subagent *purpose* (transcripts show cost, not whether the delegation was worth it)

Do not over-interpret low-signal metrics.

## Output format for the insights report

For each pattern identified, produce:

```
### [Pattern name]
**Signal**: [what the data shows — specific numbers]
**Interpretation**: [what this likely means]
**Recommendation**: [one concrete change to the setup, workflow, or prompts]
```

Limit to the 3–5 patterns with the clearest signal. More than 5 dilutes actionability.

End with a **Priority** section: which single change would have the highest impact on token efficiency or workflow quality, and why. When ranking, weight by `usage_cost_units` share — a 64% context bucket beats a 2% skill every time.

## Usage observability signals (2026-07-24)

| Signal | What to look for | Workflow implication |
|--------|-----------------|----------------------|
| **`execution_skill_compliance_pct`** | Execution-intent sessions below 60% skill invocation rate | The skill set doesn't match the work pattern — sessions are doing execution work without skill guardrails |
| **`friction_labels_total`** | Any explicit `FRICTION:` label | Direct user-reported friction — always surface in recommendations, regardless of count |
| **`agent_spawns` by type** | Explore agents consuming >30% of subagent cost | Searches could be replaced by direct grep; reconsider agent routing |
| **`session_intent` distribution** | High unknown % | Intent classifier needs refinement, or sessions are genuinely ambiguous |

**Symptom: low execution skill compliance**
- Cause: sessions doing work (editing files, multiple turns) but not invoking any skills
- Fix: check if the skill set covers the work being done; add skills for common patterns; verify skill auto-trigger hooks

**Symptom: friction labels present**
- Cause: user explicitly flagged a friction point with `FRICTION:` prefix
- Fix: read the label content — these are direct user signals, not inferred. Every one deserves a recommendation
