# Model Pairing — skills, agents, sessions

*Principle: opening sessions default to fable (or opus if fable unavailable). Only
spawned agents with a complete, bounded plan get lower tiers — and performance is
observed to determine when to upgrade. Fan-out and extraction → haiku; bounded
execution with complete spec → sonnet; extended thinking + planning → fable;
judgment-dense / irreversible / identity work → opus-class.
/fast = same Opus, faster output — a latency lever, not a cost lever.*

**Fable** (Claude Sonnet 4.5 / `claude-sonnet-4-5-v2`) — the extended-thinking sonnet.
Sits between sonnet and opus: cheaper than opus with deeper reasoning via thinking
tokens. The preferred default for new sessions. Use via `--model claude-sonnet-4-5-v2`
or set `"model": "claude-sonnet-4-5-v2"` in settings.json when confirmed available.
Good candidates: complex migration analysis, multi-file refactors with tricky
dependencies, research synthesis with many inputs, most planning sessions.

**Current default**: `claude-opus-4-6` (settings.json). Fable (`claude-sonnet-4-5-v2`) is
not available as a Claude Code session model ID — use opus until fable becomes available.

Skills run in the invoking session's model — this table says **which session tier to
invoke them in** (and which model their sub-agents pin). Enforcement strength: agent-def
frontmatter > skill-text spawn instructions > this ref (session choice is Ramsey's).

## Global skills

| Tier | Skills | Why |
|------|--------|-----|
| **Opus-class** | `/plan`, `/research` (synthesis phases), `/code-review`, `/sanyi` (esp. audit), `/retro`, `/plan-refactor`, `/design-sprint`, `/scope-initiative`, `/define-milestones`, `/skill-creator`, `/mcp-builder` (design phases) | Verdicts, architecture, contract judgment, changes to the tooling itself — errors compound |
| **Fable** | `/workflow-review` (diff analysis on multi-file changes), research synthesis (many inputs), complex migration analysis, multi-file refactors with tricky dependencies | More reasoning than sonnet, cheaper than opus; extended thinking shines on "weigh N things" tasks |
| **Sonnet** | `/execute`, `/execute-tasks`, `/code-debug`, `/config-audit`, `/quick-pr`, `/doc-to-linear-tickets`, `/github-projects`, `/insights`, `/insights-analysis`, `/prototype`, `/compact-session`, `/review-sweep` level:1–2 | Plan is already made or task is bounded; needs competence, not maximal judgment |
| **Any / haiku-ok** | `/quick-commit`, `/parallel-research` (orchestration; its sub-agents are haiku by design), `/keybindings-help` | Mechanical or already delegating downward |

`/review-sweep` level:3 graduates to opus-class (full sanyi audit inside).

## Sub-agent spawns (pinned, not session-dependent)

| Agent / spawn | Model | Set where |
|---------------|-------|-----------|
| `akira-scan` batches | haiku | `~/.claude/agents/akira-scan.md` frontmatter |
| `parallel-research` fan-out | haiku | skill text |
| Explore lookups | haiku | Agent tool `model` param |
| Finding verification + report merge | session model | deliberate — cheap generate, narrow expensive verify (the 2026-07-17 false-positive catch is the proof) |

## Guacamayo lifecycle (repo-local skills)

| Tier | Skills | Why |
|------|--------|-----|
| **Opus-class, always** | `/synthesize`, `/dream` (transform pass) | Identity transforms; voice preservation is the most judgment-dense operation in the setup — cheap compression is how identity dies politely |
| **Any** | `/wake`, `/grow`, `/reflect`, `/intermission` | Read/append capture — no transforms by design |

## Rules of thumb

- Default session opens at **fable**. Escalate to **opus** when the task is judgment-dense,
  irreversible, or identity-transforming — not as a general fallback.
- Spawned agents with a defined plan: **haiku or sonnet** per task complexity. Observe;
  upgrade if the agent reframes rather than executes.
- Fan-out research batches (haiku agents) don't care what the parent session runs.
- /plan, /retro, /sanyi audit, /dream synthesis, /design-sprint → opus (judgment-dense).
- /execute runs in a FRESH session per item (plan doc as input) — never as a
  continuation of the planning session (~5k fresh context beats compacted-150k).
- Never let a sub-agent's confident output skip main-model verification — model choice
  changes cost, not the verification duty.
