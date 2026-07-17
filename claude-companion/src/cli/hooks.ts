import type { Config } from '../config/types.js';

/**
 * Produce the Claude Code `settings.json` hooks block that feeds this app.
 *
 * Each hook is a one-line `curl` that POSTs the hook's JSON payload (delivered
 * on stdin) to our local server. `--data-binary @-` forwards stdin verbatim;
 * `-m 2` bounds the hook so it can never stall Claude Code; `|| true` makes the
 * hook non-fatal if the companion isn't running.
 */
export function buildHooksSnippet(config: Config): string {
  const url = `http://${config.server.host}:${config.server.port}/hook`;
  const cmd = `curl -sS -m 2 -X POST ${url} -H 'content-type: application/json' --data-binary @- || true`;
  const hooks = {
    hooks: {
      Stop: [{ hooks: [{ type: 'command', command: cmd }] }],
      SubagentStop: [{ hooks: [{ type: 'command', command: cmd }] }],
      Notification: [{ hooks: [{ type: 'command', command: cmd }] }],
    },
  };
  return JSON.stringify(hooks, null, 2);
}
