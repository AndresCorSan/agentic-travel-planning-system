<!-- Live research status while the reply streams: phase text plus one
     row per invoked subagent (spinner while active, tick when done). -->
<script setup lang="ts">
import { computed } from 'vue';
import ProgressSpinner from 'primevue/progressspinner';
import type { AgentRow } from '../../types';

const props = defineProps<{ status: string; agents: AgentRow[] }>();

// Status texts arrive with a static "…" ("Writing answer…"); the animated
// typing dots replace it so it isn't shown twice.
const cleanStatus = computed(() => props.status.replace(/(\u2026|\.{3})\s*$/, ''));
</script>

<template>
  <div class="thinking-row">
    <div class="avatar">AI</div>
    <div class="thinking-body">
      <span class="phase">
        <span>{{ cleanStatus }}</span>
        <span class="tballs" aria-hidden="true"><span></span><span></span><span></span></span>
      </span>
      <ul v-if="agents.length" class="agent-list">
        <li v-for="a in agents" :key="a.id" class="agent-row">
          <ProgressSpinner v-if="a.state === 'active'" stroke-width="5" class="spin" />
          <i v-else class="pi pi-check-circle ok" />
          <span>{{ a.label }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.thinking-row {
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  gap: 12px;
  margin: 14px 0;
}
.thinking-row .avatar {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: var(--p-primary-600);
  color: #fff;
  font-size: 0.7rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 0;
}
.thinking-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: var(--p-surface-500);
  font-size: 0.88rem;
}
.phase {
  display: flex;
  align-items: center;
  gap: 6px;
  /* Match the 30px avatar so single-line statuses center against it. */
  min-height: 30px;
}
.tballs {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  /* Sit on the text baseline so the dots look like they bounce off the ground. */
  align-self: flex-end;
  padding-bottom: 9px;
}
.tballs span {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--p-primary-600);
  animation: tbounce 1.2s infinite;
}
.tballs span:nth-child(2) { animation-delay: 0.15s; }
.tballs span:nth-child(3) { animation-delay: 0.3s; }
@keyframes tbounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-5px); opacity: 1; }
}
.agent-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.agent-row {
  display: flex;
  align-items: center;
  gap: 10px;
  color: inherit;
}
.spin {
  width: 18px;
  height: 18px;
  /* PrimeVue centers the spinner with margin auto: force left alignment. */
  margin: 0;
  flex-shrink: 0;
}
.ok {
  color: var(--p-green-500);
}
</style>
