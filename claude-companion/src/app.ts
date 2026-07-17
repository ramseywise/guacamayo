import type { Config } from './config/types.js';
import { HookServer } from './monitor/HookServer.js';
import type { Source } from './monitor/Source.js';
import { HeuristicSummarizer } from './summarizer/HeuristicSummarizer.js';
import { createChannels } from './notifications/factory.js';
import { NotificationDispatcher } from './notifications/NotificationDispatcher.js';
import { Pipeline } from './pipeline.js';
import { logger } from './util/log.js';

const log = logger('app');

/**
 * Wires the whole application from config and runs it until stopped. Kept small
 * and dependency-free so the composition is obvious: sources -> pipeline
 * (summarizer + dispatcher) -> channels.
 */
export class App {
  private readonly sources: Source[];
  private readonly pipeline: Pipeline;

  constructor(private readonly config: Config) {
    const summarizer = new HeuristicSummarizer();
    const channels = createChannels(config);
    const dispatcher = new NotificationDispatcher(channels, config);
    this.pipeline = new Pipeline(summarizer, dispatcher);
    this.sources = [new HookServer(config.server)];
  }

  async start(): Promise<void> {
    for (const source of this.sources) {
      await source.start(this.pipeline.handleEvent);
      log.info(`source started: ${source.name}`);
    }
    log.info('Claude Companion is listening. Leave it running; it will stay quiet until a task finishes.');
  }

  async stop(): Promise<void> {
    for (const source of this.sources) {
      await source.stop();
    }
    log.info('stopped.');
  }
}
