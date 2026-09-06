// Domain stores (Pinia): `travel` holds the active conversation thread
// (messages, requirements, research, budget); `library` holds the sidebar
// collections (conversations, saved plans) with rename/delete actions.
import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import * as service from '../api/travelService';
import type { BudgetSummary, ChatMessage, Conversation, ResearchStatus, RequirementItem, SavedPlan } from '../types';

export const useTravelStore = defineStore('travel', () => {
  const conversationId = ref<string>('lisbon-trip');
  const messageIds = ref<string[]>([]);
  const cache = ref<Record<string, ChatMessage>>({});
  const loading = ref(false);
  const requirements = ref<RequirementItem[]>(service.baseRequirements('Lisbon'));
  const research = ref<ResearchStatus>(service.fullResearch());
  // Static mock snapshot (never reassigned yet); the backend will own it.
  const budget = ref<BudgetSummary>(service.lisbonBudget());

  const messages = computed(() => messageIds.value.map((id) => cache.value[id]).filter(Boolean));

  async function loadConversation(id: string, ids: string[]) {
    conversationId.value = id;
    loading.value = true;
    try {
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
    try {
      const res = await service.sendMessage(conversationId.value, text);
      append(res);
    } finally {
      messageIds.value = messageIds.value.filter((id) => id !== pending.id);
      delete cache.value[pending.id];
      loading.value = false;
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

  return { messages, loading, requirements, research, budget, loadConversation, send, choose };
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
