import { spawn } from 'node:child_process';

/** Result of running a subprocess. */
export interface RunResult {
  code: number | null;
  stdout: string;
  stderr: string;
}

/**
 * Run a command with args (no shell — args are passed as a vector, so there is
 * no shell-injection surface). Never rejects; a failure to spawn is reported as
 * code -1 with the error in stderr. Optionally feed `input` to stdin.
 */
export function run(cmd: string, args: string[], input?: string): Promise<RunResult> {
  return new Promise((resolve) => {
    let child;
    try {
      child = spawn(cmd, args, { stdio: ['pipe', 'pipe', 'pipe'] });
    } catch (err) {
      resolve({ code: -1, stdout: '', stderr: (err as Error).message });
      return;
    }
    let stdout = '';
    let stderr = '';
    child.stdout?.on('data', (d) => (stdout += d));
    child.stderr?.on('data', (d) => (stderr += d));
    child.on('error', (err) => resolve({ code: -1, stdout, stderr: err.message }));
    child.on('close', (code) => resolve({ code, stdout, stderr }));
    if (input !== undefined) {
      child.stdin?.end(input);
    } else {
      child.stdin?.end();
    }
  });
}

/** True if a binary is found on PATH. Cached per binary. */
const whichCache = new Map<string, boolean>();
export async function hasBinary(name: string): Promise<boolean> {
  const cached = whichCache.get(name);
  if (cached !== undefined) return cached;
  const finder = process.platform === 'win32' ? 'where' : 'which';
  const { code } = await run(finder, [name]);
  const found = code === 0;
  whichCache.set(name, found);
  return found;
}

export function isMacOS(): boolean {
  return process.platform === 'darwin';
}
