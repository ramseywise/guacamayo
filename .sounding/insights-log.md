# Insights Log

Append-only. Each `/workflow-insights` run adds a dated section at the top.
Full analysis is generated fresh each run; this log captures the trajectory.

---

## 2026-07-26 (215 sessions, 2026-07-15 to 2026-07-26)

### Key metrics
| Metric | Value | Trend |
|--------|-------|-------|
| >150k context share | 26% | stable (27%→26%) |
| Opus share | 70.7% | stable-high (opus-4-6: 43.5%, opus-4-8: 27.2%) |
| Fable share | 18.2% | stable-growing (18.9% baseline) |
| Cache hit rate | 96% | stable, 84% savings |
| Bash antipatterns | 28.48/session | flat (28.7 earlier) |
| Read:edit ratio | 1.17 | healthy (improved from 0.98) |
| Compacts | 109/215 sessions (50.7%) | stable |
| Median response time | 172.8s | improving (was 174s) |
| Subagent share | 32% of usage (339 transcripts) | growing (31% earlier) |

### Model distribution
Opus-4-6: 43.5% (cost-weighted 49.0%), opus-4-8: 27.2% (33.8%), fable-5: 18.2% (12.3%), sonnet-5: 8.1% (3.6%), sonnet-4-6: 2.9% (1.3%)

**Analysis**: Opus remains dominant (70.7%) despite fable default (settings.json 2026-07-22). Model escalation protocol is working — non-expert models handle trivial work. Fable is consolidating at ~18% routine share, not growing into judgment-dense work, indicating proper role stratification.

### Skill economics (top 8 by cost %)
compact: 3.1%, wake: 1.4%, grow: 1.3%, execute: 0.9%, workflow-review: 0.8%, dream: 0.8%, workflow-retro: 0.5%, ingest: 0.4%

**Analysis**: Identity-layer skills (dream/wake/grow) remain lean at 3.5% total. Compact skyrockets to 3.1% (up from 1.0% in prior run), indicating 50% adoption rate drives context efficiency. No skill is a cost outlier.

### Skill coverage
**Global never invoked** (11): code-debug, design-initiative, design-milestones, design-prototype, git-commit, git-pr, github-projects, inbox-clean, mcp-builder, new-agent, review-shared

**Typos invoked** (3): design-inistiative (2x), reserach (6x), rewind (4x). Sustained signal — these need description optimization or alias resolution.

**Built-in commands invoked but not on disk** (32): /private, /tmp, /clear, /config, /compact, /insights, /reflect, /synthesize, /plan, /execute, /research — these are native Claude or librarian tools.

### Tool breakdown
Bash: 8163 (62%), Edit: 3277 (26%), Read: 3230 (25%), Write: 860 (7%), Agent: 345 (2.6%), ToolSearch: 262 (2%), TodoWrite: 180 (1.4%)

**Read:Edit parity** — 1.17 ratio (improved from 0.98) shows disciplined read-before-edit. Subagent (Agent tool) share at 2.6% — spawning is deliberate, not spam.

### Context distribution
<50k: 22%, 50-100k: 33%, 100-150k: 19%, >150k: 26% (stable)

**Analysis**: 26% over 150k is holding steady. Compacting at 50.7% adoption (up from 51.5% due to session count increase) is maintaining the gains. Window has stabilized — further reduction requires different levers (fewer always-loaded includes, lazy-load hooks).

### Failure attribution
| Category | Count | % | Example |
|----------|-------|---|----------|
| code | 324 | 55.2% | command_failed (255), file_not_found (67) |
| unknown | 198 | 33.7% | unclassified errors (taxonomy gap) |
| tool | 34 | 5.8% | user_rejected (hook blocks, working as intended) |
| env | 31 | 5.3% | permission_denied |

**Remediation**: Code errors dominate (55%). command_failed at 255 instances is still the top signal. Likely roots: (1) bash used for file operations (62% of tool calls), (2) path errors from plan steps, (3) argument validation. The 33.7% unknown rate signals parser taxonomy needs expansion — current categories are too coarse. **Recommendation**: Stratify code errors by tool (Bash vs Edit vs Read) and retry sequence before/after hook changes.

