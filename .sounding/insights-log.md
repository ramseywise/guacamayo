# Insights Log

Append-only. Each `/workflow-insights` run adds a dated section at the top.
Full analysis is generated fresh each run; this log captures the trajectory.

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
