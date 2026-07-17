import { readFileSync } from 'node:fs';
import type { SummaryFacts } from '../models/events.js';
import { logger } from '../util/log.js';

const log = logger('transcript');

/**
 * Reads a Claude Code JSONL transcript and distills it into {@link SummaryFacts}.
 *
 * The transcript format is an internal detail of Claude Code, so every access
 * here is defensive: unknown shapes are skipped, never thrown on. If the format
 * shifts we degrade to "unknown facts" rather than crashing — the summarizer
 * still falls back to the last assistant message.
 */

const EDIT_TOOLS = new Set([
  'Edit',
  'Write',
  'MultiEdit',
  'NotebookEdit',
  'create_or_update_file',
  'push_files',
]);

const TEST_COMMAND = /\b(npm (run )?test|yarn test|pnpm test|jest|vitest|pytest|go test|cargo test|mvn test|rspec|phpunit|ctest)\b/;
const COMMIT_COMMAND = /\bgit commit\b/;
const FAILURE_MARKER = /(\bFAIL\b|failed|failing|\berror\b|✗|✘|assertionerror|traceback)/i;
const PASS_MARKER = /(\bPASS\b|passed|passing|all tests? (pass|passed)|✓|✔|0 failures?)/i;
const FAIL_COUNT = /(\d+)\s+(?:tests? )?(?:failed|failing|failures?)/i;

interface ContentBlock {
  type?: string;
  text?: string;
  name?: string;
  input?: Record<string, unknown>;
  content?: unknown;
}

interface TranscriptLine {
  type?: string;
  message?: { role?: string; content?: ContentBlock[] | string; stop_reason?: string };
}

export interface TranscriptReadResult extends SummaryFacts {}

export function readTranscriptFacts(path: string): SummaryFacts {
  let raw: string;
  try {
    raw = readFileSync(path, 'utf8');
  } catch (err) {
    log.warn(`could not read transcript ${path}: ${(err as Error).message}`);
    return {};
  }
  return parseTranscript(raw);
}

/** Exposed for testing without touching the filesystem. */
export function parseTranscript(raw: string): SummaryFacts {
  const changedFiles = new Set<string>();
  let testsRan = false;
  let sawFailure = false;
  let sawPass = false;
  let failCount: number | undefined;
  let commitMade = false;
  let lastAssistantText: string | undefined;
  let errorHint: string | undefined;

  for (const line of raw.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    let entry: TranscriptLine;
    try {
      entry = JSON.parse(trimmed) as TranscriptLine;
    } catch {
      continue; // partial or non-JSON line
    }
    const blocks = asBlocks(entry.message?.content);

    for (const block of blocks) {
      if (block.type === 'text' && typeof block.text === 'string') {
        if (entry.message?.role === 'assistant' && block.text.trim()) {
          lastAssistantText = block.text.trim();
        }
      } else if (block.type === 'tool_use' && typeof block.name === 'string') {
        const filePath = block.input?.['file_path'] ?? block.input?.['path'] ?? block.input?.['notebook_path'];
        if (EDIT_TOOLS.has(block.name) && typeof filePath === 'string') {
          changedFiles.add(filePath);
        }
        if (block.name === 'Bash') {
          const cmd = String(block.input?.['command'] ?? '');
          if (TEST_COMMAND.test(cmd)) testsRan = true;
          if (COMMIT_COMMAND.test(cmd)) commitMade = true;
        }
      } else if (block.type === 'tool_result') {
        const text = blockText(block.content);
        if (text) {
          if (testsRan && FAILURE_MARKER.test(text)) {
            sawFailure = true;
            const m = text.match(FAIL_COUNT);
            if (m?.[1]) failCount = Number(m[1]);
            if (!errorHint) errorHint = firstMeaningfulLine(text);
          }
          if (testsRan && PASS_MARKER.test(text)) sawPass = true;
        }
      }
    }
  }

  const facts: SummaryFacts = {
    filesChanged: changedFiles.size || undefined,
    commitMade: commitMade || undefined,
    lastAssistantText,
  };
  if (testsRan) {
    facts.testsRan = true;
    if (sawFailure) {
      facts.testsPassed = false;
      facts.testsFailed = failCount;
      facts.errorHint = errorHint;
    } else if (sawPass) {
      facts.testsPassed = true;
    }
  }
  return facts;
}

function asBlocks(content: ContentBlock[] | string | undefined): ContentBlock[] {
  if (Array.isArray(content)) return content;
  if (typeof content === 'string') return [{ type: 'text', text: content }];
  return [];
}

/** Tool results carry either a string or an array of {type:'text',text}. */
function blockText(content: unknown): string {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content
      .map((c) => (c && typeof c === 'object' && 'text' in c ? String((c as ContentBlock).text ?? '') : ''))
      .join('\n');
  }
  return '';
}

function firstMeaningfulLine(text: string): string {
  const line = text
    .split('\n')
    .map((l) => l.trim())
    .find((l) => l.length > 0 && FAILURE_MARKER.test(l));
  if (!line) return '';
  return line.length > 120 ? `${line.slice(0, 117)}...` : line;
}
