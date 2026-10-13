<!-- Message timestamp: "now" during the first minute, then the local
     clock time (HH:MM). Non-ISO values render as-is. Re-evaluates
     every 30s so old messages flip on their own without a page reload.
     Root keeps class "time" so each parent's scoped style still applies. -->
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

const props = defineProps<{ value: string }>();

const tick = ref(0);
let timer: ReturnType<typeof setInterval> | undefined;
// Re-evaluate every 30s so messages flip from "now" on their own.
onMounted(() => {
  timer = setInterval(() => {
    tick.value++;
  }, 30000);
});
onUnmounted(() => {
  if (timer) clearInterval(timer);
});

// GOTCHA: root keeps class `time` so each parent's scoped style still applies.
const label = computed(() => {
  void tick.value;
  const raw = String(props.value ?? '').trim();
  let t = Date.parse(raw);
  if (Number.isNaN(t)) {
    // Tolerate stray characters (or embedded quotes) around an ISO datetime.
    const m = raw.match(/(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?/);
    if (!m) return props.value;
    t = Date.parse(`${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6] ?? '00'}`);
    if (Number.isNaN(t)) return props.value;
  }
  if (Date.now() - t < 60000) return 'now';
  return new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
});
</script>

<template>
  <span class="time" data-msgtime>{{ label }}</span>
</template>
