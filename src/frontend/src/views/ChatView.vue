<!-- Main chat screen (/trip/:id): header + message thread + floating composer
     on the left, collapsible travel-state panel on the right (drawer on
     narrow screens). -->
<script setup lang="ts">
import Drawer from 'primevue/drawer';
import { computed, onMounted, watch } from 'vue';
import ChatComposer from '../components/chat/ChatComposer.vue';
import ChatHeader from '../components/chat/ChatHeader.vue';
import MessageList from '../components/chat/MessageList.vue';
import TravelStatePanel from '../components/state/TravelStatePanel.vue';
import { useLibraryStore, useTravelStore } from '../stores/travel';
import { useUiStore } from '../stores/ui';

const props = defineProps<{ id: string }>();

const travel = useTravelStore();
const library = useLibraryStore();
const ui = useUiStore();

const chosenDestination = computed(() => travel.requirements.find((r) => r.key === 'destination')?.value ?? null);

async function load(id: string) {
  if (!library.conversations.length) await library.load();
  const conv = library.conversations.find((c) => c.id === id);
  // Unknown id (e.g. fresh mock trip): load an empty thread under that id.
  await travel.loadConversation(conv?.id ?? id, conv?.messageIds ?? []);
}
onMounted(() => load(props.id));
watch(() => props.id, load);

function onSend(text: string) {
  void travel.send(text);
}
function onChoose(id: string, name: string) {
  void travel.choose(id, name);
}
</script>

<template>
  <div class="chat-layout">
    <ChatHeader :conversation-id="props.id" />
    <div class="chat-body">
      <div class="chat-main">
        <MessageList
          :messages="travel.messages"
          :loading="travel.loading"
          :chosen-destination="chosenDestination"
          @choose="onChoose"
        />
        <ChatComposer :loading="travel.loading" @send="onSend" />
      </div>
      <div class="state-wrap" :class="{ collapsed: ui.statePanelCollapsed }">
        <button
          class="edge-toggle"
          :aria-label="ui.statePanelCollapsed ? 'Show travel state' : 'Hide travel state'"
          :title="ui.statePanelCollapsed ? 'Show travel state' : 'Hide travel state'"
          @click="ui.toggleStatePanel()"
        >
          <i :class="ui.statePanelCollapsed ? 'pi pi-chevron-left' : 'pi pi-chevron-right'" />
        </button>
        <TravelStatePanel />
      </div>
    </div>
    <Drawer v-model:visible="ui.statePanelOpen" position="right" header="Travel state">
      <TravelStatePanel drawer />
    </Drawer>
  </div>
</template>

<style scoped>
.chat-layout {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
.chat-body {
  display: flex;
  flex: 1;
  min-height: 0;
}
.chat-main {
  position: relative;
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
/* Right panel: grid columns animate (22px strip stays, panel 320px <-> 0).
   The panel stays mounted; the wrapper clips it mid-animation. */
.state-wrap {
  min-height: 0;
  display: grid;
  grid-template-columns: 22px var(--app-state-width);
  transition: grid-template-columns 0.32s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}
.state-wrap.collapsed {
  grid-template-columns: 22px 0px;
}
/* Slim strip keeping the toggle reachable while the panel is collapsed. */
.edge-toggle {
  width: 22px;
  flex-shrink: 0;
  border: 0;
  border-right: 1px solid var(--p-surface-200);
  background: var(--p-surface-50);
  color: var(--p-surface-500);
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
}
.edge-toggle:hover {
  background: var(--p-surface-100);
  color: var(--p-primary-600);
}
/* Narrow screens: inline panel becomes a slide-over drawer instead. */
@media (max-width: 1180px) {
  .state-wrap {
    display: none;
  }
}
@media (min-width: 1181px) {
  :deep(.p-drawer) {
    display: none;
  }
}
</style>
