#!/usr/bin/env node
import { App } from './app.js';
import { buildHooksSnippet } from './cli/hooks.js';
import { loadConfig } from './config/config.js';
import type { EventKind, RawEvent } from './models/events.js';
import { HeuristicSummarizer } from './summarizer/HeuristicSummarizer.js';
import { createChannels } from './notifications/factory.js';
import { NotificationDispatcher } from './notifications/NotificationDispatcher.js';
import { logger } from './util/log.js';

const log = logger('main');

async function main(): Promise<void> {
  const [command, ...rest] = process.argv.slice(2);
  const config = loadConfig();

  switch (command) {
    case undefined:
    case 'run':
      return runServer();
    case 'print-hooks':
      process.stdout.write(buildHooksSnippet(config) + '\n');
      return;
    case 'config':
      process.stdout.write(JSON.stringify(config, null, 2) + '\n');
      return;
    case 'simulate':
      return simulate(rest);
    case 'help':
    case '--help':
    case '-h':
      printHelp();
      return;
    default:
      log.error(`unknown command: ${command}`);
      printHelp();
      process.exitCode = 1;
  }
}

async function runServer(): Promise<void> {
  const app = new App(loadConfig());
  await app.start();
  const shutdown = async (signal: string) => {
    log.info(`received ${signal}, shutting down`);
    await app.stop();
    process.exit(0);
  };
  process.on('SIGINT', () => void shutdown('SIGINT'));
  process.on('SIGTERM', () => void shutdown('SIGTERM'));
}

/**
 * Feed one synthetic event through summarizer + dispatcher without needing
 * Claude Code or a running server. Great for testing on any platform.
 *
 *   claude-companion simulate <transcript.jsonl> [--kind stop|subagent|notification] [--name "My task"]
 */
async function simulate(args: string[]): Promise<void> {
  const config = loadConfig();
  const kindArg = valueOf(args, '--kind') ?? 'stop';
  const name = valueOf(args, '--name');
  const message = valueOf(args, '--message');
  const transcriptPath = positional(args);

  const event: RawEvent = {
    source: 'simulate',
    kind: kindToEventKind(kindArg),
    timestamp: Date.now(),
    sessionId: 'simulate',
    taskName: name,
    transcriptPath,
    message,
  };

  const summarizer = new HeuristicSummarizer();
  const summary = await summarizer.summarize(event);
  log.info(`outcome=${summary.outcome}`);
  log.info(`speech: ${summary.speech}`);
  log.info(`detail: ${summary.detail}`);

  const dispatcher = new NotificationDispatcher(createChannels(config), config);
  dispatcher.dispatch(summary);
  await dispatcher.flush();
}

function kindToEventKind(kind: string): EventKind {
  switch (kind) {
    case 'subagent':
      return 'subagent-complete';
    case 'notification':
      return 'needs-input';
    default:
      return 'task-complete';
  }
}

function valueOf(args: string[], flag: string): string | undefined {
  const i = args.indexOf(flag);
  return i >= 0 ? args[i + 1] : undefined;
}

/** First non-flag argument that isn't consumed as a flag's value. */
function positional(args: string[]): string | undefined {
  const KNOWN_FLAGS = ['--kind', '--name', '--message'];
  for (let i = 0; i < args.length; i++) {
    const arg = args[i]!;
    if (arg.startsWith('--')) {
      if (KNOWN_FLAGS.includes(arg)) i++; // skip this flag's value
      continue;
    }
    return arg;
  }
  return undefined;
}

function printHelp(): void {
  process.stdout.write(
    [
      'Claude Companion — quiet completion alerts for Claude Code',
      '',
      'Usage:',
      '  claude-companion [run]            Start the listener (default).',
      '  claude-companion print-hooks     Print the Claude Code hooks config to install.',
      '  claude-companion simulate <t>    Run one transcript through the pipeline.',
      '  claude-companion config          Print the resolved configuration.',
      '  claude-companion help            Show this help.',
      '',
      'Simulate flags:',
      '  --kind stop|subagent|notification   Event kind (default: stop).',
      '  --name "Task name"                  Override the task title.',
      '  --message "..."                     Message for a notification event.',
      '',
    ].join('\n'),
  );
}

void main();
