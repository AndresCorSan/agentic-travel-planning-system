/*
 * The only gateway to the backend: live message stream over SSE, conversations
 * CRUD, deterministic choice saves and saved-plan snapshots. Its purpose is to
 * keep HTTP details (paths, envelopes, fallbacks) in one place so stores and
 * views deal only in domain types.
 *
 * Resilience policy: reads fail soft (empty list / null) so panels render
 * without data instead of crashing; renames and deletes are optimistic
 * fire-and-forget — the local change stays whatever the server answers.
 * Also hosts the local-only helpers: instant pending-user placeholder,
 * client-generated conversation ids (the backend row is created lazily on
 * the first message) and empty panel factories.
 * (Stores also read the stream.ts constants directly; no other module may
 * touch api/.)
 */
import { api } from './client';
import { AGENT_LABELS, postStream } from './stream';
import type { StreamEvent } from '../types';
import type {
  BudgetSummary,
  ChatMessage,
  Conversation,
  PlanOption,
  PlanUpdate,
  ResearchStatus,
  RequirementItem,
  SavedPlan
} from '../types';

let msgCounter = 100;

/** Live event stream for POST /conversations/{id}/messages. */
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
  try {
    const { data } = await api.get('/conversations');
    return (data.conversations ?? []) as Conversation[];
  } catch {
    return [];
  }
}

/** Client-generated conversation id so the sidebar can navigate synchronously
    before the backend row exists (it is created lazily on the first message). */
export function createConversationId(): string {
  return `trip-${Date.now().toString(36)}${Math.floor(Math.random() * 1e4).toString(36)}`;
}

/** Stored message history for rehydrating the thread after a reload. */
export async function getConversationMessages(id: string): Promise<ChatMessage[]> {
  const { data } = await api.get(`/conversations/${id}/messages`);
  const msgs = (data.messages ?? []) as ChatMessage[];
  // Server stores id/text only; labels are a frontend mapping.
  for (const m of msgs) {
    if (m.subagentResults) {
      for (const r of m.subagentResults) {
        if (!r.label) r.label = AGENT_LABELS[r.id] ?? r.id;
      }
    }
  }
  return msgs;
}

export interface ConversationState {
  requirements: RequirementItem[];
  options: Record<string, PlanOption[]>;
  plan: PlanUpdate | null;
}

/** Graph-owned side-panel state (requirements/options/plan) for rehydrate. */
export async function getConversationState(id: string): Promise<ConversationState | null> {
  try {
    const { data } = await api.get(`/conversations/${id}/state`);
    return data as ConversationState;
  } catch {
    return null;
  }
}

export async function renameConversationRemote(id: string, title: string): Promise<void> {
  try {
    await api.patch(`/conversations/${id}`, { title });
  } catch {
    // Optimistic local rename stays.
  }
}

export async function deleteConversationRemote(id: string): Promise<void> {
  try {
    await api.delete(`/conversations/${id}`);
  } catch {
    // Optimistic local delete stays.
  }
}

export async function listSavedPlans(): Promise<SavedPlan[]> {
  try {
    const { data } = await api.get('/plans');
    return (data.plans ?? []) as SavedPlan[];
  } catch {
    return [];
  }
}

export async function getSavedPlan(id: string): Promise<SavedPlan | null> {
  try {
    const { data } = await api.get(`/plans/${id}`);
    return data as SavedPlan;
  } catch {
    return null;
  }
}

/** Snapshot the conversation (requirements + trip plan + budget) as a new saved plan. */
export async function savePlan(conversationId: string, title?: string): Promise<SavedPlan> {
  const { data } = await api.post(`/conversations/${conversationId}/plans`, { title: title ?? null });
  return data as SavedPlan;
}

export async function renamePlanRemote(id: string, title: string): Promise<void> {
  try {
    await api.patch(`/plans/${id}`, { title });
  } catch {
    // Optimistic local rename stays.
  }
}

export async function deletePlanRemote(id: string): Promise<void> {
  try {
    await api.delete(`/plans/${id}`);
  } catch {
    // Optimistic local delete stays.
  }
}

/** Blank state: nothing known until stream events arrive. */
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
