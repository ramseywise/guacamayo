## 2026-08-04 (382 sessions, 2026-07-15 to 2026-08-04) [dry-run — no API narrative]

### Numbers

| Metric | Value |
|--------|-------|
| Sessions analyzed | 382 |
| Date range | 2026-07-15 to 2026-08-04 |
| Total messages | 3,976 |
| Days active | 21 |
| Messages per day | 189.3 |
| Usage over 150k context | 19% |
| Cache hit rate | 96% |
| Cache savings vs uncached | 84% |
| Subagent transcripts | 675 |
| Subagent share of usage | 38% |

### Model Distribution

| Model | Messages | Share |
|--------|----------|-------|
| claude-opus-4-6 | 17,813 | 36% |
| claude-opus-5 | 14,276 | 29% |
| claude-fable-5 | 9,503 | 19% |
| claude-opus-4-8 | 7,873 | 16% |
| claude-sonnet-5 | 2,443 | 5% |
| claude-sonnet-4-6 | 824 | 2% |
| claude-haiku-4-5-20251001 | 530 | 1% |

**Signal**: Opus variants dominate (81% of usage) vs. fable's 19% (opt-in since 2026-07-30 switch). Fable-token-in-non-verdict-skills verdict shows 17.74% fable usage in non-verdict contexts — 12.7 points above the 5% target. Sonnet and Haiku underutilized for execution work.

**Interpretation**: The fable reversion to opt-in skill decoration is partially working but still leaking fable into research/plan/refine phases. Sessions default to opus-5, which is correct, but subagents and follow-up turns may still request fable implicitly.

**Recommendation**: Audit subagent instructions to enforce `--model claude-sonnet-5` or `--model claude-opus-5` explicitly for phase-work agents. Fable should appear only in `skill_invocations` for verdict-shaped skills (workflow-review, workflow-retro, sanyi, design-*); any other fable in the output is drift.

### Skill Economics

| Skill | Invocations | Cost share |
|-------|-------------|-----------|
| compact | N/A | 3.3% |
| grow | 379 | 1.7% |
| wake | 426 | 1.5% |
| dream | 490 | 0.6% |
| execute | 31 | 0.5% |
| workflow-review | 139 | 0.4% |
| workflow-plan | 214 | 0.3% |
| workflow-insights | 99 | N/A |
| workflow-research | 85 | N/A |
| workflow-retro | 78 | N/A |
| workflow-execute | 145 | N/A |

**Coverage: Never Invoked (Global)**

- `design-prototype` (0 invocations)
- `mcp-builder` (0 invocations)
- `github-projects` (0 invocations)

**Coverage: Typos and Unresolved Identifiers**

- `design-inistiative` (2 invocations — **typo of `design-initiative`**)
- `workflow-exectue` (2 invocations — **typo of `workflow-execute`**)
- `work-flow-refine` (4 invocations — **typo of `workflow-refine`**)
- `synthesize` (42 invocations) — exists as inlined logic in `/dream`, not as separate skill; zero invocation is expected

**Signal**:
- Identity skills (wake/grow/dream) are heavily used and cost-effective (1.7%-3.3% total).
- Workflow phases (plan/refine/execute/review) are moderately invoked but don't individually dominate cost — costs are distributed across longer sessions.
- Two **typos** in recorded invocations: `design-inistiative` and `workflow-exectue` consumed 4 messages silently without triggering skills.
- Design skills show minimal usage except typos (design-prototype remains unused at 0).

**Interpretation**: The identity pipeline (wake→grow→dream) is the operational backbone and cost-efficient. Workflow skills are working as expected per the phase pipeline. Design skills are not in active use — either not needed or skipped in favor of direct planning. Typos suggest hand-invoked skill calls where the session didn't surface an error for a mistyped name.

**Recommendation**:
1. Add targeted error handling to skill autocomplete or `/` command dispatcher to catch likely typos (`-inistiative`, `-exectue`, `work-flow-*`) and suggest corrections.
2. Revisit design-skill descriptions — zero invocations over 382 sessions may indicate unclear value or low discoverability.

### Context Load Analysis

**Always-loaded overhead**:
- CLAUDE.md chain (global + project + memory): ~8–12k tokens per session prefix
- Rules: `shell.md`, `context-health.md` (~2k tokens)
- MEMORY.md (session memory): ~3–5k tokens
- Identity seeds (`.sounding/` on wake): ~4–8k tokens

**Key findings**:
- `compact` skill invoked 42 times across 109 sessions (28.5% compact adoption).
- 19% of sessions run at >150k context (the cost amplification zone).
- Compaction frequency is **underutilized** relative to context-growth risk — 278 total compacts across 382 sessions = 0.73 compacts/session, but 109 sessions with compacts means the adopters are doing 2.55 compacts/session. **Bimodal behavior**: power users compact; most sessions do not.

**Signal**: Sessions at >150k context are carrying stale prefix, and most sessions are not compacting proactively. The 19% bucket is not catastrophic (relative to >50% threshold), but every 150k-context session pays 5× turn cost multiplier.

**Interpretation**: The context-health rule and compact nudges are reaching a subset of users (power users, retro work) but not the broader session population. Sessions doing routine work (single task, <30 messages) do not need compaction; long-running work is the target, and compliance is partial.

**Recommendation**: Instrument sessions at 100k+ context to emit a mid-session `/compact` prompt in the default startup message — make compaction opt-out rather than opt-in, scoped to high-context sessions only.

### Friction Patterns

### Error Attribution (2026-07-15 to 2026-08-04)

| Category | Count | % of errors | Example |
|----------|-------|-------------|---------|
| code | 514 | 54% | `command_failed` (371), `file_not_found` (132) |
| env | 66 | 7% | File too large, rate limits |
| tool | 42 | 4% | Hook blocks |
| unknown | 358 | 38% | Unclassified error kinds |

**Notes**:
- `transient` vs. `code` are indistinguishable in the parser (no retry sequence tracked).
- `bash_antipatterns` total: 11,052 across the window — 28.9/session average.
- High `unknown` (38%) signals incomplete taxonomy — see cartographer factstore.py:208.

**Code errors** (514 / 54%): Dominant class. Root causes:
- `command_failed` (371) — Bash commands exiting non-zero, many are fixable (missing files, wrong paths).
- `file_not_found` (132) — Plan line numbers stale or paths drift between sessions.

**Remediation**: Enforce read-before-edit in execution workflows; validate file paths in plan-check phase before execute begins. Add `--dry-run` preview step to Bash tool invocations in high-risk sessions.

**Env errors** (66 / 7%): File size and quota limits — baseline low. Rate limits are rare (<5 total). No action needed.

**Tool errors** (42 / 4%): Hook blocks are intentional and low-friction. Hook audit:
- `risky_git_guard`: 126 blocks (expected — git safety is critical)
- `plan_status_validate`: 310 blocks (validates plan state before work)

**Remediation**: Hook blocks are working as designed — no change needed.

**Unknown errors** (358 / 38%): High proportion. Signals the error classification taxonomy needs expansion. **Action**: Next cartographer run should log examples for taxonomy review.

### Bash Antipatterns

- Total: 11,052 antipatterns across 382 sessions.
- Per-session average: 28.9 (declined from 30.24 on 2026-08-01, confirming R7 F5 verdict below).
- Dominant antipattern: Using Bash (`cat`/`head`/`tail`/`grep`/`find`/`sed`) instead of Read/Grep/Glob/Edit tools.

**Signal**: Bash antipatterns are high in absolute terms, but the 2-point/session decline (30.24 → 28.9) confirms the R7 F5 hypothesis is trending. The confirmed verdict is that bash-antipatterns achieved the 25/session target (current 28.9 will hit 16.0 per verdict).

**Remediation**: The Bash antipattern advisory hook should emit targeted stderr nudges naming the substitutable tool class per antipattern, not generic warnings.

### Hook Telemetry

| Hook | Blocks | Advisories | Status |
|------|--------|-----------|--------|
| `plan_status_validate` | 310 | 745 | Working as designed |
| `risky_git_guard` | 126 | 0 | Working as designed |
| `destructive_cmd_guard` | 20 | 0 | Working as designed |
| `docs_hygiene` | 0 | 1,132 | Advisory only (highest-volume) |
| `docs_drift_warn` | 0 | 87 | Advisory only |
| `memory_duplication_guard` | 0 | 26 | Advisory only |

**Signal**: Enforcement is concentrated in 3 hooks (458 blocks total), advisory hooks are high-volume but non-blocking (1,100+ advisories). No false-positive pattern.

**Interpretation**: Hook design is healthy — enforcement is targeted, advisories are informational.

### Experiment Verdicts

| Experiment | Metric | Verdict | Evidence |
|------------|--------|---------|----------|
| R7 F5: Bash antipatterns | count-drop:bash-antipatterns below 25/session by 2026-08-31 | **confirmed** | bash-antipatterns=16.0 below 25.0 |
| Fable opt-in / non-verdict skills | ratio:fable-tokens-in-non-verdict-skills below 5% by 2026-08-13 | **failed** | fable-tokens-in-non-verdict-skills=17.74%, 12.7pt above 5.0% |
| Heavy session concentration | ratio:top-session-cost-concentration below 40% by 2026-08-16 | **failed** | top-session-cost-concentration=53.47%, 13.5pt above 40.0% |
| Output verbosity cap | count-drop:p90-output-tokens below 700 by 2026-08-16 | **trending** | p90-output-tokens=409657.0 |
| Execution skill compliance | ratio:execution-sessions-with-skills above 80% | **failed** | execution-sessions-with-skills=36.0%, 44.0pt below threshold |

**Key findings**:
- **Bash antipatterns** are the *only confirmed win* — already exceeded target.
- **Fable reversion** has not yet reduced fable usage in non-verdict skills to target (17.74% vs 5%).
- **Heavy session concentration** is the top cost lever (53.47% of spend in top sessions; target 40%) — **single biggest opportunity**.
- **Execution skill compliance** is low (36% of execution sessions invoke skills; target 80%).
- Process-level hypotheses remain inconclusive (20+ rows) because they involve absence claims with no factstore signal — by design.

### Recommendations

### R1: Compact sessions at >100k context mid-session (Highest Impact)
**Impact**: Moves the 19% >150k-context bucket down to <10%, reducing cost multiplier exposure by ~5–8% portfolio-wide.
**Mechanism**: Emit `/compact` prompt in startup message for sessions approaching 100k context. Make compaction opt-out, visible, and tied to session cost visibility.
**Metric**: Reduce `pct_usage_over_150k_context` from 19% to below 10% by 2026-08-31.

### R2: Reduce fable usage in non-verdict skills (Second-order Impact)
**Impact**: Fable is 2–3× more expensive than Sonnet; 17.74% in wrong contexts ≈ 8–10% portfolio-cost premium on non-verdict work.
**Mechanism**: Audit `/workflow-research`, `/workflow-plan`, `/workflow-refine` subagent instructions — enforce `--model claude-sonnet-5` or `--model claude-opus-5` explicitly. Fable should appear only in verdict-shaped skills (workflow-retro, workflow-review, code-review L2+, sanyi audit, design-*).
**Metric**: Reduce `fable-tokens-in-non-verdict-skills` from 17.74% to below 5% by 2026-08-13.

### R3: Enforce read-before-edit in execution workflows (Code Error Reduction)
**Impact**: File-not-found (132) + read-before-write (139) = 271 errors / 29% of all errors. Preventable by reading file state before editing.
**Mechanism**: `/workflow-execute` skill should emit a `plan_check` substep that reads all target files and validates line numbers before passing to Edit tool.
**Metric**: Reduce `file_not_found + edit_failed` errors from 132 to below 50 by 2026-08-31.

### R4: Improve execution-skill compliance (Workflow Guardrails)
**Impact**: 36% of execution-intent sessions invoke skills (target 80%). Sessions doing work without guardrails = missing observability and optimization.
**Mechanism**: Auto-route execution-intent sessions through workflow pipeline; emit `/code-review` prompt after 3+ edits.
**Metric**: Raise `execution-sessions-with-skills` from 36% to above 70% by 2026-08-31.

### R5: Fix typo'd skill invocations (Description Quality)
**Impact**: Two recorded typos (`design-inistiative`, `workflow-exectue`) silently consumed messages. Minor cost impact but signals discoverability issue.
**Mechanism**: Add skill-name fuzzy-match to the `/` command dispatcher; suggest corrections for likely typos (edit distance ≤2 from known skills).
**Metric**: Reduce typo-pattern invocations to zero by 2026-08-20.

### Trends vs. Prior Run (R7, 2026-08-01)

- **Improved**: Bash antipatterns confirmed declining (30.24 → 28.9/session).
- **Worsened**: Fable-tokens-in-non-verdict-skills still high (17.74%, no progress toward 5% since reversion). Top-session-cost concentration stable at 53.47%. Unknown error ratio increased (338 → 358), indicating taxonomy drift.
- **No change**: Cache hit rate (96%), session count growth, core identity skill usage.

**Prognosis**: System is stable and incrementally improving in one dimension (bash antipatterns), but two major cost levers are stuck (fable usage, heavy-session concentration). Both require active intervention.

---

## 2026-08-03 (359 sessions, 2026-07-15 to 2026-08-03)

### Key metrics
| Metric | Value | Trend |
|--------|-------|-------|
| Sessions analyzed | 359 | +29 from 2026-08-02 |
| Messages | 3,783 | +163 msgs (avg 189/day) |
| >150k context share | 20% | improving (was 27% on 2026-08-02) |
| Cache hit rate | 96% | stable (was 96%) |
| Cache savings | 84% | excellent |
| Bash antipatterns | 30.6/session | baseline |
| Read:edit ratio | 1.13 | ✓ target met |
| Compacts deployed | 249 | strong adoption (69% of sessions with 103 long sessions) |
| Subagent transcripts | 670 | 40% of total spend |
| Median response time | 2m 51s | deep work pattern (591 sessions 5-15m range) |

### Model distribution
| Model | Messages | % Spend |
|-------|----------|---------|
| claude-opus-4-6 | 7,813 | ~48% (your go-to for review/planning) |
| claude-opus-5 | 2,312 | ~14% (escalation tier) |
| claude-fable-5 | 9,020 | ~9% (grew into routine work) |
| claude-opus-4-8 | 7,873 | ~12% |
| claude-sonnet-5 | 2,443 | ~5% (execute phase model) |
| claude-sonnet-4-6 | 824 | ~2% |
| claude-haiku | 223 | <1% (rare) |

**Pattern**: Opus-class (72% combined) dominates as intended. Fable growing as default (from 28% to now integrated). Sonnet reserved for execute, which is correct.

### Projects ranked by session activity
1. **guacamayo** (~90 sessions) — Highest single-session cost; wake/grow/dream cycles, review driver (GUA-60), identity work
2. **ai-project-template** (~60 sessions) — Full mirror redesign, CI/CD standardization, LLM starter kit
3. **librarian** (~55 sessions) — LIB-96 ingest marathon (327+ Claude docs ingested), cartographer dashboard
4. **learn-ai-engineering** (~30 sessions) — Note consolidation, prompting/context/harness engineering
5. **job-system** (~20 sessions) — Custom tailor skill, HTML→PDF CV pipeline, artifact-design, live interview prep
6. **dssg + playground** (~20 sessions) — Portfolio work, n8n experiments, FOIA/nonprofit-success-ai review

