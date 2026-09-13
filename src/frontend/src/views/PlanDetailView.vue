<!-- Saved-plan detail page (/plans/:id): description + requirements +
      trip plan + budget, all from the stored snapshot. -->
<script setup lang="ts">
import Button from 'primevue/button';
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { getSavedPlan } from '../api/travelService';
import { categoryLabel, formatOptionPrice } from '../components/chat/richtext';
import type { SavedPlan } from '../types';

const props = defineProps<{ id: string }>();
const router = useRouter();

const plan = ref<SavedPlan | null>(null);
const missing = ref(false);

onMounted(async () => {
  const loaded = await getSavedPlan(props.id);
  if (loaded) plan.value = loaded;
  else missing.value = true;
});

const confirmed = computed(() => (plan.value?.requirements ?? []).filter((r) => r.value));
const unspecified = computed(() => (plan.value?.requirements ?? []).filter((r) => !r.value));

function money(n: number | null | undefined, currency: string | null | undefined): string {
  if (n === null || n === undefined) return '—';
  return formatOptionPrice({ price: n, currency: currency ?? plan.value?.currency ?? null, per_person: false });
}

function backToConversation() {
  if (plan.value?.conversationId) router.push(`/trip/${plan.value.conversationId}`);
  else router.push('/plans');
}
</script>

<template>
  <div class="detail">
    <Button label="Back to plans" icon="pi pi-arrow-left" severity="secondary" text @click="router.push('/plans')" />
    <template v-if="plan">
      <h1>{{ plan.title }}</h1>
      <p class="muted">{{ [plan.destination, plan.dates].filter(Boolean).join(' · ') }}</p>
      <p v-if="plan.description" class="desc">{{ plan.description }}</p>

      <h2>Trip requirements</h2>
      <dl v-if="confirmed.length" class="reqs">
        <div v-for="r in confirmed" :key="r.key" class="req">
          <dt>{{ r.label }}</dt>
          <dd>{{ r.value }}</dd>
        </div>
      </dl>
      <div v-if="unspecified.length" class="missing">
        <p class="missing-title">Not specified</p>
        <ul>
          <li v-for="r in unspecified" :key="r.key">{{ r.label }}</li>
        </ul>
      </div>

      <h2>Trip plan</h2>
      <div v-if="plan.plan?.length" class="items">
        <div v-for="item in plan.plan" :key="`${item.category}:${item.option_id}`" class="item">
          <span class="tx">
            <b>{{ item.label }}</b>
            <small>{{ categoryLabel(item.category) }}<template v-if="item.details"> · {{ item.details }}</template></small>
          </span>
          <span class="pr">{{ money(item.price, item.currency) }}</span>
        </div>
      </div>
      <p v-else class="muted">No choices in this snapshot.</p>

      <h2>Budget</h2>
      <div class="row total">
        <span>Total</span>
        <strong>{{ money(plan.total, plan.currency) }}<span v-if="plan.budget !== null && plan.budget !== undefined" class="muted"> of {{ money(plan.budget, plan.currency) }}</span></strong>
      </div>
      <div v-if="plan.budget !== null && plan.budget !== undefined" class="row">
        <span class="muted">{{ plan.overBudget ? 'Over by' : 'Remaining' }}</span>
        <strong :class="plan.overBudget ? 'bad' : 'ok'">{{ money(Math.abs(plan.budget - (plan.total ?? 0)), plan.currency) }}</strong>
      </div>

      <Button
        v-if="plan.conversationId"
        label="Open conversation"
        icon="pi pi-comments"
        severity="secondary"
        text
        class="conv-link"
        @click="backToConversation()"
      />
    </template>
    <p v-else-if="missing" class="muted">Plan not found.</p>
    <p v-else class="muted">Loading…</p>
  </div>
</template>

<style scoped>
.detail {
  max-width: var(--app-max-chat-width);
  margin: 0 auto;
  padding: 24px;
  width: 100%;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
h1 {
  font-size: 1.3rem;
  margin: 12px 0 4px;
}
h2 {
  font-size: 0.95rem;
  margin: 24px 0 8px;
}
.desc {
  font-size: 0.95rem;
  line-height: 1.55;
  margin: 12px 0 0;
}
.reqs {
  margin: 0;
}
.req {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 5px 0;
  border-bottom: 1px dashed var(--p-surface-200);
  font-size: 0.88rem;
}
.req dt {
  color: var(--p-surface-500);
  flex: none;
}
.req dd {
  margin: 0;
  font-weight: 500;
  text-align: right;
}
.missing {
  margin-top: 10px;
}
.missing-title {
  font-size: 0.78rem;
  color: var(--p-surface-500);
  margin: 0 0 6px;
}
.missing ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.missing li {
  border: 1px dashed var(--p-surface-300);
  color: var(--p-surface-500);
  border-radius: 99px;
  padding: 3px 10px;
  font-size: 0.8rem;
}
.items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.88rem;
  border: 1px solid var(--p-surface-200);
  border-radius: 8px;
  padding: 8px 12px;
}
.tx {
  flex: 1;
  min-width: 0;
  line-height: 1.3;
}
.tx b {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
}
.tx small {
  color: var(--p-surface-500);
}
.pr {
  font-weight: 700;
  white-space: nowrap;
}
.row {
  display: flex;
  justify-content: space-between;
  font-size: 0.88rem;
  margin-bottom: 4px;
}
.row.total {
  font-weight: 700;
  padding-top: 8px;
  border-top: 1px solid var(--p-surface-200);
}
.ok {
  color: var(--p-green-600);
}
.bad {
  color: var(--p-red-500);
}
.conv-link {
  margin-top: 20px;
  padding-left: 0;
}
</style>
