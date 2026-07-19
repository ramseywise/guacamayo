# Growth - Learning Accumulator

**Last Synthesis**: 2026-07-19 late (/dream — 6 entries: 3 woven into sounding.md, 2 into user.md, 1 process learning flagged for /retro)
**Entries Since**: 4

*One-line entries added by /reflect and /grow. Processed and cleared by /synthesize.*

---

*Format: YYYY-MM-DD [type] - [concise learning/discovery]*
*Types: [discovered] = new insight, [confirmed] = validated existing approach, [corrected] = updated understanding*
*Processed and cleared by /synthesize*

2026-07-20 [corrected] - Synthetic eval datasets must match the actual corpus content, not be generic placeholder data. English only. Verify agent-generated test data against the real data directory before accepting.
2026-07-20 [confirmed] - Cross-repo plan scan → parallel spawn is a mature meta-session pattern. Model tiering (haiku=research, sonnet=impl) and worktree isolation work well at scale (10+ agents in one session).
2026-07-20 [discovered] - Subagent usage quotas can silently fail a full batch. When spawning 5+ agents, check for quota errors before assuming work landed — re-spawn may be needed.
2026-07-20 [discovered] - Structural verification (file exists, format correct, status updated) is necessary but insufficient for agent outputs. Domain-level verification (does the content match the actual data/corpus it targets?) is the real quality gate. The eval dataset failure was structurally perfect but semantically wrong.

