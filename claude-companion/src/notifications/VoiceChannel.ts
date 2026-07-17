import type { TaskSummary } from '../models/events.js';
import type { TtsEngine } from '../tts/TtsEngine.js';
import { logger } from '../util/log.js';
import type { NotificationChannel } from './NotificationChannel.js';

const log = logger('channel:voice');

/**
 * Speaks the summary aloud. Thin adapter: all engine specifics live behind
 * {@link TtsEngine}, so this channel is unchanged when the engine swaps.
 */
export class VoiceChannel implements NotificationChannel {
  readonly name = 'voice';

  constructor(private readonly engine: TtsEngine) {}

  async notify(summary: TaskSummary): Promise<void> {
    log.debug(`speaking (${this.engine.name}): ${summary.speech}`);
    await this.engine.speak(summary.speech);
  }
}
