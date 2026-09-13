<!-- Top bar of the chat view: conversation title plus Rename dialog
     and Save-plan actions. -->
<script setup lang="ts">
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import { useToast } from 'primevue/usetoast';
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { savePlan as savePlanRemote } from '../../api/travelService';
import { useLibraryStore, useTravelStore } from '../../stores/travel';
import { useUiStore } from '../../stores/ui';

const props = defineProps<{ conversationId: string }>();

const library = useLibraryStore();
const travel = useTravelStore();
const ui = useUiStore();
const toast = useToast();
const router = useRouter();

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

// Save-plan dialog: validation first (destination + >=1 choice),
// then a confirm dialog; the backend snapshots + describes the plan.
const showSave = ref(false);
const planTitle = ref('');
const saving = ref(false);
const destination = computed(() => travel.requirements.find((r) => r.key === 'destination')?.value ?? null);
const saveBlockReason = computed(() => {
  if (!destination.value) return 'Set a destination before saving a plan.';
  if (!travel.plan.length) return 'Pick at least one option before saving a plan.';
  return null;
});
function openSave() {
  const reason = saveBlockReason.value;
  if (reason) {
    toast.add({ severity: 'warn', summary: 'Nothing to save yet', detail: reason, life: 3200 });
    return;
  }
  planTitle.value = destination.value ? `${destination.value} trip` : '';
  showSave.value = true;
}
async function confirmSave() {
  saving.value = true;
  try {
    const plan = await savePlanRemote(props.conversationId, planTitle.value.trim() || undefined);
    library.addPlan(plan);
    showSave.value = false;
    toast.add({ severity: 'success', summary: 'Plan saved', detail: 'Find it under Saved plans.', life: 2600 });
    router.push(`/plans/${plan.id}`);
  } catch (err) {
    const detail =
      ((err as { response?: { data?: { detail?: string } } }).response?.data?.detail as string | undefined) ??
      'Could not save the plan.';
    toast.add({ severity: 'error', summary: 'Save failed', detail, life: 4000 });
  } finally {
    saving.value = false;
  }
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
      <Button icon="pi pi-bookmark" label="Save plan" aria-label="Save plan" @click="openSave()" />
      <Button icon="pi pi-list" severity="secondary" text rounded class="only-narrow" aria-label="Toggle travel state" @click="ui.statePanelOpen = true" />
    </div>
    <Dialog v-model:visible="showRename" modal header="Rename conversation" :style="{ width: '24rem' }">
      <InputText v-model="title" class="w-full" @keydown.enter="confirmRename()" />
      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showRename = false" />
        <Button label="Save" @click="confirmRename()" />
      </template>
    </Dialog>
    <Dialog v-model:visible="showSave" modal header="Save plan" :style="{ width: '26rem' }">
      <p class="muted">This saves a snapshot of the current requirements and trip plan. You can keep chatting afterwards — a new save creates a new plan.</p>
      <label class="fld-label" for="plan-title">Title</label>
      <InputText id="plan-title" v-model="planTitle" class="w-full" @keydown.enter="confirmSave()" />
      <template #footer>
        <Button label="Cancel" severity="secondary" text :disabled="saving" @click="showSave = false" />
        <Button label="Save plan" icon="pi pi-bookmark" :loading="saving" @click="confirmSave()" />
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
.muted {
  color: var(--p-surface-500);
  font-size: 0.85rem;
  margin: 0 0 12px;
}
.fld-label {
  display: block;
  font-size: 0.8rem;
  font-weight: 600;
  margin-bottom: 6px;
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
