<!-- Right-column panel of the chat view: trip requirements, research
     checklist and budget summary. Collapses to a slim toggle strip;
     on narrow screens it renders inside a slide-over drawer instead. -->
<script setup lang="ts">
import ProgressBar from 'primevue/progressbar';
import { computed } from 'vue';
import { useLocalStorageToggle } from '../../composables/useLocalStorageToggle';
import { useTravelStore } from '../../stores/travel';

defineProps<{ drawer?: boolean }>();

const travel = useTravelStore();

// Persisted open state per section (shared composable).
const [reqOpen, toggleReq] = useLocalStorageToggle('state-req-open');
const [researchOpen, toggleResearch] = useLocalStorageToggle('state-research-open');
const [budgetOpen, toggleBudget] = useLocalStorageToggle('state-budget-open');

const confirmed = computed(() => travel.requirements.filter((r) => r.value));
const missing = computed(() => travel.requirements.filter((r) => !r.value));

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
        <div v-for="r in confirmed" :key="r.key" class="req">
          <dt>{{ r.label }}</dt>
          <dd>{{ r.value }}</dd>
        </div>
      </dl>
      <div v-if="missing.length" class="missing">
        <p class="missing-title">Not specified</p>
        <ul>
          <li v-for="r in missing" :key="r.key"><i class="pi pi-circle" /> {{ r.label }}</li>
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
  font-size: 0.88rem;
}
.req dt {
  color: var(--p-surface-500);
}
.req dd {
  margin: 0;
  font-weight: 500;
  text-align: right;
}
/* Unspecified requirements */
.missing {
  margin-top: 10px;
}
.missing-title {
  font-size: 0.78rem;
  color: var(--p-surface-500);
  margin: 0 0 4px;
}
.missing ul {
  list-style: none;
  margin: 0;
  padding: 0;
  font-size: 0.85rem;
  color: var(--p-surface-500);
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.missing i {
  font-size: 0.5rem;
  margin-right: 6px;
  vertical-align: middle;
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
</style>
