<!-- Rich card inside assistant messages: flight/hotel/transport/activity/
     rental options grouped by category (mock Lisbon data). -->
<script setup lang="ts">
import { computed } from 'vue';
import { getLisbonOptions } from '../../api/travelService';

const icons: Record<string, string> = {
  flight: 'pi pi-send',
  hotel: 'pi pi-building',
  transport: 'pi pi-car',
  activity: 'pi pi-ticket',
  rental: 'pi pi-key'
};
const labels: Record<string, string> = {
  flight: 'Flights',
  hotel: 'Stays',
  transport: 'Transport',
  activity: 'Experiences',
  rental: 'Rental car'
};

const groups = computed(() => {
  const map = new Map<string, ReturnType<typeof getLisbonOptions>>();
  for (const o of getLisbonOptions()) {
    if (!map.has(o.category)) map.set(o.category, []);
    map.get(o.category)!.push(o);
  }
  return [...map.entries()];
});
</script>

<template>
  <div class="opts">
    <section v-for="[cat, items] in groups" :key="cat">
      <h4><i :class="icons[cat]" /> {{ labels[cat] }}</h4>
      <div v-for="o in items" :key="o.id" class="opt">
        <div class="opt-main">
          <strong>{{ o.title }}</strong>
          <span class="muted"> · {{ o.detail }}</span>
          <div class="meta">{{ o.meta }}</div>
        </div>
        <span class="price">{{ o.price }}</span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.opts {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 6px 0 4px;
}
h4 {
  margin: 0 0 6px;
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--p-surface-500);
  display: flex;
  gap: 6px;
  align-items: center;
}
.opt {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  border: 1px solid var(--p-surface-200);
  border-radius: 8px;
  padding: 8px 12px;
  background: var(--p-surface-50);
  font-size: 0.88rem;
}
.opt + .opt {
  margin-top: 6px;
}
.price {
  font-weight: 600;
  white-space: nowrap;
  color: var(--p-primary-700);
}
</style>
