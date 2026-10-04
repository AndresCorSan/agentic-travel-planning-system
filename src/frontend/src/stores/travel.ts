// Domain stores (Pinia): `travel` holds the active conversation thread
// (messages, requirements, research, budget); `library` holds the sidebar
// collections (conversations, saved plans) with rename/delete actions.
import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import * as service from '../api/travelService';
import { AGENT_LABELS, AGENT_RESEARCH_KEY, SAVED_CHOICES_PREFIX } from '../api/stream';
import { categoryLabel, groupLabel } from '../components/chat/richtext';
import type { SubagentResult, AgentRow, BudgetSummary, ChatMessage, Conversation, PlanItem, PlanOption, PlanUpdate, ResearchStatus, RequirementItem, SavedPlan, StreamEvent } from '../types';
import { SINGLE_CHOICE_CATEGORIES } from '../types';

export const useTravelStore = defineStore('travel', () => {
  const conversationId = ref<string>('lisbon-trip');
  const messageIds = ref<string[]>([]);
  const cache = ref<Record<string, ChatMessage>>({});
  const loading = ref(false);
  // The panel starts blank; `requirements.updated` /
  // `research.update` stream events are the only writers.
  const requirements = ref<RequirementItem[]>(service.emptyRequirements());
  const research = ref<ResearchStatus>(service.emptyResearch());
  const budget = ref<BudgetSummary>(service.emptyBudget());
  // Selectable options published by main_llm (`options` events), by category.
  // A republish for a category replaces its list (new searches overwrite).
  const optionsByCategory = ref<Record<string, PlanOption[]>>({});
  const optionsById = computed(() => {
    const map: Record<string, PlanOption & { category: string }> = {};
    for (const [category, opts] of Object.entries(optionsByCategory.value)) {
      for (const o of opts) map[o.id] = { ...o, category };
    }
    return map;
  });
  // Trip plan saved choices (`plan.updated` events).
  const plan = ref<PlanItem[]>([]);
  const planTotal = ref(0);
  const planCurrency = ref<string | null>(null);
  const planBudget = ref<number | null>(null);
  const planOverBudget = ref(false);
  // Trip plan application shared by the `plan.updated` event and the
  // instant UI update right after a button save (server truth both ways).
  function applyPlan(p: PlanUpdate) {
    plan.value = p.plan;
    planTotal.value = p.total;
    planCurrency.value = p.currency;
    planBudget.value = p.budget;
    planOverBudget.value = p.overBudget;
    // The Budget panel's Estimated is the deterministic plan total.
    budget.value = { ...budget.value, estimated: p.total };
  }
  // Per-message selection drafts for the inline option controls, plus
  // messages already saved (controls locked afterwards).
  const drafts = ref<Record<string, Record<string, boolean>>>({});
  const choicesSaved = ref<Record<string, boolean>>({});
  // Merge incoming options into a category list per group: a republish
  // replaces only its own group's options (e.g. a fresh "outbound" keeps
  // the published "return" ones). Mirrors backend _merge_options.
  function mergeOptions(existing: PlanOption[], incoming: PlanOption[]): PlanOption[] {
    const groups = new Set(incoming.map((o) => o.group ?? ''));
    return [...existing.filter((o) => !groups.has(o.group ?? '')), ...incoming];
  }
  function toggleOption(messageId: string, optionId: string) {
    const opt = optionsById.value[optionId];
    if (!opt || choicesSaved.value[messageId]) return;
    const draft = { ...(drafts.value[messageId] ?? {}) };
    const next = !draft[optionId];
    if (next && SINGLE_CHOICE_CATEGORIES.includes(opt.category)) {
      for (const [id, on] of Object.entries(draft)) {
        const other = optionsById.value[id];
        if (on && other?.category === opt.category && (other.group ?? '') === (opt.group ?? '')) draft[id] = false;
      }
    }
    draft[optionId] = next;
    drafts.value = { ...drafts.value, [messageId]: draft };
  }
  function draftChoices(messageId: string): { category: string; group: string; option_id: string }[] {
    const draft = drafts.value[messageId] ?? {};
    return Object.entries(draft)
      .filter(([, on]) => on)
      .map(([id]) => ({ category: optionsById.value[id]?.category ?? '', group: optionsById.value[id]?.group ?? '', option_id: id }))
      .filter((c) => c.category);
  }
  async function saveChoices(messageId: string) {
    const choices = draftChoices(messageId);
    if (!choices.length || choicesSaved.value[messageId]) return;
    loading.value = true;
    try {
      // 1. Deterministic save (no LLM). 2. Same user message through the
      // normal pipeline — like "Let's go with…" for destinations — where
      // extract+router short-circuit straight to main_llm for confirmation.
      const res = await service.saveChoices(conversationId.value, choices);
      // Instant UI update from server truth (like the optimistic vote
      // for destinations); the confirm turn re-syncs afterwards.
      if (res.plan) applyPlan(res.plan);
      const names = res.saved?.length
        ? res.saved
        : choices.map((c) => optionsById.value[c.option_id]?.label ?? c.option_id);
      choicesSaved.value = { ...choicesSaved.value, [messageId]: true };
      // Friendly list ordered by category (no prices): the first line is
      // the prefix the backend short-circuits on.
      const order = (c: string) => {
        const idx = ['transportation', 'accommodation', 'rental_car', 'activities'].indexOf(c);
        return idx < 0 ? 99 : idx;
      };
      const catLabel = (c: string, g: string) => {
        const base = categoryLabel(c);
        return g ? `${base} (${groupLabel(g)})` : base;
      };
      const named = choices.map((c, i) => ({
        category: c.category,
        group: c.group ?? '',
        name: names[i] ?? c.option_id,
      }));
      // One line per (category, group) (multi-choice ones join with commas).
      const byCategory = new Map<string, { category: string; group: string; names: string[] }>();
      for (const n of named.sort((a, b) => order(a.category) - order(b.category) || (a.group < b.group ? -1 : a.group > b.group ? 1 : 0))) {
        const k = `${n.category}||${n.group}`;
        const entry = byCategory.get(k) ?? { category: n.category, group: n.group, names: [] };
        entry.names.push(n.name);
        byCategory.set(k, entry);
      }
      const lines = [...byCategory.values()].map((e) => `- ${catLabel(e.category, e.group)}: ${e.names.join(', ')}`);
      await send(`${SAVED_CHOICES_PREFIX}\n${lines.join('\n')}`);
    } finally {
      loading.value = false;
    }
  }

  const messages = computed(() => messageIds.value.map((id) => cache.value[id]).filter(Boolean));

  // Live streaming state (SSE).
  const streamStatus = ref('Reasoning…');
  const agentRows = ref<AgentRow[]>([]);
  const streaming = ref<ChatMessage | null>(null);
  // Optimistic per-message votes (carousel Choose clicks): shown instantly
  // as Selected until the confirmed destination arrives via requirements.
  const voted = ref<Record<string, string>>({});
  function vote(messageId: string, name: string) {
    voted.value[messageId] = name;
  }
  // Specialist outputs buffered during the current turn (`agent.result`
  // events); attached to the assistant message when it is finalized.
  let pendingResults: SubagentResult[] = [];
  // Options published during the current turn (`options` events). If the
  // finalized message carries no [[option:id]] flags (the LLM skipped
  // them), these render as an automatic block under that message instead
  // of losing the choice controls for the turn.
  let pendingTurnOptions: { category: string; options: PlanOption[] }[] = [];
  const optionsByMessage = ref<Record<string, { category: string; options: PlanOption[] }[]>>({});
  function attachPendingOptions(messageId: string) {
    if (!pendingTurnOptions.length) return;
    optionsByMessage.value = { ...optionsByMessage.value, [messageId]: pendingTurnOptions };
    pendingTurnOptions = [];
  }
  let streamCounter = 1000;

  async function loadConversation(id: string) {
    conversationId.value = id;
    loading.value = true;
    // Blank slate; backend rehydrate fills it below.
    messageIds.value = [];
    requirements.value = service.emptyRequirements();
    research.value = service.emptyResearch();
    budget.value = service.emptyBudget();
    optionsByCategory.value = {};
    plan.value = [];
    planTotal.value = 0;
    planCurrency.value = null;
    planBudget.value = null;
    planOverBudget.value = false;
    drafts.value = {};
    choicesSaved.value = {};
    optionsByMessage.value = {};
    agentRows.value = [];
    streaming.value = null;
    streamStatus.value = '';
    try {
      // Rehydrate persisted history + graph-owned panel state so a
      // reload (or backend restart) restores the thread.
      const [msgs, state] = await Promise.all([
        service.getConversationMessages(id).catch(() => []),
        service.getConversationState(id),
      ]);
      for (const m of msgs) cache.value[m.id] = m;
      messageIds.value = msgs.map((m) => m.id);
      // Past subagent outputs imply their research already ran.
      for (const m of msgs) {
        for (const r of m.subagentResults ?? []) {
          const key = AGENT_RESEARCH_KEY[r.id];
          if (key) research.value[key] = 'done';
        }
      }
      if (state) {
        if (state.requirements?.length) requirements.value = state.requirements;
        if (state.options) optionsByCategory.value = state.options;
        if (state.plan) applyPlan(state.plan);
      }
    } finally {
      loading.value = false;
    }
  }

  async function send(text: string) {
    // Lazy creation: the sidebar row appears with the first message (the
    // backend ensures its own row too), so empty trips are never stored.
    const library = useLibraryStore();
    if (!library.conversations.some((c) => c.id === conversationId.value)) {
      library.addConversation('New trip', conversationId.value);
    }
    const pending = service.createPendingUser(text);
    cache.value[pending.id] = pending;
    messageIds.value.push(pending.id);
    loading.value = true;
    // Streaming path: the pending message becomes the final user message.
    let keepPending = false;
    try {
      streamStatus.value = 'Reasoning…';
      agentRows.value = [];
      streaming.value = null;
      pendingResults = [];
      pendingTurnOptions = [];
      for await (const ev of service.streamMessage(conversationId.value, text)) applyEvent(ev);
      streaming.value = null;
      keepPending = true;
      // Keep the sidebar row fresh (the backend emits `title.updated`
      // once light_llm has enough context — no eager first-message slice).
      const row = library.conversations.find((c) => c.id === conversationId.value);
      if (row) {
        row.updatedAt = 'just now';
      }
    } finally {
      if (!keepPending) {
        messageIds.value = messageIds.value.filter((id) => id !== pending.id);
        delete cache.value[pending.id];
      }
      loading.value = false;
    }
  }

  function applyEvent(ev: StreamEvent) {
    switch (ev.type) {
      case 'status':
        streamStatus.value = ev.text;
        break;
      case 'agents.start':
        for (const id of ev.agents) {
          const key = AGENT_RESEARCH_KEY[id];
          if (key) research.value[key] = 'active';
          const row = agentRows.value.find((r) => r.id === id);
          if (row) row.state = 'active';
          else agentRows.value.push({ id, label: AGENT_LABELS[id] ?? id, state: 'active' });
        }
        break;
      case 'agent.done': {
        const row = agentRows.value.find((r) => r.id === ev.id);
        if (row) row.state = 'done';
        const key = AGENT_RESEARCH_KEY[ev.id];
        if (key) research.value[key] = 'done';
        break;
      }
      case 'agent.result': {
        if (!pendingResults.some((r) => r.id === ev.id)) {
          pendingResults.push({ id: ev.id, label: AGENT_LABELS[ev.id] ?? ev.id, text: ev.text });
        }
        // Show the accordion live under the streaming bubble as well.
        if (streaming.value) {
          streaming.value = { ...streaming.value, subagentResults: [...pendingResults] };
        }
        break;
      }
      case 'research.update':
        research.value[ev.key] = ev.state;
        break;
      case 'requirements.updated':
        requirements.value = ev.requirements;
        break;
      case 'options':
        optionsByCategory.value = { ...optionsByCategory.value, [ev.category]: mergeOptions(optionsByCategory.value[ev.category] ?? [], ev.options) };
        pendingTurnOptions = [
          ...pendingTurnOptions.filter((g) => g.category !== ev.category),
          { category: ev.category, options: mergeOptions(pendingTurnOptions.find((g) => g.category === ev.category)?.options ?? [], ev.options) },
        ];
        break;
      case 'plan.updated':
        applyPlan(ev);
        break;
      case 'token':
        if (!streaming.value) {
          streaming.value = {
            id: `s${++streamCounter}`,
            role: 'assistant',
            kind: 'text',
            text: '',
            // Results arrived before the first token: show the accordions
            // above the answer from the start instead of popping them in
            // at the end.
            ...(pendingResults.length ? { subagentResults: [...pendingResults] } : {}),
            createdAt: new Date().toISOString()
          };
        }
        streaming.value = { ...streaming.value, text: (streaming.value.text ?? '') + ev.text };
        break;
      case 'message':
        if (streaming.value) {
          if (pendingResults.length) {
            streaming.value = { ...streaming.value, subagentResults: [...pendingResults] };
          }
          cache.value[streaming.value.id] = streaming.value;
          messageIds.value.push(streaming.value.id);
          if (ev.message.role !== 'assistant') attachPendingOptions(streaming.value.id);
          streaming.value = null;
          pendingResults = [];
        }
        cache.value[ev.message.id] = ev.message;
        messageIds.value.push(ev.message.id);
        if (ev.message.role === 'assistant') attachPendingOptions(ev.message.id);
        break;
      case 'stats': {
        // Turn usage (tokens/cost/duration): attach to the live bubble if
        // still streaming, else to the latest assistant message already
        // flushed to the cache (e.g. destination cards).
        if (streaming.value) {
          streaming.value = { ...streaming.value, stats: ev.stats };
        } else {
          for (let i = messageIds.value.length - 1; i >= 0; i--) {
            const m = cache.value[messageIds.value[i]];
            if (m?.role === 'assistant') {
              cache.value[m.id] = { ...m, stats: ev.stats };
              break;
            }
          }
        }
        break;
      }
      case 'title.updated': {
        const library = useLibraryStore();
        const row = library.conversations.find((c) => c.id === ev.conversationId);
        if (row) {
          row.title = ev.title;
          row.updatedAt = 'just now';
        }
        break;
      }
      case 'done':
        if (streaming.value) {
          if (pendingResults.length) {
            streaming.value = { ...streaming.value, subagentResults: [...pendingResults] };
          }
          cache.value[streaming.value.id] = streaming.value;
          messageIds.value.push(streaming.value.id);
          attachPendingOptions(streaming.value.id);
          streaming.value = null;
          pendingResults = [];
        }
        break;
      case 'error':
        streaming.value = null;
        throw new Error(ev.message);
    }
  }

  return { messages, loading, streamStatus, agentRows, streaming, requirements, research, budget, voted, vote, loadConversation, send, optionsByCategory, optionsById, plan, planTotal, planCurrency, planBudget, planOverBudget, drafts, choicesSaved, optionsByMessage, toggleOption, draftChoices, saveChoices };
});

