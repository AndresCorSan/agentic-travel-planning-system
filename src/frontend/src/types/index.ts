/*
 * Shared domain types: the contract between service, stores and components.
 * Covers chat messages, the SSE event union (mirrors the backend wire
 * protocol in streaming.py — keep both sides in sync), plan/budget
 * payloads, research status, and the library entities (conversations,
 * saved plans). Also hosts SINGLE_CHOICE_CATEGORIES, the only runtime
 * constant here: categories where a new choice replaces the previous one.
 */
export type MessageKind =
  | 'text'
  | 'destinations'
  | 'options'
  | 'weather'
  | 'budget'
  | 'itinerary';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  kind: MessageKind;
  /** Plain text body (assistant text uses lightweight markdown-ish rendering). */
  text?: string;
  /** Outputs of the specialist subagents for this turn (backend streams
      them via `agent.result`); rendered as accordions above the text. */
  subagentResults?: SubagentResult[];
  /** Destination candidates for `destinations` messages (backend streams
      them from the destination research branch); rendered as a carousel. */
  destinations?: Destination[];
  /** Payload id for rich kinds (destination list, option list, …). */
  ref?: string;
  createdAt: string;
  /** Turn-level LLM usage stats (backend `stats` event / payload). Present
      on assistant messages created after the stats feature; absent on
      older history and on user messages. */
  stats?: MessageStats;
  /** Frontend-only: stream failure bubble (send() catch). Rendered with
      the error style; the backend never sends this. */
  error?: boolean;
}

/** Token / cost / timing metadata for one assistant turn. */
export interface MessageStats {
  duration_s: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number | null;
  model: string | null;
}

/** One specialist subagent output attached to an assistant message. */
export interface SubagentResult {
  id: string;
  label: string;
  text: string;
}

export interface Conversation {
  id: string;
  title: string;
  updatedAt: string;
  messageIds: string[];
}

export interface RequirementItem {
  key: string;
  label: string;
  value: string | null;
  /** Backend-owned confirmation flag; the panel currently derives it from `value`. */
  confirmed: boolean;
}

export interface ResearchStatus {
  weather: ResearchState;
  transportation: ResearchState;
  accommodation: ResearchState;
  activities: ResearchState;
  rentalCar: ResearchState;
}

export type ResearchState = 'pending' | 'active' | 'done';

export type ResearchKey = 'weather' | 'transportation' | 'accommodation' | 'activities' | 'rentalCar';

export interface AgentRow {
  id: string;
  label: string;
  state: 'active' | 'done';
}

// Server-sent events for POST /conversations/{id}/messages (streaming).
export type StreamEvent =
  | { type: 'status'; text: string }
  | { type: 'agents.start'; agents: string[] }
  | { type: 'agent.done'; id: string }
  | { type: 'agent.result'; id: string; text: string }
  | { type: 'research.update'; key: ResearchKey; state: ResearchState }
  | { type: 'requirements.updated'; requirements: RequirementItem[] }
  | { type: 'options'; category: string; options: PlanOption[] }
  | { type: 'plan.updated' } & PlanUpdate
  | { type: 'token'; text: string }
  | { type: 'message'; message: ChatMessage }
  | { type: 'stats'; stats: MessageStats }
  | { type: 'title.updated'; conversationId: string; title: string }
  | { type: 'done' }
  | { type: 'error'; message: string };

/** One selectable option published by main_llm (via the `options` event). */
export interface PlanOption {
  id: string;
  label: string;
  price: number | null;
  currency: string | null;
  per_person: boolean;
  details: string;
  /** Selectable leg within the category ("outbound", "return", "leg 1"...).
      Empty means the category's single default group. */
  group: string;
}

/** A user choice saved into the trip plan (snapshot, via `plan.updated`). */
export interface PlanItem extends PlanOption {
  category: string;
  option_id: string;
}

/** Trip plan + deterministic total payload (plan.updated event / choices response). */
export interface PlanUpdate {
  plan: PlanItem[];
  total: number;
  currency: string | null;
  budget: number | null;
  overBudget: boolean;
}

/** Categories where a new choice replaces the previous one. The replacement
    key is (category, group), so legs like outbound/return are independent. */
export const SINGLE_CHOICE_CATEGORIES = ['transportation', 'accommodation', 'rental_car'];

export interface BudgetSummary {
  estimated: number;
  budget: number | null;
  currency: string;
}

export interface Destination {
  id: string;
  name: string;
  country: string;
  /** ISO 3166-1 alpha-2 lowercase (backend candidates); drives the flag image. */
  country_code?: string;
  tagline: string;
  highlights: string[];
  suitability: number;
  drawback: string;
}

export interface SavedPlan {
  id: string;
  title: string;
  destination: string;
  dates: string;
  status: string;
  /** Backend snapshot (phase 8): present on rows from GET /plans. */
  description?: string;
  conversationId?: string;
  requirements?: RequirementItem[];
  plan?: PlanItem[];
  total?: number;
  currency?: string | null;
  budget?: number | null;
  overBudget?: boolean;
  createdAt?: string | null;
}
