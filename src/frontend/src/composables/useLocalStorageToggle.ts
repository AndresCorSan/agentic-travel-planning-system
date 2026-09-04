import { ref } from 'vue';

// Boolean flag persisted to localStorage, used for every collapsible
// section (sidebar groups, travel-state sections, panel collapsed state).
// Missing key falls back to `defaultValue`.
export function useLocalStorageToggle(key: string, defaultValue = true) {
  const stored = localStorage.getItem(key);
  const state = ref(stored === null ? defaultValue : stored === 'true');

  function toggle() {
    state.value = !state.value;
    localStorage.setItem(key, String(state.value));
  }

  return [state, toggle] as const;
}
