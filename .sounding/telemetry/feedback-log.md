# Feedback Run — 2026-08-20

## Corpus
1,616 transcripts, 1.4 GB, Jul 20 – Aug 20 2026 (~31 days).
Factstore: 1,085 sessions (Apr 10 – Aug 19) in `~/workspace/librarian/data/sessions.db`.
Retention caveat: JSONL transcripts retain ~15 days; claims reaching further back are scored from the DB only.
Exclusions: current session excluded from all corpus scans.

## Verdict ledger

| Claim | Source | Stated | Measured | Verdict |
|-------|--------|--------|----------|---------|
| C1: Bash antipatterns total (382 sess) | insights 08-04 | 11,052 / 382s = 28.9/s | 7,872 / 416s = **18.9/s** (mean); p50=**15.0** | **OVERSTATED** — session count wrong (382 vs 416); total wrong (11,052 vs 7,872); mean/median conflated |
| C2: Bash "confirmed below 25" (=16.0) | insights 08-04 verdict | 16.0/session | Signal uses p50=15.0 (verdicts table); mean=18.9; insights text says "16.0". Three numbers for one metric | **OVERSTATED** — verdict is technically met (p50<25) but the reported number and the prose description of what it measures disagree |
| C3: 19% sessions >150k context | insights 08-04 | 19% | 21/416 = **5.0%** | **OVERSTATED** — factor 3.8× inflation. `max_context` column may differ from how insights computed context (possibly cumulative vs peak); or session count denominator is wrong |
| C4: Fable 17.74% in non-verdict contexts | insights 08-04 | 17.74% | Unmeasurable from factstore alone — `skill_costs` carries skill→cost but not skill→model mapping; no `non-verdict` classifier in the schema | **UNMEASURABLE** — the claim's unit (fable tokens scoped to non-verdict skills) has no stored column |
| C5: Execution skill compliance 36% | insights 08-04 | 36% | 12/243 execution sessions have workflow/code skills in `skill_costs` = **4.9%** | **OVERSTATED** — 7× inflation. The 36% may have counted sessions with *any* skill (including wake/grow/dream), not execution-specific skills |
| C6: Top-session-cost-concentration 53.47% | insights 08-04 | 53.47% | Not independently verifiable — `cost_units` column exists but the signal resolver definition was not audited this run | **DEFERRED** |
| C7: 11% sessions >150k context | insights 08-16 | 11% | 56/683 = **8.2%** | **CONFIRMED** (within ~3 points; directionally correct, improvement real) |
| C8: 191 file-not-found errors | insights 08-16 | 191 | `json_extract(tool_errors, "$.file_not_found")` = **165** | **OVERSTATED** — 16% inflation. May include other error types summed under the label |
| C9: Opus-5 at 66% message share | insights 08-16 | 66% | 40,324 / 69,677 = **57.9%** by messages | **OVERSTATED** — 8-point inflation. Insights may have used a smaller denominator (excluding subagent or synthetic sessions) |
| C10: Fable at 15% message share | insights 08-16 | 15% | 9,269 / 69,677 = **13.3%** by messages | **CONFIRMED** (within 2 points) |

### C1: Bash antipatterns — **OVERSTATED**
- Stated: 11,052 across 382 sessions = 28.9/session
- Measured: 7,872 across 416 sessions = 18.9/session (mean); p50 = 15.0
- Command: `sqlite3 ~/workspace/librarian/data/sessions.db 'SELECT COUNT(*), SUM(bash_antipatterns) FROM sessions WHERE date >= "2026-07-15" AND date <= "2026-08-04";'` → `416|7872`
- Corpus: 416 sessions, Jul 15 – Aug 4
- Divergence cause: session count wrong (382 vs 416, +34 sessions uncounted); total 11,052 vs 7,872 differs by 3,180 — the parser likely double-counted subagent sessions or used a cumulative counter. Additionally, 151 sessions have NULL `bash_antipatterns` (36% of cohort), which insights may have excluded from its denominator but included in the total.

