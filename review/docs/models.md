# Model Pairing — skills, agents, sessions

*Principle: opening sessions default to fable. Only spawned agents with a complete,
bounded plan get lower tiers — and performance is observed to determine when to upgrade.
Fan-out and extraction → haiku; bounded execution with complete spec → sonnet;
design, review, planning, and anything verdict-shaped → fable; opus is the spawn-tier
fallback when a fable session isn't warranted.
/fast = same Opus, faster output (available on 4.8/4.7) — a latency lever, not a cost lever.*

**Fable** (Claude Fable 5 / `claude-fable-5`) — Mythos-class tier, sits **above** opus
in capability. Now a real Claude Code session model ID; the session default is
`claude-fable-5[1m]` (1M context) in settings.json. The tier for design, review,
planning, research synthesis, and identity transforms.

**Opus** = `claude-opus-4-8` (bumped from 4.6, 2026-07-28). No longer the top tier —
use for spawned agents that need opus-class judgment without a fable session, or as
fallback when fable is unavailable.

Skills run in the invoking session's model — this table says **which session tier to
invoke them in** (and which model their sub-agents pin). Enforcement strength: agent-def
frontmatter > skill-text spawn instructions > this ref (session choice is Ramsey's).

## Global skills

| Tier | Skills | Why |
|------|--------|-----|
| **Fable** | `/workflow-plan`, `/workflow-research` (synthesis phases), `/workflow-review`, `/code-review`, `/workflow-retro`, `/sanyi` (esp. audit), `/design-sprint`, `/design-initiative`, `/design-prototype`, `/skill-creator`, `/mcp-builder` (design phases), multi-file refactors with tricky dependencies | Verdicts, architecture, design, contract judgment, changes to the tooling itself — errors compound; fable is now the top tier |
| **Opus (4.8)** | Fallback for any fable-tier skill when fable is unavailable | Same judgment class, one tier down |
| **Sonnet** | `/workflow-execute`, `/code-debug`, `/git-pr`, `/github-projects`, `/workflow-insights`, `/design-prototype` (spike execution), `/code-review` level:1–2 | Plan is already made or task is bounded; needs competence, not maximal judgment |
| **Any / haiku-ok** | `/git-commit`, `/workflow-research` fan-out mode (its sub-agents are haiku by design), `/keybindings-help` | Mechanical or already delegating downward |

`/code-review` level:3 graduates to fable (full sanyi audit inside).

## Sub-agent spawns (pinned, not session-dependent)

| Agent / spawn | Model | Set where |
|---------------|-------|-----------|
| `akira-scan` batches | haiku | `~/.claude/agents/akira-scan.md` frontmatter |
| `/workflow-research` fan-out | haiku | skill text |
| Explore lookups | haiku | Agent tool `model` param |
| Finding verification + report merge | session model | deliberate — cheap generate, narrow expensive verify (the 2026-07-17 false-positive catch is the proof) |

## Guacamayo lifecycle (repo-local skills)

| Tier | Skills | Why |
|------|--------|-----|
| **Fable, always** | `/dream` (synthesis/transform pass) | Identity transforms; voice preservation is the most judgment-dense operation in the setup — cheap compression is how identity dies politely |
| **Any** | `/wake`, `/grow` | Read/append capture — no transforms by design |

## Rules of thumb

- Default session opens at **fable** (`claude-fable-5[1m]`). There is no higher escalation
  tier — fable IS the judgment tier now; opus 4.8 is the step-down, not the step-up.
- Spawned agents with a defined plan: **haiku or sonnet** per task complexity. Observe;
  upgrade if the agent reframes rather than executes.
- Fan-out research batches (haiku agents) don't care what the parent session runs.
- /workflow-plan, /workflow-retro, /sanyi audit, /dream synthesis, /design-* → fable
  (judgment-dense).
- /workflow-execute runs in a FRESH session per item (plan doc as input) — never as a
  continuation of the planning session (~5k fresh context beats compacted-150k).
- Never let a sub-agent's confident output skip main-model verification — model choice
  changes cost, not the verification duty.