export const useLibraryStore = defineStore('library', () => {
  const conversations = ref<Conversation[]>([]);
  const plans = ref<SavedPlan[]>([]);
  const loaded = ref(false);
  // Shared in-flight request: Sidebar and ChatView both call load() on cold
  // start — the second caller awaits the same request instead of refetching.
  let loadInflight: Promise<void> | null = null;

  async function load() {
    loadInflight ??= (async () => {
      conversations.value = await service.listConversations();
      plans.value = await service.listSavedPlans();
      loaded.value = true;
    })();
    await loadInflight;
  }
  function renameConversation(id: string, title: string) {
    const c = conversations.value.find((c) => c.id === id);
    if (c) c.title = title;
    void service.renameConversationRemote(id, title);
  }
  function deleteConversation(id: string) {
    conversations.value = conversations.value.filter((c) => c.id !== id);
    void service.deleteConversationRemote(id);
  }
  function addPlan(plan: SavedPlan) {
    if (!plans.value.some((p) => p.id === plan.id)) plans.value.unshift(plan);
  }
  function renamePlan(id: string, title: string) {
    const p = plans.value.find((p) => p.id === id);
    if (p) p.title = title;
    void service.renamePlanRemote(id, title);
  }
  function deletePlan(id: string) {
    plans.value = plans.value.filter((p) => p.id !== id);
    void service.deletePlanRemote(id);
  }
  function addConversation(title: string, id?: string): Conversation {
    const c: Conversation = {
      id: id ?? service.createConversationId(),
      title,
      updatedAt: 'just now',
      messageIds: []
    };
    conversations.value.unshift(c);
    // Local-only: the backend row is created lazily via ensure_conversation
    // on the first streamed message, so empty trips are never persisted.
    return c;
  }

  return { conversations, plans, loaded, load, renameConversation, deleteConversation, renamePlan, deletePlan, addConversation, addPlan };
});
