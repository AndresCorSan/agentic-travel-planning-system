<!-- Saved-plan detail page (/plans/:id): title + research, budget and
     itinerary blocks (mock content). -->
<script setup lang="ts">
import Button from 'primevue/button';
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import BudgetSummary from '../components/travel/BudgetSummary.vue';
import ItineraryBlock from '../components/travel/ItineraryBlock.vue';
import TravelOptionCard from '../components/travel/TravelOptionCard.vue';
import { useLibraryStore } from '../stores/travel';

const props = defineProps<{ id: string }>();
const library = useLibraryStore();
const router = useRouter();

onMounted(() => {
  if (!library.plans.length) void library.load();
});

const plan = computed(() => library.plans.find((p) => p.id === props.id));
</script>

<template>
  <div class="detail">
    <Button label="Back to plans" icon="pi pi-arrow-left" severity="secondary" text @click="router.push('/plans')" />
    <template v-if="plan">
      <h1>{{ plan.title }}</h1>
      <p class="muted">{{ plan.destination }} · {{ plan.dates }} · {{ plan.status }}</p>
      <h2>Research highlights</h2>
      <TravelOptionCard />
      <h2>Budget</h2>
      <BudgetSummary />
      <h2>Itinerary</h2>
      <ItineraryBlock />
    </template>
    <p v-else class="muted">Plan not found (mock data has two saved plans).</p>
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
</style>
