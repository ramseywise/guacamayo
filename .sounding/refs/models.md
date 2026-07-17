# Model Pairing — skills, agents, sessions

*Principle: pay for judgment, not for reading. Fan-out and extraction → haiku;
workhorse execution → sonnet; judgment-dense / error-expensive / irreversible →
opus-class. /fast = same Opus, faster output — a latency lever, not a cost lever.*

Skills run in the invoking session's model — this table says **which session tier to
invoke them in** (and which model their sub-agents pin). Enforcement strength: agent-def
frontmatter > skill-text spawn instructions > this ref (session choice is Ramsey's).

## Global skills

| Tier | Skills | Why |
|------|--------|-----|
| **Opus-class** | `/plan`, `/research` (synthesis phases), `/code-review`, `/review-pr`, `/sanyi` (esp. audit), `/retro`, `/plan-refactor`, `/design-sprint`, `/scope-initiative`, `/define-milestones`, `/skill-creator`, `/mcp-builder` (design phases) | Verdicts, architecture, contract judgment, changes to the tooling itself — errors compound |
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

- Session about to run /plan, /retro, /sanyi audit, or /synthesize → start it opus.
- Routine sweep/execute day → sonnet session is fine; the pinned haiku fan-outs don't care.
- /execute runs in a FRESH sonnet session per item (plan doc as input) — never as a
  continuation of the opus planning session (~5k fresh context beats compacted-150k;
  /insights 2026-07-17: /execute was 12% of usage, mostly at bloated context).
- Never let a sub-agent's confident output skip main-model verification — model choice
  changes cost, not the verification duty.
