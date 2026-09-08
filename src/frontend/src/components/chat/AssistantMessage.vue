<!-- AI answer row inside MessageList: avatar + rich text plus the rich
     card matching the message kind (destinations, options, budget…). -->
<script setup lang="ts">
import { computed } from 'vue';
import type { ChatMessage } from '../../types';
import BudgetSummary from '../travel/BudgetSummary.vue';
import ItineraryBlock from '../travel/ItineraryBlock.vue';
import DestinationRecommendation from '../travel/DestinationRecommendation.vue';
import TravelOptionCard from '../travel/TravelOptionCard.vue';
import SubagentResults from './SubagentResults.vue';
import MessageTime from './MessageTime.vue';
import { renderRich } from './richtext';

const props = defineProps<{ message: ChatMessage; chosenDestination: string | null }>();
const emit = defineEmits<{ choose: [messageId: string, id: string, name: string] }>();

const html = computed(() => (props.message.text ? renderRich(props.message.text) : ''));
</script>

<template>
  <div class="ai-row">
    <div class="avatar">AI</div>
    <div class="ai-body">
      <SubagentResults v-if="message.subagentResults?.length" :results="message.subagentResults" />
      <div v-if="html" class="prose" v-html="html" />
      <DestinationRecommendation
        v-if="message.kind === 'destinations'"
        :message-id="message.id"
        :chosen="chosenDestination"
        :items="message.destinations"
        @choose="(messageId, id, name) => emit('choose', messageId, id, name)"
      />
      <TravelOptionCard v-else-if="message.kind === 'options'" />
      <BudgetSummary v-else-if="message.kind === 'budget'" />
      <ItineraryBlock v-else-if="message.kind === 'itinerary'" />
      <MessageTime :value="message.createdAt" />
    </div>
  </div>
</template>

<style scoped>
.ai-row {
  display: flex;
  gap: 12px;
  margin: 14px 0;
}
.avatar {
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
  margin-top: 2px;
}
.ai-body {
  flex: 1;
  min-width: 0;
}
/* .prose rich-text styles live in main.css (shared with ItineraryBlock). */
.time {
  font-size: 0.7rem;
  color: var(--p-surface-500);
}
</style>
