/*
 * Sidebar collections store (Pinia): conversations and saved plans with
 * optimistic rename/delete (the remote call is fire-and-forget; the local
 * change stays whatever the server answers). Sidebar and ChatView both
 * call load() on cold start — the second caller awaits the same in-flight
 * request instead of refetching.
 */
import { defineStore } from 'pinia';
import { ref } from 'vue';
import * as service from '../api/travelService';
import type { Conversation, SavedPlan } from '../types';

export const useLibraryStore = defineStore('library', () => {
  const conversations = ref<Conversation[]>([]);
  const plans = ref<SavedPlan[]>([]);
  const loaded = ref(false);
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
