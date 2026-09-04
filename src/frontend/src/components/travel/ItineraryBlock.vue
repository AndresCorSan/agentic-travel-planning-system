<!-- Rich card inside assistant messages: day-by-day itinerary text plus
     a Lock-in button (mock save with toast feedback). -->
<script setup lang="ts">
import Button from 'primevue/button';
import { useToast } from 'primevue/usetoast';
import { computed } from 'vue';
import { getItineraryText } from '../../api/travelService';
import { renderRich } from '../chat/richtext';

const toast = useToast();
const html = computed(() => renderRich(getItineraryText()));

function lockPlan() {
  toast.add({ severity: 'success', summary: 'Plan locked in', detail: 'Lisbon · September 2026 saved (mock).', life: 2600 });
}
</script>

<template>
  <div class="plan">
    <div class="prose" v-html="html" />
    <Button label="Lock in this plan" icon="pi pi-check" size="small" @click="lockPlan()" />
  </div>
</template>

<style scoped>
.plan {
  border: 1px solid var(--p-surface-200);
  border-left: 3px solid var(--p-primary-500);
  border-radius: 10px;
  padding: 12px 14px;
  background: var(--p-surface-50);
  margin: 6px 0 4px;
}
/* .prose rich-text styles live in main.css (shared with AssistantMessage). */
</style>