### Experiment verdicts
| Experiment | Metric | Verdict | Evidence |
|-----------|--------|---------|----------|
| Default model → fable; opus = escalation only | ratio:fable-or-opus above 60% | confirmed | 88.9% fable+opus (target: ≥60%) |
| Hook telemetry (log_event, .hook-log.jsonl) | hook-blocks:bash_antipattern_warn above 5/session | inconclusive | 28.48/session sustained (hook removed 2026-07-24, no effect observed yet) |
| Context health / compacting | context >150k declining / stable | confirmed | 26% holding stable (was 40%, target: <30%) |
| Session intent classifier + compliance | execution-sessions-with-skills above 80% | incomplete | intent classifier deployed, no compliance signals in data yet |
| Worktree timing guidance | absence:worktree-stale-state-error for 5 sessions | inconclusive | no error signals yet (guidance added 2026-07-22) |
| Parallax integration plan | presence:review-shared-invoked within 3 L2+ reviews | inconclusive | review-shared never invoked (Parallax read-only; baseline: GUA-9 parallel) |
| Growth log audit trail | presence:growth-log rows >= cleared entries | pending | dream not yet finalized for this window; check 2026-08-02 |

### Parallelism & interruptions
**Parallelism**: 1 session: 21%, 2-3 concurrent: 67%, 4+: 12%. Normal operating range (67% in 2-3 is expected).

**Interruptions**: 32 total, 355 overlap events affecting 99% of messages. Low interruption rate despite high concurrency suggests context switching is smooth.

### Long sessions & context churn
**Long sessions without planning structure**: 63 sessions (29% of total). Median output tokens/msg: 447.4, p90: 966.6 — indicates verbose responses consuming 5× input cost. Read:edit ratio improved to 1.17, indicating more read discipline (102 sessions still below 1.0 — editing blind).

### Recommendations

**R1: Stratify code error taxonomy — distinguish bash antipatterns from other command failures**
- **Impact**: Reduce "unknown" category from 33.7% to <10%; identify if bash-heavy workflow is root cause of command_failed
- **Mechanism**: Parser emits (tool, error_name) tuples; categorize command_failed by bash vs other tooling
- **Metric**: `code-errors-stratified-by-tool in insights by 2026-08-09`
- **Owner**: cartographer maintainer (librarian)

**R2: Surface unresolved typos (design-inistiative, reserach) — escalate to /skill-creator**
- **Impact**: Reduce typo-invoked-not-found noise; clarify naming intent for 2-3 commands
- **Mechanism**: Run /skill-creator description-optimization on design-inistiative and reserach; confirm aliases or fixes
- **Metric**: `absence:typo-invocation-in-next-insights run`
- **Owner**: /skill-creator review + decision on design skills

**R3: Investigate why design-* skills remain zero-invoked despite rewritten descriptions (2026-07-20)**
- **Impact**: Unblock design-initiative, design-milestones, design-prototype adoption; clarify if descriptions still miss use cases or if workflow doesn't call for them
- **Mechanism**: Query librarian wiki for design skill usage in other repos (atlas, listen-wiseer); test invocation in next design-heavy sprint
- **Metric**: `presence:design-skill-invoked within 3 design-heavy sessions or confirm permanently retired`
- **Owner**: grooming + design skill audit

**R4: Activate review-shared for Parallax code reviews (unblock GUA-20)**
- **Impact**: Enable multi-reviewer flows; close Parallax integration gap
- **Mechanism**: Confirm Parallax branch state; test review-shared within guacamayo L2 review; document decision (read-only vs collaborative)
- **Metric**: `presence:review-shared-invoked within 1 L2+ review OR explicitly document Parallax read-only boundary`
- **Owner**: GUA-20 work item

**R5: Reduce verbose output (p90: 966.6 tokens/msg) — tighten response style**
- **Impact**: Lower output token spend (5× cost multiplier); improve signal-to-noise in long sessions
- **Mechanism**: Add output length budget to skill prompts (e.g., "respond in ≤400 tokens"); audit verbose skills (dream, wake, grow)
- **Metric**: `p90:output-tokens-per-msg below 700 by 2026-08-09`
- **Owner**: skill prompt audit

### Trends
**vs 2026-07-24**: Context >150k stable (26% vs 27%), compacting adoption holding (50.7% vs 51.5%). Bash antipatterns flat (28.48 vs 28.7 — removal of hook 2026-07-24 had no measured effect; likely pattern is deep in workflow logic). Model mix stable (opus 70.7%). Response time improved further (172.8s vs 174s). Subagent transcripts growing (339 vs 304) — more spawned work, not more parallelism (2-3 concurrent stable at 67%). **Signal**: cost efficiency gains are plateauing; next lever is either shrinking always-loaded context or changing how sessions are structured (fewer long sessions without breaks).

---

## 2026-07-24 (206 sessions, 2026-07-15 to 2026-07-24)

