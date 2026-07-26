# Growth - Learning Accumulator

**Last Synthesis**: 2026-07-24 13:12 (/dream — 5 entries: all discarded as process/tooling, not identity-level; all dispositions logged)
**Entries Since**: 5

2026-07-24 [discovered] - Sessions that grow beyond their branch scope need a mid-session branch-check; bug/ prefix signals small fix but retro R1 expanded into migration work that belonged on a feature branch
2026-07-24 [corrected] - Observability loop had a gap: /grow only read signals but never refreshed insights data. Fix: /grow background-spawns /workflow-insights, /dream background-spawns /workflow-retro. Reading without writing creates stale reads
2026-07-25 [corrected] - /wake only checks guacamayo issue board but the meta-session's job is the cross-cutting view. Should check all active repos (job-system, learn-ai-engineering, librarian, atlas, ai-project-template, listen-wiseer). A meta-session that only sees one repo's issues is a local session pretending to be meta
2026-07-26 [discovered] - Two worktree agents targeting the same repo cause branch collisions (LAE #30 commits landed on #35's branch). Serialize agents per-repo or create distinct branches before spawning
2026-07-26 [corrected] - /workflow-refine needs fable model, not sonnet. Sonnet agents defer verification questions instead of resolving them — refine requires reasoning depth to actually answer DoR checklist questions

*One-line entries added by /reflect and /grow. Processed and cleared by /synthesize.*

---

*Format: YYYY-MM-DD [type] - [concise learning/discovery]*
*Types: [discovered] = new insight, [confirmed] = validated existing approach, [corrected] = updated understanding*
*Processed and cleared by /synthesize*
