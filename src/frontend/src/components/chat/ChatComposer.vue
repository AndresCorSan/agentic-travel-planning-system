<!-- Floating message composer pinned to the bottom of the chat column
     (overlaps the thread; Enter sends, loading disables it). -->
<script setup lang="ts">
import Button from 'primevue/button';
import Textarea from 'primevue/textarea';
import { ref } from 'vue';

const props = defineProps<{ loading: boolean }>();
const emit = defineEmits<{ send: [text: string] }>();

const draft = ref('');

function submit() {
  const t = draft.value.trim();
  if (!t || props.loading) return;
  emit('send', t);
  draft.value = '';
}
</script>

<template>
  <div class="float-wrap">
    <div class="float-composer">
      <Textarea
        v-model="draft"
        rows="1"
        auto-resize
        placeholder="How can I help you plan your trip?"
        :disabled="loading"
        class="input"
        @keydown.enter.exact.prevent="submit()"
      />
      <Button
        icon="pi pi-send"
        rounded
        class="send-btn"
        :loading="loading"
        :disabled="!draft.trim() || loading"
        aria-label="Send message"
        @click="submit()"
      />
    </div>
  </div>
</template>

<style scoped>
.float-wrap {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  bottom: 25px;
  width: min(calc(100% - 40px), var(--app-max-chat-width));
  z-index: 5;
}
.float-composer {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  background: color-mix(in srgb, var(--p-surface-0) 88%, transparent);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid var(--p-surface-200);
  border-radius: 18px;
  padding: 8px 8px 8px 16px;
  box-shadow: 0 12px 32px rgba(60, 50, 30, 0.16);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.float-composer:focus-within {
  border-color: var(--p-primary-300);
  box-shadow: 0 12px 32px rgba(60, 50, 30, 0.2), 0 0 0 2px var(--p-primary-100);
}
/* Dark shadows live in main.css (shared selected-state section). */
.input {
  flex: 1;
  resize: none;
}
.float-composer :deep(.p-textarea) {
  background: transparent;
  border: 0;
  padding: 8px 0;
}
.float-composer :deep(.p-textarea:enabled:focus) {
  border: 0;
  box-shadow: none;
}
/* pi-send glyph carries asymmetric bearings: nudge down-left to center. */
.send-btn :deep(.pi-send) {
  transform: translate(-1px, 1px);
}
</style>
