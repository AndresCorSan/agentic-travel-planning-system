<!-- Rich card inside assistant messages: candidate destinations with
     score badges and a Choose button per destination. -->
<script setup lang="ts">
import Badge from 'primevue/badge';
import Button from 'primevue/button';
import { getDestinations } from '../../api/travelService';

defineProps<{ chosen: string | null }>();
const emit = defineEmits<{ choose: [id: string, name: string] }>();

const items = getDestinations();
</script>

<template>
  <div class="dest-list">
    <div v-for="d in items" :key="d.id" class="dest" :class="{ selected: chosen === d.name }">
      <div class="dest-head">
        <div>
          <strong>{{ d.name }}</strong>
          <span class="muted"> · {{ d.country }}</span>
        </div>
        <Badge :value="`${d.suitability}/100`" severity="success" />
      </div>
      <p class="tagline">{{ d.tagline }}</p>
      <ul>
        <li v-for="h in d.highlights" :key="h">{{ h }}</li>
      </ul>
      <p class="meta">Watch out: {{ d.drawback }}</p>
      <Button
        :label="chosen === d.name ? 'Selected' : `Choose ${d.name}`"
        size="small"
        :severity="chosen === d.name ? 'success' : 'primary'"
        :disabled="chosen === d.name"
        :icon="chosen === d.name ? 'pi pi-check' : undefined"
        @click="emit('choose', d.id, d.name)"
      />
    </div>
  </div>
</template>

<style scoped>
.dest-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 6px 0 4px;
}
.dest {
  border: 1px solid var(--p-surface-200);
  border-radius: 10px;
  padding: 12px 14px;
  background: var(--p-surface-50);
}
.dest.selected {
  border-color: var(--p-primary-400);
}
.dest-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.tagline {
  margin: 6px 0;
  font-size: 0.9rem;
}
ul {
  margin: 0 0 6px;
  padding-left: 18px;
  font-size: 0.87rem;
}
</style>
