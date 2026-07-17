import type { RawEvent } from '../models/events.js';

/** Callback a Source uses to hand an event to the pipeline. */
export type EmitFn = (event: RawEvent) => void;

/**
 * A Source produces normalized {@link RawEvent}s from some external signal
 * (a hook callback, a log tail, a websocket, ...). This is the single
 * extension point for supporting new agent CLIs — implement `Source`, emit
 * `RawEvent`s, and the rest of the pipeline is unchanged.
 */
export interface Source {
  readonly name: string;
  /** Begin producing events. Resolves once the source is ready. */
  start(emit: EmitFn): Promise<void>;
  /** Stop producing events and release resources. */
  stop(): Promise<void>;
}
