import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseTranscript } from '../src/monitor/TranscriptReader.js';

function jsonl(lines: unknown[]): string {
  return lines.map((l) => JSON.stringify(l)).join('\n');
}

test('counts distinct changed files across edit tools', () => {
  const raw = jsonl([
    { type: 'assistant', message: { role: 'assistant', content: [
      { type: 'tool_use', name: 'Edit', input: { file_path: '/a.ts' } },
      { type: 'tool_use', name: 'Write', input: { file_path: '/b.ts' } },
      { type: 'tool_use', name: 'Edit', input: { file_path: '/a.ts' } },
    ] } },
  ]);
  const facts = parseTranscript(raw);
  assert.equal(facts.filesChanged, 2);
});

test('detects passing tests', () => {
  const raw = jsonl([
    { type: 'assistant', message: { role: 'assistant', content: [
      { type: 'tool_use', name: 'Bash', input: { command: 'npm test' } },
    ] } },
    { type: 'user', message: { role: 'user', content: [
      { type: 'tool_result', content: 'Test Suites: 3 passed, 3 total\nAll tests passed' },
    ] } },
  ]);
  const facts = parseTranscript(raw);
  assert.equal(facts.testsRan, true);
  assert.equal(facts.testsPassed, true);
});

test('detects failing tests with a count', () => {
  const raw = jsonl([
    { type: 'assistant', message: { role: 'assistant', content: [
      { type: 'tool_use', name: 'Bash', input: { command: 'pytest' } },
    ] } },
    { type: 'user', message: { role: 'user', content: [
      { type: 'tool_result', content: '2 failed, 5 passed\nFAIL test_thing' },
    ] } },
  ]);
  const facts = parseTranscript(raw);
  assert.equal(facts.testsPassed, false);
  assert.equal(facts.testsFailed, 2);
});

test('captures last assistant text and commit', () => {
  const raw = jsonl([
    { type: 'assistant', message: { role: 'assistant', content: [{ type: 'text', text: 'First.' }] } },
    { type: 'assistant', message: { role: 'assistant', content: [
      { type: 'tool_use', name: 'Bash', input: { command: 'git commit -m x' } },
    ] } },
    { type: 'assistant', message: { role: 'assistant', content: [{ type: 'text', text: 'Done at last.' }] } },
  ]);
  const facts = parseTranscript(raw);
  assert.equal(facts.lastAssistantText, 'Done at last.');
  assert.equal(facts.commitMade, true);
});

test('ignores malformed lines without throwing', () => {
  const raw = 'not json\n{"type":"assistant"}\n{bad';
  const facts = parseTranscript(raw);
  assert.equal(facts.filesChanged, undefined);
});
