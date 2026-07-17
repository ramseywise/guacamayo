import { createServer, type Server, type IncomingMessage, type ServerResponse } from 'node:http';
import type { RawEvent, EventKind } from '../models/events.js';
import type { ServerConfig } from '../config/types.js';
import { logger } from '../util/log.js';
import type { EmitFn, Source } from './Source.js';

const log = logger('hook-server');

/**
 * The primary Source: a tiny HTTP endpoint on localhost that Claude Code hooks
 * POST to. This is the recommended monitoring strategy (see README): hooks are
 * configuration, not a modification of Claude Code, and they hand us a
 * structured payload — including the transcript path — instead of forcing us to
 * scrape terminal output.
 *
 * Bind is localhost-only; the payload is trusted local input.
 */
export class HookServer implements Source {
  readonly name = 'claude-code-hooks';
  private server?: Server;

  constructor(private readonly config: ServerConfig) {}

  start(emit: EmitFn): Promise<void> {
    return new Promise((resolve, reject) => {
      this.server = createServer((req, res) => this.handle(req, res, emit));
      this.server.on('error', reject);
      this.server.listen(this.config.port, this.config.host, () => {
        log.info(`listening on http://${this.config.host}:${this.config.port}/hook`);
        resolve();
      });
    });
  }

  stop(): Promise<void> {
    return new Promise((resolve) => {
      if (!this.server) return resolve();
      this.server.close(() => resolve());
    });
  }

  private handle(req: IncomingMessage, res: ServerResponse, emit: EmitFn): void {
    if (req.method === 'GET' && req.url === '/health') {
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end('{"ok":true}');
      return;
    }
    if (req.method !== 'POST' || !req.url?.startsWith('/hook')) {
      res.writeHead(404);
      res.end();
      return;
    }

    let body = '';
    let tooBig = false;
    req.on('data', (chunk) => {
      body += chunk;
      if (body.length > 1_000_000) {
        tooBig = true;
        req.destroy();
      }
    });
    req.on('end', () => {
      if (tooBig) return;
      try {
        const event = this.normalize(body);
        emit(event);
        res.writeHead(200, { 'content-type': 'application/json' });
        res.end('{"ok":true}');
      } catch (err) {
        log.warn(`bad hook payload: ${(err as Error).message}`);
        res.writeHead(400, { 'content-type': 'application/json' });
        res.end('{"ok":false}');
      }
    });
  }

  /** Map a Claude Code hook payload onto our normalized RawEvent. */
  private normalize(body: string): RawEvent {
    const payload = (body ? JSON.parse(body) : {}) as Record<string, unknown>;
    const hookName = String(payload['hook_event_name'] ?? '');
    return {
      source: 'claude-code',
      kind: mapKind(hookName),
      timestamp: Date.now(),
      sessionId: str(payload['session_id']),
      cwd: str(payload['cwd']),
      transcriptPath: str(payload['transcript_path']),
      message: str(payload['message']),
      taskName: str(payload['task_name']),
      raw: payload,
    };
  }
}

function mapKind(hookName: string): EventKind {
  switch (hookName) {
    case 'Stop':
      return 'task-complete';
    case 'SubagentStop':
      return 'subagent-complete';
    case 'Notification':
      return 'needs-input';
    default:
      return 'custom';
  }
}

function str(value: unknown): string | undefined {
  return typeof value === 'string' && value.length > 0 ? value : undefined;
}
