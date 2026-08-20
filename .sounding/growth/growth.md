# Growth - Learning Accumulator

**Last Synthesis**: 2026-08-19 22:15 (/meta-dream — 9 entries: 6 merged into sounding.md, 3 friction routed to /meta-retro; 9 disposition rows logged. Outcome tags retained per pilot.)
**Entries Since**: 3

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
- [outcome:success] Dispatch session cleared the guacamayo board: #145/#149/#150/#151/#152 closed (all verified by content on main), #154 created, PR #155 merged in-session; 9 agent spawns, 1 cherry-pick regression caught by grep, orphan worktree verified empty and removed — 2026-08-19


- [outcome:success] Galactus board cleared: #31/#35/#36 closed (work already landed), #5 closed (deferred), #39 executed via agent + cherry-picked onto GAL-40 with GAL-31 orphan work, single PR merged — 2026-08-20

2026-08-20 [friction] - Cross-repo worktree dispatch creates worktree in dispatcher's repo not target repo; agent self-recovered via /tmp but the isolation: "worktree" flag has no cross-repo awareness — must create worktree manually in target repo before spawning
2026-08-20 [confirmed] - Board-state-vs-reality divergence: 4 of 5 galactus "open" issues were already done (work landed via PR, branch merged, content on main) — verify by content not labels
2026-08-20 [discovered] - Ramsey prefers consolidating small related changes across issues into a single PR (cherry-pick + patch) over per-issue PRs for the same repo

*Format: YYYY-MM-DD [type] - [concise learning/discovery]*
*Types: [discovered] = new insight, [confirmed] = validated existing approach, [corrected] = updated understanding, [friction] = what cost time and will cost it again (write the pattern, not the instance)*
*Outcome tags persist across synthesis (pilot measurement — first 20 sessions)*
*Processed and cleared by /meta-dream's synthesis phase*
