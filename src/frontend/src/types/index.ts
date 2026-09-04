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
  /** Payload id for rich kinds (destination list, option list, …). Unread by
      current renderers, which fetch mock payloads directly; kept for the
      backend contract, which will serve payloads by id. */
  ref?: string;
  createdAt: string;
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
  weather: boolean;
  transportation: boolean;
  accommodation: boolean;
  activities: boolean;
  rentalCar: boolean;
}

export interface BudgetSummary {
  estimated: number;
  budget: number | null;
  currency: string;
}

export interface Destination {
  id: string;
  name: string;
  country: string;
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
