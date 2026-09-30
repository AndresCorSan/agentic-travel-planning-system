// Routes: / opens a fresh empty trip (welcome hero; nothing is stored until
// the first message is sent), /trip/:id is the chat screen,
// /plans and /plans/:id are the saved-plans overview and detail.
import { createRouter, createWebHistory } from 'vue-router';
import { createConversationId } from '../api/travelService';
import ChatView from '../views/ChatView.vue';
import PlanDetailView from '../views/PlanDetailView.vue';
import PlansView from '../views/PlansView.vue';
import { useTravelStore } from '../stores/travel';

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: () => `/trip/${createConversationId()}` },
    { path: '/trip/:id', name: 'trip', component: ChatView, props: true },
    { path: '/plans', name: 'plans', component: PlansView },
    { path: '/plans/:id', name: 'plan-detail', component: PlanDetailView, props: true }
  ]
});

// Block trip-to-trip navigation mid-reply: stream events would leak into the wrong thread.
router.beforeEach((to, from) => {
  if (to.name === 'trip' && from.name === 'trip' && to.params.id !== from.params.id) {
    if (useTravelStore().loading) return false;
  }
  return true;
});
