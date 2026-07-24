# Insights Log

Append-only. Each `/workflow-insights` run adds a dated section at the top.
Full analysis is generated fresh each run; this log captures the trajectory.

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