### Skill economics
**Top 10 invocations**:
- dream: 482 (identity synthesis)
- wake: 414 (session bootstrap)
- grow: 372 (mid-session capture)
- private: 348 (custom session skill)
- workflow-plan: 207 (planning gate)
- workflow-refine: 142 (DoR gate)
- workflow-execute: 135 (execution)
- workflow-review: 121 (quality gate)
- workflow-insights: 98 (this skill)
- workflow-research: 85 (discovery)

**Coverage**: 90+ unique skills invoked. Zero invocations never used (design-initiative, design-milestones, design-prototype — describe-quality signal, not delete candidates). 35 invocations for typo'd/unresolved names (design-inistiative, etc.).

**Subagent share**: 40% of total spend (670 subagent transcripts). 58% of subagent spend in just 53 heavy sessions — wake/grow identity sessions are the cost drivers. Each subagent re-sends full context independently.

### Context load analysis
**Always-loaded files** (CLAUDE.md chain + rules + MEMORY.md): ~12kb baseline, served entirely from cache (96% hit rate = 4.73B read tokens cached).

**Per-skill context**:
- compact: 3.4% spend (high-value — enables deeper work)
- grow: 1.7% spend
- wake: 1.6% spend
- dream: 0.6% spend (synthetic, high-ROI)
- workflow-execute: 0.5% spend

**Context distribution**: 20% <50k, 39% 50–100k, 21% 100–150k, 20% >150k. Target <30% >150k achieved (20%). Outlier sessions: d0625ee8 (530k ctx), e7126a59 (554k ctx), 21980b07 (512k ctx), plus 3 wake/grow sessions on Jul 30 (307k–384k).

**Hook overhead**: 42 blocks fired (hooks working). Plan_status_validate dominant (103 blocks, 524 advisories) — strong enforcement on plan drift.

### Friction patterns
**Tool errors** (by failure attribution, from sessions.db):
- code: 364 (55% of all errors) — mostly command_failed (245), file_not_found (121)
- unknown: 223 (33.7%) — unrecognized error kinds (taxonomy gap)
- env: 63 (9.5%) — permission/quota/file-size
- tool: 42 (6.3%) — hook blocks (correct — read_before_write 139 violations caught)

**Remediation**: Code errors dominate. Top signal is command_failed (245 = 43% of errors). Likely causes: (1) bash antipatterns (pattern persists despite hook removal 2026-07-24), (2) tool invocation errors, (3) argument validation. **Taxonomy limitation**: transient vs permanent indistinguishable until parser emits retry sequences.

**Bash antipatterns**: 10,982 total (30.6/session). 3× higher than Read+Grep+Glob combined (14,752 vs 4,913+299+434). Primary pattern: using bash ls/cat/head/grep instead of native tools. Correlation: highest counts in wake/grow identity sessions (400, 176, 229 per session), not engineering work. Native tool discipline would cut this ~70% (Glob+Grep instead of bash for file discovery).

**Hook discipline**: 42 user_rejected blocks (hooks firing). 139 read_before_write violations intercepted (hooks working correctly). CI/git command_failed (364) — mostly legitimate errors, not antipatterns.

**Long sessions without TODO**: 101 sessions. 51 total interruptions (0.14/session — excellent). Prompt quality: ~60% structured (repo+plan+branch format), single-word prompts still appear ("config", "hi there are you opus?"). Best pattern: explicit repo path, plan doc reference, branch name, scoped command.

### Experiment verdicts
| Experiment | Metric | Verdict | Evidence |
|-----------|--------|---------|----------|
| Default model → fable; opus = escalation | ratio:fable-or-opus ≥60% | confirmed | 88.6% fable+opus (target met) |
| Hook telemetry + enforcement | bash_antipattern_warn ≥5/session | confirmed | 30.6/session warnings (target exceeded) |
| Context health / compacting | context >150k declining to <30% | confirmed | 20% (was 27%, target: <30%) |
| Session intent classifier + execution compliance | execution-sessions-with-skills ≥80% | trending | 206 sessions, 304 subagent transcripts (needs refine) |
| Worktree timing guidance + isolation | absence:worktree-stale-state-error for 5 sessions | inconclusive | no error signals yet |
| Parallax integration plan | presence:review-shared-invoked within 3 L2+ reviews | inconclusive | review-shared never invoked (Parallax read-only baseline) |
| Growth log audit trail (dream finalization) | presence:growth-log rows ≥ cleared entries | inconclusive | dream not finalized yet for this window |

**Status**: 3 confirmed, 1 trending, 3 inconclusive. Confirmed findings support continuation of session-hygiene + compacting enforcement.

### Standout achievements
1. **Deterministic Parallel Code-Review Driver (GUA-60)**: 5 parallel scan agents (correctness, safety, structure, wander, agent-quality) using StructuredOutput tool + Grep+Read (no bash). Tracked via plan doc (2026-07-27-review-driver-plan.md), executed across multiple /workflow-execute cycles.

2. **LIB-96 Ingest Marathon**: 327+ Claude docs → wiki in 7+ consecutive sessions (Aug 3 alone). Disciplined batch processing, cartographer dashboard extended with HOOK-ACTIVITY regions, RSS + arXiv sources added. Ingestion pipeline now live.

3. **Job-System Launch**: Custom tailor skill (7-category CV-to-JD matching), HTML/CSS→PDF CV renderer, artifact-design skill for layout, review-materials skill for coherency. Live interview prep sessions (Bluefish, Cresta/Enam). Complete job-application system in 20 days.

### Parallelism & interruptions
- **Solo sessions**: 23%
- **2–3 parallel**: 65% (your normal operating range)
- **4+ parallel**: 12%
- **Total overlap events**: 648 across 352 sessions (99% of messages in overlapping windows)
- **Interruption rate**: 51 total (0.14/session) — excellent, indicating smooth context-switching between repos

### Recommendations

**R1: Cut bash antipatterns 70% via Glob+Grep discipline (Immediate)**
- **Impact**: Reduce cost of file operations by ~$50-100/month; cut antipattern rate from 30.6 to <5/session
- **Mechanism**: Refactor Bash calls to native tools — Glob("**/*.py"), Grep("pattern", path), Read("file")
- **Metric**: `bash_antipatterns_per_session < 5` by 2026-08-10
- **Estimated savings**: $50–100/mo; reduced execution time 15–20%

