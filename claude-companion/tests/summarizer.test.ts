import { test } from 'node:test';
import assert from 'node:assert/strict';
import { HeuristicSummarizer } from '../src/summarizer/HeuristicSummarizer.js';
import type { RawEvent } from '../src/models/events.js';

const summarizer = new HeuristicSummarizer();

function event(partial: Partial<RawEvent>): RawEvent {
  return { source: 'test', kind: 'task-complete', timestamp: 0, ...partial };
}

test('task with no transcript still yields a success summary', async () => {
  const s = await summarizer.summarize(event({ taskName: 'Retrieval refactor' }));
  assert.equal(s.outcome, 'success');
  assert.match(s.speech, /Retrieval refactor finished successfully/);
});

test('needs-input event reads as waiting', async () => {
  const s = await summarizer.summarize(
    event({ kind: 'needs-input', taskName: 'Deploy', message: 'Approve production deploy?' }),
  );
  assert.equal(s.outcome, 'waiting');
  assert.match(s.speech, /waiting for you/i);
});

test('speech stays within the ~30s budget (<= 75 words)', async () => {
  const s = await summarizer.summarize(event({ taskName: 'Big task' }));
  assert.ok(s.speech.split(/\s+/).length <= 75);
});

test('subagent completion is phrased as an agent', async () => {
  const s = await summarizer.summarize(event({ kind: 'subagent-complete', taskName: 'search' }));
  assert.match(s.speech, /The search agent/);
});
