import type { TaskSummary } from '../models/events.js';

/**
 * A delivery channel for a completed-task summary. This is the app's main
 * extension point: macOS notification and voice ship in the MVP; Pushover,
 * ntfy.sh, Slack, and Discord are future channels that implement this same
 * interface and register in the factory.
 *
 * A channel receives the whole {@link TaskSummary} and decides how to render it
 * (speak `speech`, show `title` + `detail`, POST a webhook, ...).
 */
export interface NotificationChannel {
  readonly name: string;
  /** Deliver the summary. Should resolve even on soft failure (log, don't throw). */
  notify(summary: TaskSummary): Promise<void>;
}
