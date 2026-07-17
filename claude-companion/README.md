# Claude Companion

A quiet macOS companion for Claude Code. Launch long-running coding tasks, walk
away, and let the companion **notice when work finishes**, **speak a concise
summary**, and **post a native notification** you can click to jump back to your
terminal.

> "The retrieval refactor completed successfully. Four files changed. All tests
> passed. Ready for review."

Design goal: **stay out of the way until you need to make a decision.** No
dashboard, no window — a background listener that talks only when something
finishes.

---

## Table of contents

1. [Architecture](#architecture)
2. [How completion is detected — tradeoffs](#how-completion-is-detected--the-tradeoffs)
3. [Quick start](#quick-start)
4. [Milestones: build and test incrementally](#milestones-build-and-test-incrementally)
5. [Configuration](#configuration)
6. [Extending it](#extending-it-plugins)
7. [Tool-agnostic by design](#tool-agnostic-by-design)
8. [Project layout](#project-layout)

---

## Architecture

The app is a small, one-directional pipeline. Everything downstream of a
**Source** speaks a normalized vocabulary (`RawEvent`, `TaskSummary`), never
Claude Code internals — that is what keeps each stage swappable.

```
                         ┌────────────────────────────────────────────┐
  Claude Code hooks ───► │ Source        normalize → RawEvent          │
  (Stop / Subagent /     │  HookServer                                  │
   Notification)         └───────────────┬──────────────────────────────┘
                                         │ RawEvent
                                         ▼
                         ┌────────────────────────────────────────────┐
                         │ Summarizer    read transcript → facts →      │
                         │  Heuristic     TaskSummary (speech + detail) │
                         └───────────────┬──────────────────────────────┘
                                         │ TaskSummary
                                         ▼
                         ┌────────────────────────────────────────────┐
                         │ Dispatcher    policy · quiet hours · queue   │
                         └───────┬─────────────────────┬────────────────┘
                                 │                     │
                         ┌───────▼───────┐     ┌───────▼───────┐
                         │ VoiceChannel  │     │ MacNotifyChan │   … Pushover,
                         │  → TtsEngine  │     │  → say/tn     │     ntfy, Slack
                         │    → `say`    │     │               │     (future)
                         └───────────────┘     └───────────────┘
```

**Four seams, each a single file to add to:**

| Seam | Interface | MVP implementation | Swap in later |
|------|-----------|--------------------|---------------|
| Source | `monitor/Source.ts` | `HookServer` | stdout tail, websocket, other agent CLIs |
| Summarizer | `summarizer/Summarizer.ts` | `HeuristicSummarizer` | LLM summarizer |
| TTS engine | `tts/TtsEngine.ts` | `SayTtsEngine` | ElevenLabs, OpenAI TTS |
| Channel | `notifications/NotificationChannel.ts` | `VoiceChannel`, `MacNotificationChannel` | Pushover, ntfy.sh, Slack, Discord |

**Zero runtime dependencies.** Everything uses Node built-ins (`http`,
`child_process`, `fs`). TypeScript is a build-time dependency only.

---

## How completion is detected — the tradeoffs

This is the central design decision, so it is worth being explicit. Four
approaches were considered:

### 1. Claude Code hooks → local HTTP endpoint  ✅ *recommended, and what ships*

Claude Code fires **hooks** on lifecycle events — `Stop` (the main agent
finished responding), `SubagentStop` (a spawned agent finished), and
`Notification` (it needs permission or input). A hook is a shell command that
receives a JSON payload on stdin, including `session_id`, `cwd`, and
`transcript_path`. We register a one-line `curl` that POSTs that payload to a
localhost server the companion runs.

- **Pros:** Officially supported and stable. Structured payload — we get the
  transcript path for free, so summaries are rich. It's *configuration*, not a
  modification of Claude Code (satisfies "without modifying Claude Code"). Event
  driven — no polling, near-zero idle cost. Naturally covers subagents.
- **Cons:** Requires a one-time edit to Claude Code's `settings.json`. The
  payload schema is Claude Code's, so a new source is needed for other tools
  (that's exactly what the Source seam is for). `Stop` fires at every turn
  boundary, so during active back-and-forth you'd get a ping per turn — mitigated
  by the `notifyOn` policy, quiet hours, and 2-second de-duplication, and a
  non-issue in the "away from desk" case where a turn *is* a completed task.

### 2. Terminal / PTY output scraping

Wrap Claude Code in a pseudo-terminal and watch stdout for "done" patterns.

- **Pros:** Truly tool-agnostic; no config changes.
- **Cons:** Fragile — ANSI codes, spinners, and streaming output make "is it
  actually finished?" genuinely hard. Any UI change breaks the parser. No clean
  structured facts. High effort for low reliability.

### 3. Transcript file watching

Tail the JSONL transcript under `~/.claude/projects/**` and infer completion from
the last entry.

- **Pros:** No config change; structured data; robust-ish.
- **Cons:** Depends on an internal file format and directory layout. "Finished"
  vs "mid-tool-call" must be inferred from `stop_reason`, which is more brittle
  than being *told* by a `Stop` hook. Good candidate for a **fallback Source**.

### 4. Process / CPU monitoring

Watch the `claude` process going idle.

- **Cons:** No content for a summary, easily fooled by a paused-but-thinking
  agent. Rejected.

### Recommendation

**Hooks (approach 1) as the primary Source, with the architecture open to
approach 3 as a zero-config fallback.** Hooks give the best
reliability-per-line-of-code, hand us structured data, and don't touch Claude
Code itself. The transcript reader we already need for summaries is reused
whether the event arrives by hook or by file-watch, so adding the fallback later
is cheap.

---

## Quick start

Requirements: **macOS** (for `say` and native notifications) and **Node ≥ 18**.
It also *runs* on Linux/CI — voice and notifications degrade to log lines, which
is how the test suite exercises the full pipeline anywhere.

```bash
cd claude-companion
npm install
npm run build

# 1. Start the listener (leave it running — a login item or tmux pane is ideal)
npm start

# 2. In another shell, print the hooks to add to Claude Code, and install them:
node dist/main.js print-hooks
```

Merge that `hooks` block into `~/.claude/settings.json` (or a project
`.claude/settings.json`). That's it — finish a task in Claude Code and the
companion speaks.

**Optional but recommended:** install `terminal-notifier` so clicking a
notification brings your terminal to the front:

```bash
brew install terminal-notifier
```

Without it, notifications still appear (via `osascript`) but aren't clickable —
an AppleScript-notification limitation, not ours.

---

## Milestones: build and test incrementally

Each milestone is independently runnable and testable.

### Milestone 1 — Summarize a transcript (no Claude Code needed)

The heuristic summarizer + transcript reader, exercised end-to-end against a
fixture. This is the core value and it's testable on any OS.

```bash
npm run build
node dist/main.js simulate examples/sample-transcript.jsonl --name "Retrieval refactor"
```

Expected:

```
outcome=success
speech: Retrieval refactor finished successfully. 4 files changed. All tests passed. Ready for review.
detail: 4 file(s) changed · tests passing
```

Try a blocked task:

```bash
node dist/main.js simulate --kind notification --name "Deploy" \
  --message "Approve production deploy before continuing?"
# → outcome=waiting; "Deploy is waiting for you. Approve production deploy before continuing?"
```

Run the unit tests (transcript parsing, summary outcomes, dispatch policy, quiet
hours):

```bash
npm test
```

### Milestone 2 — Voice + native notification

`simulate` already routes through the real channels. On macOS you'll **hear** the
summary and **see** a banner; off macOS you'll see the `(non-macOS) would speak`
/ `notify` log lines. To hear only voice or only notifications, edit `channels`
in your config.

Test different outcomes get different sounds by simulating a failing run (make a
transcript whose test output contains `FAIL` / `2 failed`).

### Milestone 3 — Live monitoring via the hook server

```bash
npm start                      # terminal A: the listener
```

```bash
# terminal B: pretend to be a Claude Code Stop hook
curl -sS -X POST http://127.0.0.1:4599/hook \
  -H 'content-type: application/json' \
  --data-binary '{"hook_event_name":"Stop","session_id":"demo","cwd":"/repo/myproj","transcript_path":"'"$PWD"'/examples/sample-transcript.jsonl"}'
```

Terminal A logs the event → summary → delivery, and (on macOS) speaks + notifies.
Health check: `curl http://127.0.0.1:4599/health`.

### Milestone 4 — Wire into real Claude Code

`node dist/main.js print-hooks` → merge into `~/.claude/settings.json` → run a
real task. Done.

---

## Configuration

Optional. Defaults work with zero config. To customize, copy the example to
`~/.config/claude-companion/config.json`:

```bash
mkdir -p ~/.config/claude-companion
cp examples/config.example.json ~/.config/claude-companion/config.json
```

| Key | Meaning |
|-----|---------|
| `server.host` / `server.port` | Where the hook endpoint listens (default `127.0.0.1:4599`). |
| `channels` | Active channels, in delivery order. |
| `notifyOn` | `all` · `failures` · `failures-and-input`. This is **"only interrupt me if tests fail."** |
| `quietHours` | `enabled`, `start`/`end` (`HH:MM`, may wrap midnight), `suppress` (`voice` or `all`). |
| `voice.sayVoice` / `voice.rate` | macOS `say` voice name and words-per-minute. |
| `macNotification.terminalApp` | App activated on click (`Terminal`, `iTerm`, `Ghostty`, …). |
| `macNotification.successSound` / `failureSound` | Distinct sounds per outcome. |

Env overrides: `CLAUDE_COMPANION_PORT`, `CLAUDE_COMPANION_HOST`,
`CLAUDE_COMPANION_CONFIG`, `CLAUDE_COMPANION_LOG` (`debug`/`info`/`warn`/`error`).

Inspect the resolved config any time: `node dist/main.js config`.

---

## Extending it (plugins)

**A new notification channel** (e.g. Pushover) — implement `NotificationChannel`,
register one `case` in `notifications/factory.ts`:

```ts
export class PushoverChannel implements NotificationChannel {
  readonly name = 'pushover';
  async notify(summary: TaskSummary): Promise<void> {
    // POST summary.title / summary.detail to the Pushover API
  }
}
```

**A new TTS engine** (e.g. ElevenLabs) — implement `TtsEngine`, register one
`case` in `tts/factory.ts`. `VoiceChannel` is unchanged.

**An LLM summarizer** — implement `Summarizer`, construct it in `app.ts`. Sources
and channels are unchanged; the transcript reader can feed it the facts.

Nothing else in the app knows or cares.

---

## Tool-agnostic by design

The monitor watches **structured events**, not Claude internals. A `RawEvent` is
the only thing a Source must produce, and it carries a generic `transcriptPath` /
`message`, not Claude-specific fields. To support **Codex CLI, Gemini CLI, Aider,
or a future agent**, add a Source that turns that tool's completion signal into a
`RawEvent` — any tool that can run a shell command on completion can already feed
the existing HTTP endpoint with a matching payload. Summarizer, dispatcher, and
all channels work unchanged.

---

## Project layout

```
src/
  main.ts                 CLI entry: run · print-hooks · simulate · config · help
  app.ts                  Composition root — wires sources → pipeline → channels
  pipeline.ts             Event → summarize → dispatch, with de-duplication
  models/events.ts        RawEvent, TaskSummary, SummaryFacts — the shared vocabulary
  config/                 Typed config + zero-config defaults + env overrides
  monitor/
    Source.ts             Source interface (the tool-agnostic seam)
    HookServer.ts         localhost HTTP endpoint for Claude Code hooks
    TranscriptReader.ts   JSONL transcript → facts (defensive parsing)
  summarizer/
    Summarizer.ts         interface
    HeuristicSummarizer.ts rule-based, no-LLM, instant
  tts/
    TtsEngine.ts          interface   ·  SayTtsEngine  ·  factory
  notifications/
    NotificationChannel.ts interface
    VoiceChannel.ts        MacNotificationChannel.ts
    NotificationDispatcher.ts  policy · quiet hours · serial queue
    factory.ts
  util/                   log.ts · exec.ts (no-shell subprocess + which)
tests/                    node:test suites (transcript, summarizer, dispatcher)
examples/                 sample-transcript.jsonl · config.example.json
```

## Design principles

- **Reliability over cleverness** — hooks over output-scraping; defensive
  transcript parsing that degrades to "unknown" instead of crashing; channels
  that log-and-continue on failure.
- **Simplicity** — zero runtime deps, small single-purpose files, a linear
  pipeline you can read top to bottom.
- **Extensibility** — four narrow interfaces, each with a factory; adding a
  channel/engine/source touches one file plus its registration.

## License

MIT
