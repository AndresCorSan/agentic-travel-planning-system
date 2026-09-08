// Shared domain types: the contract between mocks/service, stores and
// components. Backend-facing extras (weather kind, ref, confirmed) are
// annotated inline.
export type MessageKind =
  | 'text'
  | 'destinations'
  | 'options'
  | 'weather' // reserved for a future rich weather card (mock sends text)
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
  /** Payload id for rich kinds (destination list, option list, …). Unread by
      current renderers, which fetch mock payloads directly; kept for the
      backend contract, which will serve payloads by id. */
  ref?: string;
  createdAt: string;
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
  | { type: 'token'; text: string }
  | { type: 'message'; message: ChatMessage }
  | { type: 'done' }
  | { type: 'error'; message: string };

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

export interface TravelOption {
  id: string;
  category: 'flight' | 'hotel' | 'transport' | 'activity' | 'rental';
  title: string;
  detail: string;
  price: string;
  meta?: string;
}

export interface SavedPlan {
  id: string;
  title: string;
  destination: string;
  dates: string;
  status: string;
}
