# Growth - Learning Accumulator

**Last Synthesis**: 2026-07-22 17:19 (/dream — 6 entries: 2 merged into sounding.md, 4 discarded as process/already-implemented; all dispositions logged)
**Entries Since**: 3

*One-line entries added by /reflect and /grow. Processed and cleared by /synthesize.*

---

*Format: YYYY-MM-DD [type] - [concise learning/discovery]*
*Types: [discovered] = new insight, [confirmed] = validated existing approach, [corrected] = updated understanding*
*Processed and cleared by /synthesize*

2026-07-22 [confirmed] - "pass in isolation, fail in full suite" is the contamination signature for async event loop poisoning in pytest; grep for all affected files before starting the fix, not just the one that surfaces
2026-07-22 [confirmed] - ruff --fix after removing `asyncio` imports catches isort issues automatically; run it as the last step in any test-file cleanup
2026-07-22 [confirmed] - when a fix doesn't clear all failures, expand scope (grep the class of pattern across all files) before deepening focus on the file that surfaced

