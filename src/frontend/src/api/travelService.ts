import { api } from './client';
import { postStream } from './stream';
import type { StreamEvent } from '../types';
import {
  conversations,
  destinations,
  itineraryText,
  lisbonOptions,
  messages,
  savedPlans,
  weatherText
} from '../mocks/data';
import type {
  BudgetSummary,
  ChatMessage,
  Conversation,
  PlanUpdate,
  ResearchStatus,
  RequirementItem,
  SavedPlan
} from '../types';

// ---------------------------------------------------------------------------
// Mock implementation of the future FastAPI contract.
// UI code talks to these functions, never to mocks/ directly.
// Later: replace bodies with `api.get/post(...)` calls, keep signatures.
// ---------------------------------------------------------------------------

const delay = (ms = 700) => new Promise((r) => setTimeout(r, ms));

let msgCounter = 100;
const extraMessages: Record<string, ChatMessage> = {};

/** Live event stream for POST /conversations/{id}/messages (Fase B). */
export function streamMessage(conversationId: string, text: string): AsyncGenerator<StreamEvent> {
  const base = api.defaults.baseURL ?? '';
  return postStream(`${base}/conversations/${conversationId}/messages`, { message: text });
}

/** Save UI button selections deterministically; returns saved labels + plan. */
export async function saveChoices(
  conversationId: string,
  choices: { category: string; option_id: string }[]
): Promise<{ saved: string[]; plan: PlanUpdate }> {
  const base = api.defaults.baseURL ?? '';
  const res = await api.post(`${base}/conversations/${conversationId}/choices`, { choices });
  return res.data;
}

/** Local-only placeholder shown instantly while the reply is being generated. */
export function createPendingUser(text: string): ChatMessage {
  return {
    id: `p${++msgCounter}`,
    role: 'user',
    kind: 'text',
    text,
    createdAt: new Date().toISOString()
  };
}

export async function listConversations(): Promise<Conversation[]> {
  return [...conversations];
}

export async function getMessages(ids: string[]): Promise<ChatMessage[]> {
  return ids.map((id) => extraMessages[id] ?? messages[id]).filter(Boolean);
}

export async function listSavedPlans(): Promise<SavedPlan[]> {
  return [...savedPlans];
}

export interface MockSendResult {
  user: ChatMessage;
  replies: ChatMessage[];
  destinationChosen?: string;
}

export async function sendMessage(conversationId: string, text: string): Promise<MockSendResult> {
  if (import.meta.env.VITE_USE_BACKEND === 'true') {
    const user: ChatMessage = {
      id: `u${++msgCounter}`,
      role: 'user',
      kind: 'text',
      text,
      createdAt: new Date().toISOString()
    };
    const { data } = await api.post(`/conversations/${conversationId}/messages`, { message: text }, { timeout: 300000 });
    const replies: ChatMessage[] = data.replies.map((r: { text: string }) => ({
      id: `a${++msgCounter}`,
      role: 'assistant',
      kind: 'text',
      text: r.text,
      createdAt: new Date().toISOString()
    }));
    for (const m of [user, ...replies]) extraMessages[m.id] = m;
    void conversationId;
    return { user, replies };
  }
  await delay();
  const user: ChatMessage = {
    id: `u${++msgCounter}`,
    role: 'user',
    kind: 'text',
    text,
    createdAt: new Date().toISOString()
  };
  const lowered = text.toLowerCase();
  const replies: ChatMessage[] = [];
  let destinationChosen: string | undefined;

  if (/(lisbon|lisboa)/.test(lowered)) {
    destinationChosen = 'Lisbon';
    replies.push({
      id: `a${++msgCounter}`,
      role: 'assistant',
      kind: 'text',
      text: 'Lisbon locked in. I updated your requirements and refreshed research — see the Travel State panel. Anything you want to change: dates, hotel level, or rental-car days?',
      createdAt: new Date().toISOString()
    });
  } else if (/budget|3000|price|cost/.test(lowered)) {
    replies.push({
      id: `a${++msgCounter}`,
      role: 'assistant',
      kind: 'budget',
      ref: 'lisbon-budget',
      text: 'Recomputed with your note — still comfortably inside budget:',
      createdAt: new Date().toISOString()
    });
  } else if (/weather/.test(lowered)) {
    // Plain text for now; 'weather' MessageKind is reserved for a rich card.
    replies.push({
      id: `a${++msgCounter}`,
      role: 'assistant',
      kind: 'text',
      text: weatherText,
      createdAt: new Date().toISOString()
    });
  } else if (/plan|itinerary|day/.test(lowered)) {
    replies.push({
      id: `a${++msgCounter}`,
      role: 'assistant',
      kind: 'itinerary',
      ref: 'lisbon-plan',
      createdAt: new Date().toISOString()
    });
  } else {
    replies.push({
      id: `a${++msgCounter}`,
      role: 'assistant',
      kind: 'text',
      text: 'Noted. I updated the draft requirements (mock). Tell me dates, budget shifts, or pick a destination and I will refresh research accordingly.',
      createdAt: new Date().toISOString()
    });
  }
  for (const m of [user, ...replies]) extraMessages[m.id] = m;
  // Unused in the mock; the backend will scope replies by conversation.
  void conversationId;
  return { user, replies, destinationChosen };
}

