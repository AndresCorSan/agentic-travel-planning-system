import type { ChatMessage, Conversation, Destination, SavedPlan, TravelOption } from '../types';

// ---------------------------------------------------------------------------
// Centralized mock data. Components must NOT import this directly —
// go through stores -> api/travelService so swapping in FastAPI later
// only touches the service layer.
// ---------------------------------------------------------------------------

export const conversations: Conversation[] = [
  { id: 'lisbon-trip', title: 'Lisbon trip', updatedAt: 'Sep 2, 2026', messageIds: ['m1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm8'] },
  { id: 'rome-weekend', title: 'Weekend in Rome', updatedAt: 'Aug 28, 2026', messageIds: [] },
  { id: 'paris-september', title: 'Paris in September', updatedAt: 'Aug 21, 2026', messageIds: [] },
  { id: 'japan-planning', title: 'Japan planning', updatedAt: 'Aug 10, 2026', messageIds: [] }
];

export const savedPlans: SavedPlan[] = [
  { id: 'plan-lisbon', title: 'Lisbon food & culture week', destination: 'Lisbon', dates: 'September 2026', status: 'Ready' },
  { id: 'plan-rome', title: 'Rome long weekend', destination: 'Rome', dates: 'October 2026', status: 'Draft' }
];

export const messages: Record<string, ChatMessage> = {
  m1: {
    id: 'm1',
    role: 'user',
    kind: 'text',
    text: 'I want to visit Lisbon for one week in September 2026 with my partner. We are interested in good weather, food and cultural activities.',
    createdAt: '10:02'
  },
  m2: {
    id: 'm2',
    role: 'assistant',
    kind: 'text',
    text: 'Great choice — September is ideal for Lisbon: warm days, fewer crowds, and festival season winding down.\n\nI compared a few options based on food, culture and weather. Here is my shortlist:',
    createdAt: '10:02'
  },
  m3: { id: 'm3', role: 'assistant', kind: 'destinations', ref: 'dest-shortlist', createdAt: '10:03' },
  m4: {
    id: 'm4',
    role: 'user',
    kind: 'text',
    text: 'Lisbon sounds perfect. Let\u2019s go with Lisbon.',
    createdAt: '10:05'
  },
  m5: {
    id: 'm5',
    role: 'assistant',
    kind: 'text',
    text: 'Lisbon it is. I researched flights from Madrid, a central hotel, train options, food experiences and rental cars. Weather in mid-September averages 26\u00b0C with low rain risk.',
    createdAt: '10:06'
  },
  m6: { id: 'm6', role: 'assistant', kind: 'options', ref: 'lisbon-options', createdAt: '10:06' },
  m7: { id: 'm7', role: 'assistant', kind: 'budget', ref: 'lisbon-budget', createdAt: '10:07' },
  m8: { id: 'm8', role: 'assistant', kind: 'itinerary', ref: 'lisbon-plan', createdAt: '10:08' }
};

export const destinations: Destination[] = [
  {
    id: 'lisbon',
    name: 'Lisbon',
    country: 'Portugal',
    tagline: 'Sunlit hills, tascas, fado and riverside light.',
    highlights: ['Food scene', 'Mild September weather', 'Walkable culture'],
    suitability: 91,
    drawback: 'Alfama and trams get crowded midday.'
  },
  {
    id: 'porto',
    name: 'Porto',
    country: 'Portugal',
    tagline: 'Cellars, riverfront and slower pace.',
    highlights: ['Wine culture', 'Lower prices', 'Compact center'],
    suitability: 84,
    drawback: 'Slightly higher rain chance than Lisbon.'
  },
  {
    id: 'seville',
    name: 'Seville',
    country: 'Spain',
    tagline: 'Tapas, patios and late golden evenings.',
    highlights: ['Food', 'Easy trains from Madrid'],
    suitability: 78,
    drawback: 'Early September can still be very hot.'
  }
];

export const lisbonOptions: TravelOption[] = [
  { id: 'f1', category: 'flight', title: 'MAD → LIS · Iberia direct', detail: '1h 20m · 2 adults return', price: '€218', meta: 'Hand luggage incl.' },
  { id: 't1', category: 'transport', title: 'Madrid → Lisbon by train + bus', detail: 'Combo via Badajoz · scenic route', price: '€96', meta: '~6h total' },
  { id: 'h1', category: 'hotel', title: 'Hotel Avenida Palace', detail: 'Rossio · 7 nights · central', price: '€840', meta: '8.9 · breakfast incl.' },
  { id: 'a1', category: 'activity', title: 'Time Out Market food tour', detail: '3h guided tasting · 6 stops', price: '€70', meta: '4.8 rating' },
  { id: 'a2', category: 'activity', title: 'Belém + Alfama cultural walk', detail: 'Full day · monastery & fado evening', price: '€55', meta: 'Small group' },
  { id: 'r1', category: 'rental', title: 'Compact rental · 3 days', detail: 'Sintra & Cascais day trips', price: '€141', meta: 'Full insurance' }
];

export const itineraryText = `Here is a first 7-day proposal:

**Days 1–2 — Baixa & Alfama**
Settle in, miradouros at sunset, fado evening in Alfama.

**Days 3–4 — Belém & LX Factory**
Monastery, riverfront, contemporary art and markets.

**Day 5 — Sintra day trip**
Pena Palace early, gardens, return via Cascais coast.

**Days 6–7 — Food & slow Lisbon**
Market tour, tasca crawl, river ferry to Cacilhas.

Total on-the-ground estimate: **€1,240** against your **€1,500** budget — €260 headroom for extras. Want me to lock this in as your plan?`;

export const weatherText = 'Mid-September in Lisbon: highs ~26°C, lows ~18°C, ~1 rainy day expected. Atlantic breeze in the evenings — a light layer is enough.';
