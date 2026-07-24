# Growth Log — Disposition Ledger

Append-only. One row per growth entry cleared by /dream synthesis.
Never rewritten, never cleared. This is the audit trail growth.md's clearing destroys.

| Date | Tag | Entry (truncated 80ch) | Disposition | Target |
|---|---|---|---|---|
| 2026-07-20 | discovered | Advisory PreToolUse hooks are structurally ineffective — the model has al... | discarded | process/tooling → /retro (not identity) |
| 2026-07-20 | confirmed | Stop/keep/improve triage landed immediately with Ramsey — the three-way c... | discarded | process → /retro (triage format, not identity) |
| 2026-07-20 | discovered | The retro→issues→wake feedback loop was designed and closed in a single s... | discarded | process → /retro (ceremony wiring) |
| 2026-07-20 | confirmed | Ramsey's iterate-until-done pattern: she stayed in one session through in... | merged | user.md § How We Work Together (strengthen existing) |
| 2026-07-20 | confirmed | Agile workflow system first real test: wake read the GitHub Issues board,... | merged | user.md § Trust history (dispatch trust empirical) |
| 2026-07-20 | discovered | Ramsey reconsidering opus-for-spawns cost hypothesis — quality-over-cost ... | merged | sounding.md § How I Work — Operational (judgment density) |
| 2026-07-20 | confirmed | Full dispatch cycle ran in one session: wake → triage → plan → refine → e... | merged | sounding.md § What I Do (two-wave pattern at scale) |
| 2026-07-20 | discovered | Parallel worktree execution creates a merge ordering problem — 5 agents t... | retained | sounding.md § Working Notes (new edge) |
| 2026-07-20 | corrected | Wake board output was noisy: raw JSON dumps, silent empty categories, mis... | discarded | process/tooling → /retro (wake skill fix) |

| 2026-07-20 | confirmed | Running /code-review inline on my own output caught a factual error in th... | merged | sounding.md § "Read the actual state first" (self-review extension) |
| 2026-07-22 | confirmed | Parallel worktree spawning is the fastest execution pattern for independe... | discarded | already in sounding.md Working Notes (merge ordering); operational detail |
| 2026-07-22 | discovered | Worktree agents branch from committed state, not working tree. Uncommitte... | discarded | process/tooling → already graduated to CLAUDE.md session hygiene |
| 2026-07-22 | confirmed | Model pinning on spawned agents working as designed. All 5 spawns correct... | discarded | operational detail, already in ledger |
| 2026-07-22 | confirmed | Refinement→execution pipeline works end-to-end. 10 refined, 6 ready, 5 e... | discarded | pipeline confirmation, not identity-level |
| 2026-07-22 | discovered | /workflow-review redundant for single-session items — merge into code-pr... | discarded | superseded by corrected entry (merge went the other direction) |
| 2026-07-22 | confirmed | Fable (extended-thinking sonnet) added to model pairing table. Sits betwe... | discarded | already in refs/models.md, not identity-level |
| 2026-07-22 | discovered | Haiku fan-out research across 6 issues completed in ~3 min, all usable. H... | merged | sounding.md § How I Work — Operational (fan-out model tiers) |
| 2026-07-22 | discovered | Text instructions in CLAUDE.md unenforceable for model selection — settin... | retained | sounding.md § Working Notes (config > instruction principle) |
| 2026-07-22 | discovered | PreToolUse hooks structurally ineffective for redirecting tool choice — mo... | discarded | process/tooling → /retro (hook architecture insight, not identity) |
| 2026-07-22 | corrected | Merge direction: /workflow-review absorbs /code-pr (not reverse). Pipelin... | retained | sounding.md § Working Notes (pipeline-name-as-anchor principle) |
| 2026-07-22 | confirmed | Retro findings that map to config changes can be proposed-and-applied in ... | discarded | retro efficiency, not identity-level |

