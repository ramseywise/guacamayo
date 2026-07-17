import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import type { Config } from './types.js';

/**
 * Default configuration. The app is fully functional with these alone — a
 * config file only overrides what it names.
 */
export const DEFAULT_CONFIG: Config = {
  server: { host: '127.0.0.1', port: 4599 },
  channels: ['macNotification', 'voice'],
  notifyOn: 'all',
  quietHours: {
    enabled: false,
    start: '22:00',
    end: '08:00',
    suppress: 'voice',
  },
  voice: {
    enabled: true,
    engine: 'say',
    sayVoice: null,
    rate: null,
  },
  macNotification: {
    enabled: true,
    terminalApp: 'Terminal',
    successSound: 'Glass',
    failureSound: 'Basso',
  },
};

/** Default location of the on-disk config, overridable with CLAUDE_COMPANION_CONFIG. */
export function defaultConfigPath(): string {
  return (
    process.env.CLAUDE_COMPANION_CONFIG ??
    join(homedir(), '.config', 'claude-companion', 'config.json')
  );
}

/** Shallow-per-section merge: a config file section replaces only the keys it sets. */
function mergeConfig(base: Config, override: Partial<Config>): Config {
  return {
    server: { ...base.server, ...override.server },
    channels: override.channels ?? base.channels,
    notifyOn: override.notifyOn ?? base.notifyOn,
    quietHours: { ...base.quietHours, ...override.quietHours },
    voice: { ...base.voice, ...override.voice },
    macNotification: { ...base.macNotification, ...override.macNotification },
  };
}

/**
 * Load config from disk (if present) merged over defaults. A missing file is
 * fine and expected; a malformed file throws so the user notices early.
 */
export function loadConfig(path: string = defaultConfigPath()): Config {
  let parsed: Partial<Config> = {};
  let raw: string | undefined;
  try {
    raw = readFileSync(path, 'utf8');
  } catch {
    raw = undefined; // no file -> defaults only
  }
  if (raw !== undefined) {
    try {
      parsed = JSON.parse(raw) as Partial<Config>;
    } catch (err) {
      throw new Error(`Invalid config at ${path}: ${(err as Error).message}`);
    }
  }
  // Always start from a fresh copy of defaults (never mutate the singleton),
  // and always apply env overrides regardless of whether a file was present.
  const merged = mergeConfig(DEFAULT_CONFIG, parsed);
  applyEnvOverrides(merged);
  return merged;
}

/** A few high-value env overrides, handy for quick experiments and hooks. */
function applyEnvOverrides(config: Config): void {
  const port = process.env.CLAUDE_COMPANION_PORT;
  if (port && Number.isFinite(Number(port))) {
    config.server.port = Number(port);
  }
  const host = process.env.CLAUDE_COMPANION_HOST;
  if (host) config.server.host = host;
}