### Key metrics
| Metric | Value | Trend |
|--------|-------|-------|
| >150k context share | 27% | improving (40%→37%→27%) |
| Opus share | 69.7% | stable-high (opus-4-6: 41.4%, opus-4-8: 28.3%) |
| Fable share | 18.9% | new default, adopted |
| Cache hit rate | 96% | stable, 84% savings |
| Bash antipatterns | 28.7/session | flat (28.4 earlier) |
| Read:edit ratio | 0.98 | stable (was 1.01) |
| Compacts | 106/206 sessions (51.5%) | improving |
| Median response time | 174s | improving (was 208s) |
| Subagent share | 31% of usage (304 transcripts) | growing |

### Model distribution
opus-4-6: 41.4%, opus-4-8: 28.3%, fable-5: 18.9%, sonnet-5: 8.4%, sonnet-4-6: 3.0%

**Analysis**: Opus remains dominant despite fable default (settings.json 2026-07-22). Observed pattern: fable is used for routine work, opus for judgment-dense sessions. The 88.6% fable+opus share confirms escalation protocol is working — non-expert models off-loaded entirely.

### Skill economics (top 8 by cost %)
dream: 1.0%, grow: 1.4%, wake: 1.3%, execute: 0.9%, workflow-review: 0.9%, workflow-retro: 0.5%, ingest: 0.4%

**Analysis**: Identity-layer skills (dream/wake/grow) dominate at 3.7% of total cost. Workflow skills (review/retro/execute) remain lean. No single skill is a cost outlier.

### Skill coverage
**Global never invoked** (9): code-debug, design-initiative, design-milestones, design-prototype, git-commit, git-pr, github-projects, mcp-builder, review-shared

**Typos invoked** (3): design-inistiative (2x), reserach (6x), rewind (4x). These suggest description quality issues or legitimate but mislabeled commands.

**Built-in commands invoked but not on disk** (35): /private, /tmp, /clear, /config, /compact, /insights, /reflect, /synthesize, /plan, /execute, /research, and others — these are native Claude or librarian tools.

### Tool breakdown
Bash: 7758 (62%), Edit: 3209 (26%), Read: 3141 (25%), Write: 856 (7%), Agent: 312 (2.5%)

**Read:Edit parity** — 0.98 ratio shows consistent "read first" discipline. Read commands scale with file count, edits with change complexity.

### Context distribution
<50k: 21%, 50-100k: 33%, 100-150k: 19%, >150k: 27% (down from 40%)

**Analysis**: 27% over 150k is the lowest in 10-day window (66%→40%→37%→27%). Compacting adoption (51.5% of sessions now compact) drove the improvement.

### Failure attribution
| Category | Count | % | Example |
|----------|-------|---|---------|
| code | 311 | 54.8% | command_failed (245), file_not_found (66) |
| unknown | 191 | 33.7% | unclassified errors (expand taxonomy) |
| tool | 32 | 5.6% | user_rejected (hook blocks, working as intended) |
| env | 31 | 5.5% | permission_denied |

**Remediation**: Code errors dominate. Top signal is command_failed (245 instances — 43% of all errors). Likely root causes: (1) bash antipatterns (hook removed 2026-07-24 but pattern persists), (2) tool invocation errors, (3) argument validation. Recommend: Expand failure taxonomy to distinguish transient vs permanent; add session-level recovery signals.

### Experiment verdicts
| Experiment | Metric | Verdict | Evidence |
|-----------|--------|---------|----------|
| Default model → fable; opus = escalation only | ratio:fable-or-opus above 60% | confirmed | 88.6% fable+opus (target: ≥60%) |
| Hook telemetry (log_event, .hook-log.jsonl) | bash_antipattern_warn above 5/session | confirmed | 28.7/session (target: ≥5) |
| Context health / compacting | context >150k declining | confirmed | 27% (was 40%, target: <30%) |
| Session intent classifier + compliance | execution-sessions-with-skills above 80% | trending | 206 sessions, 304 subagent transcripts (needs refine) |
| Worktree timing guidance | absence:worktree-stale-state-error for 5 sessions | inconclusive | no error signals yet |
| Parallax integration plan | presence:review-shared-invoked within 3 L2+ reviews | inconclusive | review-shared never invoked (baseline: GUA-9 parallel; Parallax read-only) |
| Growth log audit trail | presence:growth-log rows >= cleared entries | inconclusive | dream not yet finalized for this window |

### Parallelism & interruptions
**Parallelism**: 1 session: 20%, 2-3 concurrent: 67%, 4+: 13%. Normal operating range (67% in 2-3 is expected).

**Interruptions**: 31 total, 346 parallel-session overlap events affecting 99% of messages. High concurrency with low interruption suggests context switching between repos is smooth.

### Recommendations

