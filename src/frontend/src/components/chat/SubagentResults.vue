<!-- Specialist subagent outputs for one assistant turn: one collapsed
     accordion per agent, rendered above the main answer. -->
<script setup lang="ts">
import { ref } from 'vue';
import type { SubagentResult } from '../../types';
import { renderRich } from './richtext';

defineProps<{ results: SubagentResult[] }>();

const EMOJI_BY_AGENT: Record<string, string> = {
  weather_agent: '🌤️',
  accommodation_agent: '🏨',
  transportation_agent: '✈️',
  activities_agent: '🎟️',
  rental_cars_agent: '🚗'
};

// Native <details> can't animate smoothly cross-browser, so open state
// is tracked here and the panel animates via grid-template-rows.
const open = ref<Record<string, boolean>>({});
function toggle(id: string) {
  open.value[id] = !open.value[id];
}
</script>

<template>
  <div class="agent-results">
    <div v-for="r in results" :key="r.id" class="agent-result" :class="{ open: open[r.id] }">
      <button class="agent-summary" :aria-expanded="!!open[r.id]" @click="toggle(r.id)">
        <span class="arrow">▸</span>
        <span class="emoji-circle">{{ EMOJI_BY_AGENT[r.id] ?? '🤖' }}</span>
        <span>View <span class="agent-name">{{ r.label }}</span> specialist response</span>
      </button>
      <div class="collapsible">
        <div class="clip">
          <div class="prose agent-body" v-html="renderRich(r.text)" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.agent-results {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}
.agent-result {
  border: 1px solid var(--p-surface-200);
  border-radius: 8px;
  background: var(--p-surface-50);
  overflow: hidden;
}
.agent-summary {
  cursor: pointer;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.85rem;
  font-weight: 600;
  width: 100%;
  border: 0;
  background: transparent;
  color: inherit;
  font-family: inherit;
  text-align: left;
}
.agent-summary:hover {
  background: var(--p-surface-100);
}
.arrow {
  color: var(--p-surface-500);
  font-size: 0.8rem;
  transition: transform 0.4s ease;
  display: inline-block;
}
.agent-result.open .arrow {
  transform: rotate(90deg);
}
.emoji-circle {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--p-surface-100);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
}
.agent-name {
  text-transform: capitalize;
  color: var(--p-primary-600);
}
.collapsible {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.5s ease;
}
.agent-result.open .collapsible {
  grid-template-rows: 1fr;
}
.clip {
  overflow: hidden;
  min-height: 0;
}
.agent-result.open .clip {
  border-top: 1px dashed var(--p-surface-300);
}
.agent-body {
  padding: 10px 12px 12px;
}
/* .prose rich-text styles live in main.css. */
</style>
