<!-- Scrollable message thread in the center of the chat view.
     Only this column scrolls; auto-scrolls to bottom on new messages. -->
<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
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
const showStatus = computed(
  () => props.loading && (!props.messages.length || lastIsUser.value) && !hasStreamingText.value
);

async function scrollDown() {
  await nextTick();
  scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' });
}
onMounted(scrollDown);
// Multi-source watch avoids allocating an array on every trigger.
watch([() => props.messages.length, () => props.loading, () => props.streaming?.text?.length ?? 0], scrollDown);
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
          @choose="(messageId, id, name) => emit('choose', messageId, id, name)"
        />
      </div>
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
