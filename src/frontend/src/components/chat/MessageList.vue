<!-- Scrollable message thread in the center of the chat view.
     Only this column scrolls. Sending pins your bubble to the top with
     room below for the reply (which eats that room as it streams in);
     when the reply finishes the view drops to the bottom. Opening a
     conversation with history simply starts at the bottom. -->
<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import type { AgentRow, ChatMessage } from '../../types';
import AgentStatusBlock from './AgentStatusBlock.vue';
import AssistantMessage from './AssistantMessage.vue';
import UserMessage from './UserMessage.vue';

const props = defineProps<{
  messages: ChatMessage[];
  loading: boolean;
  statusText: string;
  agents: AgentRow[];
  streaming: ChatMessage | null;
  chosenDestination: string | null;
}>();
const emit = defineEmits<{ choose: [messageId: string, id: string, name: string] }>();

const scroller = ref<HTMLElement | null>(null);

// While the reply is being generated, the last message is the just-sent
// user message: show the live status block until answer tokens arrive,
// then the streaming bubble takes its place.
const lastIsUser = computed(() => {
  const msgs = props.messages;
  return msgs.length > 0 && msgs[msgs.length - 1].role === 'user';
});
const hasStreamingText = computed(() => !!props.streaming?.text);
// Stall detection: tokens normally arrive in a steady flow, so if none
// arrives for STALL_MS while the turn is still loading, the LLM is most
// likely thinking or running a tool — show the dots only then, so the
// bubble doesn't look frozen. Any new token hides them again.
const STALL_MS = 1500;
const stalled = ref(false);
let stallTimer: number | undefined;
function clearStallTimer() {
  if (stallTimer !== undefined) {
    clearTimeout(stallTimer);
    stallTimer = undefined;
  }
}
function armStallTimer() {
  clearStallTimer();
  stalled.value = false;
  stallTimer = window.setTimeout(() => {
    if (props.loading) stalled.value = true;
  }, STALL_MS);
}
watch(
  () => props.streaming?.text?.length ?? 0,
  () => {
    if (props.loading && hasStreamingText.value) armStallTimer();
  }
);
watch(
  () => props.loading,
  (v) => {
    if (v) {
      if (lastIsUser.value) void scrollToUserTop();
      if (hasStreamingText.value) armStallTimer();
    } else {
      clearStallTimer();
      stalled.value = false;
      // Reply finished: reveal the full answer at the bottom.
      void scrollDown();
    }
  }
);
onUnmounted(clearStallTimer);
const showStreamingBusy = computed(() => props.loading && hasStreamingText.value && stalled.value);
const showStatus = computed(
  () => props.loading && (!props.messages.length || lastIsUser.value) && !hasStreamingText.value
);

// Elastic spacer under the just-sent user message: it always covers
// exactly the gap between the real content below your bubble (status
// block, streamed text, padding, ...) and one viewport, so the bubble
// sits at the top with room below that the reply eats as it grows.
// Stateless: the current spacer is subtracted arithmetically before
// measuring, so no baseline snapshot is needed.
const spacerPx = ref(0);
const showReplySpacer = computed(() => props.loading && lastIsUser.value && props.messages.length > 0);

async function scrollDown() {
  await nextTick();
  scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' });
}
// Refit the spacer; returns the last user bubble's top (content coords)
// so callers can scroll to it, or null when there is nothing to fit.
async function fitSpacer(): Promise<number | null> {
  if (!showReplySpacer.value) return null;
  await nextTick();
  const el = scroller.value;
  if (!el) return null;
  const rows = el.querySelectorAll('.user-row');
  const last = rows[rows.length - 1] as HTMLElement | undefined;
  if (!last) return null;
  const userTop = last.getBoundingClientRect().top - el.getBoundingClientRect().top + el.scrollTop;
  const below = el.scrollHeight - spacerPx.value - userTop;
  spacerPx.value = Math.max(el.clientHeight - below - 16, 0);
  return userTop;
}
// Anchor the last user bubble to the top of the viewport.
async function scrollToUserTop() {
  const userTop = await fitSpacer();
  if (userTop !== null) scroller.value?.scrollTo({ top: userTop - 16, behavior: 'smooth' });
}
onMounted(scrollDown);
// New user message while sending: pin it to the top (only for fresh
// sends — history loads have loading == false and keep bottom scroll).
watch(
  () => props.messages.length,
  () => {
    if (props.loading && lastIsUser.value) void scrollToUserTop();
  }
);
// Reply content growing (tokens, status block, agent rows): refit so the
// text fills the reserved blank instead of extending the page. Floor of
// 0: once the reply fills the viewport the view simply stays put until
// the final scrollDown on completion.
watch([() => props.streaming?.text?.length ?? 0, () => props.agents.length, () => props.statusText], () => {
  void fitSpacer();
});
</script>

<template>
  <div ref="scroller" class="messages">
    <div class="inner">
      <template v-for="m in messages" :key="m.id">
        <UserMessage v-if="m.role === 'user'" :text="m.text ?? ''" :time="m.createdAt" />
        <AssistantMessage v-else :message="m" :chosen-destination="chosenDestination" @choose="(messageId, id, name) => emit('choose', messageId, id, name)" />
      </template>
      <AgentStatusBlock v-if="showStatus" :status="statusText" :agents="agents" />
      <div v-if="streaming?.text" class="streaming-live">
        <AssistantMessage
          :message="streaming"
          :chosen-destination="chosenDestination"
          :live="true"
          :busy="showStreamingBusy"
          @choose="(messageId, id, name) => emit('choose', messageId, id, name)"
        />
      </div>
      <div v-if="showReplySpacer" class="reply-spacer" :style="{ height: spacerPx + 'px' }" />
      <div v-if="!messages.length && !loading" class="page-empty">
        <p>No messages yet. Describe your trip to get started.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 8px 20px;
}
.inner {
  max-width: var(--app-max-chat-width);
  margin: 0 auto;
  padding-bottom: 100px;
}
/* The live bubble intentionally reuses AssistantMessage's default
   top-aligned avatar so the icon stays fixed while text streams in
   and nothing jumps when the final message replaces it. */
/* Slightly larger gap between a user bubble and the AI reply below it. */
.inner :deep(.user-row + .ai-row),
.inner :deep(.user-row + .thinking-row) {
  margin-top: 22px;
}
</style>