### C2: Bash "confirmed" verdict — **OVERSTATED**
- Stated: "confirmed — bash-antipatterns=16.0 below 25.0" (insights 08-04); verdicts table says 15.0
- Measured: Signal resolver `_bash_antipatterns_p50` computes **median**, not mean. p50 = 15.0 is correct. But insights text calls it "per-session average" (line 131: "Per-session average: 28.9") and also claims "current 28.9 will hit 16.0 per verdict" — conflating two different statistics.
- Command: `grep -A10 'def _bash_antipatterns_p50' telemetry/signals.py` → median, not mean
- Divergence cause: The verdict (p50 < 25) is technically TRUE. But the prose narrative leading to it describes a mean declining from 28.9 to 16.0, which is not what the signal measures. A reader of the insights log would believe the per-session average is 16 — it is 18.9.

### C3: 19% >150k context — **OVERSTATED**
- Stated: 19% of sessions >150k context
- Measured: 21 / 416 = 5.0%
- Command: `sqlite3 ... 'SELECT COUNT(*), SUM(CASE WHEN max_context > 150000 THEN 1 ELSE 0 END) FROM sessions WHERE date >= "2026-07-15" AND date <= "2026-08-04";'` → `416|21`
- Divergence cause: 3.8× inflation. `max_context` is stored as an integer; the 19% figure may have been computed from a different column or using a different threshold (possibly 100k, or cumulative rather than peak). **This is the largest magnitude error in the claim set.**

### C5: Execution compliance 36% — **OVERSTATED**
- Stated: 36% of execution sessions invoke skills
- Measured: 12 / 243 execution-intent sessions have workflow/code skills in `skill_costs` = 4.9%
- Command: `sqlite3 ... 'SELECT COUNT(*), SUM(CASE WHEN skill_costs LIKE "%workflow%" OR skill_costs LIKE "%code-%" THEN 1 ELSE 0 END) FROM sessions WHERE date >= "2026-07-15" AND session_intent = "execution";'` → `243|12`
- Divergence cause: 7.3× inflation. The 36% likely counted ANY skill invocation (including wake/grow/dream/compact) as "compliance" — those are identity skills, not execution guardrails. Or the denominator excluded meta-intent sessions differently.

### C8: 191 file-not-found — **OVERSTATED**
- Stated: 191 file-not-found errors
- Measured: 165 (via json_extract from tool_errors)
- Command: `sqlite3 ... 'SELECT SUM(json_extract(tool_errors, "$.file_not_found")) FROM sessions WHERE date >= "2026-07-17" AND date <= "2026-08-16";'` → `165`
- Divergence cause: 16% inflation. Insights may sum `file_not_found` with another error type, or use a wider window.

### C9: Opus-5 66% — **OVERSTATED**
- Stated: 66% of messages
- Measured: 40,324 / 69,677 = 57.9% by total messages across all models
- Command: `sqlite3 ... 'SELECT SUM(json_extract(models, "$.claude-opus-5")) FROM sessions WHERE date >= "2026-07-17" AND date <= "2026-08-16";'` → `40324`; total across all models = 69,677
- Divergence cause: 8-point inflation. Denominator may exclude synthetic or subagent message counts.

## Clusters

### Cluster A: Session count / denominator mismatch
- Mechanism: The insights parser reports different session counts than `SELECT COUNT(*) FROM sessions` for the same date range. This cascades into every per-session ratio (antipatterns/session, errors/session, pct-over-threshold). The 382-vs-416 gap (C1/C3) is +8% — enough to flip any borderline verdict.
- Members: C1 (416 vs 382), C3 (416 vs 382), C8 (window alignment)
- Combined yield: 3 claims overstated
- Expected knock-on: Fixing the session count should move C1's mean from 28.9 to 18.9 and C3 from 19% to 5.0% — every per-session metric re-derived from the correct count will shift.

### Cluster B: Mean/median conflation
- Mechanism: Signal resolver `_bash_antipatterns_p50` computes a median. Insights narrative uses the word "average" and presents the mean alongside the verdict number (which is the median). A reader cannot tell which number the verdict is comparing against.
- Members: C2
- Combined yield: 1 claim overstated (verdict technically correct but misleading)
- Expected knock-on: None — fixing the prose label or switching the signal to mean would move only C2.

