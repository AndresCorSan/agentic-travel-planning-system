// Routes: / redirects to the demo trip, /trip/:id is the chat screen,
// /plans and /plans/:id are the saved-plans overview and detail.
import { createRouter, createWebHistory } from 'vue-router';
import ChatView from '../views/ChatView.vue';
import PlanDetailView from '../views/PlanDetailView.vue';
import PlansView from '../views/PlansView.vue';

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/trip/lisbon-trip' },
    { path: '/trip/:id', name: 'trip', component: ChatView, props: true },
    { path: '/plans', name: 'plans', component: PlansView },
    { path: '/plans/:id', name: 'plan-detail', component: PlanDetailView, props: true }
  ]
});
