<!-- Saved-plan detail page (/plans/:id): editorial header (overline +
      title + lede + fact chips) plus the trip plan timeline, all from the
      stored snapshot. -->
<script setup lang="ts">
import Button from 'primevue/button';
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { getSavedPlan } from '../api/travelService';
import TripPlanSection from '../components/travel/TripPlanSection.vue';
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

interface FactChip {
  key: string;
  prefix: string;
  bold: string;
  suffix: string;
  missing: boolean;
}

// Requirements as editorial fact chips (destination/dates live in the
// overline). Ambiguous values get their label as context ("2 travelers").
const factChips = computed<FactChip[]>(() => {
  const chips: FactChip[] = [];
  for (const r of plan.value?.requirements ?? []) {
    if (r.key === 'destination' || r.key === 'dates') continue;
    if (!r.value) {
      chips.push({ key: r.key, prefix: '', bold: '', suffix: `${r.label} n/s`, missing: true });
      continue;
    }
    const v = r.value;
    switch (r.key) {
      case 'travelers':
        chips.push({ key: r.key, prefix: '', bold: v, suffix: 'travelers', missing: false });
        break;
      case 'budget':
        chips.push({ key: r.key, prefix: '', bold: v, suffix: 'budget', missing: false });
        break;
      case 'origin':
        chips.push({ key: r.key, prefix: 'From ', bold: v, suffix: '', missing: false });
        break;
      case 'duration':
      case 'interests':
      case 'transport':
        chips.push({ key: r.key, prefix: '', bold: v, suffix: '', missing: false });
        break;
      default:
        chips.push(
          v === 'Yes' || v === 'No'
            ? { key: r.key, prefix: '', bold: r.label, suffix: v.toLowerCase(), missing: false }
            : { key: r.key, prefix: '', bold: v, suffix: '', missing: false }
        );
    }
  }
  return chips;
});
const travelers = computed(() => {
  const raw = plan.value?.requirements?.find((r) => r.key === 'travelers')?.value;
  const n = raw ? parseInt(raw, 10) : NaN;
  return Number.isFinite(n) && n > 0 ? n : null;
});

function backToConversation() {
  if (plan.value?.conversationId) router.push(`/trip/${plan.value.conversationId}`);
  else router.push('/plans');
}

// "2026-09-14T…" -> "Sep 14, 2026" for the overline.
function savedLabel(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return `Saved ${d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
}

const overline = computed(() =>
  [plan.value?.destination, plan.value?.dates].filter(Boolean).join(' · ')
);
const savedText = computed(() => savedLabel(plan.value?.createdAt));
</script>

<template>
  <div class="detail slim-scroll">
    <div class="topbar">
      <Button label="Back to plans" icon="pi pi-arrow-left" severity="secondary" text @click="router.push('/plans')" />
      <Button
        v-if="plan?.conversationId"
        label="Open conversation"
        icon="pi pi-comments"
        severity="secondary"
        text
        @click="backToConversation()"
      />
    </div>
    <template v-if="plan">
      <div class="head">
        <div class="head-main">
          <p class="overline">{{ overline }}</p>
          <h1 class="title">{{ plan.title }}</h1>
        </div>
        <p v-if="savedText" class="saved">{{ savedText }}</p>
      </div>
      <p v-if="plan.description" class="lede">{{ plan.description }}</p>

      <div v-if="factChips.length" class="facts">
        <span v-for="c in factChips" :key="c.key" :class="{ miss: c.missing }"><template v-if="!c.missing">{{ c.prefix }}<b>{{ c.bold }}</b>{{ c.suffix ? ` ${c.suffix}` : '' }}</template><template v-else>{{ c.suffix }}</template></span>
      </div>

      <h2 class="plan-sep">Trip plan</h2>
      <TripPlanSection
        :items="plan.plan ?? []"
        :total="plan.total ?? 0"
        :currency="plan.currency ?? null"
        :budget="plan.budget ?? null"
        :over-budget="!!plan.overBudget"
        :travelers="travelers"
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
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin: 12px 0 10px;
}
.head-main {
  min-width: 0;
}
.overline {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--p-primary-600);
  margin: 0 0 6px;
}
.title {
  font-size: 1.7rem;
  margin: 0;
  letter-spacing: -0.01em;
}
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.saved {
  flex: none;
  margin: 0;
  font-size: 0.78rem;
  color: var(--p-surface-500);
  white-space: nowrap;
}
.lede {
  font-size: 1.02rem;
  line-height: 1.6;
  color: var(--p-surface-700);
  margin: 0;
  border-top: 3px solid var(--p-primary-600);
  padding-top: 12px;
}
.facts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}
.facts span {
  background: var(--p-surface-50);
  border: 1px solid var(--p-surface-200);
  border-radius: 99px;
  padding: 5px 13px;
  font-size: 0.82rem;
}
.facts span.miss {
  border-style: dashed;
  color: var(--p-surface-500);
}
h2 {
  font-size: 0.95rem;
  margin: 24px 0 8px;
}
.plan-sep {
  border-top: 1px solid var(--p-surface-200);
  padding-top: 20px;
}
</style>
