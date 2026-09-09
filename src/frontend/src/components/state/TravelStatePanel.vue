<!-- Right-column panel of the chat view: trip requirements, research
     checklist and budget summary. Collapses to a slim toggle strip;
     on narrow screens it renders inside a slide-over drawer instead. -->
<script setup lang="ts">
import ProgressBar from 'primevue/progressbar';
import { computed, ref, watch } from 'vue';
import { useLocalStorageToggle } from '../../composables/useLocalStorageToggle';
import { useTravelStore } from '../../stores/travel';
import { formatOptionPrice } from '../chat/richtext';

defineProps<{ drawer?: boolean }>();

const travel = useTravelStore();

// Persisted open state per section (shared composable).
const [reqOpen, toggleReq] = useLocalStorageToggle('state-req-open');
const [researchOpen, toggleResearch] = useLocalStorageToggle('state-research-open');
const [planOpen, togglePlan] = useLocalStorageToggle('state-plan-open');
const [budgetOpen, toggleBudget] = useLocalStorageToggle('state-budget-open');

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

const researchRows = computed(() => [
  { label: 'Weather', state: travel.research.weather },
  { label: 'Transportation', state: travel.research.transportation },
  { label: 'Accommodation', state: travel.research.accommodation },
  { label: 'Activities', state: travel.research.activities },
  { label: 'Rental car', state: travel.research.rentalCar }
]);
const researchDone = computed(() => researchRows.value.filter((r) => r.state === 'done').length);

// Flat budget rows (unlike BudgetSummary's card, which suits the chat).
const pct = computed(() =>
  travel.budget.budget ? Math.round((travel.budget.estimated / travel.budget.budget) * 100) : 0
);
const fmt = (n: number) => `${travel.budget.currency}${n.toLocaleString()}`;
</script>

<template>
  <aside class="state" :class="{ 'in-drawer': drawer }">
    <section>
      <button class="sec-toggle" @click="toggleReq()" :aria-expanded="reqOpen">
        <i class="pi pi-chevron-down toggle-ic" :class="{ closed: !reqOpen }" />
        Trip requirements
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
      <button class="sec-toggle" @click="toggleResearch()" :aria-expanded="researchOpen">
        <i class="pi pi-chevron-down toggle-ic" :class="{ closed: !researchOpen }" />
        Research <span class="muted">{{ researchDone }}/{{ researchRows.length }}</span>
      </button>
      <div class="collapse" :class="{ closed: !researchOpen }">
        <div class="clip">
      <ul class="research">
        <li v-for="r in researchRows" :key="r.label">
          <i v-if="r.state === 'done'" class="pi pi-check-circle ok" />
          <i v-else-if="r.state === 'active'" class="pi pi-spin pi-spinner active" />
          <i v-else class="pi pi-circle muted" />
          {{ r.label }}
        </li>
      </ul>
        </div>
      </div>
    </section>

    <section>
      <button class="sec-toggle" @click="togglePlan()" :aria-expanded="planOpen">
        <i class="pi pi-chevron-down toggle-ic" :class="{ closed: !planOpen }" />
        Trip plan
        <span v-if="travel.plan.length" class="muted">{{ formatOptionPrice({ price: travel.planTotal, currency: travel.planCurrency, per_person: false }) }}</span>
      </button>
      <div class="collapse" :class="{ closed: !planOpen }">
        <div class="clip">
          <p v-if="!travel.plan.length" class="empty">Nothing saved yet — pick options from the chat.</p>
          <dl v-else>
            <div v-for="item in travel.plan" :key="`${item.category}:${item.option_id}`" class="req">
              <dt>{{ item.label }}<span class="muted"> · {{ item.category }}</span></dt>
              <dd>{{ formatOptionPrice(item) || '—' }}</dd>
            </div>
          </dl>
          <div v-if="travel.plan.length" class="row total">
            <span>Total</span>
            <strong>{{ formatOptionPrice({ price: travel.planTotal, currency: travel.planCurrency, per_person: false }) || '—' }}</strong>
          </div>
          <p v-if="travel.planOverBudget" class="over">Over budget.</p>
        </div>
      </div>
    </section>

    <section>
      <button class="sec-toggle" @click="toggleBudget()" :aria-expanded="budgetOpen">
        <i class="pi pi-chevron-down toggle-ic" :class="{ closed: !budgetOpen }" />
        Budget
      </button>
      <div class="collapse" :class="{ closed: !budgetOpen }">
        <div class="clip">
      <div class="budget-rows">
        <div class="row"><span class="muted">Estimated</span><strong>{{ fmt(travel.budget.estimated) }}</strong></div>
        <div class="row"><span class="muted">Budget</span><span>{{ travel.budget.budget ? fmt(travel.budget.budget) : '—' }}</span></div>
        <ProgressBar :value="pct" :show-value="false" class="bar" />
        <div class="row"><span class="muted">Remaining</span><strong class="ok">{{ fmt((travel.budget.budget ?? 0) - travel.budget.estimated) }}</strong></div>
      </div>
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
/* Research checklist */
.research {
  list-style: none;
  margin: 0;
  padding: 0;
  font-size: 0.88rem;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.research i {
  margin-right: 8px;
}
.research .active {
  color: var(--p-primary-500);
}
/* Flat budget rows (.ok highlight + .bar in main.css) */
.budget-rows .row {
  display: flex;
  justify-content: space-between;
  font-size: 0.88rem;
  margin-bottom: 4px;
}
/* Narrow variant inside the small-screen drawer */
.in-drawer {
  width: auto;
  border: 0;
  padding: 0;
  overflow: visible;
}
/* Trip plan section */
.row.total {
  display: flex;
  justify-content: space-between;
  font-size: 0.88rem;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid var(--p-surface-200);
}
.over {
  margin: 6px 0 0;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--p-red-500);
}
</style>
