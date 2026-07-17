import type { RawEvent } from './models/events.js';
import type { Summarizer } from './summarizer/Summarizer.js';
import type { NotificationDispatcher } from './notifications/NotificationDispatcher.js';
import { logger } from './util/log.js';

const log = logger('pipeline');

/**
 * Connects the three stages: an event arrives, gets summarized, gets dispatched.
 * Also de-duplicates rapid double-fires of the same event (some hooks can fire
 * more than once for a single logical completion).
 */
export class Pipeline {
  private readonly recent = new Map<string, number>();
  private static readonly DEDUP_WINDOW_MS = 2000;

  constructor(
    private readonly summarizer: Summarizer,
    private readonly dispatcher: NotificationDispatcher,
  ) {}

  handleEvent = async (event: RawEvent): Promise<void> => {
    if (this.isDuplicate(event)) {
      log.debug(`ignoring duplicate ${event.kind} for ${event.sessionId ?? 'unknown'}`);
      return;
    }
    log.info(`event: ${event.kind} from ${event.source} (${event.sessionId ?? 'no-session'})`);
    try {
      const summary = await this.summarizer.summarize(event);
      log.info(`summary: [${summary.outcome}] ${summary.speech}`);
      this.dispatcher.dispatch(summary);
    } catch (err) {
      log.error(`failed to handle event: ${(err as Error).message}`);
    }
  };

  private isDuplicate(event: RawEvent): boolean {
    const key = `${event.source}:${event.sessionId ?? ''}:${event.kind}`;
    const now = event.timestamp;
    const last = this.recent.get(key);
    this.recent.set(key, now);
    this.pruneRecent(now);
    return last !== undefined && now - last < Pipeline.DEDUP_WINDOW_MS;
  }

  private pruneRecent(now: number): void {
    for (const [key, ts] of this.recent) {
      if (now - ts > Pipeline.DEDUP_WINDOW_MS * 5) this.recent.delete(key);
    }
  }
}
