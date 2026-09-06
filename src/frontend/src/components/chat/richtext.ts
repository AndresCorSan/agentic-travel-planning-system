// Full markdown renderer for LLM replies: marked for parsing,
// DOMPurify for sanitizing (content comes from the LLM into v-html).
import DOMPurify from 'dompurify';
import { marked } from 'marked';

marked.setOptions({ breaks: true });

export function renderRich(text: string): string {
  return DOMPurify.sanitize(marked.parse(text) as string);
}
