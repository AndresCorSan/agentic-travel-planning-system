<!-- Dark/light switch shown in the sidebar prefs row at the bottom of the
     left column: sliding pill when expanded, single cycle icon when the
     sidebar is collapsed to its rail. -->
<script setup lang="ts">
import Button from 'primevue/button';
import { useUiStore } from '../../stores/ui';

withDefaults(defineProps<{ variant?: 'pill' | 'cycle' }>(), { variant: 'pill' });

const ui = useUiStore();
</script>

<template>
  <!-- Expanded: sliding day/night pill (option 3) -->
  <button
    v-if="variant === 'pill'"
    class="theme-pill"
    :class="{ dark: ui.dark }"
    role="switch"
    :aria-checked="ui.dark"
    aria-label="Toggle dark mode"
    :title="ui.dark ? 'Switch to light mode' : 'Switch to dark mode'"
    @click="ui.toggleTheme()"
  >
    <span class="bg-sun"><i class="pi pi-sun" /></span>
    <span class="bg-moon"><i class="pi pi-moon" /></span>
    <span class="thumb">
      <i :class="ui.dark ? 'pi pi-moon' : 'pi pi-sun'" />
    </span>
  </button>
  <!-- Collapsed rail: cycling icon button (option 5) -->
  <Button
    v-else
    :icon="ui.dark ? 'pi pi-sun' : 'pi pi-moon'"
    severity="secondary"
    text
    rounded
    aria-label="Toggle dark mode"
    @click="ui.toggleTheme()"
  />
</template>

<style scoped>
.theme-pill {
  position: relative;
  width: 74px;
  height: 32px;
  border-radius: 18px;
  background: var(--p-surface-100);
  border: 1px solid var(--p-surface-200);
  cursor: pointer;
  padding: 0;
  flex-shrink: 0;
  transition: background 0.25s;
}
.theme-pill.dark {
  background: #242832;
  border-color: #2f3541;
}
.theme-pill .bg-sun,
.theme-pill .bg-moon {
  position: absolute;
  top: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  font-size: 0.72rem;
  opacity: 0.45;
}
.theme-pill .bg-sun {
  left: 10px;
  color: var(--p-surface-500);
}
.theme-pill .bg-moon {
  right: 10px;
  color: var(--p-surface-500);
}
.theme-pill .thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 34px;
  height: 26px;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.78rem;
  color: var(--p-primary-600);
  transition: left 0.25s;
}
.theme-pill.dark .thumb {
  left: 36px;
  background: #14161b;
  color: var(--p-primary-400);
}
.theme-pill:focus-visible {
  outline: 2px solid var(--p-primary-500);
  outline-offset: 2px;
}
</style>
