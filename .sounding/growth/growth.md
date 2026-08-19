# Growth - Learning Accumulator

**Last Synthesis**: 2026-08-18 12:35 (/meta-dream — 10 entries: 5 merged into sounding.md, 1 into portfolio.md, 4 routed to /meta-retro; 10 disposition rows logged. Outcome tags retained per pilot.)
**Entries Since**: 5

*One-line entries added by /meta-grow and /meta-dream. Processed and cleared by /meta-dream's synthesis phase.*

---

- [outcome:partial] AIT-33 executed + verified on stacked branch (uncommitted); GUA-60 driver smoke 4/5, live re-run deferred to post-7pm — 2026-07-30
- [outcome:success] CLA-71 guard fix committed (2863fb4), librarian#73 verified + closed, GUA-63 verified merge-clean, LAE-30 triaged and discarded — 2026-08-01
- [outcome:success] LIB-60 executed end-to-end and merged; #60 and #65 closed; privacy exposure in the public wiki session log caught and reverted — 2026-08-02
- [outcome:success] Fable-default config drift found and fixed (settings.json:269 → claude-opus-5); 5-day gap between documented decision and executing config closed — 2026-08-04
- [outcome:success] Cross-repo cleanup (17 branches deleted, 2 issues closed), job-system→sisyphus rename + SIS prefix, interview-voice integrated into sisyphus, galactus added to portfolio (GAL prefix) — 2026-08-11
- [outcome:success] AIT board cleared to 3 open (#62/#63/#68/#70 closed with blob-level evidence, #77 closed as superseded); `test-render` ml_model failure root-caused to the staging→promotion predicate split and fixed + verified both directions on `bug/ml-shape-rag-promotion` (uncommitted); guacamayo #100/#103/#105 closed; 8 merged local branches deleted; galactus remote `main` restored via branch rename (12 branches → 3) — 2026-08-14
- [outcome:partial] GUA-109 `occurrence.py` executed + reviewed (verdict `comment` → Review: passed; 0 branch-introduced blockers, 11 pre-existing important findings, ruff clean, 772 tests green); plan-status hook + vocabulary decided and guacamayo's 9 plan docs backfilled; branch pushed but no PR, so #109/#111 stay open — 2026-08-14
- [outcome:success] PR #124 conflict re-derived against the pushed head and resolved (one file, not two — GitHub double-counts rename pairs); merged `ee2502e`, closing #109/#111/#114/#115/#116. Telemetry sinks untracked, GUA-125 ported-then-deleted, GUA-103 deleted, board down to 5 open — 2026-08-15


2026-08-18 [confirmed] - The negative test at write time earned its keep twice in one run: closes_link_guard's test fired on PR #135's real missing-Closes body AND exposed lib.sh eating stdin at source — without it the guard would have been registered, green, and a silent no-op forever.
2026-08-18 [discovered] - When Ramsey's phrasing puzzles me, the resolution is usually concrete and visual, not conceptual: 'component drift' meant 'I like this sparkline, put it everywhere' — I offered four taxonomies; she wanted a component.
2026-08-18 [friction] - Overwriting files Ramsey is actively viewing: cp/write to a file she has open destroys her reference. The pattern is surgical edit of her file, never replace — and always confirm which file she's looking at before writing.
2026-08-18 [friction] - Wrong data store path silently produces empty dashboards: `data/sessions.db` (local decoy) vs `~/workspace/librarian/data/sessions.db` (real). Any manual injection script must use the librarian path — the `__main__.py` default is correct, manual scripts bypass it.
2026-08-18 [discovered] - Ramsey's dashboard design process is taxonomy-first: settle WHAT each tab monitors and WHY before building the viz. The overview is system documentation (agent architecture), not a summary of the data tabs.

*Format: YYYY-MM-DD [type] - [concise learning/discovery]*
*Types: [discovered] = new insight, [confirmed] = validated existing approach, [corrected] = updated understanding, [friction] = what cost time and will cost it again (write the pattern, not the instance)*
*Outcome tags persist across synthesis (pilot measurement — first 20 sessions)*
*Processed and cleared by /meta-dream's synthesis phase*
