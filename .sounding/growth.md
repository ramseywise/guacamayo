# Growth - Learning Accumulator

**Last Synthesis**: 2026-07-27 18:36 (/dream — 1 merged to sounding.md § Working Notes (primitive-over-mode instinct); 2 discarded as already captured; 3 discarded as process/tooling; all dispositions logged)
**Entries Since**: 0

*One-line entries added by /reflect and /grow. Processed and cleared by /synthesize.*

---

*Format: YYYY-MM-DD [type] - [concise learning/discovery]*
*Types: [discovered] = new insight, [confirmed] = validated existing approach, [corrected] = updated understanding*
*Processed and cleared by /synthesize*

2026-07-27 [discovered] - Worktree isolation + denied git commit = lost work. The settings deny commit, but worktree cleanup destroys staged changes. These are contradictory — worktree agents MUST commit (transport commits), so the deny rule needs a worktree exception or worktree agents need to be replaced with non-isolated agents that stage directly.
2026-07-27 [confirmed] - Fleet dispatch at scale works: 14 agents across 7 repos, 4-5 parallel, no file conflicts. The key is prompt completeness (agents with full context produce on first pass) and dependency ordering (Wave 1 independent, Wave 2 after dependencies land).
2026-07-27 [discovered] - Agents don't pre-lint. Every agent that wrote Python needed post-hoc lint fixes (import sorting, unused imports, subprocess check=False). A pre-stage lint step in agent prompts or a post-agent hook would eliminate 3 rounds of manual cleanup.
2026-07-27 [confirmed] - The retire-or-keep triage framework is decisive: 222 sessions of zero invocations + workflow structural analysis = confident retirement. The investigation agent (haiku) delivered a clear verdict with evidence in one pass.
