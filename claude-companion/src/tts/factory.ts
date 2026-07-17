import type { VoiceConfig } from '../config/types.js';
import { SayTtsEngine } from './SayTtsEngine.js';
import type { TtsEngine } from './TtsEngine.js';

/**
 * Build the configured TTS engine. This is the single seam where a future
 * ElevenLabs / OpenAI engine plugs in:
 *
 *   case 'elevenlabs': return new ElevenLabsTtsEngine(config);
 */
export function createTtsEngine(config: VoiceConfig): TtsEngine {
  switch (config.engine) {
    case 'say':
      return new SayTtsEngine(config);
    default:
      throw new Error(`Unknown TTS engine: ${config.engine}`);
  }
}