### Cluster C: Skill/model scoping gap
- Mechanism: Claims about model usage "in non-verdict skills" (C4) and "execution compliance" (C5) require joining skill invocations with model or skill type — a join the factstore does not support. The insights engine either guesses or uses a different (unstated) proxy.
- Members: C4 (unmeasurable), C5 (7× overstated)
- Combined yield: 2 claims unreliable; C5 is the more dangerous because it drives a ledger row and recommendation
- Expected knock-on: Fixing C5's definition (execution compliance = workflow/code skills in execution-intent sessions) would drop the metric from 36% to 4.9%, making the "trending toward 80%" narrative collapse.

## Recommendations (ranked by measured yield)

### F1: Session-count divergence in insights parser — **metric-fix**
- Tag: improve
- Verdict source: C1/C3 (OVERSTATED)
- Yield: 3 claims affected; every per-session metric is miscounted
- Friction observed: Insights parser reports 382 sessions for a window that has 416 in the DB. All per-session ratios built on this denominator are wrong.
- Evidence: `sqlite3 ... 'SELECT COUNT(*) FROM sessions WHERE date >= "2026-07-15" AND date <= "2026-08-04";'` → 416
- Proposed diff: Audit `telemetry/factstore.py` (or wherever the session-count query lives) for date-range filtering, NULL exclusion, or subagent deduplication logic that drops 34 sessions. The correct count is the DB's.
- Target: `telemetry/factstore.py` or `telemetry/signals.py`
- Enforcement level: code fix (parser)
- Metric: `absence:session-count-divergence-between-parser-and-db for 2 retro windows`
- Pattern key: —
- Recurrence signal: —
- Promotion target: ledger-only (measurement layer, not behavioral)
- Deploy: PROPOSED — parser fix needed, not a hook/rule.

### F2: Bash antipattern signal uses median, insights report says "average" — **metric-fix**
- Tag: improve
- Verdict source: C2 (OVERSTATED)
- Yield: 1 experiment verdict misleading (readers believe mean=16 when mean=18.9)
- Friction observed: The insights narrative at line 131 says "Per-session average: 28.9 (declined from 30.24)" and at line 134 says "the confirmed verdict is that bash-antipatterns achieved the 25/session target (current 28.9 will hit 16.0 per verdict)". The "16.0" is the p50 median, not a projected mean.
- Evidence: `grep -A10 'def _bash_antipatterns_p50' telemetry/signals.py` → returns median
- Proposed diff: Either (a) rename the signal to make unit explicit (`bash-antipatterns-p50`) and update the insights template to say "median" not "average", or (b) switch the resolver to mean if that's what the narrative intends to track.
- Target: `telemetry/signals.py:115-124` + insights template
- Enforcement level: code fix (signal definition or narrative template)
- Metric: `absence:mean-median-conflation-in-insights for 2 retro windows`
- Pattern key: —
- Promotion target: ledger-only
- Deploy: PROPOSED.

### F3: >150k context percentage 3.8× overstated — **metric-fix**
- Tag: improve
- Verdict source: C3 (OVERSTATED)
- Yield: The "19% pay 5× cost multiplier" claim drove R1 (highest-impact recommendation). Actual rate is 5%. The recommendation may still be valid but its stated impact is 3.8× smaller.
- Friction observed: Insights says 19% of sessions exceed 150k. Factstore says 5%. The discrepancy is too large for a date-range issue alone.
- Evidence: `sqlite3 ... 'SELECT COUNT(*), SUM(CASE WHEN max_context > 150000 THEN 1 ELSE 0 END) FROM sessions WHERE date >= "2026-07-15" AND date <= "2026-08-04";'` → `416|21` = 5.0%
- Proposed diff: Audit how `pct_usage_over_150k_context` is computed. Check: is it using `max_context` or a different column? Is the threshold 150,000 or 150? Is it cumulative tokens or peak window?
- Target: `telemetry/signals.py` or `telemetry/dashboard.py`
- Enforcement level: code fix
- Metric: `absence:context-threshold-miscalculation for 2 retro windows`
- Pattern key: —
- Promotion target: ledger-only
- Deploy: PROPOSED.

