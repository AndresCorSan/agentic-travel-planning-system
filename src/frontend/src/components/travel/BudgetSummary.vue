<!-- Rich card inside assistant messages: estimated cost vs budget with a
     progress bar. The travel-state panel renders its own flat rows. -->
<script setup lang="ts">
import ProgressBar from 'primevue/progressbar';
import { computed } from 'vue';
import { lisbonBudget } from '../../api/travelService';

// Card variant of the budget block (the travel-state panel renders its own
// flat rows instead). Reads the mock directly; wire to the store on backend
// integration.
const b = lisbonBudget();
const pct = computed(() => Math.round((b.estimated / (b.budget ?? b.estimated)) * 100));
const remaining = computed(() => (b.budget ?? 0) - b.estimated);
const fmt = (n: number) => `${b.currency}${n.toLocaleString()}`;
</script>

<template>
  <div class="budget">
    <div class="row"><span class="muted">Estimated trip cost</span><strong>{{ fmt(b.estimated) }}</strong></div>
    <div class="row"><span class="muted">Budget</span><span>{{ b.budget ? fmt(b.budget) : '—' }}</span></div>
    <ProgressBar :value="pct" :show-value="false" class="bar" />
    <div class="row"><span class="muted">Remaining</span><strong class="ok">{{ fmt(remaining) }}</strong></div>
  </div>
</template>

<style scoped>
.budget {
  border: 1px solid var(--p-surface-200);
  border-radius: 10px;
  padding: 12px 14px;
  background: var(--p-surface-50);
  margin: 6px 0 4px;
  font-size: 0.9rem;
  max-width: 26rem;
}
.row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}
/* .bar highlight + .ok colors live in main.css (shared with the panel). */
</style>
