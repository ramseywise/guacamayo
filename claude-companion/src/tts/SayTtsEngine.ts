import type { VoiceConfig } from '../config/types.js';
import { logger } from '../util/log.js';
import { isMacOS, run } from '../util/exec.js';
import type { TtsEngine } from './TtsEngine.js';

const log = logger('tts:say');

/**
 * macOS native TTS via the `say` binary. Zero dependencies, always available on
 * macOS. Off macOS (CI, Linux dev) it degrades to logging what it *would* say,
 * so the rest of the pipeline stays testable everywhere.
 */
export class SayTtsEngine implements TtsEngine {
  readonly name = 'say';

  constructor(private readonly config: VoiceConfig) {}

  async speak(text: string): Promise<void> {
    if (!text.trim()) return;
    if (!isMacOS()) {
      log.info(`(non-macOS) would speak: "${text}"`);
      return;
    }
    const args: string[] = [];
    if (this.config.sayVoice) args.push('-v', this.config.sayVoice);
    if (this.config.rate) args.push('-r', String(this.config.rate));
    args.push(text);

    const { code, stderr } = await run('say', args);
    if (code !== 0) log.warn(`say exited ${code}: ${stderr.trim()}`);
  }
}
