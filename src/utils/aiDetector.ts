import { Language } from '../types';

/** File-extension UI validation only. The actual CodeBERT tokenizer and AI
 * classification always run on the backend; the browser must never invent
 * an AI probability or reject files using a different approximate tokenizer. */
export const EXT_TO_LANG: Record<string, Language> = {
  '.c': 'c',
  '.java': 'java',
  '.py': 'python',
};
