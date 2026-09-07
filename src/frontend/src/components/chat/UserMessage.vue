<!-- Right-aligned user bubble row rendered inside MessageList. -->
<script setup lang="ts">
import MessageTime from './MessageTime.vue';

defineProps<{ text: string; time: string }>();
</script>

<template>
  <div class="user-row">
    <div class="user-bubble">
      <p>{{ text }}</p>
      <MessageTime :value="time" />
    </div>
  </div>
</template>

<style scoped>
.user-row {
  display: flex;
  justify-content: flex-end;
  margin: 10px 0;
}
.user-bubble {
  max-width: 75%;
  background: var(--p-primary-50);
  border: 1px solid var(--p-primary-100);
  border-radius: 12px 12px 4px 12px;
  padding: 8px 14px 6px;
}
/* Dark variant lives in main.css (shared selected-state section). */
.user-bubble p {
  margin: 0;
  font-size: 0.92rem;
}
.time {
  font-size: 0.7rem;
  color: var(--p-surface-500);
}
</style>
