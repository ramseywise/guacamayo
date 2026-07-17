---
name: project-legacy-scrub
description: "Former-employer reference scrub (2026-07-16) — decisions and remaining follow-ups"
metadata: 
  node_type: memory
  type: project
  originSessionId: 179f5f51-baa7-4216-983b-26a1eec59616
---

Scrubbed all former-employer references across workspace repos on 2026-07-16. The literal term→placeholder map lives ONLY in `~/.claude/scripts/scrub-terms.txt` (9 terms, e.g. vendor-a, client-a, product-a, corpus-a, rag-v1, tx-project, project-g) — use it with `grep -f` to re-verify repos; never write the original terms into repos or memory again.

Decisions made:
- playground/atlas: deleted wholly-legacy docs, genericized code/doc mentions ("backend API", "live/legacy KB domain" constants); project-g renamed to "playground"/"Atlas" where it meant the repo itself
- librarian `raw/`: untracked via .gitignore (844 staged removals) AND contents redacted in place with plain tokens; term-bearing filenames/dirs renamed to match manifest
- librarian `wiki/`: tracked, redacted with placeholder tokens; wiki/private client notes deleted earlier (were gitignored — not recoverable), 5 project-g files kept but renamed+redacted
- ~/.claude: old session transcripts + file-history redacted; memory redacted; current session (179f5f51) left untouched — ages out

Open follow-ups:
- All scrub changes uncommitted — user reviews and commits per repo
- **Pushed GitHub history of public librarian repo still contains pre-scrub raw/ and wiki** — only `git filter-repo` + force push purges; user aware, their call
- 3 playground `.env.example` files blocked by permissions — user edits by hand; lg_agent one must rename its MCP URL env vars to MCP_BACKEND_SSE_URL/MCP_BACKEND_API_URL (terraform already renamed)
- `github/_archived/` dir outside workspace still carries the vendor name
- Current session's transcript + file-history in ~/.claude contain terms until cleanup ages them out

Next planned work (agreed): L1 knowledge-digest pilot — distill Python/generative-ai into Python/.claude/docs/knowledge/*.md, then librarian `make scrape-docs` + targeted /ingest; later: wiki taxonomy branches (ml/, data-eng/, analytics/), cartographer L4 code-level indexing (see [[project_librarian_dssg_extension]]).
