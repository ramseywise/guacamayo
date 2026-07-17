import { test } from 'node:test';
import assert from 'node:assert/strict';
import { matchesPolicy, withinQuietHours } from '../src/notifications/NotificationDispatcher.js';
import type { TaskSummary } from '../src/models/events.js';
import type { QuietHoursConfig } from '../src/config/types.js';

function summary(outcome: TaskSummary['outcome']): TaskSummary {
  return {
    title: 't',
    outcome,
    speech: '',
    detail: '',
    facts: {},
    event: { source: 'test', kind: 'task-complete', timestamp: 0 },
  };
}

test('policy "failures" only passes failures', () => {
  assert.equal(matchesPolicy('failures', summary('failure')), true);
  assert.equal(matchesPolicy('failures', summary('success')), false);
  assert.equal(matchesPolicy('failures', summary('waiting')), false);
});

test('policy "failures-and-input" passes failures and waiting', () => {
  assert.equal(matchesPolicy('failures-and-input', summary('waiting')), true);
  assert.equal(matchesPolicy('failures-and-input', summary('success')), false);
});

test('policy "all" passes everything', () => {
  for (const o of ['success', 'failure', 'waiting', 'unknown'] as const) {
    assert.equal(matchesPolicy('all', summary(o)), true);
  }
});

const quiet: QuietHoursConfig = { enabled: true, start: '22:00', end: '08:00', suppress: 'voice' };

test('quiet hours wrap past midnight', () => {
  assert.equal(withinQuietHours(quiet, new Date('2026-01-01T23:30:00')), true);
  assert.equal(withinQuietHours(quiet, new Date('2026-01-01T02:00:00')), true);
  assert.equal(withinQuietHours(quiet, new Date('2026-01-01T12:00:00')), false);
});

test('same-day quiet window', () => {
  const day: QuietHoursConfig = { enabled: true, start: '09:00', end: '17:00', suppress: 'all' };
  assert.equal(withinQuietHours(day, new Date('2026-01-01T10:00:00')), true);
  assert.equal(withinQuietHours(day, new Date('2026-01-01T18:00:00')), false);
});
