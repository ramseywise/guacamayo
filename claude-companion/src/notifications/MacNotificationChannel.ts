import type { MacNotificationConfig } from '../config/types.js';
import type { TaskOutcome, TaskSummary } from '../models/events.js';
import { hasBinary, isMacOS, run } from '../util/exec.js';
import { logger } from '../util/log.js';
import type { NotificationChannel } from './NotificationChannel.js';

const log = logger('channel:macnotify');

/**
 * Native macOS notification.
 *
 * Two backends, picked at runtime:
 *  - `terminal-notifier` if installed — supports a click action, so clicking the
 *    banner brings the terminal to the front (and different sounds per outcome).
 *  - `osascript` otherwise — always present on macOS, shows the banner + sound
 *    but cannot run a click action (macOS limitation of AppleScript notifications).
 *
 * Off macOS it logs what it would show, keeping the pipeline testable.
 */
export class MacNotificationChannel implements NotificationChannel {
  readonly name = 'macNotification';
  private backend: 'terminal-notifier' | 'osascript' | 'log' | undefined;

  constructor(private readonly config: MacNotificationConfig) {}

  private async resolveBackend(): Promise<'terminal-notifier' | 'osascript' | 'log'> {
    if (this.backend) return this.backend;
    if (!isMacOS()) this.backend = 'log';
    else if (await hasBinary('terminal-notifier')) this.backend = 'terminal-notifier';
    else this.backend = 'osascript';
    return this.backend;
  }

  async notify(summary: TaskSummary): Promise<void> {
    const sound = this.soundFor(summary.outcome);
    const subtitle = outcomeSubtitle(summary.outcome);
    const backend = await this.resolveBackend();

    if (backend === 'log') {
      log.info(`(non-macOS) notify: [${summary.title}] ${subtitle} — ${summary.detail}`);
      return;
    }
    if (backend === 'terminal-notifier') {
      await this.viaTerminalNotifier(summary, subtitle, sound);
      return;
    }
    await this.viaOsascript(summary, subtitle, sound);
  }

  private async viaTerminalNotifier(summary: TaskSummary, subtitle: string, sound: string): Promise<void> {
    // -execute runs on click; bring the configured terminal app to the front.
    const activate = `osascript -e 'tell application "${this.config.terminalApp}" to activate'`;
    const { code, stderr } = await run('terminal-notifier', [
      '-title', `Claude · ${summary.title}`,
      '-subtitle', subtitle,
      '-message', summary.detail,
      '-sound', sound,
      '-execute', activate,
      '-group', `claude-companion-${summary.event.sessionId ?? 'default'}`,
    ]);
    if (code !== 0) log.warn(`terminal-notifier exited ${code}: ${stderr.trim()}`);
  }

  private async viaOsascript(summary: TaskSummary, subtitle: string, sound: string): Promise<void> {
    const script =
      `display notification "${esc(summary.detail)}"` +
      ` with title "${esc(`Claude · ${summary.title}`)}"` +
      ` subtitle "${esc(subtitle)}"` +
      ` sound name "${esc(sound)}"`;
    const { code, stderr } = await run('osascript', ['-e', script]);
    if (code !== 0) log.warn(`osascript exited ${code}: ${stderr.trim()}`);
  }

  private soundFor(outcome: TaskOutcome): string {
    return outcome === 'failure' ? this.config.failureSound : this.config.successSound;
  }
}

function outcomeSubtitle(outcome: TaskOutcome): string {
  switch (outcome) {
    case 'success':
      return '✅ Success';
    case 'failure':
      return '❌ Failed';
    case 'waiting':
      return '⏳ Needs input';
    default:
      return 'Finished';
  }
}

/** Escape a string for embedding in an AppleScript double-quoted literal. */
function esc(text: string): string {
  return text.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}