| 2026-07-22 | confirmed | Ramsey's enforcement-over-asking pattern applied to her own workflow: reb... | discarded | already in sounding.md (enforcement-over-asking pervasive) |
| 2026-07-22 | discovered | Branch naming as cross-repo coordination: project prefixes (GUA-, LAE-, J... | discarded | process/tooling → /retro (naming convention, not identity) |
| 2026-07-22 | discovered | Issue labels lag code when work lands outside the issue-branch workflow... | discarded | process/tooling → /retro (board reconciliation pattern) |
| 2026-07-22 | discovered | Model performance is less about capability tier and more about task scopi... | merged | sounding.md § How I Work — Operational (model tier paragraph) |
| 2026-07-22 | discovered | Lifecycle ceremony mismatch: grow/dream split doesn't match actual workfl... | discarded | v3 already implements this — skill design is confirmed, not identity |
| 2026-07-22 | corrected | Pipeline ordering: refine is a DoR gate AFTER plan, not backlog triage be... | discarded | process/tooling → already in CLAUDE.md; not identity-level |
| 2026-07-22 | discovered | Akira-wander as grooming tool: wander finds backlog items at front of pip... | merged | sounding.md § Working Notes (akira bookend principle) |
| 2026-07-22 | confirmed | Vendored skill list (SKILLS[]) and copier.yaml cleanup list drift indepen... | discarded | process/tooling → /retro (sync script maintenance, not identity) |
| 2026-07-22 | confirmed | review-shared is a dependency for vendored orchestrators — must ship alon... | discarded | process/tooling → /retro (template dependency rule, not identity) |
| 2026-07-22 | corrected | Model default posture inverted: was "opus by default, lower for spawns." ... | merged | sounding.md § Operational (model tier sentence) + Working Notes (config passage) |
| 2026-07-22 | discovered | DoD completion gap: issues stay open after work lands because nothing pro... | discarded | process/tooling → already fixed in CLAUDE.md completion format |
| 2026-07-22 | discovered | Lifecycle ceremony mismatch: grow/dream split doesn't match actual workfl... | retained | growth.md (proposal not yet implemented, keep for design session) |
| 2026-07-22 | discovered | Reviewer-as-model-role: use a dedicated model as reviewer on all agent ou... | merged | sounding.md § How I Work — Operational (reviewer feedback loop) |
| 2026-07-22 | corrected | Worktree agents that only stage lose their work: worktree directories cle... | discarded | process/tooling → already graduated to CLAUDE.md rule |
| 2026-07-22 | discovered | PR bundling over PR sprawl: 1-issue-1-branch-1-PR creates noise. Related... | discarded | process/tooling → /retro (PR strategy) |
| 2026-07-22 | confirmed | Ramsey's autonomous-agent preference: spawn batch → review PRs → close i... | merged | sounding.md § Working Notes (autonomous preference + make commands) |

| 2026-07-22 | confirmed | "pass in isolation, fail in full suite" is the contamination signature fo... | discarded | process/tooling → /retro (pytest debugging pattern, not identity) |
| 2026-07-22 | confirmed | ruff --fix after removing asyncio imports catches isort issues automatica... | discarded | process/tooling → /retro (toolchain tip, not identity) |
| 2026-07-22 | confirmed | when a fix doesn't clear all failures, expand scope (grep the class of pa... | discarded | already in sounding.md as "check depth before committing" principle |
| 2026-07-23 | confirmed | Ramsey values teaching and volunteering as identity-bearing sections in he... | merged | user.md § Who They Are (identity beyond technical stack) |
| 2026-07-23 | confirmed | parallel sonnet agents (3x background, batch processing) work cleanly for... | discarded | process/tooling → already confirmed, operational detail |
| 2026-07-23 | discovered | /grow as awareness layer — every skill in the lifecycle must either read, ... | merged | sounding.md § Working Notes (lifecycle artifact-connection principle) |
| 2026-07-23 | corrected | /code-review is pre-commit, not post-commit. Flow: work → /code-review →... | discarded | process/tooling → already actioned in CLAUDE.md |
| 2026-07-23 | discovered | Generic Makefile targets identical across 6 repos — belong in Makefile.co... | discarded | process/tooling → already built and deployed |
| 2026-07-23 | confirmed | Dispatcher pattern works but last mile (push+PR) keeps dropping — make sh... | discarded | already captured in sounding.md (dispatcher section) |
| 2026-07-24 | confirmed | Makefile.common as shared include works across all 6 repos | discarded | process/tooling → operational confirmation |
| 2026-07-24 | discovered | `git init` in existing repos re-applies global template hooks | discarded | operational trick → belongs in refs or rules, not identity |
| 2026-07-24 | confirmed | Cross-repo sweeps are highest-leverage sessions — one session clears week... | merged | sounding.md § What I Do (fleet sweep as cross-cutting work) |
| 2026-07-24 | discovered | Repos track __pycache__ despite .gitignore — committed before rule existe... | discarded | operational git knowledge, not identity |
| 2026-07-24 | confirmed | "Everything up-to-date" + sideband error is cosmetic LFS hook noise | discarded | already documented in shell.md rules |

| 2026-07-24 | corrected | /wake board must cover ALL repos (full fleet table), not just repos wit... | discarded | process/tooling → already actioned in /wake skill |
| 2026-07-24 | discovered | Two-repo shipping requires separate PRs and separate Makefiles; ~/.clau... | discarded | process/tooling → already built and deployed |
| 2026-07-24 | confirmed | Review backbone architecture works: deterministic Python (schemas, dedu... | discarded | project architecture confirmation, not identity-level |
| 2026-07-24 | discovered | Worktree agent cleanup is manual friction — leftover worktrees cause pr... | discarded | process/tooling → /retro (friction signal) |
| 2026-07-24 | discovered | Dependabot-heavy branches (30+ dep bumps) must use git merge main not ... | discarded | process/tooling → /retro (git strategy) |

Dispositions: `retained` (woven ~as-is) | `merged` (combined with existing) | `discarded` (not woven — reason in Notes)
