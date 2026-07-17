import type { RawEvent, TaskSummary } from '../models/events.js';

/**
 * Turns a {@link RawEvent} into a {@link TaskSummary}. The MVP ships a
 * heuristic (no-LLM) implementation; an LLM-backed summarizer can be swapped in
 * behind this interface without touching sources or channels.
 */
export interface Summarizer {
  summarize(event: RawEvent): Promise<TaskSummary>;
}
