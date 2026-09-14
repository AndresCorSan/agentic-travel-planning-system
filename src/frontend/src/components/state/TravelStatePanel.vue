<!-- Right-column panel of the chat view: trip requirements and trip plan.
      Collapses to a slim toggle strip;
      on narrow screens it renders inside a slide-over drawer instead. -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useLocalStorageToggle } from '../../composables/useLocalStorageToggle';
import { useTravelStore } from '../../stores/travel';
import TripPlanSection from '../travel/TripPlanSection.vue';

defineProps<{ drawer?: boolean }>();

const travel = useTravelStore();

// Persisted open state per section (shared composable).
const [reqOpen, toggleReq] = useLocalStorageToggle('state-req-open');
const [planOpen, togglePlan] = useLocalStorageToggle('state-plan-open');

const confirmed = computed(() => travel.requirements.filter((r) => r.value));
const missing = computed(() => travel.requirements.filter((r) => !r.value));

// Briefly highlight rows whose value just changed via a live stream update,
// so the eye catches what the agent just filled in. Skipped on first load.
const flashKeys = ref<Set<string>>(new Set());
let prevSnapshot: string | null = null;
watch(
  () => travel.requirements.map((r) => `${r.key}=${r.value ?? ''}`).join('|'),
  (snap) => {
    if (prevSnapshot !== null && snap !== prevSnapshot) {
      const prev = new Map(prevSnapshot.split('|').map((p) => p.split('=') as [string, string]));
      const changed: string[] = [];
      for (const part of snap.split('|')) {
        const [key, val] = part.split('=') as [string, string];
        if (val && prev.get(key) !== val) changed.push(key);
      }
      if (changed.length) {
        flashKeys.value = new Set(changed);
        setTimeout(() => { flashKeys.value = new Set(); }, 1600);
      }
    }
    prevSnapshot = snap;
  },
  { immediate: true }
);

const travelersCount = computed(() => {
  const raw = travel.requirements.find((r) => r.key === 'travelers')?.value;
  const n = raw ? parseInt(raw, 10) : NaN;
  return Number.isFinite(n) && n > 0 ? n : null;
});
</script>

<template>
  <aside class="state" :class="{ 'in-drawer': drawer }">
    <section>
      <button class="sec-toggle" @click="toggleReq()" :aria-expanded="reqOpen">
        <i class="pi pi-chevron-down toggle-ic" :class="{ closed: !reqOpen }" />
        Trip requirements
        <span class="count">{{ confirmed.length }}/{{ travel.requirements.length }}</span>
      </button>
      <div class="collapse" :class="{ closed: !reqOpen }">
        <div class="clip">
      <dl>
        <div v-for="r in confirmed" :key="r.key" class="req" :class="{ flash: flashKeys.has(r.key) }">
          <dt>{{ r.label }}</dt>
          <dd>{{ r.value }}</dd>
        </div>
      </dl>
      <div v-if="missing.length" class="missing">
        <p v-if="!confirmed.length" class="empty">Tell me about your trip to get started.</p>
        <p class="missing-title">Not specified</p>
        <ul>
          <li v-for="r in missing" :key="r.key">{{ r.label }}</li>
        </ul>
      </div>
        </div>
      </div>
    </section>

    <section>
      <button class="sec-toggle" @click="togglePlan()" :aria-expanded="planOpen">
        <i class="pi pi-chevron-down toggle-ic" :class="{ closed: !planOpen }" />
        Trip plan
        <span v-if="travel.plan.length" class="count">{{ travel.plan.length }}</span>
      </button>
      <div class="collapse" :class="{ closed: !planOpen }">
        <div class="clip">
          <TripPlanSection
            :items="travel.plan"
            :total="travel.planTotal"
            :currency="travel.planCurrency"
            :budget="travel.planBudget"
            :over-budget="travel.planOverBudget"
            :travelers="travelersCount"
            empty-text="Your picks will land here when you choose options from the chat."
          />
        </div>
      </div>
    </section>
  </aside>
</template>

<style scoped>
.state {
  width: var(--app-state-width);
  flex-shrink: 0;
  height: 100%;
  min-height: 0;
  background: var(--p-surface-50);
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
/* Section header button (collapsible). Animation classes in main.css. */
.sec-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  border: 0;
  background: transparent;
  color: var(--p-surface-500);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
  padding: 6px 8px;
  margin-bottom: 10px;
  border-radius: 6px;
  cursor: pointer;
  text-align: left;
}
.sec-toggle:hover {
  background: var(--p-surface-100);
  color: inherit;
}
.sec-toggle i {
  font-size: 0.65rem;
}
.sec-toggle .count {
  background: var(--p-surface-100);
  border-radius: 10px;
  padding: 1px 8px;
  font-size: 0.7rem;
  letter-spacing: 0;
  margin-left: auto;
}
/* .toggle-ic rotation + .collapse animation live in main.css (shared). */
dl {
  margin: 0;
}
/* Trip requirements definition list */
.req {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 5px 0;
  border-bottom: 1px dashed var(--p-surface-200);
  border-radius: 4px;
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
  min-width: 0;
}
/* Flash on rows just filled in by a live update. */
.req.flash {
  animation: req-flash 1.6s ease-out;
}
@keyframes req-flash {
  0% { background: color-mix(in srgb, var(--p-primary-500) 25%, transparent); }
  100% { background: transparent; }
}
/* Unspecified requirements */
.missing {
  margin-top: 10px;
}
.empty {
  font-size: 0.85rem;
  color: var(--p-surface-500);
  margin: 0 0 10px;
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
/* Narrow variant inside the small-screen drawer */
.in-drawer {
  width: auto;
  border: 0;
  padding: 0;
  overflow: visible;
}
</style>
