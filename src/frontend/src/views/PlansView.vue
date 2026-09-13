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

function subtitle(p: { destination: string; dates: string }): string {
  return [p.destination, p.dates].filter(Boolean).join(' · ') || 'Saved trip';
}
</script>

<template>
  <div class="plans">
    <div class="plans-head">
      <div>
        <h1>Saved plans</h1>
        <p class="muted">Snapshots of your conversations, ready to revisit.</p>
      </div>
      <Button label="New trip" icon="pi pi-plus" @click="router.push('/trip/lisbon-trip')" />
    </div>
    <div v-if="!library.plans.length" class="empty">
      <b>No saved plans yet</b>
      <p>Open a conversation, pick some options and press “Save plan”.</p>
    </div>
    <div v-else class="grid">
      <RouterLink v-for="p in library.plans" :key="p.id" :to="`/plans/${p.id}`" class="plan-card">
        <strong>{{ p.title }}</strong>
        <p class="meta">{{ subtitle(p) }}</p>
        <p v-if="p.description" class="desc">{{ p.description }}</p>
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
  display: block;
}
.plan-card:hover {
  border-color: var(--p-primary-400);
  text-decoration: none;
}
.meta {
  margin: 4px 0 0;
  font-size: 0.85rem;
  color: var(--p-surface-500);
}
.desc {
  margin: 8px 0 0;
  font-size: 0.85rem;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.empty {
  border: 1.5px dashed var(--p-surface-300);
  border-radius: 10px;
  padding: 20px;
}
.empty p {
  margin: 4px 0 0;
  color: var(--p-surface-500);
  font-size: 0.88rem;
}
</style>