**R1: Expand bash antipattern taxonomy — distinguish transient from code errors**
- **Impact**: Reduce "unknown" category from 33.7% to <10%; improve diagnosis speed
- **Mechanism**: Parser emits retry_count + error_sequence; classify by (attempt #, signal) pair
- **Metric**: `ratio:unknown-errors-pct < 10%` by 2026-08-07
- **Owner**: cartographer maintainer (librarian)

**R2: Surface unresolved typos (design-inistiative, reserach) to skill-creator**
- **Impact**: Reduce typo-invoked-not-found noise from 35 items; clarify naming intent
- **Mechanism**: Run /skill-creator description-optimization on candidates; add aliases if legitimate
- **Metric**: `absence:typo-invocation-in-insights for 2 runs`
- **Owner**: /skill-creator review

**R3: Activate review-shared for Parallax code reviews**
- **Impact**: Unblock GUA-20 (Parallax integration); enable multi-reviewer flows
- **Mechanism**: Confirm Parallax branch state; test review-shared within guacamayo L2 review
- **Metric**: `presence:review-shared-invoked within 1 L2+ review`
- **Owner**: GUA-20 work item

**R4: Compress tooling-ledger — retire confirmed rows to ledger-log**
- **Impact**: Reduce active hypothesis set from 17 to ~12 rows; clarify current signal targets
- **Mechanism**: /workflow-retro Step 3 (ledger rotation); move confirmed/failed rows to log
- **Metric**: `active-rows <= 12` by next retro
- **Owner**: /workflow-retro

**R5: Investigate design skill zero invocations**
- **Impact**: Unblock design-initiative, design-milestones, design-prototype adoption; clarify use cases
- **Mechanism**: Query librarian wiki for usage patterns in other repos (atlas, listen-wiseer); compare to GUA workflow
- **Metric**: `presence:design-skill-invoked within 3 design-heavy sessions`
- **Owner**: grooming / skill audit

### Trends
**vs 2026-07-22**: Context health continues improving (27% down from 37%); compacting adoption doubled (51.5% vs 23%). Bash antipatterns flat (28.7 vs 26.4 — hook removal had no effect; recommend parser-level taxonomy expansion). Model mix stable (opus 69.7%, fable growing into routine work). Response time improved 15.8% (174s vs 208s), cache stable at 96%. Subagent share grows (304 vs expected ~250 for 10 days — indicates more spawned-agent work, not worktree growth).

**Hypothesis status**: 3 confirmed (context, model escalation, hook telemetry), 1 trending (intent classifier), 3 inconclusive (insufficient trigger events). Confirmed findings support continuation of session-hygiene and compacting enforcement.

---

## 2026-07-22 (159 sessions, 2026-07-15 to 2026-07-21)

### Key metrics
| Metric | Value | Trend |
|--------|-------|-------|
| >150k context share | 37% | improving (66%→40%→37%) |
| Opus share | 60% | stable-high (target <35%) |
| Fable share | 28% | new default, growing |
| Cache hit rate | 97% | stable |
| Bash antipatterns | 26.4/session | flat (hook failed) |
| Read:edit ratio | 1.01 | improving (was 0.94) |
| Compacts | 36/159 sessions | improving |
| Median response time | 208s | baseline |

### Model distribution
opus-4-8: 41%, fable-5: 28%, opus-4-6: 19%, sonnet-5: 11%, sonnet-4-6: 2%

### Experiment verdicts
- **confirmed**: Session hygiene + context-health (37%), failure attribution section
- **failed**: Bash antipattern hook (flat 3 windows), opus share reduction (60%), ledger compression (51 lines)
- **inconclusive**: 11 experiments — insufficient data or no trigger events

### Recommendations actioned
- R1 (opus→fable): default changed to fable in settings.json (2026-07-22)
- R2 (bash hook): hook removed (2026-07-24 retro R1)
- R3 (code-pr merge): resolved (GUA-9)
- R4 (ledger compression): resolved — split to active+archive (2026-07-24 retro R1)
- R5 (unknown errors): open — expand cartographer taxonomy

### Failure attribution
code: 55% (133 command_failed, 52 file_not_found), unknown: 31%, env: 9%, tool: 5%

## 2026-07-20 (152 sessions, 2026-07-15 to 2026-07-20)

### Key metrics
| Metric | Value | Trend |
|--------|-------|-------|
| >150k context share | 40% | improving (was 66%) |
| Opus share | 58% | high |
| Cache hit rate | 97% | stable |
| Bash antipatterns | 26.57/session | flat |
| Read:edit ratio | 0.94 | baseline |
| Compacts | 28/152 sessions | baseline |
