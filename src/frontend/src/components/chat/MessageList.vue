<!-- Scrollable message thread in the center of the chat view.
     Only this column scrolls; auto-scrolls to bottom on new messages. -->
<script setup lang="ts">
import ProgressSpinner from 'primevue/progressspinner';
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import type { ChatMessage } from '../../types';
import AssistantMessage from './AssistantMessage.vue';
import UserMessage from './UserMessage.vue';

const props = defineProps<{
  messages: ChatMessage[];
  loading: boolean;
  chosenDestination: string | null;
}>();
const emit = defineEmits<{ choose: [id: string, name: string] }>();

const scroller = ref<HTMLElement | null>(null);

// While the reply is being generated, the last message is the just-sent
// user message: show an empty assistant row with a Reasoning… indicator.
const lastIsUser = computed(() => {
  const msgs = props.messages;
  return msgs.length > 0 && msgs[msgs.length - 1].role === 'user';
});

async function scrollDown() {
  await nextTick();
  scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' });
}
onMounted(scrollDown);
// Multi-source watch avoids allocating an array on every trigger.
watch([() => props.messages.length, () => props.loading], scrollDown);
</script>

<template>
  <div ref="scroller" class="messages">
    <div class="inner">
      <template v-for="m in messages" :key="m.id">
        <UserMessage v-if="m.role === 'user'" :text="m.text ?? ''" :time="m.createdAt" />
        <AssistantMessage v-else :message="m" :chosen-destination="chosenDestination" @choose="(id, name) => emit('choose', id, name)" />
      </template>
      <div v-if="loading && lastIsUser" class="thinking-row">
        <div class="avatar">AI</div>
        <div class="thinking-body"><ProgressSpinner stroke-width="5" class="spin" /><span>Reasoning…</span></div>
      </div>
      <div v-else-if="loading" class="typing"><ProgressSpinner stroke-width="5" class="spin" /><span>Researching…</span></div>
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
.typing {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--p-surface-500);
  font-size: 0.88rem;
  margin: 12px 0;
}
.thinking-row {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 12px;
  margin: 14px 0;
}
.thinking-row .avatar {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: var(--p-primary-600);
  color: #fff;
  font-size: 0.7rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 0;
}
.thinking-body {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  color: var(--p-surface-500);
  font-size: 0.88rem;
}
.spin {
  width: 22px;
  height: 22px;
  /* PrimeVue centers the spinner with margin auto: force left alignment. */
  margin: 0;
  flex-shrink: 0;
}
</style>
