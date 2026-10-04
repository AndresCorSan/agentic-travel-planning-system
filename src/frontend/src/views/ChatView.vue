<!-- Main chat screen (/trip/:id): floating title pill over the message
     thread + floating composer. The travel-state rail lives in AppShell
     (full-height, trip routes only). -->
<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import ChatComposer from '../components/chat/ChatComposer.vue';
import MessageList from '../components/chat/MessageList.vue';
import WelcomeHero from '../components/chat/WelcomeHero.vue';
import { useLibraryStore, useTravelStore } from '../stores/travel';
import { useUiStore } from '../stores/ui';

const props = defineProps<{ id: string }>();

const travel = useTravelStore();
const library = useLibraryStore();
const ui = useUiStore();

const title = computed(
  () => library.conversations.find((c) => c.id === props.id)?.title ?? 'Trip'
);
// The upper title only appears once the trip has a real title: fresh threads
// (no stored row, or still carrying the 'Untitled trip' placeholder)
// show the bare hero instead.
const DEFAULT_TITLES = new Set(['Trip', 'Untitled trip']);
const showTitle = computed(() => {
  const found = library.conversations.find((c) => c.id === props.id);
  return !!found && !DEFAULT_TITLES.has(found.title);
});

const chosenDestination = computed(() => travel.requirements.find((r) => r.key === 'destination')?.value ?? null);
// Fresh thread (no stored row): show the hero instantly, even mid-rehydrate.
// Otherwise the AI status block flashes before the hero appears.
const isFreshTrip = computed(() => library.loaded && !library.conversations.some((c) => c.id === props.id));
const showWelcome = computed(() => isFreshTrip.value && !travel.messages.length && !travel.streaming);
// Suggestion clicks fill the composer for editing before sending.
const composerDraft = ref('');
async function onSuggestion(text: string) {
  // Bounce through empty so clicking the same suggestion twice still refires
  // the composer's draft watcher (it only reacts to value changes).
  composerDraft.value = '';
  await nextTick();
  composerDraft.value = text;
}

async function load(id: string) {
  if (!library.loaded) await library.load();
  const conv = library.conversations.find((c) => c.id === id);
  // Unknown id: load an empty thread under that id.
  await travel.loadConversation(conv?.id ?? id);
}
onMounted(() => load(props.id));
watch(() => props.id, load);

function onSend(text: string) {
  void travel.send(text);
}
function onChoose(messageId: string, _id: string, name: string) {
  // Optimistic: mark Selected instantly; the confirmed requirements catch
  // up when the backend round-trip completes.
  travel.vote(messageId, name);
  // The choice resumes the destination interrupt as a
  // regular user message; the graph continues from main_llm.
  void travel.send(`Let's go with ${name}.`);
}
</script>

<template>
  <div class="chat-layout">
    <div class="chat-body">
      <div class="chat-main">
        <Transition name="title-in">
          <div v-if="showTitle" class="title-pill" :title="title">
            <span class="title-text">{{ title }}</span>
            <span class="title-u" aria-hidden="true" />
          </div>
        </Transition>
        <button
          class="float-btn left only-mobile"
          aria-label="Open navigation"
          @click="ui.navOpen = true"
        >
          <i class="pi pi-bars" />
        </button>
        <button
          class="float-btn right only-narrow"
          aria-label="Toggle travel state"
          @click="ui.statePanelOpen = true"
        >
          <i class="pi pi-list" />
        </button>
        <WelcomeHero v-if="showWelcome" @select="onSuggestion" />
        <MessageList
          v-else
          :messages="travel.messages"
          :loading="travel.loading"
          :status-text="travel.streamStatus"
          :agents="travel.agentRows"
          :streaming="travel.streaming"
          :chosen-destination="chosenDestination"
          @choose="onChoose"
        />
        <ChatComposer :loading="travel.loading" :draft-override="composerDraft" @send="onSend" />
      </div>
    </div>
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
/* Floating title bar: same recipe as the composer below (translucent
   surface-0 + blur, hairline border, 18px radius) */
.title-pill {
  position: absolute;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 5;
  width: min(calc(100% - 40px), var(--app-max-chat-width));
  padding: 10px 26px 12px;
  text-align: center;
  background: color-mix(in srgb, var(--p-surface-0) 78%, transparent);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid var(--p-surface-200);
  border-radius: 18px;
  box-shadow: 0 12px 32px rgba(60, 50, 30, 0.16);
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.12rem;
  white-space: nowrap;
}
.title-text {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
}
.title-u {
  display: block;
  height: 2px;
  width: 72px;
  margin: 6px auto 0;
  border-radius: 99px;
  background: var(--p-primary-600);
}
html.dark .title-pill {
  box-shadow: none;
}
/* Entrance animation: the bar drops in first, then the
   accent rule draws itself with a delay. */
.title-in-enter-active .title-pill {
  animation: title-bar-in 0.7s cubic-bezier(0.2, 0.7, 0.3, 1);
}
.title-in-enter-active .title-u {
  animation: title-u-draw 0.5s cubic-bezier(0.2, 0.7, 0.3, 1) 0.55s both;
}
@keyframes title-bar-in {
  from {
    opacity: 0;
    transform: translate(-50%, -14px);
  }
  to {
    opacity: 1;
    transform: translate(-50%, 0);
  }
}
@keyframes title-u-draw {
  from {
    transform: scaleX(0);
  }
  to {
    transform: scaleX(1);
  }
}
.title-in-leave-active {
  transition: opacity 0.18s ease;
}
.title-in-leave-to {
  opacity: 0;
}
/* Floating round buttons (narrow screens only) */
.float-btn {
  position: absolute;
  top: 14px;
  z-index: 6;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid var(--p-surface-200);
  background: #fff;
  box-shadow:
    0 2px 6px rgb(30 25 15 / 0.1),
    0 18px 44px rgb(30 25 15 / 0.22);
  color: var(--p-surface-500);
  cursor: pointer;
  display: none;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  padding: 0;
}
html.dark .float-btn {
  background: #20242e;
  border-color: #3d4452;
  box-shadow:
    0 2px 6px rgb(0 0 0 / 0.5),
    0 18px 44px rgb(0 0 0 / 0.65);
}
.float-btn:hover {
  color: var(--p-primary-600);
}
.float-btn.left {
  left: 16px;
}
.float-btn.right {
  right: 16px;
}
@media (max-width: 860px) {
  .only-mobile {
    display: inline-flex;
  }
  .title-pill {
    /* Clear both floating buttons (40px + 16px margin each side). */
    width: calc(100% - 112px);
    padding-left: 16px;
    padding-right: 16px;
  }
}
@media (max-width: 1180px) {
  .only-narrow {
    display: inline-flex;
  }
}
@media (max-width: 1180px) and (min-width: 861px) {
  .title-pill {
    width: calc(100% - 112px);
  }
}
</style>
