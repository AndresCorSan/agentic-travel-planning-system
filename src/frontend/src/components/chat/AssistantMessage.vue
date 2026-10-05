<!-- AI answer row inside MessageList: avatar + rich text plus the rich
     card matching the message kind (destinations, options, budget…). -->
<script setup lang="ts">
import { computed } from 'vue';
import type { ChatMessage } from '../../types';
import { SINGLE_CHOICE_CATEGORIES } from '../../types';
import { useTravelStore } from '../../stores/travel';
import DestinationRecommendation from '../travel/DestinationRecommendation.vue';
import SubagentResults from './SubagentResults.vue';
import MessageMeta from './MessageMeta.vue';
import { renderOptionGroups, renderRich } from './richtext';

const props = defineProps<{ message: ChatMessage; chosenDestination: string | null; live?: boolean; busy?: boolean }>();
const emit = defineEmits<{ choose: [messageId: string, id: string, name: string] }>();

const travel = useTravelStore();

const locked = computed(() => !!props.live || !!travel.choicesSaved[props.message.id]);

const html = computed(() => (props.message.text ? renderRich(props.message.text) : ''));

// Options published this turn, rendered as a grouped block under the
// message with per-message drafts + the Save bar.
const autoGroups = computed(() => travel.optionsByMessage[props.message.id] ?? []);

const draftCount = computed(() => {
  const known = travel.optionsById;
  return Object.entries(travel.drafts[props.message.id] ?? {}).filter(
    ([id, on]) => on && known[id]
  ).length;
});

const autoHtml = computed(() => {
  if (!autoGroups.value.length) return '';
  const draft = travel.drafts[props.message.id] ?? {};
  const known = travel.optionsById;
  return renderOptionGroups(autoGroups.value, {
    lookup: (id) => known[id],
    checked: (id) => !!draft[id],
    locked: locked.value,
    single: (category) => SINGLE_CHOICE_CATEGORIES.includes(category),
  });
});

const hasSaveable = computed(() => autoGroups.value.length > 0);

function onProseClick(e: MouseEvent) {
  const el = (e.target as HTMLElement).closest?.('[data-option]') as HTMLElement | null;
  if (!el || locked.value) return;
  e.preventDefault();
  travel.toggleOption(props.message.id, el.dataset.option ?? '');
}

function onSave() {
  void travel.saveChoices(props.message.id);
}
</script>

<template>
  <div class="ai-row" :class="{ 'is-error': message.error }">
    <div class="avatar">AI</div>
    <div class="ai-body">
      <SubagentResults v-if="message.subagentResults?.length" :results="message.subagentResults" />
      <div v-if="html" class="prose" v-html="html" @click="onProseClick" />
      <span v-if="live && busy" class="busy-line"><span>Working on it</span><span class="tballs" aria-hidden="true"><span></span><span></span><span></span></span></span>
      <div v-if="autoHtml" class="prose" v-html="autoHtml" @click="onProseClick" />
      <div v-if="!live && hasSaveable" class="save-bar">
        <span v-if="travel.choicesSaved[message.id]" class="saved-note"><i class="pi pi-check-circle" /> Choices saved to your trip plan.</span>
        <button v-else class="save-btn" :disabled="draftCount === 0 || travel.loading" @click="onSave">
          Save choices{{ draftCount ? ` (${draftCount})` : '' }}
        </button>
      </div>
      <DestinationRecommendation
        v-if="message.kind === 'destinations'"
        :message-id="message.id"
        :chosen="chosenDestination"
        :items="message.destinations"
        @choose="(messageId, id, name) => emit('choose', messageId, id, name)"
      />
      <MessageMeta :created-at="message.createdAt" :stats="message.stats" />
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
/* Stream failure bubble: soft error tint.
   color-mix over theme reds so dark mode keeps working. */
.is-error .ai-body {
  border-left: 3px solid var(--p-red-500);
  padding-left: 12px;
}
.is-error .prose {
  color: var(--p-red-700);
}
/* .prose rich-text styles live in main.css (shared with ItineraryBlock). */
.save-bar {
  margin-top: 10px;
}
.save-btn {
  font-size: 0.85rem;
  font-weight: 600;
  color: #fff;
  background: var(--p-primary-600);
  border: 0;
  border-radius: 8px;
  padding: 7px 16px;
  cursor: pointer;
}
.save-btn:disabled {
  opacity: 0.45;
  cursor: default;
}
.saved-note {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--p-green-700);
  background: color-mix(in srgb, var(--p-green-500) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--p-green-500) 35%, transparent);
  border-radius: 99px;
  padding: 5px 13px;
}
.saved-note i {
  font-size: 0.85rem;
  line-height: 0;
}
.time {
  font-size: 0.7rem;
  color: var(--p-surface-500);
}
/* Stall indicator shown under live text when no tokens arrive for a
   while (LLM thinking / tool calls): same look as AgentStatusBlock. */
.busy-line {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-top: 10px;
  color: var(--p-surface-500);
  font-size: 0.88rem;
}
</style>
