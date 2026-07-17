/** Configuration types. Every field has a default (see `config.ts`) so the app
 *  runs with no config file at all. */

export type NotifyPolicy =
  | 'all' // notify on every completion
  | 'failures' // only failures
  | 'failures-and-input'; // failures and "needs input"

/** What quiet hours suppress. */
export type QuietSuppress = 'voice' | 'all';

export interface ServerConfig {
  host: string;
  port: number;
}

export interface QuietHoursConfig {
  enabled: boolean;
  /** 24h "HH:MM". Range may wrap past midnight (e.g. 22:00 -> 08:00). */
  start: string;
  end: string;
  suppress: QuietSuppress;
}

export interface VoiceConfig {
  enabled: boolean;
  /** TTS engine id. MVP ships "say"; others plug in via the factory. */
  engine: 'say';
  /** macOS `say` voice name (e.g. "Samantha"); null = system default. */
  sayVoice: string | null;
  /** Words per minute for `say` (e.g. 190); null = default. */
  rate: number | null;
}

export interface MacNotificationConfig {
  enabled: boolean;
  /** App to bring to the front when a notification is clicked. */
  terminalApp: string;
  /** Notification sound names (macOS system sounds). */
  successSound: string;
  failureSound: string;
}

export interface Config {
  server: ServerConfig;
  /** Which channels are active, in dispatch order. */
  channels: string[];
  notifyOn: NotifyPolicy;
  quietHours: QuietHoursConfig;
  voice: VoiceConfig;
  macNotification: MacNotificationConfig;
}
