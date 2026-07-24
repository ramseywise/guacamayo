---
name: project-feedback-loop
description: "Puffin feedback-loop plan executed 2026-07-17 — /retro + tooling-ledger + /config-audit live in global; skill collisions deduped; open — repo settings fixes, first /retro run, puffin→sounding rename"
metadata:
  node_type: memory
  type: project
  originSessionId: 73f6b61f-286a-46fc-bc5b-a18d1d260fff
---

Puffin's `feedback-loop.md` plan (context-engineering loop) executed 2026-07-17, Phases 1/2/3/3b/5:
`~/.claude/skills/retro` (proposal-only tooling retrospective; reads ledger first; skill-change
proposals need eval sketch = Phase 4 encoded), `~/.claude/docs/tooling-ledger.md` (hypothesis→
verified rows; 7 rows), `~/.claude/skills/config-audit` (layering duplicates, settings schema,
plan Status: hygiene), `~/.claude/rules/docs.md` (machine- vs human-consumed doc writer split;
pointer added in global CLAUDE.md). Dedupe: puffin `research` → global `parallel-research`
(renamed; .sounding paths genericized); puffin `skill-writer` deleted after merging its
gotchas.md + reference.md into `skill-creator/references/`.

**First cycle complete (2026-07-17, user-approved):** repo settings wildcards fixed in 4 repos
(audit rerun clean); first /retro ran — 5/5 findings accepted+applied (sync-script diff
detail+--dry-run, cartographer .env fallback + keyless --dry-run in /retro, relinker line-exact
See-Also anchor + tests, zsh-gotchas rule, pointers-not-copies rule). Ledger at 11 rows,
6 verified.

**Open:**
1. ~12 plan docs missing `Status:` lines (listen-wiseer phase plans, template's
   multi-agent-tooling-expansion) — reported, not fixed.
2. Hypothesis rows awaiting future sessions — see `../tooling-ledger.md`.
   F5 growth entry needs graduated flag at next guacamayo /reflect.
3. Rename to **guacamayo** done 2026-07-17 (settings.local.json stale allows fixed too);
   remaining on Ramsey: GitHub remote + final commit + delete leftover `puffin/` copy.

**How to apply:** tooling changes get a ledger row; /retro verifies them; don't re-add generic
skills to guacamayo. Link: [[project-contracts-rollout]], [[project-config-layering]].
