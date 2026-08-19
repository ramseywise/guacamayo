# Handover — 2026-08-18 19:55 GUA-137 dashboard facelift — taxonomy + Session Health built

**Context**: Dashboard facelift for guacamayo's context-dashboard. Redesigned from 7 overlapping tabs to 5 clean tabs (Overview + Session Health + Context Health + Loop Health + Retro), each answering one question. Major Python + HTML work.

## Current State
- **`.sounding/context-dashboard-v2.html`** is the working file (1,185 lines). NOT yet canonical — the live dashboard is still `context-dashboard.html`. Swap when ready.
- **Overview tab**: DONE — persistence cards, work pipeline, 5-node loop SVG diagram (SESSION→TELEMETRY→INSIGHTS→RETRO→CONFIG→SESSION), review dimensions (12 pills), monitoring contents (4-column grid). Ramsey wants the diagram to show MORE detail — how hooks/skills/meta-skills actually connect as nodes, like an agent architecture graph.
- **Session Health tab**: DONE — 3 KPIs + 3x2 dual-line charts (cost p50/p90, cache 95% threshold, output/input per session + per day with p90 thresholds) + Session Profile section (context dist gradient bars, parallelism stacked bar, duration gradient bars) + skill/agent economics (split table with repo column).
- **Context Health tab**: IN PROGRESS — currently has the original `context-dashboard.html` content pasted in (explainer text, static stat values, empty JS chart containers). The charts (`#chart-context`, `#chart-over150k`, `#chart-shape`, `#chart-compaction`, `#chart-sessions-week`) need JS `drawLine()` + a DATA object to render — they're empty divs without it. Ramsey wants: keep north star + window toggle + the charts, remove the big text blocks.
- **Loop Health tab**: populated via regions (friction, experiments, actions, workflow loop, review findings, verdict trajectories).
- **Retro tab**: populated via regions (retro summary + insights narrative embed).
- **Python changes** (`telemetry/dashboard.py`): `_dual_chart_svg` (SVG with p50+p90+threshold), `_session_health_panel` (3x2 charts + viz), `_session_health_viz` (gradient distributions), `_context_health_panel` (subagent-focused), `render_session_health_region` / `render_context_health_kpi_region` (windowed wrappers), `render_skill_economics_card` (split skills vs agents with repo column). All 586 tests green, lint clean.
- **`telemetry/__main__.py`**: `SESSION-HEALTH` and `CONTEXT-HEALTH-KPI` regions added to injector.
- **`dashboards/`**: REVERTED to git state. Do NOT overwrite — those are Ramsey's reference copies.
- **Evaluator false positives**: GUA-137 (branch=main at creation) and GAL-31 (worktree with uncommitted work) both rejected. GAL-23, GAL-34, GAL-33, SIS-33 closed. GAL-31/35/36 labels fixed.

## Decisions Made
- **5-tab taxonomy**: Overview (system design) → Session Health (token efficiency) → Context Health (tooling health) → Loop Health (learning) → Retro (improvement evidence).
- **Session Health question**: "How efficient are my token usage patterns?" (not "How am I spending?").
- **Compact rate removed** as chart — low rate in short sessions isn't friction.
- **Token Economics (TOKEN-GRID) removed** from Session Health — duplicate of the 3x2 charts.
- **Skill economics split** into Skills (with repo column) and Agents tables.
- **Overview = system documentation**: persistence + pipeline + architecture loop diagram + review dimensions + monitoring contents grid. Tables removed in favor of SVG graph.
- **dashboards/ is read-only reference** — never cp or overwrite.
- **Always use librarian store** (`~/workspace/librarian/data/sessions.db`) for manual injection.

## Open Threads
- **Context Health JS charts**: the original dashboard uses client-side `drawLine()` with a hardcoded `DATA` object. The v2 doesn't have this JS/data. Options: (a) port the DATA object + drawLine to v2, (b) replace with server-rendered SVG charts like Session Health uses. Option (b) is more consistent but requires computing the series in `_context_health_panel` — same pattern as Session Health.
- **Overview diagram depth**: Ramsey wants MORE — not just 5 nodes in a loop, but how hooks fire DURING a session, how meta-skills invoke each other, how the evaluator connects to the board. Think mermaid-style agent architecture, not a flowchart.
- **Context Health content from original**: the explainer text is too heavy ("The 150k cliff" paragraph). Keep charts, remove prose.
- **Window toggle on Context Health**: the CONTEXT-HEALTH-KPI region has it but the original pasted content doesn't. Need to wire the charts to the toggle.
- **`dashboards/context-dashboard-v2.html`**: Ramsey's 3,044-line version with Gemini edits was LOST (untracked, overwritten by cp). The current `dashboards/` v2 is the git-restored v1 content (2,881 lines). She may want to rebuild it.

## Immediate Next Steps
1. Port Context Health charts — either add `drawLine` JS + DATA, or convert to server-rendered `_dual_chart_svg` (recommended: consistent with Session Health).
2. Deepen the Overview SVG — show hook→store→skill connections as an agent graph with more detail on how nodes communicate.
3. Remove heavy explainer text from Context Health, keep north star + toggle + charts.
4. Run `uv run telemetry` against the canonical dashboard to keep it fresh (the v2 work doesn't affect the live dashboard).
5. When v2 is ready: `mv .sounding/context-dashboard-v2.html .sounding/context-dashboard.html`.

## Key Files
- `.sounding/context-dashboard-v2.html` (the working dashboard)
- `.sounding/context-dashboard.html` (the live canonical dashboard — not yet replaced)
- `telemetry/dashboard.py` (Python renderers — _dual_chart_svg, _session_health_panel, etc.)
- `telemetry/__main__.py:1066-1104` (region injection dict)
- `tests/telemetry/test_region_injector.py` (marker contract tests)
- `tests/telemetry/test_region_wiring.py` (renderer unit tests)
- `.claude/docs/plans/2026-08-18-gua-137-dashboard-facelift.md` (original plan — taxonomy has evolved past it)
