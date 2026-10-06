<!-- Application shell: left sidebar rail + routed content + right
     travel-state card (trip routes only, docked — not full-height).
     On small screens the sidebar hides and opens as an overlay drawer
     (same for the state panel). -->
<script setup lang="ts">
import Drawer from 'primevue/drawer';
import { computed } from 'vue';
import { RouterView, useRoute } from 'vue-router';
import { useUiStore } from '../../stores/ui';
import Sidebar from '../sidebar/Sidebar.vue';
import TravelStatePanel from '../travel-state/TravelStatePanel.vue';

const ui = useUiStore();
const route = useRoute();
// Right rail only exists on the chat screen; other pages go full width.
const showState = computed(() => route.name === 'trip');
</script>

<template>
  <div class="shell" :class="{ collapsed: ui.sidebarCollapsed, 'with-state': showState }">
    <aside class="rail">
      <Sidebar />
    </aside>
    <main class="content">
      <RouterView />
    </main>
    <div v-if="showState" class="state-wrap" :class="{ collapsed: ui.statePanelCollapsed }">
      <button
        class="edge-toggle"
        :aria-label="ui.statePanelCollapsed ? 'Show travel state' : 'Hide travel state'"
        :title="ui.statePanelCollapsed ? 'Show travel state' : 'Hide travel state'"
        @click="ui.toggleStatePanel()"
      >
        <i :class="ui.statePanelCollapsed ? 'pi pi-chevron-left' : 'pi pi-chevron-right'" />
      </button>
      <div class="state-card">
        <TravelStatePanel />
      </div>
    </div>
    <!-- Small screens: sidebar becomes an overlay drawer -->
    <Drawer v-model:visible="ui.navOpen" position="left" header="Trips & plans" class="mobile-drawer">
      <Sidebar overlay />
    </Drawer>
    <Drawer v-if="showState" v-model:visible="ui.statePanelOpen" position="right" header="Travel state" class="state-drawer">
      <TravelStatePanel drawer />
    </Drawer>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: var(--app-sidebar-width) 1fr;
  height: 100vh;
  overflow: hidden;
  transition: grid-template-columns 0.32s cubic-bezier(0.4, 0, 0.2, 1);
}
.shell.collapsed {
  grid-template-columns: var(--app-sidebar-collapsed) 1fr;
}
.shell.with-state {
  grid-template-columns: var(--app-sidebar-width) 1fr auto;
}
.shell.collapsed.with-state {
  grid-template-columns: var(--app-sidebar-collapsed) 1fr auto;
}
.rail {
  border-right: 1px solid var(--p-surface-200);
  background: var(--p-surface-50);
  overflow: hidden;
  min-height: 0;
}
.content {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
/* Right side: docked card (same 18px/shadow language as title pill and
   composer). Column + fold behavior unchanged; grid columns animate
   (toggle stays, card 320px <-> 0) and the card clips mid-animation. */
.state-wrap {
  min-height: 0;
  display: grid;
  grid-template-columns: auto var(--app-state-width);
  transition: grid-template-columns 0.32s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  background: transparent;
  /* Left breathing room: the chat scrollbar lives on its column's edge,
     so this gap keeps it visually attached to the chat, not the card. */
  padding: 14px 14px 14px 10px;
}
.state-wrap.collapsed {
  grid-template-columns: auto 0px;
}
/* Card carrying the panel: same language as title pill + composer. */
.state-card {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  border: 1px solid var(--p-surface-200);
  border-radius: 18px;
  background: var(--p-surface-0);
  box-shadow: 0 12px 32px rgb(60 50 30 / 0.14);
}
html.dark .state-card {
  box-shadow: none;
}
/* Toggle as a small floating pill overlapping the card's edge. */
.edge-toggle {
  width: 22px;
  height: 48px;
  align-self: center;
  flex-shrink: 0;
  margin-right: -12px;
  z-index: 1;
  border: 1px solid var(--p-surface-200);
  border-radius: 99px;
  background: var(--p-surface-0);
  box-shadow: 0 4px 14px rgb(60 50 30 / 0.12);
  color: var(--p-surface-500);
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
}
html.dark .edge-toggle {
  box-shadow: none;
}
.edge-toggle:hover {
  color: var(--p-primary-600);
}
@media (max-width: 860px) {
  .shell,
  .shell.collapsed,
  .shell.with-state,
  .shell.collapsed.with-state {
    grid-template-columns: 1fr;
  }
  .rail {
    display: none;
  }
}
/* Narrow screens: inline panel becomes a slide-over drawer instead. */
@media (max-width: 1180px) {
  .state-wrap {
    display: none;
  }
}
@media (min-width: 1181px) {
  :deep(.state-drawer) {
    display: none;
  }
}
</style>
