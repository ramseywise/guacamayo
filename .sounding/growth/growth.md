# Growth - Learning Accumulator

**Last Synthesis**: 2026-07-30 20:19 (/dream — 6 merged into sounding.md (stale-cache→boards+quota, domain-truth propagation, worktree repo-scoped isolation, parent-tree-clean, stacking pattern), 1 discarded (--no-track → /retro); all dispositions logged)
**Entries Since**: 7 (synthesis due — 5+ threshold passed)

*One-line entries added by /reflect and /grow. Processed and cleared by /synthesize.*

---

- [outcome:partial] AIT-33 executed + verified on stacked branch (uncommitted); GUA-60 driver smoke 4/5, live re-run deferred to post-7pm — 2026-07-30

2026-07-31 [corrected] - Subagent factual claims about *which branch holds what* are the class I must verify before relaying. A sonnet diagnosis agent inverted diff direction twice with HIGH confidence — said main had the `.jinja` rename (it doesn't) and prescribed a `nbks` fix the PR had already made. I repeated one error to Ramsey before checking. Diagnosis agents are trustworthy on "what failed"; not on "who has the fix".
2026-07-31 [discovered] - FRICTION: repo-prefix/branch-name mismatch. Three librarian branches carry `GUA-` prefixes because the issues live on the guacamayo board, but convention says prefix tracks the repo *changed* (`LIB-`). The rule is in CLAUDE.md and was still violated — enforcement is absent, not the rule.
2026-07-31 [discovered] - FRICTION: I don't reliably leave work staged for review. The gate says stage-then-stop, but across today's dispatches changes landed as agent commits, as live-checkout writes, and as staged diffs inconsistently. Default needs to be mechanical, not remembered.
2026-07-31 [discovered] - FRICTION: `make ship` / `make pull` still misfiring. `make ship` shipped the branch I was standing on rather than the one intended (CLA-67 instead of GUA-62) — the target is implicit, so a stale checkout ships the wrong work silently.
2026-07-31 [discovered] - FRICTION: autocompact not firing in terminal mode — recurrence of the 07-30 report that I closed as metric confusion (ledger row 26). The new detail is *terminal mode specifically*, which the earlier transcript investigation (VS Code session) would not have caught. My "no defect found" was scoped too narrowly.
2026-07-31 [discovered] - Red main accepting merges is a portfolio-wide condition, not an incident: librarian, playground, and ai-project-template all had main red today while PRs merged into it. Same shape as the label-cache drift — CI status, like issue labels, is a cache nobody invalidates.
2026-07-31 [confirmed] - Lazy imports do not protect tests when the app uses a lifespan. `TestClient(app)` as a context manager runs startup, so moving an import into `lifespan` just relocates the failure. Optional-dependency startup work has to degrade (try/except + log), not merely defer.

*Format: YYYY-MM-DD [type] - [concise learning/discovery]*
*Types: [discovered] = new insight, [confirmed] = validated existing approach, [corrected] = updated understanding*
*Outcome tags persist across synthesis (pilot measurement — first 20 sessions)*
*Processed and cleared by /synthesize*
