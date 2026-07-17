import type { Config } from '../config/types.js';
import { createTtsEngine } from '../tts/factory.js';
import { logger } from '../util/log.js';
import { MacNotificationChannel } from './MacNotificationChannel.js';
import type { NotificationChannel } from './NotificationChannel.js';
import { VoiceChannel } from './VoiceChannel.js';

const log = logger('channels');

/**
 * Build the enabled channels, in the order listed in `config.channels`.
 * Adding a new channel (Pushover, ntfy, Slack, Discord) is a single `case`
 * here plus its class — the dispatcher and everything upstream are untouched.
 */
export function createChannels(config: Config): NotificationChannel[] {
  const channels: NotificationChannel[] = [];
  for (const name of config.channels) {
    switch (name) {
      case 'voice':
        if (config.voice.enabled) channels.push(new VoiceChannel(createTtsEngine(config.voice)));
        break;
      case 'macNotification':
        if (config.macNotification.enabled) channels.push(new MacNotificationChannel(config.macNotification));
        break;
      default:
        log.warn(`unknown channel "${name}" — skipping`);
    }
  }
  if (channels.length === 0) log.warn('no channels enabled; completions will be silent');
  return channels;
}