export async function chooseDestination(destinationId: string): Promise<MockSendResult> {
  await delay();
  const dest = destinations.find((d) => d.id === destinationId);
  const name = dest?.name ?? 'Lisbon';
  const user: ChatMessage = {
    id: `u${++msgCounter}`,
    role: 'user',
    kind: 'text',
    text: `Let's go with ${name}.`,
    createdAt: new Date().toISOString()
  };
  const replies: ChatMessage[] = [
    {
      id: `a${++msgCounter}`,
      role: 'assistant',
      kind: 'text',
      text: `${name} locked in. I pulled flights, hotel, transport, activities and rental options plus the September weather outlook:`,
      createdAt: new Date().toISOString()
    },
    { id: `a${++msgCounter}`, role: 'assistant', kind: 'options', ref: 'lisbon-options', createdAt: new Date().toISOString() },
    { id: `a${++msgCounter}`, role: 'assistant', kind: 'budget', ref: 'lisbon-budget', createdAt: new Date().toISOString() }
  ];
  for (const m of [user, ...replies]) extraMessages[m.id] = m;
  return { user, replies, destinationChosen: name };
}

export function getDestinations() {
  return destinations;
}

export function getLisbonOptions() {
  return lisbonOptions;
}

export function getItineraryText() {
  return itineraryText;
}

export function baseRequirements(destination: string | null): RequirementItem[] {
  return [
    { key: 'destination', label: 'Destination', value: destination, confirmed: !!destination },
    { key: 'origin', label: 'Origin', value: 'Madrid', confirmed: true },
    { key: 'dates', label: 'Dates', value: 'September 2026', confirmed: true },
    { key: 'exact-dates', label: 'Exact travel dates', value: null, confirmed: false },
    { key: 'duration', label: 'Duration', value: '7 days', confirmed: true },
    { key: 'travelers', label: 'Travelers', value: '2', confirmed: true },
    { key: 'budget', label: 'Budget', value: '€1,500', confirmed: true },
    { key: 'interests', label: 'Interests', value: 'Food, culture', confirmed: true },
    { key: 'transport', label: 'Transport', value: 'Flight or train', confirmed: true },
    { key: 'rental', label: 'Rental car', value: 'Yes', confirmed: true }
  ];
}

export function fullResearch(): ResearchStatus {
  return { weather: 'done', transportation: 'done', accommodation: 'done', activities: 'done', rentalCar: 'done' };
}

/** Blank state for backend mode: nothing known until stream events arrive. */
export function emptyRequirements(): RequirementItem[] {
  return [
    { key: 'destination', label: 'Destination', value: null, confirmed: false },
    { key: 'origin', label: 'Origin', value: null, confirmed: false },
    { key: 'dates', label: 'Dates', value: null, confirmed: false },
    { key: 'duration', label: 'Duration', value: null, confirmed: false },
    { key: 'travelers', label: 'Travelers', value: null, confirmed: false },
    { key: 'budget', label: 'Budget', value: null, confirmed: false },
    { key: 'interests', label: 'Interests', value: null, confirmed: false },
    { key: 'transport', label: 'Transport', value: null, confirmed: false },
    { key: 'accommodation', label: 'Accommodation', value: null, confirmed: false },
    { key: 'constraints', label: 'Constraints', value: null, confirmed: false }
  ];
}

export function emptyResearch(): ResearchStatus {
  return {
    weather: 'pending',
    transportation: 'pending',
    accommodation: 'pending',
    activities: 'pending',
    rentalCar: 'pending'
  };
}

export function emptyBudget(): BudgetSummary {
  return { estimated: 0, budget: null, currency: '€' };
}

export function lisbonBudget(): BudgetSummary {
  return { estimated: 1240, budget: 1500, currency: '€' };
}
