# Growth - Learning Accumulator

**Last Synthesis**: 2026-07-27 18:36 (/dream — 1 merged to sounding.md § Working Notes (primitive-over-mode instinct); 2 discarded as already captured; 3 discarded as process/tooling; all dispositions logged)
**Entries Since**: 3

*One-line entries added by /reflect and /grow. Processed and cleared by /synthesize.*

---

*Format: YYYY-MM-DD [type] - [concise learning/discovery]*
*Types: [discovered] = new insight, [confirmed] = validated existing approach, [corrected] = updated understanding*
*Processed and cleared by /synthesize*

2026-07-27 [discovered] - Worktree isolation + denied git commit = lost work. The settings deny commit, but worktree cleanup destroys staged changes. These are contradictory — worktree agents MUST commit (transport commits), so the deny rule needs a worktree exception or worktree agents need to be replaced with non-isolated agents that stage directly.
2026-07-27 [confirmed] - Fleet dispatch at scale works: 14 agents across 7 repos, 4-5 parallel, no file conflicts. The key is prompt completeness (agents with full context produce on first pass) and dependency ordering (Wave 1 independent, Wave 2 after dependencies land).
2026-07-27 [discovered] - Agents don't pre-lint. Every agent that wrote Python needed post-hoc lint fixes (import sorting, unused imports, subprocess check=False). A pre-stage lint step in agent prompts or a post-agent hook would eliminate 3 rounds of manual cleanup.
2026-07-27 [confirmed] - The retire-or-keep triage framework is decisive: 222 sessions of zero invocations + workflow structural analysis = confident retirement. The investigation agent (haiku) delivered a clear verdict with evidence in one pass.
2026-07-28 [corrected] - Issue labels must track workflow state transitions — we weren't updating them as agents executed. Labels went stale across 14 agents. The fix is #42 (auto-label hook tied to workflow skills), but the deeper lesson: any state that isn't automatically maintained will drift.
2026-07-28 [confirmed] - Refine-before-execute gate catches real problems. 2 of 6 DoR checks failed (#31 no ACs, #36 stale scope), #32 needed structural diagnosis before code changes. Without the gate, agents would have executed stale specs.
2026-07-28 [discovered] - The design skill problem is structural bypass, not description quality. Two rounds of description rewrites failed (0 invocations). The real cause: /workflow-plan absorbs the work before users ever discover the 3-skill hidden chain. Wiring pipeline footers + consolidation is the fix — description quality was a red herring.
