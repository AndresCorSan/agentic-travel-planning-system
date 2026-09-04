<!-- Application shell: left sidebar rail + routed content grid.
     On small screens the sidebar hides and opens as an overlay drawer. -->
<script setup lang="ts">
import Drawer from 'primevue/drawer';
import { RouterView } from 'vue-router';
import { useUiStore } from '../../stores/ui';
import Sidebar from '../sidebar/Sidebar.vue';

const ui = useUiStore();
</script>

<template>
  <div class="shell" :class="{ collapsed: ui.sidebarCollapsed }">
    <aside class="rail">
      <Sidebar />
    </aside>
    <main class="content">
      <RouterView />
    </main>
    <!-- Small screens: sidebar becomes an overlay drawer -->
    <Drawer v-model:visible="ui.navOpen" position="left" header="Trips & plans" class="mobile-drawer">
      <Sidebar overlay />
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
@media (max-width: 860px) {
  .shell,
  .shell.collapsed {
    grid-template-columns: 1fr;
  }
  .rail {
    display: none;
  }
}
</style>
