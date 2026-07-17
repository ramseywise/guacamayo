import { basename } from 'node:path';
import type { RawEvent, SummaryFacts, TaskOutcome, TaskSummary } from '../models/events.js';
import { readTranscriptFacts } from '../monitor/TranscriptReader.js';
import type { Summarizer } from './Summarizer.js';

/** Roughly 75 words ≈ 30 seconds of speech at a normal rate. */
const MAX_SPEECH_WORDS = 75;

/**
 * Rule-based summarizer. Reads the transcript facts and composes a short spoken
 * summary and a notification detail line. No network, no LLM — deterministic and
 * instant, which is exactly what the "stay out of the way" MVP wants.
 */
export class HeuristicSummarizer implements Summarizer {
  async summarize(event: RawEvent): Promise<TaskSummary> {
    const facts = event.transcriptPath ? readTranscriptFacts(event.transcriptPath) : {};
    if (event.kind === 'needs-input') facts.needsInput = true;

    const title = taskTitle(event);
    const outcome = deriveOutcome(event, facts);
    const speech = clampWords(buildSpeech(title, outcome, facts, event), MAX_SPEECH_WORDS);
    const detail = buildDetail(outcome, facts, event);

    return { title, outcome, speech, detail, facts, event };
  }
}

function taskTitle(event: RawEvent): string {
  if (event.taskName) return event.taskName;
  if (event.cwd) return basename(event.cwd);
  return 'Claude Code task';
}

function deriveOutcome(event: RawEvent, facts: SummaryFacts): TaskOutcome {
  if (event.kind === 'needs-input' || facts.needsInput) return 'waiting';
  if (facts.testsRan && facts.testsPassed === false) return 'failure';
  if (facts.errorHint) return 'failure';
  // Test pass, or edits/commit with no failures, reads as success.
  if (facts.testsPassed === true || facts.filesChanged || facts.commitMade) return 'success';
  return event.kind === 'task-complete' || event.kind === 'subagent-complete'
    ? 'success'
    : 'unknown';
}

function buildSpeech(
  title: string,
  outcome: TaskOutcome,
  facts: SummaryFacts,
  event: RawEvent,
): string {
  const parts: string[] = [];
  const subject = event.kind === 'subagent-complete' ? `The ${title} agent` : title;

  switch (outcome) {
    case 'success':
      parts.push(`${subject} finished successfully.`);
      break;
    case 'failure':
      parts.push(`${subject} finished with problems.`);
      break;
    case 'waiting':
      parts.push(`${subject} is waiting for you.`);
      break;
    default:
      parts.push(`${subject} finished.`);
  }

  if (facts.filesChanged) {
    parts.push(`${facts.filesChanged} file${facts.filesChanged === 1 ? '' : 's'} changed.`);
  }
  if (facts.testsPassed === true) parts.push('All tests passed.');
  else if (facts.testsPassed === false) {
    parts.push(
      facts.testsFailed
        ? `${facts.testsFailed} test${facts.testsFailed === 1 ? '' : 's'} failing.`
        : 'Some tests are failing.',
    );
  }
  if (facts.commitMade) parts.push('Changes were committed.');

  if (outcome === 'waiting') {
    parts.push(event.message ? shorten(event.message, 20) : 'It needs your input before continuing.');
  } else if (outcome === 'success') {
    parts.push('Ready for review.');
  }

  return parts.join(' ');
}

function buildDetail(outcome: TaskOutcome, facts: SummaryFacts, event: RawEvent): string {
  const bits: string[] = [];
  if (facts.filesChanged) bits.push(`${facts.filesChanged} file(s) changed`);
  if (facts.testsPassed === true) bits.push('tests passing');
  if (facts.testsPassed === false) bits.push(facts.testsFailed ? `${facts.testsFailed} failing` : 'tests failing');
  if (facts.commitMade) bits.push('committed');
  if (outcome === 'waiting' && event.message) bits.push(shorten(event.message, 16));
  if (bits.length === 0 && facts.lastAssistantText) return shorten(facts.lastAssistantText, 24);
  return bits.join(' · ') || outcomeLabel(outcome);
}

function outcomeLabel(outcome: TaskOutcome): string {
  return { success: 'Completed', failure: 'Failed', waiting: 'Waiting for input', unknown: 'Finished' }[outcome];
}

function shorten(text: string, maxWords: number): string {
  const words = text.replace(/\s+/g, ' ').trim().split(' ');
  return words.length <= maxWords ? words.join(' ') : `${words.slice(0, maxWords).join(' ')}…`;
}

function clampWords(text: string, maxWords: number): string {
  const words = text.trim().split(/\s+/);
  if (words.length <= maxWords) return text;
  return `${words.slice(0, maxWords).join(' ')}.`;
}
