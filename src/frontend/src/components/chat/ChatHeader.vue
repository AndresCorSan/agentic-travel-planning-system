<!-- Top bar of the chat view: conversation title plus Rename dialog
     and Save-plan actions. -->
<script setup lang="ts">
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import { useToast } from 'primevue/usetoast';
import { ref } from 'vue';
import { useLibraryStore } from '../../stores/travel';
import { useUiStore } from '../../stores/ui';

const props = defineProps<{ conversationId: string }>();

const library = useLibraryStore();
const ui = useUiStore();
const toast = useToast();

const title = ref('');
const showRename = ref(false);

function currentTitle() {
  return library.conversations.find((c) => c.id === props.conversationId)?.title ?? 'Trip';
}
function openRename() {
  title.value = currentTitle();
  showRename.value = true;
}
function confirmRename() {
  if (title.value.trim()) library.renameConversation(props.conversationId, title.value.trim());
  showRename.value = false;
}
function savePlan() {
  toast.add({ severity: 'success', summary: 'Plan saved', detail: 'Added to your saved plans (mock).', life: 2600 });
}
</script>

<template>
  <header class="chat-header">
    <Button icon="pi pi-bars" severity="secondary" text rounded class="only-mobile" aria-label="Open navigation" @click="ui.navOpen = true" />
    <div class="title-wrap">
      <h1>{{ currentTitle() }}</h1>
      <span class="status"><span class="dot" />Planning · mock data</span>
    </div>
    <div class="actions">
      <Button icon="pi pi-pencil" label="Rename" severity="secondary" text aria-label="Rename conversation" @click="openRename()" />
      <Button icon="pi pi-bookmark" label="Save plan" aria-label="Save plan" @click="savePlan()" />
      <Button icon="pi pi-list" severity="secondary" text rounded class="only-narrow" aria-label="Toggle travel state" @click="ui.statePanelOpen = true" />
    </div>
    <Dialog v-model:visible="showRename" modal header="Rename conversation" :style="{ width: '24rem' }">
      <InputText v-model="title" class="w-full" @keydown.enter="confirmRename()" />
      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showRename = false" />
        <Button label="Save" @click="confirmRename()" />
      </template>
    </Dialog>
  </header>
</template>

<style scoped>
.chat-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-bottom: 1px solid var(--p-surface-200);
  flex-shrink: 0;
}
.title-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 12px;
}
h1 {
  margin: 0;
  font-size: 1.02rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.status {
  font-size: 0.76rem;
  color: var(--p-surface-500);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--p-primary-500);
}
.actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
.only-mobile,
.only-narrow {
  display: none;
}
.w-full {
  width: 100%;
}
@media (max-width: 860px) {
  .only-mobile {
    display: inline-flex;
  }
}
@media (max-width: 1180px) {
  .only-narrow {
    display: inline-flex;
  }
}
</style>
