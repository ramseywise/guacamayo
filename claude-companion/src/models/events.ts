/**
 * Domain models shared across the whole pipeline.
 *
 * The pipeline is deliberately simple and one-directional:
 *
 *   Source  ->  RawEvent  ->  Summarizer  ->  TaskSummary  ->  Dispatcher  ->  Channel[]
 *
 * Everything downstream of a Source speaks in terms of these types, never in
 * terms of Claude Code internals. That is what keeps the monitor tool-agnostic:
 * a new agent CLI only has to produce a `RawEvent`.
 */

/** How a task ended, as far as we can tell. */
export type TaskOutcome = 'success' | 'failure' | 'waiting' | 'unknown';

/** The lifecycle moment a Source is reporting. */
export type EventKind =
  | 'task-complete' // main agent finished responding (Claude Code "Stop")
  | 'subagent-complete' // a spawned agent finished ("SubagentStop")
  | 'needs-input' // agent is blocked on a human ("Notification")
  | 'custom';

/**
 * A normalized event emitted by a Source. This is the ONLY thing a new
 * integration has to produce. Fields beyond `source`/`kind`/`timestamp` are
 * best-effort — the summarizer degrades gracefully when they are missing.
 */
export interface RawEvent {
  /** Identifier of the producing integration, e.g. "claude-code". */
  source: string;
  kind: EventKind;
  /** Epoch milliseconds when the event was observed. */
  timestamp: number;
  /** Stable id for the session/agent, used for de-duplication and grouping. */
  sessionId?: string;
  /** Human-facing task name if the source knows one. */
  taskName?: string;
  /** Working directory of the task, used as a fallback task name. */
  cwd?: string;
  /** Path to a transcript/log the summarizer can read for detail. */
  transcriptPath?: string;
  /** Free-text message (e.g. the permission prompt for a needs-input event). */
  message?: string;
  /** The original, unmodified payload — kept for debugging and future use. */
  raw?: unknown;
}

/** Structured facts extracted from a transcript. All optional and best-effort. */
export interface SummaryFacts {
  filesChanged?: number;
  testsRan?: boolean;
  testsPassed?: boolean;
  testsFailed?: number;
  commitMade?: boolean;
  needsInput?: boolean;
  /** The last thing the agent said, used as a fallback summary. */
  lastAssistantText?: string;
  /** Short error description if a failure was detected. */
  errorHint?: string;
}

/**
 * The product of summarization: everything a channel needs to render an alert,
 * in any medium. `speech` is tuned for TTS (<= ~30s); `detail` for a
 * notification body.
 */
export interface TaskSummary {
  /** Short task name for titles. */
  title: string;
  outcome: TaskOutcome;
  /** Spoken text, kept under ~30 seconds (~75 words). */
  speech: string;
  /** One or two line notification body. */
  detail: string;
  facts: SummaryFacts;
  /** The event this summary was derived from. */
  event: RawEvent;
}
