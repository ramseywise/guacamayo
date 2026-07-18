# Cross-Repo Queue — committed pointer for mobile /wake

*Why this file exists:* On the Mac, `/wake` Phase 4 globs `~/workspace/*/.claude/docs/plans/*.md`
for live cross-repo state. Those plan docs are **git-ignored** (`~/.gitignore_global`), so a
mobile/cloud sandbox clones the repos but not the plans — Phase 4 comes back empty. This file
is committed (lives in `.sounding/`, which travels), so it survives the clone and gives mobile
sessions the same orientation the Mac gets from the plan glob.

*What it is:* a **pointer**, not a copy (per `docs.md` "pointers not copies" and guacamayo's own
"continuity files hold pointers, never copies"). It names where live state lives and its last-known
Status. It drifts if not refreshed — treat entries older than a few days as suspect and re-derive
from the source when on the Mac. **Refresh cadence:** update at `/grow` and `/dream`, same
as the handover. The Mac plan glob remains source of truth; this is the mobile shadow.

Legend: `=>` marks a pick-up point (decision / next step / verification owed).

---

## Live pick-up points (as of 2026-07-18)

**guacamayo** (this repo)
- `2026-07-17-feedback-loop.md` — EXECUTED. Phase 4 (/retro eval-gate) pending first real
  skill-change proposal to exercise end-to-end.
  => First `/retro` run that proposes a skill change — verifies the eval-gate path.
- `2026-07-17-review-sweep.md` — EXECUTED, acceptance criteria 1–4 pending.
  => First real `/review-sweep` from a FRESH session (new skill/agent defs load at session start).
- Rename puffin→guacamayo done except: GitHub remote + final commit + delete leftover `puffin/` copy.
  => On Ramsey (commits are always yours).

**ai-project-template**
- `2026-07-17-template-core-redesign.md` — IN PROGRESS (A0 + B1 + B2 done).
  => Next: A1 in a fresh session.
- `2026-07-17-evals-suite-port.md` — IN PROGRESS.
- `multi-agent-tooling-expansion.md` — missing `Status:` line (see feedback-loop open item).

**librarian**
- `2026-07-17-knowledge-compaction.md` — IN PROGRESS.
- `2026-07-17-learn-ai-ingest-guacamayo-loop.md` — IN PROGRESS.
- Akira rollout blocked: subagents hardcode `src/agents/*` paths, can't scan librarian's
  app/etl/tools layout.
  => Fix upstream: settings-driven scan roots in template scaffold, then re-pilot.

**listen-wiseer**
- Phases 1–2d COMPLETE (see CHANGELOG). `phase6_refactor.md` + `phase7a-exploration-tools.md` ACTIVE.
- Several phase plans (2e, 3a–d, 4a–b, 5a–c, 6) missing `Status:` lines.

**playground**
- `rag-latency-optimization.md` — baseline documented, experiments queued.

**contracts rollout** (cross-repo)
- Buyi confirmation interviews owed on all three SANYI.md files (drafted autonomously from CLAUDE.md rules).

---

## How mobile /wake uses this

1. Run the normal Phase 4 plan glob. If it returns results (Mac), use them — they're authoritative.
2. If it returns nothing (sandbox), read this file for cross-repo orientation instead.
3. Bodies of the plans referenced here won't be in the sandbox (git-ignored). To act on one,
   either work from the pointer + the repo's committed code, or continue on the Mac.
