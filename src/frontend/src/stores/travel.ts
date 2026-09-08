// Domain stores (Pinia): `travel` holds the active conversation thread
// (messages, requirements, research, budget); `library` holds the sidebar
// collections (conversations, saved plans) with rename/delete actions.
import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import * as service from '../api/travelService';
import { AGENT_LABELS, AGENT_RESEARCH_KEY } from '../api/stream';
import type { SubagentResult, AgentRow, BudgetSummary, ChatMessage, Conversation, ResearchStatus, RequirementItem, SavedPlan, StreamEvent } from '../types';

export const useTravelStore = defineStore('travel', () => {
  const BACKEND_MODE = import.meta.env.VITE_USE_BACKEND === 'true';
  const conversationId = ref<string>('lisbon-trip');
  const messageIds = ref<string[]>([]);
  const cache = ref<Record<string, ChatMessage>>({});
  const loading = ref(false);
  // Backend mode: the panel starts blank; `requirements.updated` /
  // `research.update` stream events are the only writers. Mock mode keeps
  // the Lisbon snapshot so the UI demo works offline.
  const requirements = ref<RequirementItem[]>(
    BACKEND_MODE ? service.emptyRequirements() : service.baseRequirements('Lisbon')
  );
  const research = ref<ResearchStatus>(BACKEND_MODE ? service.emptyResearch() : service.fullResearch());
  // Static mock snapshot (never reassigned yet); the backend will own it.
  const budget = ref<BudgetSummary>(BACKEND_MODE ? service.emptyBudget() : service.lisbonBudget());

  const messages = computed(() => messageIds.value.map((id) => cache.value[id]).filter(Boolean));

  // Live streaming state (Fase A: driven by streamMock, later by SSE).
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
  let streamCounter = 1000;

  async function loadConversation(id: string, ids: string[]) {
    conversationId.value = id;
    loading.value = true;
    try {
      if (BACKEND_MODE) {
        // The backend owns thread state: start blank, stream events fill in.
        messageIds.value = [];
        requirements.value = service.emptyRequirements();
        research.value = service.emptyResearch();
        agentRows.value = [];
        streaming.value = null;
        streamStatus.value = '';
        return;
      }
      const msgs = await service.getMessages(ids);
      for (const m of msgs) cache.value[m.id] = m;
      messageIds.value = ids;
      // Mock shows detail only for Lisbon; everything else gets blank requirements.
      requirements.value = service.baseRequirements(id === 'lisbon-trip' ? 'Lisbon' : null);
    } finally {
      loading.value = false;
    }
  }

  function append(result: { user: ChatMessage; replies: ChatMessage[]; destinationChosen?: string }) {
    cache.value[result.user.id] = result.user;
    messageIds.value.push(result.user.id);
    for (const r of result.replies) {
      cache.value[r.id] = r;
      messageIds.value.push(r.id);
    }
    if (result.destinationChosen) {
      requirements.value = service.baseRequirements(result.destinationChosen);
      research.value = service.fullResearch();
    }
  }

  async function send(text: string) {
    const pending = service.createPendingUser(text);
    cache.value[pending.id] = pending;
    messageIds.value.push(pending.id);
    loading.value = true;
    // Streaming path: the pending message becomes the final user message.
    // Classic path: the backend echoes the user message via append(res).
    let keepPending = false;
    try {
      if (BACKEND_MODE) {
        streamStatus.value = 'Reasoning…';
        agentRows.value = [];
        streaming.value = null;
        pendingResults = [];
        for await (const ev of service.streamMessage(conversationId.value, text)) applyEvent(ev);
        streaming.value = null;
        keepPending = true;
      } else {
        const res = await service.sendMessage(conversationId.value, text);
        messageIds.value = messageIds.value.filter((id) => id !== pending.id);
        delete cache.value[pending.id];
        append(res);
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
          streaming.value = null;
          pendingResults = [];
        }
        cache.value[ev.message.id] = ev.message;
        messageIds.value.push(ev.message.id);
        break;
      case 'done':
        if (streaming.value) {
          if (pendingResults.length) {
            streaming.value = { ...streaming.value, subagentResults: [...pendingResults] };
          }
          cache.value[streaming.value.id] = streaming.value;
          messageIds.value.push(streaming.value.id);
          streaming.value = null;
          pendingResults = [];
        }
        break;
      case 'error':
        streaming.value = null;
        throw new Error(ev.message);
    }
  }

  async function choose(destinationId: string, destinationName: string) {
    loading.value = true;
    try {
      const res = await service.chooseDestination(destinationId);
      append({ ...res, destinationChosen: destinationName });
    } finally {
      loading.value = false;
    }
  }

  return { messages, loading, streamStatus, agentRows, streaming, requirements, research, budget, voted, vote, loadConversation, send, choose };
});

export const useLibraryStore = defineStore('library', () => {
  const conversations = ref<Conversation[]>([]);
  const plans = ref<SavedPlan[]>([]);

  async function load() {
    conversations.value = await service.listConversations();
    plans.value = await service.listSavedPlans();
  }
  function renameConversation(id: string, title: string) {
    const c = conversations.value.find((c) => c.id === id);
    if (c) c.title = title;
  }
  function deleteConversation(id: string) {
    conversations.value = conversations.value.filter((c) => c.id !== id);
  }
  function renamePlan(id: string, title: string) {
    const p = plans.value.find((p) => p.id === id);
    if (p) p.title = title;
  }
  function deletePlan(id: string) {
    plans.value = plans.value.filter((p) => p.id !== id);
  }
  function addConversation(title: string): Conversation {
    const c: Conversation = {
      id: `trip-${Date.now()}`,
      title,
      updatedAt: 'just now',
      messageIds: []
    };
    conversations.value.unshift(c);
    return c;
  }

  return { conversations, plans, load, renameConversation, deleteConversation, renamePlan, deletePlan, addConversation };
});
