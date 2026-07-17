# Vendored refs — mobile mirror of ~/.claude/refs/

*Why:* Cloud/mobile sandboxes clone this repo but not `~/.claude`, so the global refs
(`~/.claude/refs/*.md`) that Mac sessions read on demand are absent there. These are copies
of the few refs a mobile session most needs.

**Source of truth is `~/.claude/refs/`.** These are shadows — they drift. On the Mac, always
prefer the global originals. Refresh these copies at `/dream` (maintenance pass) if the
originals have changed.

Vendored: `models.md` (tier pairing — /wake exits reference it), `python.md`, `typescript.md`,
`logging.md`. Not vendored (Mac-only, too niche for mobile): langgraph, google-adk, adk-vercel,
ml, repo-security-setup.
