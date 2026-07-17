import type { Config, NotifyPolicy, QuietHoursConfig } from '../config/types.js';
import type { TaskSummary } from '../models/events.js';
import { logger } from '../util/log.js';
import type { NotificationChannel } from './NotificationChannel.js';

const log = logger('dispatcher');

/** Injectable clock so quiet-hours logic is testable. */
export type Clock = () => Date;

/**
 * The policy + fan-out layer between summaries and channels. Responsibilities:
 *  - filter by `notifyOn` ("only interrupt me if tests fail")
 *  - apply quiet hours (suppress voice, or everything)
 *  - serialize delivery through a queue so simultaneous agent completions don't
 *    talk over each other or fire a burst of banners
 */
export class NotificationDispatcher {
  private readonly queue: TaskSummary[] = [];
  private draining = false;

  constructor(
    private readonly channels: NotificationChannel[],
    private readonly config: Config,
    private readonly now: Clock = () => new Date(),
  ) {}

  /** Enqueue a summary for delivery. Returns immediately; delivery is async. */
  dispatch(summary: TaskSummary): void {
    if (!this.passesPolicy(summary)) {
      log.debug(`suppressed by notifyOn=${this.config.notifyOn}: ${summary.title} (${summary.outcome})`);
      return;
    }
    this.queue.push(summary);
    void this.drain();
  }

  /** Resolves once the queue is empty — used for clean shutdown and tests. */
  async flush(): Promise<void> {
    while (this.draining || this.queue.length > 0) {
      await new Promise((r) => setTimeout(r, 25));
    }
  }

  private passesPolicy(summary: TaskSummary): boolean {
    return matchesPolicy(this.config.notifyOn, summary);
  }

  private async drain(): Promise<void> {
    if (this.draining) return;
    this.draining = true;
    try {
      while (this.queue.length > 0) {
        const summary = this.queue.shift()!;
        await this.deliver(summary);
      }
    } finally {
      this.draining = false;
    }
  }

  private async deliver(summary: TaskSummary): Promise<void> {
    const quiet = this.config.quietHours;
    const inQuiet = quiet.enabled && withinQuietHours(quiet, this.now());
    const silenceAll = inQuiet && quiet.suppress === 'all';
    if (silenceAll) {
      log.debug(`quiet hours: fully suppressed ${summary.title}`);
      return;
    }
    for (const channel of this.channels) {
      if (inQuiet && quiet.suppress === 'voice' && channel.name === 'voice') {
        log.debug('quiet hours: skipping voice channel');
        continue;
      }
      try {
        await channel.notify(summary);
      } catch (err) {
        log.warn(`channel ${channel.name} failed: ${(err as Error).message}`);
      }
    }
  }
}

/** Pure policy check, exported for testing. */
export function matchesPolicy(policy: NotifyPolicy, summary: TaskSummary): boolean {
  switch (policy) {
    case 'all':
      return true;
    case 'failures':
      return summary.outcome === 'failure';
    case 'failures-and-input':
      return summary.outcome === 'failure' || summary.outcome === 'waiting';
  }
}

/** Pure quiet-hours check (supports windows that wrap past midnight). */
export function withinQuietHours(config: QuietHoursConfig, now: Date): boolean {
  const start = toMinutes(config.start);
  const end = toMinutes(config.end);
  if (start === null || end === null) return false;
  const cur = now.getHours() * 60 + now.getMinutes();
  if (start === end) return false;
  if (start < end) return cur >= start && cur < end; // same-day window
  return cur >= start || cur < end; // wraps midnight
}

function toMinutes(hhmm: string): number | null {
  const m = /^(\d{1,2}):(\d{2})$/.exec(hhmm.trim());
  if (!m) return null;
  const h = Number(m[1]);
  const min = Number(m[2]);
  if (h > 23 || min > 59) return null;
  return h * 60 + min;
}
