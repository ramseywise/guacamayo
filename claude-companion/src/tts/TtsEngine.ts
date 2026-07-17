/**
 * A text-to-speech engine. The MVP implements this with macOS `say`; swapping in
 * ElevenLabs or OpenAI TTS later means adding one class and a factory branch —
 * nothing else in the app changes.
 */
export interface TtsEngine {
  readonly name: string;
  /** Speak the text. Resolves when playback finishes (or is safely skipped). */
  speak(text: string): Promise<void>;
}
