/*
 * Live-turn transport: opens the backend SSE stream and parses its
 * `event: <type>` / `data: <json>` frames into typed StreamEvents
 * (`token`, `status`, `options`, `plan.updated`, ...) that the travel
 * store consumes to update the UI incrementally as the turn runs.
 * Aborts after a timeout (default 5 min); malformed frames are skipped
 * without killing the stream. REST wrappers live in travelService.
 *
 * Also hosts the protocol constants shared with the backend: the choice
 * prefix (must stay in sync, it short-circuits extract+router), the
 * subagent id -> human label for the live status block, and the
 * subagent id -> research-key mapping for the state panel.
 */
import type { ResearchKey, StreamEvent } from '../types';

// First line of the user message for UI button saves. Must stay
// in sync with SAVED_CHOICES_PREFIX in backend app/agents/tools/plan.py:
// the backend short-circuits extract+router on it.
export const SAVED_CHOICES_PREFIX = "I'll go with:";

// Subagent id -> human label for the live status block.
export const AGENT_LABELS: Record<string, string> = {  weather_agent: 'Weather',
  accommodation_agent: 'Accommodation',
  transportation_agent: 'Transportation',
  activities_agent: 'Activities',
  rental_cars_agent: 'Rental car'
};

// Subagent id -> right-column research key.
export const AGENT_RESEARCH_KEY: Record<string, ResearchKey> = {
  weather_agent: 'weather',
  accommodation_agent: 'accommodation',
  transportation_agent: 'transportation',
  activities_agent: 'activities',
  rental_cars_agent: 'rentalCar'
};

/** POST yielding parsed SSE events from a backend turn stream. */
export async function* postStream(url: string, body: unknown, timeoutMs = 300000): AsyncGenerator<StreamEvent> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: ctrl.signal
    });
    if (!res.ok || !res.body) throw new Error(`Stream failed: ${res.status}`);
    yield* readSSE(res.body);
  } finally {
    clearTimeout(timer);
  }
}

/** Parse `event: <type>\ndata: <json>\n\n` frames from a byte stream. */
export async function* readSSE(body: ReadableStream<Uint8Array>): AsyncGenerator<StreamEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const frame = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      let name = '';
      const dataLines: string[] = [];
      for (const line of frame.split('\n')) {
        if (line.startsWith('event:')) name = line.slice(6).trim();
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
      }
      if (!name) continue;
      if (name === 'done') {
        yield { type: 'done' };
        return;
      }
      try {
        yield { type: name, ...JSON.parse(dataLines.join('\n')) } as StreamEvent;
      } catch {
        // Skip malformed frames; the stream continues.
      }
    }
  }
  yield { type: 'done' };
}
