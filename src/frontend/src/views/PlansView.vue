<!-- Saved-plans overview page (/plans): grid of plan cards linking to detail. -->
<script setup lang="ts">
import Button from 'primevue/button';
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useLibraryStore } from '../stores/travel';

const library = useLibraryStore();
const router = useRouter();

onMounted(() => {
  if (!library.plans.length) void library.load();
});
</script>

<template>
  <div class="plans">
    <div class="plans-head">
      <div>
        <h1>Saved plans</h1>
        <p class="muted">Locked-in itineraries, ready to revisit or refine.</p>
      </div>
      <Button label="New trip" icon="pi pi-plus" @click="router.push('/trip/lisbon-trip')" />
    </div>
    <div class="grid">
      <RouterLink v-for="p in library.plans" :key="p.id" :to="`/plans/${p.id}`" class="plan-card">
        <div class="plan-top">
          <strong>{{ p.title }}</strong>
          <span class="status">{{ p.status }}</span>
        </div>
        <p class="meta">{{ p.destination }} · {{ p.dates }}</p>
      </RouterLink>
    </div>
  </div>
</template>

<style scoped>
.plans {
  max-width: 56rem;
  margin: 0 auto;
  padding: 32px 24px;
  width: 100%;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.plans-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}
h1 {
  margin: 0;
  font-size: 1.3rem;
}
.plans-head p {
  margin: 4px 0 0;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}
.plan-card {
  border: 1px solid var(--p-surface-200);
  border-radius: 10px;
  padding: 14px 16px;
  background: var(--p-surface-50);
  color: inherit;
}
.plan-card:hover {
  border-color: var(--p-primary-400);
  text-decoration: none;
}
.plan-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: baseline;
}
.status {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--p-primary-600);
  white-space: nowrap;
}
</style>
