/** Minimal leveled logger. No dependency, timestamps, one line per event. */

type Level = 'debug' | 'info' | 'warn' | 'error';

const LEVELS: Record<Level, number> = { debug: 10, info: 20, warn: 30, error: 40 };

function threshold(): number {
  const env = (process.env.CLAUDE_COMPANION_LOG ?? 'info').toLowerCase();
  return LEVELS[env as Level] ?? LEVELS.info;
}

function emit(level: Level, scope: string, msg: string): void {
  if (LEVELS[level] < threshold()) return;
  const ts = new Date().toISOString();
  const line = `${ts} ${level.toUpperCase().padEnd(5)} [${scope}] ${msg}`;
  if (level === 'error' || level === 'warn') console.error(line);
  else console.log(line);
}

export function logger(scope: string) {
  return {
    debug: (msg: string) => emit('debug', scope, msg),
    info: (msg: string) => emit('info', scope, msg),
    warn: (msg: string) => emit('warn', scope, msg),
    error: (msg: string) => emit('error', scope, msg),
  };
}