### F4: Execution compliance metric definition mismatch — **metric-fix + retraction**
- Tag: stop
- Verdict source: C5 (OVERSTATED, 7.3×)
- Yield: Drives ledger row `ratio:execution-sessions-with-skills above 70%` and recommendation R4. True compliance is 4.9%, not 36%. The ledger row's 70% target is 14× above actual — it cannot be met by any intervention short of redefining the metric.
- Friction observed: The "36%" likely counts ANY skill (including identity skills wake/grow/dream) as "compliance" in execution-intent sessions. Real compliance (workflow/code skills) is 4.9%.
- Evidence: `sqlite3 ... 'SELECT COUNT(*), SUM(CASE WHEN skill_costs LIKE "%workflow%" OR skill_costs LIKE "%code-%" THEN 1 ELSE 0 END) FROM sessions WHERE session_intent = "execution";'` → `243|12` = 4.9%
- Proposed diff: Redefine the signal to use an explicit skill whitelist (workflow-execute, workflow-review, code-review, code-debug, code-refactor). Rewrite the ledger row's target to something achievable (e.g., >15% within 2 retro windows). The current 70% target is aspirational fiction.
- Target: `telemetry/signals.py` + `.sounding/tooling-ledger.md` row
- Enforcement level: metric rewrite
- Metric: `ratio:execution-sessions-with-guardrail-skills above 15% by 2026-09-30`
- Pattern key: —
- Promotion target: ledger-only
- Deploy: PROPOSED.

## Predictions to check next run
1. Fixing Cluster A (session count) should move C1's mean from 28.9 to 18.9 and C3 from 19% to 5%.
2. C5 (execution compliance) at 4.9% means the ledger row `execution-sessions-with-skills above 70%` will fail at next retro — it should be rewritten before then.
3. C7 (context >150k) is the only CONFIRMED claim that also showed improvement (19% → 8.2%). If this continues trending down, the R1 recommendation becomes less impactful.
4. Fable convergence (C10) is real (15% → 13.3% in the latest window). Expect it to hit the 5% target by end of August if current trajectory holds.

## Metric defects found

| Defect | Impact | Fix location |
|--------|--------|-------------|
| Session count mismatch (382 vs 416) | Every per-session ratio is wrong | Parser query or date filter |
| Mean/median conflation in bash-antipatterns | Verdict correct, prose misleading | Signal name or insights template |
| >150k threshold overcounting (19% vs 5%) | R1 impact overstated 3.8× | Signal resolver or column choice |
| Execution compliance overcounting (36% vs 4.9%) | R4 recommendation + ledger row built on 7× inflated number | Skill whitelist in signal definition |
| Fable non-verdict scoping (C4) | Unmeasurable — no skill→model join | Needs collection change (skill_models column) |

## Automation design question (from Ramsey)

**Current flow**: insights → (manual) feedback → (manual) retro → hypothesis → loop
**Proposed flow**: insights → (auto) feedback → retro (human approve only) → hypothesis → loop

The feedback gate exists because automated enforcement on miscounted metrics creates hooks that block correct work. This run found 4 of 10 claims OVERSTATED and 1 UNMEASURABLE — 50% of the monitoring surface is measuring wrong. Automating feedback without fixing the measurement layer first would route phantom findings into retro, which would propose enforcement on them.

**Recommendation**: Fix Cluster A (session count), B (mean/median), and C3 (context threshold) first. Once the OVERSTATED rate drops below 20%, feedback can safely auto-run after insights as a background agent, with only the retro apply step requiring human approval.

**On renaming "hypothesis"**: The skill name is fine mechanically — it's the concept that's awkward. "experiment" or "metric" or "track" would all work. Suggest `/track` — it's what the skill does (track whether a change worked). Rename is a one-file edit + SKILL.md metadata.
