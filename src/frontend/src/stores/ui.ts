// UI preferences store (Pinia): sidebar/panel collapsed states, dark mode
// and accent color. Theme choices persist to localStorage.
import { defineStore } from 'pinia';
import { ref } from 'vue';
import { useLocalStorageToggle } from '../composables/useLocalStorageToggle';
import { DEFAULT_ACCENT_ID, applyAccent } from '../theme/accents';

export const useUiStore = defineStore('ui', () => {
  const sidebarCollapsed = ref(false);
  const navOpen = ref(false); // mobile: left nav drawer
  const statePanelOpen = ref(false); // small screens: right travel-state drawer
  const dark = ref(false);
  const accent = ref<string>(DEFAULT_ACCENT_ID);
  const [statePanelCollapsed, toggleStatePanel] = useLocalStorageToggle('travel-state-collapsed', false);

  function initTheme() {
    const saved = localStorage.getItem('travel-theme');
    dark.value = saved === 'dark' || (!saved && window.matchMedia?.('(prefers-color-scheme: dark)').matches);
    document.documentElement.classList.toggle('dark', dark.value);
    const savedAccent = localStorage.getItem('travel-accent');
    accent.value = savedAccent ?? DEFAULT_ACCENT_ID;
    applyAccent(accent.value);
  }
  function toggleTheme() {
    dark.value = !dark.value;
    document.documentElement.classList.toggle('dark', dark.value);
    localStorage.setItem('travel-theme', dark.value ? 'dark' : 'light');
  }
  function setAccent(id: string) {
    accent.value = id;
    localStorage.setItem('travel-accent', id);
    applyAccent(id);
  }
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value;
  }

  return { sidebarCollapsed, navOpen, statePanelOpen, statePanelCollapsed, dark, accent, initTheme, toggleTheme, setAccent, toggleSidebar, toggleStatePanel };
});
