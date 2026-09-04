<!-- Accent-color selector shown in the sidebar prefs row at the bottom of
     the left column: full menu button when expanded, single color dot with
     a grid popover when the sidebar is collapsed to its rail. -->
<script setup lang="ts">
import Popover from 'primevue/popover';
import { computed, ref } from 'vue';
import { useUiStore } from '../../stores/ui';
import { ACCENTS } from '../../theme/accents';

withDefaults(defineProps<{ variant?: 'circle' | 'menu' }>(), { variant: 'circle' });

const ui = useUiStore();
const pop = ref<InstanceType<typeof Popover> | null>(null);

const current = computed(() => ACCENTS.find((a) => a.id === ui.accent) ?? ACCENTS[0]);

function pick(id: string) {
  ui.setAccent(id);
  pop.value?.hide();
}
</script>

<template>
  <!-- Collapsed rail: single color dot + grid popover -->
  <button
    v-if="variant === 'circle'"
    class="accent-btn"
    :style="{ background: current.dot }"
    aria-label="Choose accent color"
    title="Accent color"
    @click="pop?.toggle($event)"
  />
  <!-- Expanded sidebar: menu button (opens upward) + list popover -->
  <button v-else class="accent-menu-btn" aria-label="Choose accent color" @click="pop?.toggle($event)">
    <span class="mdot" :style="{ background: current.dot }" />
    <span class="mlabel">{{ current.label }}</span>
    <i class="pi pi-chevron-up" />
  </button>

  <Popover ref="pop">
    <p class="pop-title">Accent color</p>
    <template v-if="variant === 'menu'">
      <ul class="pop-list accent-list">
        <li v-for="a in ACCENTS" :key="a.id">
          <button class="pop-row" :class="{ sel: ui.accent === a.id }" @click="pick(a.id)">
            <span class="mdot" :style="{ background: a.dot }" />
            {{ a.label }}
            <i v-if="ui.accent === a.id" class="pi pi-check tick" />
          </button>
        </li>
      </ul>
    </template>
    <template v-else>
      <div class="pop-grid">
        <button
          v-for="a in ACCENTS"
          :key="a.id"
          class="dot"
          :class="{ active: ui.accent === a.id }"
          :style="{ background: a.dot }"
          :title="a.label"
          :aria-label="`Accent ${a.label}`"
          @click="pick(a.id)"
        >
          <i v-if="ui.accent === a.id" class="pi pi-check" />
        </button>
      </div>
    </template>
  </Popover>
</template>

<style scoped>
/* --- circle variant --- */
.accent-btn {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 0;
  outline: 2px solid var(--p-surface-300);
  outline-offset: 3px;
  cursor: pointer;
  padding: 0;
  flex-shrink: 0;
}
.accent-btn:hover {
  transform: scale(1.1);
}
/* --- menu variant --- */
.accent-menu-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  border: 1px solid var(--p-surface-200);
  background: transparent;
  color: inherit;
  border-radius: 9px;
  padding: 7px 10px;
  font-size: 0.85rem;
  cursor: pointer;
}
.accent-menu-btn:hover {
  background: var(--p-surface-100);
}
.accent-menu-btn i {
  margin-left: auto;
  font-size: 0.7rem;
  color: var(--p-surface-500);
}
.mdot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  flex-shrink: 0;
}
/* --- popover content (.pop-title/.pop-list/.pop-row shared in main.css) --- */
.accent-list {
  min-width: 150px;
}
.pop-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.dot {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 0;
  outline: 1px solid var(--p-surface-300);
  outline-offset: 1px;
  cursor: pointer;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.dot i {
  font-size: 0.65rem;
  font-weight: 700;
}
.dot.active {
  outline: 2px solid var(--p-surface-500);
}
.dot:hover {
  transform: scale(1.1);
}
/* Selected-row check mark */
.pop-row .tick {
  margin-left: auto;
  font-size: 0.75rem;
  color: var(--p-primary-600);
}
</style>