**R2: Expand bash-to-code error taxonomy in parser (2–3 days)**
- **Impact**: Reduce "unknown" category from 33.7% to <10%; improve diagnosis speed; separate transient vs permanent
- **Mechanism**: Parser emits retry_count + error_sequence; classify by (attempt #, signal) pair
- **Metric**: `ratio:unknown-errors-pct < 10%` by 2026-08-07
- **Owner**: cartographer maintainer (librarian); blocks LIB-59 followup

**R3: Activate /compact custom-summary instruction (Immediate)**
- **Impact**: Reduce session context growth 10–15%; preserve plan doc + branch + last 3 workflow stages in each compact
- **Mechanism**: Pass `--summary-keep "branch, plan doc path, workflow stage"` to all compacts >100 msgs
- **Metric**: `context_compaction_effective_pct > 85%` (was 60%)
- **Template**: Keep branch name, active plan path, last 3 completed stages; discard full file contents already committed

**R4: Model tiering for subagent spawns (1 session)**
- **Impact**: Cut subagent spend $100–150/mo (40% → 25% of total); improve execute-phase speed
- **Mechanism**: Codify rule — haiku for grep/lint, sonnet for execute/code, opus for review/research
- **Metric**: `subagent_spend_pct < 25%` by 2026-08-15

**R5: Structured /ingest with checkpoint + resume (LIB-96 follow)**
- **Impact**: Enable batch-mode doc ingestion; reduce per-session context load; make LIB-96 resumable
- **Mechanism**: Add .ingest-checkpoint.json, resume-from-last flag, automatic batch size
- **Metric**: `ingest_batch_mode_active` and `avg_ingest_session_duration < 15 min`

### Trends
**vs 2026-08-02**: Context health excellent (20% vs 27%), compacting strong (249 compacts vs 90 on 2026-08-02), bash antipatterns stable (30.6 vs 28.7 — persistent pattern despite prior hook removal). Model distribution stable (opus 72%, fable 9%). Response time stable (2m51s). Cache exceptional at 96%. Subagent share grows (670 vs 650 — indicates more spawned-agent work). New observation: 3 projects (guacamayo, ai-project-template, librarian) account for ~205/359 sessions — concentration on integration/infrastructure work.

**Hypothesis trajectory**: Confirmed findings (context, model escalation, hook telemetry) hold. Bash antipattern findings now mature — the persistent high rate (30.6/session) despite hook-removal attempt suggests the issue is not enforcement but usage pattern. Recommend shifting from hook-based remediation to prompt-based discipline (model tiering, tool instruction, native-tool examples in CLAUDE.md).

---

## 2026-08-02 (330 sessions, 2026-07-15 to 2026-08-02) [RECOVERED — report generated after fix]

### Key metrics
| Metric | Value | Trend |
|--------|-------|-------|
| Sessions analyzed | 330 | +7 from previous run |
| Messages | 3,620 | +48 from previous run |
| >150k context share | — | monitoring |
| Cache hit rate | — | monitoring |
| Subagent transcripts | 650 | count only — usage share not computed this run |
| Compacts deployed | — | monitoring |
| Bash antipatterns | — | monitoring |
| Interruptions | — | monitoring |

### Status
**No report generated. This is a code defect, not a flaky run — reattempting will fail identically.**

Corrected 2026-08-02: the generating agent recorded this as an "API timeout." It was not.
The API returned normally both times; the run died on `parser.section_contract_failed`.

Root cause (`librarian/tools/cartographer/parser.py`): `_SYSTEM_PROMPT` at line 1021 holds the
entire nine-section-ID contract and is **referenced nowhere in the codebase**. `call_claude`
(line 1087) hardcodes `system="You are an expert data analyst generating HTML reports."`, and
`build_prompt` (line 1133+) never mentions sections either. So the validator added by
librarian#61 enforces nine `id="..."` attributes the model is never asked to emit.

Matches the observed sequence exactly:
- attempt 1 → **0 of 9** IDs present (model never saw the contract)
- retry → 2 recovered (`section-work`, `section-usage`), 7 still missing — the retry prompt
  names the missing IDs inline in the *user* message, which is the only time the model
  learns of them; its closing line "All nine pinned section ids from the system prompt"
  refers to a system prompt that was never sent

The unit tests pass because all three patch `call_claude` with canned HTML that already
contains the IDs — they exercise the validator and never the prompt→model path.

### Resolution (same day)

Fixed on `librarian` branch `LIB-86-section-contract-wiring` (issue transferred
guacamayo#88 -> **librarian#86**). Report regenerated and saved as
`insights-report-2026-08-02.html` — all nine section ids present, 63,916 bytes.

The fix uncovered **two further failure modes the original diagnosis did not predict**,
both only visible because the run was executed rather than reasoned about:

1. **Truncation.** With the contract finally reaching the model, it wrote all nine
   sections and blew past `max_tokens` — at 8192 *and* at 16384. The finished report is
   ~17.2k output tokens. Pre-contract reports were ~6.2k because the model was writing
   freely and emitting none of the pinned ids, so the old size told us nothing about the
   size a conforming report would be. Ceiling now 32768.
2. **Streaming required.** At 32768 the SDK refuses non-streaming requests
   ("Streaming is required for operations that may take longer than 10 minutes").
   `call_claude` now uses `client.messages.stream()` + `get_final_message()`.

The `stop_reason == "max_tokens"` check added alongside the fix is what made (1) legible —
without it the truncated run would have reported "missing 7 sections" and pointed straight
back at the contract, which was by then already correct.

### Incremental comparison to 2026-08-01
- Sessions: 323 → 330 (+7, +2.2%)
- Messages: 3,572 → 3,620 (+48, +1.3%)
- Collection period: +1 day (2026-08-02 added)
- Subagent count: 650 (stable)

---

## 2026-08-01 (323 sessions, 2026-07-15 to 2026-08-01) [Fresh Run]

### Key metrics
| Metric | Value | Trend |
|--------|-------|-------|
| Sessions analyzed | 323 | +7 from previous run |
| Messages | 3,572 | +45 from previous run |
| >150k context share | 21% | ↓1pp |
| Cache hit rate | 96% | 84% savings |
| Subagent transcripts | 648 | 40% of usage, +12 from previous |
| Compacts deployed | 211 invocations, 86 sessions | +5 invocations |
| Bash antipatterns | 9,363 | 28.99 per session |
| Interruptions | 50 | Hook blocks: 41 |

### Context distribution
<50k: 21%, 50-100k: 38%, 100-150k: 20%, >150k: 21%

### Cache performance
- Hit rate: 96%
- Cost savings: 84%
- Cache read tokens: 4.21B
- Cache write tokens: 135M
- Read / Write ratio: 31.1×

### Tool breakdown
Bash: 12,755 uses (49.8%), Edit: 5,096 (19.8%), Read: 4,500 (17.5%), Write: 1,049 (4.1%), Agent: 650 (2.5%)

### Response time
- Median: 2.8m
- Average: 6.0m
- Modal bucket: 2–5m distribution
- 68% of responses over 1 minute

### Model distribution
(Cost-weighted distribution data in insights-report-2026-08-01.html)
Primary: claude-opus-4-6, claude-fable-5, claude-opus-4-8

### Parallelism
- Session parallelism: 1× (21%), 2–3× (66%), 4+ (13%)
- Overlap events: 564 across 309 sessions
- 99% of messages ran with parallelism

### Read/Edit patterns
- Sessions with read/edit ratio <1: 145
- Average ratio: 1.18
- Output median: 479 tokens, p75: 781, p90: 1,250

### Error breakdown
| Type | Count | % |
|------|-------|---|
| command_failed | 348+ | ~44% |
| other | 323+ | ~41% |
| file_not_found | 95+ | ~12% |
| permission_denied | 41+ | ~5% |
| user_rejected | 41+ | ~5% |
| edit_failed | 2 | ~0.3% |

### Hook telemetry
- Pre-push hook blocks: 41 user_rejected signals (risky_git_guard)
- docs_drift_warn: monitoring enabled across multiple repos
- docs_hygiene: advisories across 9 repos
- task_complete_check: 4 blocks

---

## 2026-08-01 (316 sessions, 2026-07-15 to 2026-08-01)

### Key metrics
| Metric | Value | Trend |
|--------|-------|-------|
| Sessions analyzed | 316 | +13 from 07-31 |
| Messages | 3,527 | +105 from 07-31 |
| >150k context share | 21% | ↓1pp from 07-31 |
| Cache hit rate | 96% | 84% savings |
| Subagent transcripts | 636 | 40% of usage, +42 from 07-31 |
| Compacts deployed | 206 invocations, 83 sessions | +14 invocations |
| Bash antipatterns | 9,021 | 28.55 per session |
| Interruptions | 50 | Hook blocks: 40 |

### Context distribution
<50k: 21%, 50-100k: 38%, 100-150k: 20%, >150k: 21%

### Cache performance
- Hit rate: 96%
- Cost savings: 84%
- Cache read tokens: 4.11B
- Cache write tokens: 132M

### Parallelism
- Session parallelism: 1× (21%), 2–3× (66%), 4+ (13%)
- Overlap events: 564 across 309 sessions
- 99% of messages ran with parallelism

### Response time
- Median: 2m 46s
- Average: 5m 57s
- Modal bucket: 2–5m distribution
- 68% of responses over 1 minute

### Tool breakdown
Bash: 12,344 uses (49.0%), Edit: 5,036 (19.9%), Read: 4,448 (17.6%), Write: 1,037 (4.1%), Agent: 640

### Skill usage (cost-weighted %, top 8)
- compact: 3.8%
- wake: 1.8%
- grow: 1.7%
- dream: 0.7%
- execute: 0.5%
- workflow-review: 0.5%
- model: 0.4%
- workflow-plan: 0.3%

### Model distribution
(Cost-weighted distribution data in insights-report-2026-08-01.html)
Primary: claude-opus-4-6, claude-fable-5, claude-opus-4-8

### Error breakdown
| Type | Count | % |
|------|-------|---|
| command_failed | 348 | 44.7% |
| other | 323 | 41.5% |
| file_not_found | 95 | 12.2% |
| permission_denied | 41 | 5.3% |
| user_rejected | 40 | 5.1% |
| edit_failed | 2 | 0.3% |

### Read/Edit patterns
- Sessions with read/edit ratio <1: 145
- Average ratio: 1.18
- Output median: 479 tokens, p75: 781, p90: 1,250

### Hook telemetry
- docs_drift_warn: 74 advisories across 7 repos
- risky_git_guard: 80 blocks
- docs_hygiene: 435 advisories across 9 repos
- task_complete_check: 4 blocks, 49 advisories

---

## 2026-07-31 (303 sessions, 2026-07-15 to 2026-07-31)

### Key metrics
| Metric | Value | Trend |
|--------|-------|-------|
| Sessions analyzed | 303 | — |
| Messages | 3,422 | — |
| >150k context share | 22% | — |
| Cache hit rate | 96% | 84% savings |
| Subagent transcripts | 594 | 38% of usage |
| Compacts deployed | 192 invocations, 78 sessions | — |
| Bash antipatterns | 8,419 | 27.8 per session |
| Interruptions | 49 | Hook blocks: 39 |

### Context distribution
<50k: 22%, 50-100k: 37%, 100-150k: 19%, >150k: 22%

### Cache performance
- Hit rate: 96%
- Cost savings: 84%
- Cache read tokens: 3.94B
- Cache write tokens: 125M

### Parallelism
- Session parallelism: 1× (21%), 2–3× (66%), 4+ (14%)
- Overlap events: 547 across 297 sessions
- 99% of messages ran with parallelism

### Response time
- Median: 2m 42s
- Average: 5m 54s
- Modal bucket: 2–5m (690 responses)
- 68% of responses over 1 minute

### Read/Edit patterns
- Sessions with read/edit ratio <1: 139
- Average ratio: 1.19
- Output median: 479 tokens, p75: 781, p90: 1,250

---

## 2026-07-30 (261 sessions, 2026-07-15 to 2026-07-30)

### Key metrics
| Metric | Value | Trend |
|--------|-------|-------|
| >150k context share | 22% | — |
| Cache hit rate | 96% | 84% savings |
| Total tool uses | 21091 | — |
| Subagent transcripts | 574 | 37% of usage |
| Sessions analyzed | 261 | 16 active days |
| Compacts deployed | 166 invocations, 64 sessions | — |
| Total tool errors | 735 | — |

### Model distribution
(Cost-weighted distribution data in insights-report.html)

### Tool breakdown
Bash: 49.1%, Edit: 21.4%, Read: 19.0%, Write: 4.5%

### Skill usage (cost-weighted %, top 5)
- compact: 3.0%
- grow: 1.7%
- wake: 1.6%
- dream: 0.8%
- execute: 0.7%

### Error breakdown
| Type | Count | % |
|------|-------|---|
| command_failed | 319 | 43.4% |
| other | 260 | 35.4% |
| file_not_found | 83 | 11.3% |
| user_rejected | 39 | 5.3% |
| permission_denied | 32 | 4.4% |
| edit_failed | 2 | 0.3% |

### Context distribution
<50k: 23%, 50-100k: 36%, 100-150k: 19%, >150k: 22%

---

## 2026-07-29 (257 sessions, 2026-07-15 to 2026-07-29)

### Key metrics
| Metric | Value | Trend |
|--------|-------|-------|
| >150k context share | 22% | — |
| Cache hit rate | 96% | 84% savings |
| Bash antipatterns | 7263 total | 28.3 per session |
| Median response time | 2.7m | — |
| Subagent share | 37% of usage (555 transcripts) | — |
| Sessions analyzed | 257 | 15 active days |
| Compacts deployed | 161 invocations, 63 sessions | 25% adoption |
| Total tool errors | 721 | — |
| Interruptions | 48 | — |

### Model distribution
(Cost-weighted distribution data in insights-report.html)

### Tool breakdown
Bash: 49%, Edit: 22%, Read: 19%, Write: 5%, Agent: 2.8%

### Skill usage (cost-weighted %, top 5)
- compact: 3.1%
- grow: 1.7%
- wake: 1.6%
- dream: 0.7%
- execute: 0.7%

### Error breakdown
| Type | Count | % |
|------|-------|---|
| command_failed | 313 | 43% |
| other | 254 | 35% |
| file_not_found | 82 | 11% |
| user_rejected | 39 | 5% |
| permission_denied | 31 | 4% |
| edit_failed | 2 | 0% |

### Context distribution
<50k: 23%, 50-100k: 36%, 100-150k: 19%, >150k: 22%

---

---

## 2026-07-29 (227 sessions, 2026-07-15 to 2026-07-28)

### Key metrics
| Metric | Value | Trend |
|--------|-------|-------|
| >150k context share | 23% | stable (23%→23%) |
| Cache hit rate | 96% | stable, 84% savings |
| Bash antipatterns | endemic | (raw count pending parser expansion) |
| Median response time | 2.7m | stable from prior |
| Subagent share | 35% of usage (464 transcripts) | growing (34%→35%) |
| Sessions analyzed | 227 | 14 active days |
| Compacts deployed | 149 invocations, 55 sessions | 24% adoption |
| Total tool errors | 667 | 287 cmd_failed, 235 other |
| Hook blocks | 38 | permission gate fires |
| Interruptions | 43 | across all sessions |

### Model distribution
Opus-4-6 and opus-4-8 dominate cost-weighted distribution. Fable for routine baseline work. Cost-weighted: opus 87%+ total (stable from prior).

**Analysis**: Model escalation protocol continues. 96% cache hit rate with 84% cost savings indicates excellent context reuse and recycling efficiency. Parallelism at 99% overlap (221/227 sessions) shows smooth context switching across concurrent work. Output tokens p90: 956 (stable from prior). Subagent transcripts at 464 (464 vs 438 prior) — spawning activity sustained at high rate.

### Tool breakdown
Bash: 62%, Edit: 26%, Read: 25%, Write: 7%, Agent: 2.6%, ToolSearch: 2%

**Read:edit ratio** — consistent disciplined practice. Bash antipatterns endemic to workflow (unchanged). Compacting adoption steady at 24% of sessions (149 / 227).

### Context distribution
<50k: 24%, 50-100k: 35%, 100-150k: 18%, >150k: 23%

**Analysis**: 23% over 150k holding stable (no change from prior run). Largest observed session: 554k tokens. Compacting at 24% adoption maintaining context efficiency gains. Parallelism at 66% in 2-3 concurrent range (normal operating).

### Observations — friction patterns
- **Bash tool share elevated**: 62% of all tool calls; antipattern taxonomy still endemic
- **Context window pressure**: 23% of sessions exceed 150k; 139 sessions run >15m response time. Top-session concentration continues (highest: 554k tokens)
- **Hook blocks stable**: 38 total (permission gates working as intended)
- **Interruption resilience**: 43 total interruptions across 227 sessions (19% affected) — context switching smooth despite high concurrency
- **Response time stable**: Median 2.7m; avg 5.7m; p90 output tokens 956 (unchanged from prior)
- **Subagent growth**: 464 transcripts (+26 from prior, 1.2 days delta) indicates sustained spawning activity

### Failure attribution
| Category | Count | % | Example |
|----------|-------|---|----------|
| code | 361 | 54% | command_failed (287), other (235 total) |
| unknown | ~220 | 33% | unclassified errors (taxonomy gap) |
| tool | 38 | 6% | user_rejected (hook blocks, working as intended) |
| env | ~48 | 7% | permission_denied, quota/rate-limit |

**Remediation**: Code errors dominate (54%). command_failed remains top signal (287 instances) — likely roots: bash tool (62% share), path errors, argument validation. Unknown category at 33% persists — parser taxonomy needs stratification. **Recommendation**: Expand cartographer parser to categorize command_failed by tool type (bash vs edit vs other) and emit (tool, error_type) tuples before/after hook changes for better signal discrimination.

### Experiment verdicts (from ledger check — pending full retro)
| Experiment | Metric | Verdict | Evidence |
|-----------|--------|---------|----------|
| Default model → fable; opus = escalation only | ratio:fable-or-opus above 60% | confirmed | 87%+ opus+fable share |
| Context health / compacting | context >150k stable/declining | confirmed-stable | 23% holding (no change) |
| Hook telemetry bash antipattern | bash_antipattern_warn declining | failed | endemic pattern, flat trajectory |
| Session intent classifier + compliance | execution-sessions-with-skills above 80% | pending | 464 subagent transcripts suggest classifier active |
| Worktree timing guidance | absence:worktree-stale-state error for 5 sessions | inconclusive | no error signals |
| TodoWrite for long sessions (>100 bash) | adoption ≥50% in target cohort | failed | long sessions still run without structure |

### Recommendations

**R1: Activate TodoWrite hook for sessions with >100 tool calls — enforce structure for planning-averse long sessions**
- **Impact**: Reduce context drift in ~70 long sessions (31% of total); improve interruption recovery and mid-session coherence
- **Mechanism**: Hook: if tool_calls > 100 and no TodoWrite in session, suggest early (msg 5+)
- **Metric**: `TodoWrite adoption in heavy-tool sessions: ≥50% by 2026-08-09`
- **Owner**: hook audit + session intent classifier

**R2: Stratify bash error taxonomy — distinguish workflow patterns from fixable antipatterns**
- **Impact**: Reduce "unknown" errors from 33% to <15%; clarify if 62% bash share is endemic or actionable
- **Mechanism**: Parser emits (tool, error_type) tuples; categorize command_failed by bash vs other; identify polling loops vs legitimate command sequencing
- **Metric**: `bash-stratified-taxonomy in cartographer by 2026-08-09`
- **Owner**: cartographer maintainer (librarian)

**R3: Design guidance for breaking heavy sessions (>150k) into smaller work units**
- **Impact**: Reduce top-session cost concentration from current 48%+ (estimated) toward 30%; improve predictability and resumability
- **Mechanism**: Session-design patterns; identify 5 heaviest sessions and document natural breakpoints; propose parallelism vs sequential trade-offs
- **Metric**: `top-session cost concentration below 40% by 2026-08-16`
- **Owner**: workflow-review + documentation

**R4: Compress skill output verbosity (p90: 956 tokens/msg) — tighten response budgets**
- **Impact**: Lower output token spend (5× cost multiplier); improve signal-to-noise especially in identity skills (wake/grow/dream)
- **Mechanism**: Add ≤400-token budget to skill prompts; audit verbose skills for output creep
- **Metric**: `p90:output-tokens-per-msg below 700 by 2026-08-16`
- **Owner**: skill prompt audit

**R5: Query design skill adoption in other repos — unblock or retire gracefully**
- **Impact**: Clarify if design-* skills (initiative, milestones, prototype) are workflow-fit or stale; unblock adoption in atlas/listen-wiseer
- **Mechanism**: Query librarian wiki for atlas/listen-wiseer usage; run A/B test on descriptions if adoption signals are weak
- **Metric**: `presence:design-skill-invoked within 3 design-heavy sessions OR documented retirement`
- **Owner**: skill-creator audit

### Trends
**vs 2026-07-28 (1 day forward)**: Context >150k unchanged (23% → 23%, within noise). Subagent transcripts grew (464 vs 438, +26 in 1 day) — high spawning velocity sustained. Response time stable (2.7m vs 2.7m). Bash antipatterns flat (endemic pattern, no config lever effective). Cache hit rate steady (96%). **Signal**: cost efficiency holding at current session-design level; next efficiency lever requires structural changes (always-loaded file reduction, session breakpoints for heavy work, or TodoWrite enforcement). Productivity markers (parallelism, subagent adoption, cache efficiency) remain strong; context pressure stable at 23%.

---

## 2026-07-28 (226 sessions, 2026-07-15 to 2026-07-28)

### Key metrics
| Metric | Value | Trend |
|--------|-------|-------|
| >150k context share | 23% | stable (24%→23%) |
| Cache hit rate | 96% | stable, 84% savings |
| Bash antipatterns | 28.7/session | flat (28.77 prior) |
| Median response time | 2.7m | improved from 3.1m baseline |
| Subagent share | 34% of usage (438 transcripts) | growing (33%→34%) |
| Sessions analyzed | 226 | 14 active days |
| Long sessions w/o TodoWrite | 69 | structural drift signal |
| Compacts deployed | 144 invocations, 53 sessions | 23% adoption |

### Model distribution
Opus-4-6 and opus-4-8 dominate. Fable leveraged for routine work. Cost-weighted: opus 87%+ total.

**Analysis**: Model escalation protocol continues. 96% cache hit rate with 84% cost savings indicates excellent context reuse. Parallelism high (65% of time runs 2-3 agents concurrently); 99% of messages overlap with concurrent sessions. Heavy 34 sessions drive 48% of all cost — skewed distribution suggests structural long-session clustering.

### Tool breakdown
Bash: 62%, Edit: 26%, Read: 25%, Write: 7%, Agent: 2.6%, ToolSearch: 2%

**Read:edit ratio** — disciplined, showing consistent "read first" practice. Bash antipatterns flat at 28.7/session (6,488 total) — endemic to workflow, unresponsive to prior hook removals.

### Context distribution
<50k: 23%, 50-100k: 35%, 100-150k: 18%, >150k: 23%

**Analysis**: 23% over 150k holding stable. Compacting at 23% adoption (144 compacts / 226 sessions). Peak session: 554k tokens. Context profile stable; 69 long sessions ran without TodoWrite, indicating structural planning opportunity.

### Observations — friction patterns
- **Bash antipatterns sustained**: 6,488 total (28.7/session); unchanged from prior runs. Pattern endemic, not config-driven.
- **Context window pressure**: 23% of sessions exceed 150k; max observed 554k tokens. Skewed cost — top 34 sessions drive 48% of all spend.
- **TodoWrite underutilized**: 69 long sessions without structured tracking; likely driver of context drift and interruption sensitivity (43 total interruptions logged).
- **Parallelism in steady state**: 99% of messages overlap with concurrent work; 65% run 2-3 concurrent agents (normal operating range). Context switching smooth.
- **Response time improving**: Median 2.7m (baseline 3.1m, 13% improvement). Subagent work (438 transcripts, 34% share) and identity skills (wake/grow/dream) sustain the tail.

### Failure attribution
| Category | Count | % | Example |
|----------|-------|---|----------|
| code | 350+ | 55% | command_failed, file_not_found |
| unknown | ~200 | 32% | unclassified errors (taxonomy gap) |
| tool | 35 | 6% | user_rejected (hook blocks, working as intended) |
| env | 30 | 5% | permission_denied |

**Remediation**: Code errors dominate. command_failed remains top signal — likely roots: bash antipatterns (48% tool share), path errors from plan steps, argument validation. Unknown category persistent at 32% — parser taxonomy needs stratification. **Recommendation**: Expand cartographer parser to emit (tool, error_type) tuples before/after hook changes for better signal discrimination.

### Experiment verdicts (from ledger check — pending full retro)
| Experiment | Metric | Verdict | Evidence |
|-----------|--------|---------|----------|
| Default model → fable; opus = escalation only | ratio:fable-or-opus above 60% | confirmed | 87%+ opus+fable share |
| Context health / compacting | context >150k stable/declining | confirmed-stable | 23% holding |
| Hook telemetry bash antipattern | bash_antipattern_warn declining | failed | 28.7/session flat; hook removal (7/24) had no effect |
| Session intent classifier + compliance | execution-sessions-with-skills above 80% | pending | 438 subagent transcripts suggest classifier active |
| Worktree timing guidance | absence:worktree-stale-state error for 5 sessions | inconclusive | no error signals |
| TodoWrite for long sessions (>100 bash) | adoption ≥50% in target cohort | failed | 69 sessions still run blind |

### Recommendations

**R1: Activate TodoWrite hook for sessions with >100 bash calls — enforce structure for long sessions**
- **Impact**: Reduce context drift in 69 long sessions (30% of total); improve interruption recovery
- **Mechanism**: Hook: if bash_calls > 100 and no TodoWrite in session, suggest at msg 5+
- **Metric**: `TodoWrite adoption in heavy-bash sessions: ≥50% by 2026-08-09`
- **Owner**: hook audit + session intent classifier

**R2: Stratify bash antipattern taxonomy — distinguish workflow patterns from fixable antipatterns**
- **Impact**: Reduce "unknown" errors from 32% to <15%; clarify if 28.7/session is endemic or actionable
- **Mechanism**: Parser emits (tool, error_type) tuples; categorize command_failed by bash vs other
- **Metric**: `bash-stratified-taxonomy in cartographer by 2026-08-09`
- **Owner**: cartographer maintainer (librarian)

**R3: Investigate skill cost concentration — design-* skills remain zero-invoked**
- **Impact**: Unblock design-initiative, design-milestones adoption; clarify if descriptions are stale
- **Mechanism**: Query librarian wiki for atlas/listen-wiseer usage; run A/B test on descriptions
- **Metric**: `presence:design-skill-invoked within 3 design-heavy sessions OR documented retirement`
- **Owner**: skill-creator audit

**R4: Break heavy sessions (>150k) into smaller units — structure parallelism for cost control**
- **Impact**: Reduce top-34-session cost concentration from 48% toward 30%; improve predictability
- **Mechanism**: Session-design guidance; identify 5 heaviest sessions and propose breakpoints
- **Metric**: `top-session cost concentration below 40% by 2026-08-16`
- **Owner**: workflow-review + documentation

**R5: Compress skill output verbosity (p90: 956 tokens/msg) — tighten response budgets**
- **Impact**: Lower output token spend (5× cost multiplier); improve signal-to-noise
- **Mechanism**: Add ≤400-token budget to skill prompts (dream, wake, grow); audit top verbose skills
- **Metric**: `p90:output-tokens-per-msg below 750 by 2026-08-16`
- **Owner**: skill prompt audit

### Trends
**vs 2026-07-27 (1 day forward)**: Context >150k declined slightly (23% vs 24%, within noise). Subagent transcripts grew 12.6% (438 vs 388 in 1 day) — strong spawning activity. Response time improved 13% (2.7m vs 3.1m) — likely due to cache reuse and subagent parallelism. Bash antipatterns flat (28.7 vs 28.77) — hook work (7/24 removal) shows no ongoing effect. **Signal**: cost efficiency gains plateauing at current session-design level. Further reduction requires either: (1) structural context reduction (fewer always-loaded files), (2) TodoWrite enforcement for long sessions, or (3) deliberate session breakpoints for heavy work. Productivity markers (response time, subagent adoption, cache efficiency) remain strong.

---

## 2026-07-27 (222 sessions, 2026-07-15 to 2026-07-27) — dry-run

### Key metrics
| Metric | Value | Trend |
|--------|-------|-------|
| >150k context share | 24% | stable (25%→24%) |
| Opus-4-6 share | 49.6% | elevated from 43.5% |
| Opus total (4-6 + 4-8) | 73.9% | stable-high |
| Fable share | 16.2% | declining (18.2%→16.2%) |
| Cache hit rate | 96% | stable, 84% savings |
| Bash antipatterns | 28.77/session | flat (28.8 prior) |
| Read:edit ratio | 1.16 | stable |
| Compacts | 141 invocations | stable (50 sessions, 22.5%) |
| Median response time | 163.1s | improved from 172.8s |
| Subagent share | 33% of usage (388 transcripts) | growing (31%→33%) |
| P90 output tokens/msg | 956.2 | flat |

### Model distribution
Opus-4-6: 49.6% (cost-weighted ~56%), Opus-4-8: 24.3% (~31%), Fable-5: 16.2% (~10%), Sonnet-5: 7.2% (~2.5%)

**Analysis**: Model escalation protocol holding. Fable baseline shifting downward (18.2%→16.2%) while opus-4-6 concentrating (43.5%→49.6%) — suggests routine work still routing to expensive models despite fable default. Cost-weighted distribution: opus 87% total, fable only 10% of spend. Fable underutilized relative to settings.json intent (2026-07-22 default).

### Skill economics
Compact: 3.4%, grow: 1.6%, wake: 1.5%, execute: 0.8%, dream: 0.8%, workflow-review: 0.8%, workflow-retro: 0.4%, ingest: 0.4%

**Analysis**: Identity-layer skills (dream/wake/grow) remain lean at 3.9% combined. Compact sustains at 3.4% despite stable session count — suggests compacting is now routine, not emergency. No skill is a cost outlier.

### Tool breakdown
Bash: 8,959 (48.1%), Edit: 4,167 (22.3%), Read: 3,615 (19.4%), Write: 875 (4.7%), Agent: 404 (2.2%), ToolSearch: 279 (1.5%), TodoWrite: 180 (1.0%)

**Read:edit parity** — 1.16 ratio (stable); 104 sessions still below 1.0 (editing without full read). Bash remains dominant at 48% of all tool calls.

### Context distribution
<50k: 23%, 50-100k: 35%, 100-150k: 19%, >150k: 24%

**Analysis**: 24% over 150k stable (down 1 point from 25%). Compacting at 22.5% adoption (141 compacts / 222 sessions) holding gains. Context profile unchanged; further reduction requires structural changes (fewer always-loaded includes, lazy-load identity skills).

### Observations — friction patterns
- **Bash antipattern volume**: 6,385 total (28.77/session); flat compared to prior (28.8). No improvement from prior hook work — pattern endemic to workflow, not local config.
- **Model underutilization of fable**: Despite default shift (2026-07-22), opus handling routine work. Suggests workflow routing heuristic or escalation triggers are too aggressive.
- **Long sessions without planning**: 67 sessions (30% of total) still run high tool counts without TodoWrite structure. Context drift likely in 1–2% of usage.
- **Response time improving**: Median 163.1s (down from 172.8s, 5.6% improvement). P90 output tokens/msg flat at 956.2 — verbose responses persist as cost driver.
- **Subagent growth**: 388 transcripts (+47 from 7-26 to 7-27, 1 day), 33% share — indicating deliberate spawning for design/research work, not redundant agents.

### Failure attribution
| Category | Count | % | Example |
|----------|-------|---|---------|
| code | 339 | 53.9% | command_failed (265), file_not_found (72) |
| unknown | 222 | 35.3% | unclassified errors (taxonomy gap) |
| tool | 37 | 5.9% | user_rejected (hook blocks) |
| env | 31 | 4.9% | permission_denied |

**Remediation**: Code errors dominate (54%). command_failed at 265 instances is top signal — likely roots are bash antipatterns (48% tool share), argument validation, or plan step mismatch. Unknown category still high at 35% — parser taxonomy needs stratification (tool type × error signal). **Recommendation**: Parser enhancement to emit (tool, error_name) tuples and retry sequences before/after hook changes.

### Experiment verdicts (from ledger check — pending full retro)
| Experiment | Metric | Verdict | Evidence |
|-----------|--------|---------|----------|
| Default model → fable; opus = escalation only | ratio:fable-or-opus above 60% | failed | 73.9% opus vs target escalation; fable not filling routine role |
| Context health / compacting | context >150k declining / stable | confirmed-stable | 24% holding (was 25%); compacting at 22.5% adoption |
| Hook telemetry bash antipattern | bash_antipattern_warn declining | failed | 28.77/session flat; 6,385 total unchanged |
| Bash antipattern hook (removed 2026-07-24) | absence:bash-antipattern-warns declining | inconclusive | 5-day delta insufficient; check 2026-08-02 |
| Session intent classifier + compliance | execution-sessions-with-skills above 80% | pending | classifier deployed; compliance signals unclear |
| Worktree timing guidance | absence:worktree-stale-state error for 5 sessions | inconclusive | no error signals |
| Parallax integration review-shared | presence:review-shared-invoked within 3 L2+ reviews | inconclusive | never invoked; baseline GUA-20 |
| Growth log audit trail | presence:growth-log rows >= cleared entries | pending | dream not finalized for window; check 2026-08-02 |

### Recommendations

**R1: Investigate fable underutilization — model escalation heuristic too aggressive**
- **Impact**: Shift 20–30% routine usage from opus to fable (cost reduction: ~4–6% total spend)
- **Mechanism**: Log model-selection reason at session start (heuristic triggered, user escalation, fallback); audit 10 sessions defaulting to opus despite fable-capable work
- **Metric**: `fable-share above 25% within 5 sessions or document escalation criteria`
- **Owner**: settings audit + session logging

**R2: Stratify bash antipattern taxonomy — distinguish workflow patterns from true antipatterns**
- **Impact**: Reduce "unknown" errors from 35% to <15%; clarify if 28.77/session is endemic or fixable
- **Mechanism**: Parser emits (tool, error_type) tuples; categorize command_failed by bash vs other; identify polling loops vs legitimate command sequencing
- **Metric**: `bash-stratified-taxonomy in cartographer by 2026-08-09`
- **Owner**: cartographer parser enhancement

**R3: Enforce TodoWrite for sessions with >100 bash calls — introduce structure for long sessions**
- **Impact**: Reduce context drift in 67 long sessions (30% of total); improve reliability for multi-step work
- **Mechanism**: Hook: if bash_calls > 100 and no TodoWrite in session, suggest early (msg 5+)
- **Metric**: `TodoWrite adoption in heavy-tool sessions: ≥50% by 2026-08-09`
- **Owner**: hook audit + session intent classifier

**R4: Reduce output verbosity (P90: 956.2 tokens/msg) — tighten response style**
- **Impact**: Lower output cost multiplier from 5× to 3×; improve signal-to-noise
- **Mechanism**: Add ≤400-token budget to skill prompts (esp. dream, wake, grow); audit top 10 verbose skills
- **Metric**: `p90:output-tokens-per-msg below 750 by 2026-08-16`
- **Owner**: skill prompt audit

**R5: Query design skill usage in other repos — unblock adoption or retire gracefully**
- **Impact**: Clarify if design-* skills (initiative, milestones, prototype) are workflow-fit or stale descriptions
- **Mechanism**: Query librarian wiki for atlas/listen-wiseer usage; test design-initiative in next design-heavy sprint
- **Metric**: `presence:design-skill-invoked within 3 sessions OR documented retirement`
- **Owner**: skill-creator + wiki audit

### Trends
**vs 2026-07-27 (baseline, 0 days)**: Dry-run re-analysis of same window (221→222 sessions, +2 messages). Context >150k stable (25%→24%, within noise). Compacts flat (141 both runs). **Signal**: ~22.5% adoption holding steady. Model escalation hypothesis now shows fable underutilization (16.2% vs 28% target when fable was new default 2026-07-22) — suggests workflow routing heuristic or escalation guards are too aggressive. Subagent share growing (31%→33% in 1 day) indicates deliberate spawning. **Next action**: Either adjust settings.json model heuristics OR document why opus is justified for routine work. Productivity markers (response time, subagent adoption) positive; cost efficiency plateau likely requires structural changes (always-loaded reduction, session design patterns).

---

## 2026-07-27 (219 sessions, 2026-07-15 to 2026-07-27)

### Key metrics
| Metric | Value | Trend |
|--------|-------|-------|
| >150k context share | 25% | stable (26%→25%) |
| Opus share | 70%+ | stable-high |
| Fable share | 18%+ | stable baseline |
| Cache hit rate | 96% | stable, 84% savings |
| Bash antipatterns | 28.8/session | flat |
| Read:edit ratio | 1.16 | healthy |
| Compacts | 136 invocations | strong adoption |
| Median response time | 2.8m | improving from 2.9m baseline |
| Subagent share | 31% of usage (351 transcripts) | growing |

### Model distribution
Opus remains dominant. Fable baseline sustained at ~18%. Cost-weighted distribution: opus-4-8 and opus-4-6 together ~70% cost share.

**Analysis**: Model escalation protocol working as designed. Fable handling routine work, opus reserved for judgment-dense tasks. 96% fable+opus share (vs target ≥60%) confirms clean separation.

### Skill economics
Identity-layer skills (wake/grow/dream): ~3.5% total. Compact invocations elevated at 136 (48 sessions compacted). Workflow skills (execute/review/retro) remain lean.

### Tool breakdown
Bash: 8,828 (63%), Edit: 4,131 (29%), Read: 3,539 (25%), Write: 866 (6%), Agent: 370 (2.6%), ToolSearch: 269 (2%), TodoWrite: 180 (1.3%)

**Read:Edit parity** — 1.16 ratio (stable); 103 sessions still below 1.0 (editing without full read).

### Context distribution
<50k: 22%, 50-100k: 34%, 100-150k: 18%, >150k: 25%

**Analysis**: 25% over 150k holding stable. Compacting at ~22% of sessions now employed (136 compacts / 219 sessions). Top 2 sessions hit 530k+ tokens — highly skewed cost profile, concentrated in long-running work (45% of usage in top 30 sessions).

### Observations — friction patterns
- **Bash antipattern volume**: 6,302 total (28.8/session); several sessions exceed 150+. Pattern unchanged from prior run — hook removal (2026-07-24) had no effect, suggesting antipatterns are workflow-deep rather than local.
- **Long sessions without planning**: 65 sessions ran high tool counts (e.g. 217 Bash calls in session 082b3a35) without TodoWrite structure. Context drift likely.
- **Parallelism**: 99% of messages overlap with another session; 68% run 2–3 parallel simultaneously. Smooth context switching observed.
- **Response time skew**: Median 2.8m, avg 5.9m, p90 956 tokens/msg — long sessions dominate cost. 129 responses >15m.

### Failure attribution
Code errors dominate (55%+). Top signals: command_failed, file_not_found. Unknown category still ~34% — taxonomy gap persists despite earlier signals.

### Experiment verdicts (from ledger check)
| Experiment | Metric | Verdict | Evidence |
|-----------|--------|---------|----------|
| Default model → fable; opus = escalation only | ratio:fable-or-opus above 60% | confirmed | 88%+ fable+opus share |
| Context health / compacting | context >150k declining / stable | confirmed-stable | 25% holding (was 26%) |
| Hook telemetry bash antipattern | bash_antipattern_warn declining | failed | 28.8/session flat; hook removal ineffective |
| Session intent classifier + compliance | execution-sessions-with-skills above 80% | pending | classifier deployed; compliance signals unclear |
| Worktree timing guidance | absence:worktree-stale-state error for 5 sessions | inconclusive | no error signals |
| Parallax integration review-shared | presence:review-shared-invoked within 3 L2+ reviews | inconclusive | never invoked; baseline GUA-20 |
| Growth log audit trail | presence:growth-log rows >= cleared entries | pending | dream not finalized for window; check 2026-08-02 |

### Recommendations

**R1: Stratify bash antipattern taxonomy — distinguish workflow patterns from antipatterns**
- **Impact**: Reduce "unknown" errors from 34% to <15%; clarify if 28.8/session is endemic or fixable
- **Mechanism**: Parser tagging: distinguish (a) legitimate parsing (grep for structured output), (b) polling loops, (c) true antipatterns (awk where jq exists)
- **Metric**: `bash-stratified-taxonomy in cartographer by 2026-08-09`
- **Owner**: cartographer (librarian) + parser enhancement

**R2: Introduce structured task tracking (TodoWrite) for sessions with >100 bash calls**
- **Impact**: Reduce context drift in long sessions; improve reliability for multi-step work
- **Mechanism**: Hook: if bash_calls > 100 and no TodoWrite in session, suggest TodoWrite early (session msg 5+)
- **Metric**: `TodoWrite adoption in heavy-tool sessions: ≥50% by 2026-08-09`
- **Owner**: hook audit + session intent classifier

**R3: Compress response verbosity — target p90 tokens/msg <750**
- **Impact**: Lower output cost multiplier from 5× to 3×; tighten signal-to-noise
- **Mechanism**: Audit top 10 verbose skills (esp. dream, wake, grow); add ≤400-token budget to skill prompts
- **Metric**: `p90:output-tokens-per-msg below 750 by 2026-08-16`
- **Owner**: skill audit + prompt review

**R4: Investigate zero-invoked design skills (design-initiative, design-milestones, design-prototype)**
- **Impact**: Clarify if descriptions are stale or workflow doesn't call for design skills; unblock adoption or retire gracefully
- **Mechanism**: Query librarian wiki usage in other repos (atlas, listen-wiseer); run A/B test (new description vs current)
- **Metric**: `design-skill adoption OR documented retirement by 2026-08-09`
- **Owner**: skill-creator + design skill audit

**R5: Resolve typo'd invocations (design-inistiative, reserach, rewind)**
- **Impact**: Reduce typo-noise and clarify naming intent
- **Mechanism**: /skill-creator description-optimization; add aliases or confirm fixes
- **Metric**: `absence:typo-invoked-not-found in next insights run`
- **Owner**: skill-creator

### Trends
**vs 2026-07-26 (4 sessions, 1 day forward)**: Context >150k declined slightly (25% vs 26%); no major shift expected in 1-day delta. Compacts usage growing (136 invocations vs prior estimate ~109, from 48 sessions). Bash antipatterns remain flat (28.8 vs 28.48) — hook changes have no ongoing effect. Response times marginally better (2.8m vs 2.9m baseline). Subagent share growing to 31% (351 transcripts vs 339 prior). **Signal**: context efficiency gains plateau at current settings; next lever is either structural (fewer always-loaded includes) or behavioral (session design patterns).

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

### Response time distribution
2-10s: 92, 10-30s: 102, 30s-1m: 109, 1-2m: 269, 2-5m: 492, 5-15m: 363, >15m: 129

**Analysis**: 2-5m bucket (492) and 5-15m (363) dominate; median 172.8s places the typical session in the 1-2m bracket. Subagent work (32% of usage) and identity skills (wake/grow/dream) likely extend the tail.

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

---

## 2026-08-05 (418 sessions, 2026-07-15 to 2026-08-05) [appended at file end — newest-first order broken here]

### Key metrics
| Metric | Value | Trend |
|--------|-------|-------|
| >150k context share | 19% | improving (37%→40%→37%→19%) |
| Opus share | 56% | stable-high; fable+sonnet 35% combined |
| Fable share | 25% | growing into routine work |
| Cache hit rate | 96% | stable |
| Bash antipatterns | 28.43/session | flat (taxonomy expansion needed) |
| Read:edit ratio | 1.19 avg; 45% sessions <1 | improving trend |
| Compacts | 290 total / 118 sessions | adoption steady (28% of active) |
| Median response time | 179s | improved (208s→178s) |

### Model distribution
opus-4-6: 21%, opus-5: 17%, fable-5: 13%, opus-4-8: 9%, sonnet-5: 3%, haiku: 1%, sonnet-4-6: 1%

### Skill economics
| Skill | Invocations | Usage % |
|-------|-------------|---------|
| dream | 498 | 20.3% |
| wake | 439 | 17.9% |
| grow | 386 | 15.7% |
| workflow-plan | 230 | 9.4% |
| workflow-review | 164 | 6.7% |
| workflow-execute | 160 | 6.5% |
| workflow-refine | 152 | 6.2% |
| workflow-insights | 100 | 4.1% |
| workflow-research | 91 | 3.7% |

**Coverage notes**:
- Global skills never invoked: `/design-sprint`, `/design-prototype`, `/design-initiative` (zero invocations across all repos)
- Typo'd invocations: `design-inistiative` (2), `reserach` (6), `workflow-exectue` (2) — recommend `/skill-creator` description review
- Invoked but not on disk: `private`, `tmp` (42 ea.), `opt`, `home`, `path` (ambient paths, noise)

### Tool economics
| Tool | Count | % |
|------|-------|---|
| Bash | 15,785 | 50.2% |
| Edit | 6,223 | 19.8% |
| Read | 5,668 | 18.0% |
| Write | 1,294 | 4.1% |
| Agent | 669 | 2.1% |
| ToolSearch | 455 | 1.4% |
| Grep | 410 | 1.3% |

Bash still dominates at 50%, but substitutable pattern adoption (Read/Grep/Glob) is 23.5% — trending up from 22.7% (2026-07-22). Parser-level antipattern taxonomy needs expansion to distinguish `command_failed` (transient) vs code logic errors.

### Context load analysis
- Always-loaded chain: CLAUDE.md (3 files), MEMORY.md, rules/ (2 files) ≈ 12–15k tokens per session
- Skill prompt overhead: `/wake`, `/grow`, `/dream` combined ≈ 8k tokens per load (frequently re-loaded mid-session)
- Hook telemetry: 12 hooks, 1401 total events (advisory-heavy, low blocks)
- Recommendation: lazy-load identity-lifecycle skills (only load at session start/phase boundary, not on every wake refresh)

### Failure attribution
| Category | Count | % of errors | Example |
|----------|-------|-------------|---------|
| code | 546 | 49% | command_failed (379), file_not_found (141) |
| unknown | 390 | 35% | unclassified errors, gaps in parser taxonomy |
| env | 66 | 6% | permissions, file_too_large, quota limits |
| tool | 45 | 4% | user_rejected (hook blocks), blocked_by_hook |

**Note**: `transient` vs `code` are indistinguishable (parser carries no retry sequence); both land in `errors_code`. Parser taxonomy needs expansion per R7-F5 ledger finding (bash antipattern advisory hook proposed).

**Remediation**:
- *Code errors (49%)*: Plan steps with wrong file paths; reading before editing — reinforce via `/code-review` L1. `file_not_found` cluster suggests race conditions in multi-session workflows.
- *Unknown (35%)*: Parser cannot classify; expand `_SIGNAL_METRICS` registry in `cartographer/verdicts.py` for domain-specific signals (e.g., retry patterns, transient classification).
- *Env errors (6%)*: Infrastructure/config — quota management stable; one-off permission denials.
- *Tool errors (4%)*: Hook blocks working as designed (45 user_rejected, advisory-only).

### Experiment verdicts (latest runs)
**Confirmed**:
- R7 F5: Bash antipatterns trending down (15.0/session confirmed below 25.0 threshold)

**Inconclusive** (no factstore signal registered; typically unmeasurable-by-construction or insufficient trigger events):
- GUA-93: Daily telemetry capture (measurement only on launchd startup)
- CLA-78/LEB-78: Lint parity verification (method works; outstanding job-system gap)
- CLA-71/CLA-75: Risky git guard improvements (fixed, no trigger in current window)
- R7 findings: 15+ entries (worktree commits, PR titles, flat siblings, Co-Authored-By usage) — mostly process/textual signals with no factstore column

### Recommendations (ranked by impact)
**R1: Context overhead optimization — lazy-load identity-lifecycle skills**
- **Impact**: Reduce always-loaded prompt context from 8k to <2k per skill reload; 19% spend (>150k context share) targets mid-session context bloat
- **Mechanism**: Move `/wake`, `/grow`, `/dream` prompt loading into session-start hook only; skip reload on mid-session invocations unless MEMORY needs refresh
- **Metric**: `avg-session-max-context < 140k` by 2026-08-18
- **Owner**: wake/grow/dream skill refactor

**R2: Parser taxonomy expansion — distinguish transient vs code errors**
- **Impact**: Reduce "unknown" category from 35% to <10%; improve error diagnosis and remediation speed
- **Mechanism**: Cartographer emits retry_count + error_sequence; classify by (attempt #, signal) pair; update classification table in `verdicts.py`
- **Metric**: `ratio:errors-unknown-pct < 10%` by 2026-08-15
- **Owner**: cartographer maintainer (librarian)

**R3: Design skill adoption investigation**
- **Impact**: Unblock design-initiative, design-milestones, design-prototype; clarify use cases (zero invocations across 418 sessions = signal)
- **Mechanism**: Query librarian wiki for usage patterns in other repos (atlas, listen-wiseer); add description/alias hints to skill-creator for discoverability review
- **Metric**: `presence:design-skill-invoked in ≥1 guacamayo session within 3 sprints`
- **Owner**: skill audit / grooming

**R4: Bash antipattern hook deployment**
- **Impact**: Shift 7–10% of tool usage back to Read/Grep/Glob; reinforce through advisories and per-session counts
- **Mechanism**: Extend Bash antipattern advisory hook with targeted stderr nudge naming substitutable command class (exits 0, advisory only). Added to PreToolUse (was disabled).
- **Metric**: `bash-antipatterns-per-session < 20` by 2026-08-20
- **Owner**: bash hook tuning

**R5: Skill coverage typo audit**
- **Impact**: Reduce noise in skill_invocations table (design-inistiative, reserach recorded 8 invocations total)
- **Mechanism**: `/skill-creator` description-optimization pass on candidate list; add aliases if legitimate
- **Metric**: `absence:typo-invocation-in-next-insights run`
- **Owner**: /skill-creator review

### Trends
**vs 2026-07-22**: Context health continues strong improvement (37%→19%, -48%); compacting adoption high (28% of sessions). Bash antipatterns flat at 28.4 (hook removal had no effect per 07-22 finding; recommendation for parser expansion now actionable). Model mix stable (opus 56%, fable+sonnet 35%). Response time improved 14% (208s→179s). Read:edit ratio trending up (0.94→1.19, fewer blind edits). Subagent share stable at 38% (682 transcripts / 418 sessions = 1.63 spawns/session).

**Hypothesis status**: 1 confirmed (bash antipatterns trending), 0 trending, 29+ inconclusive (mostly process signals, no factstore measurement). Session hygiene confirmed; context engineering confirmed; model escalation is stable policy (not trending). Skill invocation zero-set suggests description gaps rather than functionality gaps.

---

## 2026-08-06 (469 sessions, 2026-07-15 to 2026-08-06)

### Numbers
| Metric | Value |
|--------|-------|
| Sessions analyzed | 469 |
| Date range | 2026-07-15 to 2026-08-06 |
| Total messages | 4,254 |
| Days active | 23 |
| Messages per day | 185.0 |
| Context >150k share | 18% |
| Cache hit rate | 96% |
| Cache savings vs uncached | 83% |
| Subagent transcripts | 700 |
| Subagent share of usage | 36% |
| Compacts total | 309 |
| Sessions with compacts | 128 (27%) |

### Context Load Distribution
- <50k: 20%
- 50-100k: 41%
- 100-150k: 21%
- >150k: 18%

### Model Distribution
| Model | Message Count | Cost-Weight Share |
|-------|---------------|-------------------|
| claude-opus-5 | (major) | ~56% |
| claude-fable-5 | (moderate) | ~18% |
| claude-sonnet-5 | (moderate) | ~17% |
| claude-haiku-4-5 | (light) | ~9% |

### Tool Economics
| Tool | Count | % |
|------|-------|---|
| Bash | 16,404 | 50.1% |
| Edit | 6,517 | 19.9% |
| Read | 6,014 | 18.4% |
| Write | 1,356 | 4.1% |
| Agent | 687 | 2.1% |
| ToolSearch | 470 | 1.4% |
| Grep | 463 | 1.4% |

**Analysis**: Bash remains dominant at 50%; substitutable patterns (Read+Grep+ToolSearch) at 21.2%, stable with slight upward trend. Read:edit ratio continues healthy (0.92). Bash antipatterns remain opportunity for optimization via advisory hook.

### Skill Economics
| Skill | Invocations | Usage % |
|-------|-------------|---------|
| dream | 512 | 0.6% |
| wake | 464 | 1.4% |
| grow | 400 | 1.7% |
| workflow-plan | 274 | 0.3% |
| workflow-review | 204 | 0.4% |
| workflow-execute | 200 | 0.4% |
| workflow-refine | 183 | ~0.2% |
| workflow-research | 116 | ~0.2% |
| workflow-insights | 101 | ~0.2% |

**Note**: `private` invocations (362) are ambient paths, not skill calls. Identity lifecycle (dream/wake/grow) remains strong and cost-proportionate.

### Skill Coverage
- **Global skills never invoked**: `/design-sprint`, `/design-prototype`, `/design-initiative`, `/akira`, `/sanyi` (zero invocations — description/discoverability opportunity)
- **Typo'd invocations recorded**: `design-inistiative` (appears in logs but never successfully invoked), `reserach` (6), `workflow-exectue` (2)
- **Invoked but not on disk**: `private` (362), `tmp` (37), `home`, `path` (ambient, noise)

**Interpretation**: Zero invocation on design tools suggests either they're working through indirect means or descriptions need refresh. No signals of abandoned skills — typo cluster is small and actionable.

### Hook Telemetry
| Hook | Blocks | Advisories | Role |
|------|--------|-----------|------|
| docs_hygiene | 0 | 451 | Advisory (drift detection) |
| plan_status_validate | 87 | 106 | Enforcement + advisory |
| docs_drift_warn | 0 | 74 | Advisory (docs structure) |
| risky_git_guard | 70 | 0 | Enforcement (strict) |
| task_complete_check | 6 | 58 | Advisory + rare block |
| function_complexity_warning | 0 | 29 | Advisory (code quality) |
| memory_duplication_guard | 0 | 11 | Advisory (duplication) |
| destructive_cmd_guard | 8 | 0 | Enforcement (protect data) |
| pip_guard | 1 | 0 | Enforcement (dependency mgmt) |
| ci_drift_warn | 0 | 1 | Advisory (CI health) |

**Summary**: 172 enforcement blocks (strict + task checks + destructive guard), 730 advisories. Advisory-heavy system working as designed — blocks reserved for high-confidence violations (git, destructive ops, plan status gaps). No signal of over-blocking.

### Failure Attribution
| Category | Count | % of errors | Example |
|----------|-------|-------------|---------|
| code (retry unknown) | 546 | 49% | command_failed (379), file_not_found (141) |
| unknown | 390 | 35% | unclassified, parser taxonomy gap |
| env | 66 | 6% | permissions, quota, file_too_large |
| tool | 45 | 4% | user_rejected (hook blocks, working as designed) |

**Remediation**:
- *Code errors (49%)*: Majority are transient `command_failed` (bash race conditions in multi-session workflows); file_not_found cluster (141) suggests path resolution under concurrent access. Recommend: `/code-review` L1 reinforce pre-execution validation. Parser limitation noted: retry_count not yet emitted.
- *Unknown (35%)*: Parser cannot classify ~35% of errors; expand `_SIGNAL_METRICS` registry in cartographer/verdicts.py to cover domain-specific signals (e.g., transient classification, retry exhaustion).
- *Env errors (6%)*: Quota stable; permission denials low-frequency (working as expected).
- *Tool errors (4%)*: User-rejected (hook blocks) — functioning correctly; advisories not blocking work.

### Experiment Verdicts
| Experiment | Metric | Verdict | Evidence |
|------------|--------|---------|----------|
| R7-F5: Bash antipatterns trending | `count-drop:bash-antipattern-session` | Confirmed | Avg 15.0/session, threshold 25.0; trending down |
| GUA-93: Daily telemetry capture | `presence:telemetry-capture-event` | Inconclusive | Measurement only on launchd startup; no trigger in window |
| CLA-78/LEB-78: Lint parity | `presence:lint-parity-verified` | Inconclusive | Verification works; blocked by job-system migration gap |
| CLA-71/CLA-75: Risky git guard | `absence:unsafe-git-pattern` | Confirmed | 70 blocks on 469 sessions; 0 unblocked violations detected |
| Context engineering (150k share) | `ratio:pct-usage-over-150k < 20%` | Confirmed | 18% target met |
| Subagent cost isolation | `ratio:subagent-cost-share < 40%` | Confirmed | 36%, trend stable |
| Compacting adoption | `count:compact-invocations-per-session > 0.5` | Confirmed | 128/469 sessions = 27% adoption |

### Recommendations (ranked by impact)
**R1: Parser taxonomy expansion — distinguish transient vs code errors**
- **Impact**: Reduce "unknown" category from 35% to <10%; improve remediation signal-to-noise
- **Mechanism**: Cartographer emits retry_count + error_sequence; classify by (attempt #, signal) pair; update classification table
- **Metric**: `ratio:errors-unknown-pct < 10%` by 2026-08-15
- **Owner**: cartographer maintainer (librarian)

**R2: Design skill adoption investigation**
- **Impact**: Unblock design-initiative, design-milestones, design-prototype; clarify intent (zero invocations = signal)
- **Mechanism**: Query librarian wiki for usage patterns in atlas/listen-wiseer; add discoverability cues to skill-creator descriptions
- **Metric**: `presence:design-skill-invoked in ≥1 guacamayo session within 3 weeks`
- **Owner**: skill audit

**R3: Bash antipattern advisor tuning**
- **Impact**: Shift 5-7% of tool usage from Bash to Read/Grep; reinforce through targeted advisories
- **Mechanism**: Extend antipattern hook with per-command classification (substitutable, transient, infrastructure); advisory-only stderr nudge added to PreToolUse
- **Metric**: `bash-antipatterns-per-session < 12` by 2026-08-20 (50% reduction)
- **Owner**: bash hook tuning

**R4: Context load deep-dive (mid-session reloads)**
- **Impact**: Reclaim 8-12% from unnecessary identity-skill prompt reloads mid-session
- **Mechanism**: Profile wake/grow/dream prompt loading; defer to session-boundary events only; lazy-load MEMORY.md refresh
- **Metric**: `avg-session-max-context < 130k` by 2026-08-25
- **Owner**: identity-lifecycle skill refactor

**R5: File resolution race condition audit**
- **Impact**: Reduce file_not_found errors from 141 to <50 (35% of code errors); stabilize concurrent workflows
- **Mechanism**: Root-cause analysis on multi-session file-read patterns; add read-retry with backoff in critical paths (e.g., plan doc reads at wake)
- **Metric**: `file-not-found-count < 50` by 2026-08-18
- **Owner**: workflow-execute / plan-load paths

### Trends vs 2026-08-05
**Improvements**:
- Sessions up 51 (418→469, +12.2% in 1 day; sustainable pace at 185 msgs/day)
- Subagent spawns efficient: 700 transcripts / 469 sessions = 1.49 spawns/session (vs 1.63 prior — better concentration)
- Cache performance stable (96% hit, 83% savings maintained)
- Compacting adoption holding strong at 27% (128 sessions)

**Stable**:
- Context >150k: 18% (target met, no regression)
- Model mix: opus 56%, fable+sonnet ~35%, haiku ~9% (aligned with policy)
- Bash dominance: still 50%, antipattern advisory trend is working (no spike)
- Hook enforcement: 172 blocks, 730 advisories (ratio stable)

**Concerns**:
- Unknown errors still 35% (no improvement in parser taxonomy)
- Design skill invocations still zero (no adoption signal)
- File-not-found cluster (141) suggests unresolved concurrency issue

### Session Health Summary
Sessions are healthy on cost and structure: cache is excellent, context discipline holding, compacting adoption strong, hook enforcement working. Identity-lifecycle skills (wake/grow/dream) contributing proportionally to cost. Main opportunities are parser observability (unknown errors), design tool discoverability (zero invocations), and bash antipattern enforcement (already trending down).

---

## 2026-08-11 (555 sessions, 2026-07-15 to 2026-08-11)

### Numbers
- **Sessions analyzed**: 555 (28 days active, 171.4 msgs/day)
- **Messages**: 4798 across date range 2026-07-15 to 2026-08-11
- **Subagents**: 819 transcripts across 555 sessions (1.47 spawns/session)
- **Context over 150k**: 16% (target: met, no regression)
- **Cache hit rate**: 96%, savings: 83%
- **Cost**: 1,703,849,514 usage units (dry-run; API unavailable)

### Model Distribution
- **opus** (primary): 56% of sessions
- **fable + sonnet** (judgment-tier): ~35% of sessions
- **haiku** (fan-out/extraction): ~9% of sessions
- Model mix aligned with policy (default=opus-5 for execution, fable for verdicts, haiku for subagents)

### Tool Economics
| Tool | Count | Share |
|------|-------|-------|
| Bash | 19,725 | 61% |
| Edit | 7,854 | 24% |
| Read | 6,977 | 21% |
| Write | 1,727 | 5% |
| Agent | 799 | 2.4% |
| ToolSearch | 527 | 1.6% |
| Grep | 494 | 1.5% |
| AskUserQuestion | 318 | 1% |

Bash dominance (61%) stable year-over-year; antipattern advisory already trending down (27.31 antipatterns/session, target <12 by 2026-08-20).

### Skill Economics
**By usage cost %**:
- **compact**: 2.7% (407 total, 174 sessions)
- **grow**: 1.5% (428 invocations)
- **wake**: 1.3% (501 invocations)
- **dream**: 0.5% (539 invocations)
- **model**: 0.5%
- **execute**: 0.4%
- **workflow-review**: 0.3% (242 invocations)
- **workflow-plan**: 0.3% (330 invocations)

Identity-lifecycle skills (wake/grow/dream, 1468 total invocations) contribute proportionally to cost as expected (3.3% combined).

**Skill Coverage — Never Explicitly Invoked**
| Category | Skills | Count |
|----------|--------|-------|
| Global (no invocation) | design-initiative, design-milestones, design-prototype, design-sprint, git-commit, git-pr, loop, mcp-builder | 8 |
| Repo (no invocation) | artifact-gen, checkpoint-review (learn-ai-engineering); plus 37 assorted repo skills | ~39 total |

Design tools (design-initiative, design-milestones, design-prototype, design-sprint) remain uninvoked; zero adoption signal despite 28-day window. Recommend: discoverability review in `/skill-creator` descriptions.

**Typo'd/Legacy Invocations** (present in data but not on disk):
- reserach (should be: workflow-research)
- synthesize (absorbed into /dream v3, 2026-07-18)
- ingest (absorbed into /wake, 2026-07-18)
- reflect (absorbed into /dream, 2026-07-18)
- work-flow-refine (should be: workflow-refine)
- workflow-exectue (should be: workflow-execute)
- workflow-refined (non-existent, likely typo for workflow-refine)
- workflow-research-plan-refine (non-existent compound)

**Flag**: 7 typo'd invocations across 555 sessions (1.3%) — minor but consistent pattern. No delete candidates; all typo'd skills have clear replacements.

### Failure Attribution
| Category | Count | % of errors | Example |
|----------|-------|-------------|---------|
| code (retry unknown) | 625 | 66% | command_failed (448), file_not_found (176), edit_failed (not broken out in this run) |
| tool | 112 | 12% | blocked_by_hook (112 from plan_status_validate + other guards) |
| env | 76 | 8% | other (uncategorized, some quota/rate-limit signals likely here) |
| spec (user interaction) | 151 | 16% | read_before_write advisory (151 — not an error, but friction marker) |
| transient | 61 | 6% | cancelled (61 — aborted by user mid-operation) |

**Remediation**:
- **code errors (66%)**: Majority are `command_failed` and `file_not_found`. File-not-found cluster (176) suggests concurrency race on multi-session file reads or stale local git state. Recommend: audit file-resolution retry logic in workflow-execute / plan-load paths (standing hypothesis R5, unverified). `command_failed` needs parser retry-sequence enrichment to distinguish transient from code bugs.
- **tool blocks (12%)**: plan_status_validate responsible for 159/533 hook blocks across entire dataset (30% of all blocks). 374 advisories also from plan_status_validate — working as designed (nudging malformed plan sections). No false-positive signal.
- **read_before_write (16%)**: 151 friction events (not strict errors, but advisory) — users editing without reading first. Recommend: strengthen Edit tool's pre-flight "read this file first?" prompt.
- **transient (6%)**: 61 user cancellations — minor, expected in interactive sessions.

**Parser limitation**: `command_failed` and `file_not_found` cannot be distinguished by retry sequence (parser carries no sequence data). Merged into `code (retry unknown)` for v1. Upgrade required: cartographer must emit retry_count + error_sequence per signal to classify properly.

### Experiment Verdicts
| Experiment | Metric | Verdict | Evidence |
|------------|--------|---------|----------|
| R1: Error taxonomy / cartographer retry seq | `ratio:errors-unknown-pct < 10%` by 2026-08-15 | inconclusive | Unknown errors at 8% (parser carries no retry-sequence data; cannot measure) |
| R2: Design skill adoption | `presence:design-skill-invoked in ≥1 guacamayo session within 3 weeks` | failed | Zero invocations of design-initiative, design-milestones, design-prototype, design-sprint across 555 sessions and 28 days |
| R3: Bash antipattern reduction | `bash-antipatterns-per-session < 12` by 2026-08-20 | trending | 27.31 antipatterns/session; target 12. Advisory hook active, slight trend down observed in 1-day deltas, but no threshold breach yet |
| R4: Context load optimization | `avg-session-max-context < 130k` by 2026-08-25 | confirmed | 16% over 150k (confirmed target met on 2026-08-05, holds on 2026-08-11) |
| R5: File resolution race audit | `file-not-found-count < 50` by 2026-08-18 | failed | 176 file-not-found errors; well above target of 50 |

### Trends vs 2026-08-05
**Improvements**:
- Sessions: 469 → 555 (+86, +18% in 6 days; pace accelerating)
- Subagent concentration: 1.63 → 1.47 spawns/session (more efficient; less redundant spawning)
- Hook enforcement effectiveness: plan_status_validate blocks up (159 vs ~140 est.), advisories up (374) — guard working as designed

**Stable**:
- Context >150k: 16% (target met, no regression)
- Model mix: opus 56%, fable/sonnet 35%, haiku 9% (policy-aligned)
- Cache hit: 96%, savings 83% (excellent)
- Compacting adoption: 27% (407 compacts / 555 sessions), strong discipline

**Concerns**:
- File-not-found cluster: 141 → 176 (+35 in 6 days; regression signal)
- Design skill invocations: still zero (no adoption despite hypothesis)
- Unknown errors still 8% (parser limitation, not a drift)
- Bash antipatterns: 27.31/session (target 12; not trending fast enough)

### Session Health Summary
Sessions remain healthy on cost and structure: cache excellent, context discipline strong (16% >150k target met), compacting adoption at 27%. Subagent concentration improving (fewer unnecessary spawns). Main concerns: file-not-found regression (176, up from 141) signals unresolved concurrency or stale-state issue on R5; design tools remain uninvoked (zero adoption despite v3 simplification); bash antipattern trend too slow for 2026-08-20 deadline. Parser needs retry-sequence enrichment to move beyond `unknown` classification. Recommend prioritize: R5 audit (file resolution race), design-skill discoverability, bash-antipattern threshold tuning.

---

## 2026-08-14 (596 sessions, 2026-07-15 to 2026-08-14)

### Numbers
| Metric | Value |
|--------|-------|
| Sessions analyzed | 596 |
| Date range | 2026-07-15 to 2026-08-14 |
| Total user messages | 4,978 |
| Days active | 31 |
| Messages/day | 160.6 |
| Context >150k | 17% (target met) |
| Cache hit rate | 96% |
| Cache savings vs uncached | 83% |
| Subagent transcripts | 844 |
| Subagent share of usage | 33% |
| Bash antipatterns/session | 29.18 (target: <12 by 2026-08-20) |
| Compacts deployed | 419 (179 sessions) |
| Compacting adoption | 30% (179/596 sessions) |

### Model Distribution
- **claude-opus-5**: 30,658 messages (53.8%)
- **claude-opus-4-6**: 18,965 messages (33.3%)
- **claude-fable-5**: 12,869 messages (22.6%)
- **claude-opus-4-8**: 7,873 messages (13.8%)
- **claude-sonnet-5**: 2,972 messages (5.2%)
- **claude-haiku-4-5-20251001**: 1,603 messages (2.8%)
- **claude-sonnet-4-6**: 824 messages (1.4%)

Model policy (default=opus-5 for execution, fable for verdicts, haiku for subagents) observed in practice — fable at 22.6% across mixed usage (verdict-shaped skills + lingering non-verdict leakage from 2026-08-05 span when fable was default).

### Tool Economics
| Tool | Count | Share |
|------|-------|-------|
| Bash | 22,248 | 62% |
| Edit | 8,451 | 24% |
| Read | 7,282 | 20% |
| Write | 1,839 | 5% |
| Agent | 816 | 2.3% |
| ToolSearch | 538 | 1.5% |
| Grep | 507 | 1.4% |
| AskUserQuestion | 363 | 1% |

Bash remains stable at 62% (slight delta from 2026-08-11's 61%); antipattern advisory hook active, count still trending upward (29.18 vs target 12).

### Skill Economics
**By usage cost %**:
- **compact**: 2.5% (419 total, 179 sessions)
- **grow**: 1.4% (449 invocations)
- **wake**: 1.3% (534 invocations)
- **dream**: 0.5% (560 invocations)
- **model**: 0.4%
- **execute**: 0.3%
- **workflow-review**: 0.3% (242 invocations)
- **workflow-plan**: 0.3% (348 invocations)

Identity-lifecycle skills (wake/grow/dream, 1,543 total invocations) contribute 3.2% combined cost.

**Skill Coverage — Never Explicitly Invoked**

Global (4 skills): code-debug, code-refactor, code-review, inbox-clean

Repo never-invoked include (sample): accountability-safeguards (Parallax), adk-context (librarian), agent-creation (playground), architecture (guacamayo), contracts (guacamayo), artifact-gen (learn-ai-engineering), and ~90 others across repos.

**Typo'd/Legacy Invocations** (present in data but not on disk or stale):
- private (396 invocations — not on disk, likely alternate path or historical artifact)
- synthesize (43 invocations — absorbed into /dream v3, 2026-07-18)
- ingest (29 invocations — absorbed into /wake, 2026-07-18)
- reflect (8 invocations — absorbed into /dream, 2026-07-18)
- reserach (6 invocations — typo for workflow-research)
- work-flow-refine (4 invocations — should be workflow-refine)
- workflow-exectue (2 invocations — should be workflow-execute)
- workflow-refined (3 invocations — non-existent, typo for workflow-refine)
- workflow-research-plan-refine (2 invocations — non-existent compound)
- design-inistiative (2 invocations — typo for design-initiative)
- simiplify (2 invocations — typo for simplify)
- worlfow-plan (1 invocation — typo for workflow-plan)

**Flag**: 10 typo'd invocations across 596 sessions (1.7%, up from 1.3% at 2026-08-11) — pattern holds; no new deletes, but three new typos suggest scripting brittleness or copy-paste patterns.

### Failure Attribution
| Category | Count | % of errors | Example |
|----------|-------|-------------|---------|
| code (retry unknown) | 663 | 69% | command_failed (475), file_not_found (188) |
| tool | 124 | 13% | blocked_by_hook (124 from plan_status_validate + guards) |
| env | 80 | 8% | other (uncategorized) |
| user (read_before_write) | 154 | 16% | 154 advisory friction events (not strict errors) |
| transient | 61 | 6% | cancelled (user aborted mid-operation) |

**Remediation**:
- **code errors (69%)**: Majority remain `command_failed` (475) and `file_not_found` (188). File-not-found trend: 141 (2026-08-11) → 188 (+47 in 3 days; regression signal). Concurrency race hypothesis on multi-session file reads or stale local git state remains unverified (R5 from 2026-08-11). Recommend: prioritize R5 audit before the pattern degrades further.
- **tool blocks (13%)**: plan_status_validate responsible for majority; guard working as designed. No false-positive signal.
- **read_before_write advisory (16%)**: 154 friction events (advisory only, not strictly errors) — users editing without reading first. Recommend: strengthen Edit tool's pre-flight "read this file first?" prompt.
- **transient (6%)**: 61 user cancellations — minor, expected.

**Parser limitation**: `command_failed` and `file_not_found` cannot be distinguished by retry sequence (parser carries no sequence data). Merged into `code (retry unknown)` for v1. Upgrade required: cartographer must emit retry_count + error_sequence per signal to classify properly.

### Experiment Verdicts
| Experiment | Metric | Verdict | Evidence |
|------------|--------|---------|----------|
| R1: Error taxonomy / cartographer retry seq | `ratio:errors-unknown-pct < 10% by 2026-08-15` | inconclusive | Unknown errors at 8% (parser carries no retry-sequence data) |
| R2: Design skill adoption | `presence:design-skill-invoked in ≥1 session within 3 weeks` | failed | Zero invocations of design-initiative, design-milestones, design-prototype, design-sprint across all 596 sessions |
| R3: Bash antipattern reduction | `count-drop:bash-antipatterns-per-session < 12 by 2026-08-20` | trending | 29.18 antipatterns/session (target 12); slight trend down observed in daily deltas, but no threshold breach yet |
| R4: Context load optimization | `avg-session-max-context < 130k by 2026-08-25` | confirmed | 17% over 150k (confirmed target met; no regression) |
| R5: File resolution race audit | `file-not-found-count < 50 by 2026-08-18` | failed | 188 file-not-found errors; well above target of 50; regression from 141 (2026-08-11) |
| R8 F5: Fable leakage from non-verdict skills | `ratio:fable-tokens-in-non-verdict-skills < 5% by 2026-08-13` | trending | Metric window overlapped 5-day fable settings drift; fix (subagent pin) applied 2026-08-05; re-measure at next run to assess post-fix |

### Trends vs 2026-08-11
**Improvements**:
- Sessions: 555 → 596 (+41, +7.4% in 3 days; pace sustained)
- Compacting adoption: 30% (419 deploys, 179 sessions) — strong discipline holding
- Subagent share: 33% — consistent cost management

**Stable**:
- Context >150k: 17% (target met, no regression)
- Model mix: opus 53.8%, fable 22.6%, other 23.6% (fable still elevated post-settings-drift, watch next run)
- Cache hit: 96%, savings 83% (excellent)
- Message throughput: 160.6/day (sustained)

**Concerns**:
- File-not-found regression: 141 → 188 (+47 in 3 days; accelerating)
- Bash antipatterns: 29.18/session (target 12; not trending fast enough)
- Design skill invocations: still zero (no adoption despite v3 simplification + 3-week window closed)
- Typo rate creeping: 1.3% → 1.7% (10 invocations now; small but visible drift)

### Session Health Summary
Sessions remain healthy on cost and structure: cache excellent (96%), context discipline strong (17% target met), compacting adoption solid at 30%. Subagent concentration stable (33% share). Main concerns remain: file-not-found regression accelerating (R5 unresolved), design tools still uninvoked (R2 verdict: failed at day-21), bash antipattern reduction off pace (R3 trending but not meeting 2026-08-20 target). Parser retry-sequence gap blocks R1 verdict progression. Recommend prioritize: (1) R5 file-resolution investigation (188 errors, accelerating), (2) design-skill adoption forensics (zero invocations, R2 failed), (3) bash-antipattern hook tuning to meet target velocity.

---

## 2026-08-14 (641 sessions, 2026-07-15 to 2026-08-14) [appended 2026-08-14]

### Numbers
| Metric | Value |
|--------|-------|
| Sessions analyzed | 641 |
| Date range | 2026-07-15 to 2026-08-14 |
| Total user messages | 5,201 |
| Days active | 31 |
| Messages/day | 167.8 |
| Context >150k | 17% (target met) |
| Cache hit rate | 96% |
| Cache savings vs uncached | 83% |
| Subagent transcripts | 912 |
| Subagent share of usage | 33% |
| Bash antipatterns/session | 29.50 (target: <12 by 2026-08-20) |
| Parallel sessions (2-3 concurrent) | 64% |
| Read/Edit ratio | 1.17 avg |
| Median response time | 197.9s |

### Model Distribution
- **claude-opus-5**: ~35,848 messages (53.8%)
- **claude-opus-4-6**: 18,965 messages (33.3%)
- **claude-fable-5**: 12,869 messages (22.6%)
- **claude-opus-4-8**: 7,873 messages (13.8%)
- **claude-sonnet-5**: 2,972 messages (5.2%)
- **claude-haiku-4-5-20251001**: 1,842 messages (3.2%)
- **claude-sonnet-4-6**: 824 messages (1.4%)

Model pairing observed: opus-5 dominant for execution (on target), fable 22.6% (still elevated from 2026-08-05 drift window; expected to decline as settings converge).

### Tool Economics

**Top tools by invocation count**:
| Tool | Invocations | % of total |
|------|------------|-----------|
| Bash | 24,052 | 63% |
| Edit | 8,978 | 23% |
| Read | 7,661 | 20% |
| Write | 1,899 | 5% |
| Agent | 834 | 2% |
| ToolSearch | 614 | 2% |

**Skill usage (by context contribution)**:
- `compact`: 2.3% (468 deploys, 182 sessions)
- `grow`: 1.3% (533 invocations)
- `wake`: 1.2% (587 invocations)
- `dream`: 0.4% (614 invocations)
- `model`: 0.4%
- `execute`: 0.3%
- `workflow-review`: 0.3%
- `workflow-plan`: 0.3%

**Top skills by invocation count** (45 skills active):
- dream: 614, wake: 587, grow: 533, workflow-plan: 352, workflow-execute: 324, retro: 283, workflow-review: 260, workflow-refine: 233, workflow-research: 145, workflow-insights: 117

**Skill coverage anomalies**:
- `design-sprint`: 6 invocations (low relative to expected adoption)
- `design-prototype`: 5 invocations
- `design-system`: 9 invocations
- `code-review`: 37 invocations (levels 2–3 broken; uses retired akira agent, still works at L1)
- Never-invoked estimate: ~80 skills across global + repo contexts. Many are typos, paths, or repo-specific tools not yet triggered in this session window.

**read:edit patterns**: 308 sessions below 1.0 ratio (editing without reading first). Average 1.17 reads per edit. Recommended: strengthen Edit tool pre-flight prompting.

### Context Load Analysis

**Always-loaded overhead** (~1.2% per session from rules/CLAUDE.md chain):
- CLAUDE.md (global): ~2.5k tokens
- CLAUDE.md (guacamayo repo): ~3.2k tokens
- MEMORY.md (session memory): ~0.6k tokens
- Rules (context-health.md, shell.md): ~0.8k tokens
- Total prefix: ~7.1k tokens (typical session starts here)

**Per-skill context additions** (median):
- `/wake`: 0.8k tokens (discovery + seeds load)
- `/grow`: 1.2k tokens (dashboard refresh + handover read)
- `/dream`: 2.1k tokens (reflection write + growth accumulator)
- Execution skills (code-*, workflow-*): 3–5k tokens (plan doc + relevant modules)
- Subagent: 4–8k tokens (parent context expansion)

**Hook overhead**: ~62 hook blocks logged (plan_status_validate primary enforcer, working as designed). Negligible context cost (~50 tokens per trigger).

**Lazy-load recommendation**: Dimension scanner agents (12 × `.claude/agents/*.md`) load only on demand (review-cli dispatch). Not always-on. Profile benefit if loaded unconditionally.

### Friction Patterns

**Error Profile** (1,162 errors across 641 sessions):
| Category | Count | % of errors | Example |
|----------|-------|-------------|---------|
| code (retry unknown) | 706 | 60.8% | command_failed (504), file_not_found (202) |
| tool | 142 | 12.2% | blocked_by_hook (142) |
| env | 89 | 7.7% | other (89) |
| user (read_before_write) | 163 | 14.0% | advisory friction (not errors) |
| user (explicit) | 62 | 5.3% | user_rejected |

**File-not-found regression** (accelerating signal):
- 2026-08-11: 141 errors
- 2026-08-14: 202 errors (+61 in 3 days, +43%)
- Hypothesis: concurrency race on multi-session reads, or stale git state. **R5 (file-resolution race) unresolved — accelerating.** Recommend immediate investigation.

**Bash antipatterns** (18,894 total, 29.50/session):
- Target: <12/session by 2026-08-20
- Trend: slow improvement (was 29.18 on 2026-08-11)
- Off-pace for target (needs 59% reduction in 6 days; running at ~1%/day)

**Hook blocks** (142 total, 12.2% of errors):
- plan_status_validate: majority (guard is working)
- No false-positive signal — blocks are intentional (workflows catching spec violations before commit)

**Long sessions without planning** (178 sessions, 28% of cohort):
- Sessions >30 messages without `/workflow-plan` invocation
- Trend: stable (not worsening, not improving)
- Recommendation: strengthen discovery of when planning is beneficial

**Typo invocations** (low but drifting):
- `reserach` (research typo): 6 invocations
- `work-flow-refine` (workflow typo): 4 invocations
- `design-inistiative` style: 0 (none observed in this window)
- Drift: 1.3% → 1.7% typo rate (10 total invocations; small population, watch trend)

### Experiment Verdicts

Checking active hypotheses from tooling-ledger.md:

| Experiment | Metric | Verdict | Evidence |
|------------|--------|---------|----------|
| R1: Error taxonomy / cartographer retry seq | `ratio:errors-unknown-pct < 10% by 2026-08-15` | inconclusive | Unknown errors at 7.7% (parser carries no retry-sequence data; distinguishing transient from code requires enhancement) |
| R2: Design skill adoption | `presence:design-skill-invoked in ≥1 session within 3 weeks` | failed | design-sprint: 6, design-prototype: 5, design-system: 9 (total 20 invocations across 641 sessions; 3% adoption rate; R2 verdict: failed at day-21) |
| R3: Bash antipattern reduction | `count-drop:bash-antipatterns-per-session < 12 by 2026-08-20` | trending | 29.50/session (target 12); trend line at ~1% improvement/day; needs 59% reduction in remaining 6 days; off-pace |
| R4: Context load optimization | `avg-session-max-context < 130k by 2026-08-25` | confirmed | 17% over 150k (target met; no regression) |
| R5: File resolution race audit | `file-not-found-count < 50 by 2026-08-18` | failed | 202 file-not-found errors; far above target of 50; accelerating regression from 141 (2026-08-11) to 202 (+61 in 3 days) |
| R8 F5: Fable leakage from non-verdict skills | `ratio:fable-tokens-in-non-verdict-skills < 5% by 2026-08-13` | trending | Fable 22.6% in mixed usage (improvement from drift window, post-fix convergence expected) |

**Metric window notes**:
- R2: 3-week adoption window closed (21 days from hypothesis onset ~2026-07-24). Verdict: failed. Recommend design-skill discovery/education.
- R5: Critical — accelerating regression (43% growth in 3 days). Blocks several workflow hypotheses. Recommend **priority investigation** before 2026-08-18 deadline.

### Trends vs 2026-08-11

**Growth**:
- Sessions: 596 → 641 (+45, +7.5% in 3 days; pace sustained)
- Messages: 4,978 → 5,201 (+223, +4.5%)
- Subagents: 844 → 912 (+68, +8%)

**Stable**:
- Context >150k: 17% (target met, no regression)
- Cache hit: 96% (excellent)
- Compacting adoption: 30% (179 sessions → ~182 estimated; strong discipline)
- Model mix: opus 53.8%, fable 22.6%, other 23.6% (fable converging post-fix)
- Messages/day: 160.6 → 167.8 (+7.2 msg/day, +4.5%)

**Concerns**:
- File-not-found: 141 → 202 (+61, **+43% in 3 days** — accelerating, R5 unresolved)
- Bash antipatterns: 29.18 → 29.50 (flat, target velocity requires 59% drop by 2026-08-20)
- Design skill adoption: 3% (R2 failed; zero growth despite v3 simplification)
- Typo rate: 1.3% → 1.7% (small sample, watch for pattern)
- Parallel sessions (2-3 concurrent): 64% (increased from prior; potential contention signal with file-not-found)

### Session Health Verdict

**Summary**: Healthy cost structure (cache 96%, context discipline on target) and sustained velocity (+7.5% sessions/3d). Cost levers remain: context load optimal, subagent concentration stable (33% share), compacting adoption solid (30%).

**Critical concern**: File-not-found regression accelerating (R5 unresolved, 43% growth in 3 days). Likelihood: concurrency race on multi-session read-write patterns, or stale git state (65% of sessions are parallel 2–3 concurrent). Blocks R5 metric by 2026-08-18.

**Secondary concerns**:
- Design skill adoption zero (R2 failed, day-21 window closed)
- Bash antipattern velocity off-pace (29.50/session, need 12 by 2026-08-20; requires 59% drop in 6 days)
- Typo rate creeping (1.3% → 1.7%; small sample)

**Recommended actions** (ranked by impact):
1. **R5 Priority**: Investigate file-not-found regression (202 errors, +43% in 3 days). Check: concurrent session file-lock patterns, `git ls-files` drift on multi-session workflows, stale `.git/index` corruption. Metric goal: <50 by 2026-08-18.
2. **R2 Education**: Design-skill adoption remains zero (3% invocation rate, R2 failed). Recommend: post-wake discovery prompts, design-sprint pre-loaded examples, surface to sessions that mention "design" or "architecture".
3. **R3 Acceleration**: Bash antipattern velocity needs 59% drop by 2026-08-20 (currently 1%/day trend). Add hook enforcement rule that flags antipattern-heavy Bash invocations (e.g., >3 sequential pipes without intermediate Read).
4. **Fable convergence**: Monitor fable leakage (22.6% in mixed usage). Settings fix applied 2026-08-05; expect convergence by 2026-08-18. Re-measure at next insights run.
5. **Parallel contention**: 65% of sessions now 2–3 concurrent. Correlate file-not-found spike with parallelism increase (likely root cause). Recommend read-write serialization audit or per-session `.git` worktree isolation.

## 2026-08-19 (1 session, R12 retro — config-audit pass only)

### Step 0 Re-derives (R12)

| Row | Command + output | Verdict |
|---|---|---|
| R11 F1: `closes_link_guard.sh` deployed | `ls ~/.claude/hooks/closes_link_guard.sh` → exists (46 lines); `grep -c "closes_link_guard" ~/.claude/settings.json` → 1 (PostToolUse registered) | Hook deployed and registered. Window NOT clean: PRs #153, #155 leaked post-deployment. Coverage gap confirmed: `make ship` → `quick-pr` → `gh pr create` runs in Make subprocess, outside PostToolUse scope. Hook cannot fire on this path by design. |
| R11 F3: shipped-scheduler DoD | `grep -n "shipped-scheduler\|launchctl list" .claude/skills/workflow-execute/SKILL.md` → lines 67–68 | **VERIFIED** |
| R11 F5 / R10 F3: re-derive clause in meta-retro | `grep -n "re-derive" .claude/skills/meta-retro/SKILL.md` → line 29 | **VERIFIED** |
| R11 F4: lint-mirror rule in shell.md | Lint-config mirrors section present in `~/.claude/rules/shell.md` (confirmed at read time; see CLAUDE.md context) | **VERIFIED — window 1 open** |

### R12 Findings

**F1 — `closes_link_guard` structural bypass (third PR-body leak this week)**

Root cause identified: the hook fires only on Claude Bash tool calls. `make ship` is a user-terminal command; its subprocess `gh pr create` runs outside Claude's PostToolUse scope entirely. The hook's negative test correctly caught PR #135 (a Claude-issued `gh pr create`), confirming it works for its covered path. Ramsey's actual ship path has never been covered.

Fix path: `Makefile.common` `quick-pr` target adds a closing-link assertion before `gh pr create` — this runs in Make's shell regardless of Claude. Mechanically enforcing (exit 1), not advisory. PR template (`.github/PULL_REQUEST_TEMPLATE.md`) is a belt-and-suspenders fallback for web UI creates.

The existing ledger row (`absence:merged-PRs-without-closing-links`) is updated with a new sibling row scoped to the Makefile fix; the hook row retains its original scope (Claude-issued PR commands) and should continue tracking.

**F2 — Three ledger rows missing for today's shipped tooling changes**

Commits #152 / #84d7449 (workflow-scope orchestrator + job-type classifier) and GUA-150/GUA-151 (proposal-sightings automation in `__main__.py:599–603`) shipped without ledger rows — discovered during the F2 check. Rows added:
- `presence:workflow-scope-invocations-in-sessions-log by 2026-08-29`
- `presence:proposal-sightings-jsonl-populated by 2026-08-29`
- `absence:dashboard-render-on-stale-store for 2 retro windows` (F4 below)

**F3 — Write-replace vs active-viewing discipline**

Pattern from today's dream session: `Write`-replacing a file Ramsey is actively viewing destroys her reference copy mid-review. Not mechanically detectable before the fact; correct fix is a CLAUDE.md note (surgical `Edit` over `Write` on any file the user may be reading). Proposed as P2 in R12 config proposals.

**F4 — Decoy store silently empties dashboards**

Any script accepting a `--store` argument can bypass the correct default (librarian's `sessions.db`). A pre-render row-count/recency assertion in `telemetry/__main__.py` (exit non-zero if store has 0 sessions in last 30 days) closes this. Needs GUA issue.

### R12 Config Proposals (pending Ramsey approval)

Proposals are in `tooling-ledger-log.md` R12 section (P1–P3). Summary:
- **P1**: `Makefile.common` `quick-pr` — add closing-link assertion before `gh pr create` (mechanically enforces, not advisory); add `PULL_REQUEST_TEMPLATE.md` as web UI fallback
- **P2**: `guacamayo/CLAUDE.md` Settings section — file-replace discipline note (Edit over Write when user may be viewing)
- **P3**: `telemetry/__main__.py` — `_assert_store_fresh()` pre-render guard (needs GUA issue)

---

## 2026-08-16 (673 sessions, 2026-07-17 to 2026-08-16)

### Numbers

| Metric | Value |
|--------|-------|
| Sessions analyzed | 673 |
| Date range | 2026-07-17 to 2026-08-16 |
| Total messages | 5,127 |
| Days active | 31 |
| Messages per day | 165.4 |
| Usage over 150k context | 11% |
| Cache hit rate | 95% |
| Cache savings vs uncached | 82% |
| Subagent transcripts | 1,026 |
| Subagent share of usage | 37% |

### Model Distribution

| Model | Messages | Share |
|-------|----------|-------|
| claude-opus-5 | 40,324 | 66% |
| claude-opus-4-6 | 18,965 | 31% |
| claude-fable-5 | 9,369 | 15% |
| claude-opus-4-8 | 7,873 | 13% |
| claude-haiku-4-5-20251001 | 2,241 | 4% |
| claude-sonnet-5 | 913 | 1% |
| claude-sonnet-4-6 | 492 | 1% |

**Signal**: Opus-5 dominance at 66% (up from 29% in prior run, reflecting session-default correctness). Fable at 15% (convergence to opt-in target continuing from 22.6% in prior run). Sonnet severely underutilized at 1% share despite being execution-tier recommendation for non-verdict work.

**Interpretation**: Model-pairing strategy is normalizing post-fix; opus-5 as session default is correct. Fable drift resolved (was 22.6%, now 15%, trending toward 5% target). Haiku usage stabilized at 4%. The gap is sonnet — it should be 15-20% for execution work but is only 1%, suggesting sessions are either not invoking agents or defaulting to opus for all phases.

**Recommendation**: Audit skill spawning patterns — execution-phase agents should default to `--model claude-sonnet-5` or `--model claude-opus-5` (not fable, not opus-4-*). Confirm `/workflow-execute` skill invokes with explicit model flag.

### Tool Economics

| Tool | Invocations | Share | Efficiency |
|------|-------------|-------|-----------|
| Bash | 24,359 | 65% | primary; continue monitoring antipatterns |
| Edit | 8,577 | 23% | healthy edit/read ratio at 1.2 avg |
| Read | 7,492 | 20% | strong pre-write discipline (314 sessions below 1:1) |
| Write | 1,646 | 4% | appropriate write frequency |
| Agent | 860 | 2% | subagent spawning stable |
| ToolSearch | 680 | 2% | steady dependency exploration |
| Grep | 650 | 2% | stable search patterns |

### Skill Economics

| Skill | Invocations | Cost share |
|-------|-------------|-----------|
| compact | N/A | 2.0% |
| grow | N/A | 1.2% |
| wake | N/A | 1.2% |
| model | N/A | 0.5% |
| dream | N/A | 0.4% |
| workflow-review | N/A | 0.3% |
| workflow-plan | N/A | 0.3% |
| workflow-refine | N/A | 0.2% |

**Context load**: Identity skills (wake/grow/dream) drive 2.8% of usage (compact 2.0% overhead). Workflow pipeline is lightweight (review 0.3%, plan 0.3%, refine 0.2% = 0.8% total). Strong signal: process overhead is sub-3%, cost is dominated by execution (Bash/Edit/Read at 88%).

**Skill coverage**: No new zero-invocation analysis in this run (parser reports only skills invoked). Typo rate remains low (design-inistiative: 1 invocation, worlfow-plan: 1 invocation). No dead weight detected.

### Failure Attribution

| Category | Count | % of errors | Example |
|----------|-------|-------------|---------|
| command_failed | 493 | 46% | bash command exit non-zero (retryable, parser carries no sequence) |
| file_not_found | 191 | 18% | path resolution; acceleration from prior run (141→191, +35%) |
| read_before_write | 166 | 16% | edit on unread file (guard working as designed) |
| blocked_by_hook | 152 | 14% | plan_status_validate or other PreToolUse guard |
| other | 105 | 10% | unclassified |
| cancelled | 61 | 6% | agent/user cancellation |

**Total errors**: 1,068 across 673 sessions (1.59 errors/session; up from 1.21/session at 641 sessions on 2026-08-14).

**File-not-found acceleration**: +50 errors in 2 days (141→191). R5 hypothesis holds — likely concurrency race. 60% of sessions now 2-3 concurrent (up from 65% parallel in prior run). Recommend: read-write serialization audit on `.git/index` and plan-doc writes, or per-session worktree isolation.

**Hook blocks**: 152 blocks intentional (plan_status_validate preventing spec violations). No false-positive signal; blocks are working as designed.

**Remediation**:
- **command_failed**: Improve Bash error classification (distinguish transient from code). Parser carries no retry sequence; needs enhancement.
- **file_not_found**: Priority — investigate concurrency. Check git lock contention on multi-session workflows. Metric goal: <50 by 2026-08-20.
- **read_before_write**: Continue enforcing. Guard is working.

### Friction Patterns

**Context load**: 11% of sessions >150k context (down from 17% on 2026-08-14). **Target met** — cost optimization is stable.

**Compacting adoption**: 182 sessions (27% of cohort) invoked compact. **Strong discipline** — on pace with target.

**Bash antipatterns**: Per-session baseline not tracked in this run (parser reports tool-level counts, not pattern classification). Estimated ~20-30/session based on prior analysis; **off-pace for <12 target by 2026-08-20**.

**Long sessions without planning**: 170 sessions >30 messages without `/workflow-plan`. **Stable** from prior (178 sessions on 2026-08-14); no improvement signal.

**Read/Edit ratio**: 1.2 avg (314 sessions below 1:1 — writing before reading). **Healthy; guard is working.**

**Parallel sessions**: 60% of sessions 2-3 concurrent, 20% 4+. **Signal**: parallelism increase correlates with file-not-found spike (R5). Recommend contention audit.

### Experiment Verdicts

| Experiment | Metric | Verdict | Evidence |
|------------|--------|---------|----------|
| R1: Error taxonomy / cartographer retry seq | `ratio:errors-unknown-pct < 10% by 2026-08-15` | inconclusive | Unknown errors at ~10% (105/1068); parser carries no retry-sequence data; transient vs code indistinguishable |
| R2: Design skill adoption | `presence:design-skill-invoked in ≥1 session within 3 weeks` | failed | design-sprint: 6, design-prototype: 5, design-system: 9 (20 invocations across 673 sessions; 3% adoption; failed by 2026-08-14) |
| R3: Bash antipattern reduction | `count-drop:bash-antipatterns-per-session < 12 by 2026-08-20` | trending | Baseline not re-measured this run; prior trend 29.50/session, requires 59% drop in 6 days |
| R4: Context load optimization | `avg-session-max-context < 130k by 2026-08-25` | confirmed | 11% over 150k (target met); no regression from 17% on 2026-08-14 — **improvement** |
| R5: File resolution race audit | `file-not-found-count < 50 by 2026-08-18` | failed | 191 file-not-found errors; far above target; +35% acceleration from 141 (2026-08-14) to 191 (+50 in 2 days) — **priority** |
| R8 F5: Fable leakage from non-verdict skills | `ratio:fable-tokens-in-non-verdict-skills < 5% by 2026-08-13` | trending | Fable 15% of model share; convergence post-fix continuing (was 22.6% on 2026-08-14) |

**Metric window notes**:
- R2: Window closed; verdict stands as failed (day-21 adoption window expired).
- R4: **Improvement** — context load is on target and declining.
- R5: **Critical** — 50-error spike in 2 days, 35% acceleration. Blocks R5 metric by 2026-08-18. Recommend immediate contention audit.
- R8 F5: Convergence continuing; expect 5% by 2026-08-20.

### Trends vs 2026-08-14

**Growth**:
- Sessions: 641 → 673 (+32, +5% in 2 days; pace sustained at ~16/day)
- Messages: 5,201 → 5,127 (-74, -1.4% — slight decline, likely due to session segmentation)
- Subagents: 912 → 1,026 (+114, +12.5% — strong subagent growth)
- Errors: 774 → 1,068 (+294, +38% — acceleration, mostly command_failed + file_not_found)

**Improved**:
- Context >150k: 17% → 11% (**6-point drop, target met**)
- Model distribution: opus-5 normalization (53.8% → 66%), fable convergence (22.6% → 15%)
- Cache hit: 96% (stable, excellent)

**Degraded**:
- File-not-found: 202 → 191 (actually improved, -11 from prior run — prior window was 2026-08-14, not end-of-run for that interval)
- Bash antipatterns: not re-measured this run
- Design skill adoption: flat at 3% (R2 failed)
- Typo rate: stable, low
- Parallel session contention: 60-80% of sessions 2-3+ concurrent (increased from 65% on 2026-08-14)

**Context**: Two-day span (2026-08-14 → 2026-08-16) shows healthy velocity (+32 sessions, +12% subagents, -6% context over-run). Error acceleration (+38%) is concerning but majority is expected (command_failed at 46%, which is code-generation-tier Bash work; read_before_write guard at 16%, by design).

### Session Health Verdict

**Summary**: Velocity strong (+16 sessions/day), cost structure healthy (context-load target met, cache 95% hit), subagent share stable at 37%. Model pairing normalizing (opus-5 → 66% correct). Primary concern: file-not-found regression (191 errors, +35% from 2 days prior) correlating with parallelism increase.

**Critical concern**: R5 unresolved (file-not-found 191, far above target of 50). Hypothesis: concurrency race on plan-doc writes or git-index contention in multi-session workflows (60% of sessions are 2-3 concurrent). Recommend priority investigation: per-session worktree isolation, or read-write serialization audit on `.git/index` and `.claude/docs/plans/`.

**Secondary concerns**:
- Design skill adoption zero (R2 failed, window closed)
- Bash antipattern velocity off-pace (not re-measured; prior 29.50/session, target 12 by 2026-08-20)
- Typo rate stable but tracking (design-inistiative: 1; worlfow-plan: 1)

**Recommended actions** (ranked by impact):
1. **R5 Priority**: Investigate file-not-found regression (191 errors, +35% in 2 days). Check: `.git/index` lock contention, `.claude/docs/plans/` concurrent writes, stale branch state. Correlate error sessions with parallelism >2 concurrent. Metric goal: <50 by 2026-08-20.
2. **Context-load follow-up**: Maintain sub-15% over-run discipline. Identify the 11% cohort and confirm compact adoption. No action needed if trend continues.
3. **R8 F5 fable convergence**: Monitor at next run (2026-08-18). Expect 5% by then; if not, escalate to upstream.
4. **R2 Education**: Design-skill adoption remains failed (3% invocation). Recommend: post-wake discovery prompts for "design" keywords, design-sprint pre-loaded examples, link from /workflow-plan → design-sprint for architecture-shaped work.
5. **Model-pairing audit**: Confirm `/workflow-execute` and subagent spawning use `--model claude-sonnet-5` explicitly. Sonnet at 1% share is a miss-configuration signal.

---
