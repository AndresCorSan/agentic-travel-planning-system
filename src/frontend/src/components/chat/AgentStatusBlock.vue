<!-- Live research status while the reply streams: phase text plus one
     row per invoked subagent (spinner while active, tick when done). -->
<script setup lang="ts">
import ProgressSpinner from 'primevue/progressspinner';
import type { AgentRow } from '../../types';

defineProps<{ status: string; agents: AgentRow[] }>();
</script>

<template>
  <div class="thinking-row">
    <div class="avatar">AI</div>
    <div class="thinking-body">
      <span class="phase">{{ status }}</span>
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
  gap: 10px;
  /* Match the 30px avatar so single-line statuses center against it. */
  min-height: 30px;
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
