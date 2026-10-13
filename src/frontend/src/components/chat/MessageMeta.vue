<!-- Turn metadata under assistant messages: clock time + duration,
     tokens + authoritative OpenRouter cost on a single line with subtle
     icons, full input/output/model breakdown in the tooltip. Root keeps
     class "time" so each parent's scoped style still applies. -->
<script setup lang="ts">
import { computed } from 'vue';
import MessageTime from './MessageTime.vue';
import type { MessageStats } from '../../types';

const props = defineProps<{ createdAt: string; stats?: MessageStats }>();
// GOTCHA: root keeps class `time` so each parent's scoped style still applies.

// CONTRACT: `stats` carries the backend turn cost (`cost_usd`, `total_tokens`, `duration_s`).
function compact(n: number): string {
  if (n >= 1000) {
    const v = n / 1000;
    return `${v >= 100 ? Math.round(v) : v.toFixed(1).replace(/\.0$/, '')}k`;
  }
  return String(n);
}

const duration = computed(() =>
  typeof props.stats?.duration_s === 'number' ? `${props.stats.duration_s}s` : null
);
const tokens = computed(() =>
  typeof props.stats?.total_tokens === 'number' ? `${compact(props.stats.total_tokens)} tok` : null
);
const cost = computed(() =>
  typeof props.stats?.cost_usd === 'number' ? props.stats.cost_usd.toFixed(4) : null
);

const tooltip = computed(() => {
  const s = props.stats;
  if (!s) return undefined;
  const bits = [`in ${s.input_tokens} · out ${s.output_tokens}`, `${s.duration_s}s`];
  if (s.model) bits.push(s.model);
  if (typeof s.cost_usd === 'number') bits.push(`$${s.cost_usd.toFixed(4)}`);
  return bits.join(' · ');
});
</script>

<template>
  <span class="time meta-line" :title="tooltip">
    <MessageTime :value="createdAt" /><template v-if="duration"><span class="stat"><i class="pi pi-bolt" />{{ duration }}</span></template><template v-if="tokens"><span class="stat"><i class="pi pi-microchip" />{{ tokens }}</span></template><template v-if="cost"><span class="stat"><i class="pi pi-dollar" />{{ cost }}</span></template>
  </span>
</template>

<style scoped>
.meta-line .stat {
  margin-left: 10px;
  white-space: nowrap;
}
.meta-line .stat i {
  /* Icon fonts render thin at 0.7rem (notably the microchip strokes):
     match the text size and add a hairline stroke so they stay legible. */
  font-size: 0.78rem;
  vertical-align: -2px;
  margin-right: 4px;
  -webkit-text-stroke: 0.4px currentColor;
}
</style>
