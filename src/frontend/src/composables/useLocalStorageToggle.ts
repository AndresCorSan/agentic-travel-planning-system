/*
 * Reactive boolean persisted to localStorage, for collapsible UI that must
 * survive reloads (sidebar groups, travel-state sections, panel collapsed
 * state). Returns [state, toggle]; a missing key falls back to defaultValue.
 */
import { ref } from 'vue';
export function useLocalStorageToggle(key: string, defaultValue = true) {
  const stored = localStorage.getItem(key);
  const state = ref(stored === null ? defaultValue : stored === 'true');

  function toggle() {
    state.value = !state.value;
    localStorage.setItem(key, String(state.value));
  }

  return [state, toggle] as const;
}
