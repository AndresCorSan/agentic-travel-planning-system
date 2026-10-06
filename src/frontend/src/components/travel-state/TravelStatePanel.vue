<!-- Right-column panel of the chat view: trip requirements, trip plan,
     and a Save-plan action pinned to the bottom. AppShell docks it as a
     floating card with a pill toggle; on narrow screens it renders
     inside a slide-over drawer instead. -->
<script setup lang="ts">
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import { useToast } from 'primevue/usetoast';
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { savePlan as savePlanRemote } from '../../api/travelService';
import { useLocalStorageToggle } from '../../composables/useLocalStorageToggle';
import { useLibraryStore } from '../../stores/library';
import { useTravelStore } from '../../stores/travel';
import TripPlanSection from './TripPlanSection.vue';

defineProps<{ drawer?: boolean }>();

const travel = useTravelStore();
const library = useLibraryStore();
const toast = useToast();
const router = useRouter();
const route = useRoute();
const conversationId = computed(() => route.params.id as string);

// Persisted open state per section (shared composable).
const [reqOpen, toggleReq] = useLocalStorageToggle('state-req-open');
const [planOpen, togglePlan] = useLocalStorageToggle('state-plan-open');

const confirmed = computed(() => travel.requirements.filter((r) => r.value));
const missing = computed(() => travel.requirements.filter((r) => !r.value));

// Briefly highlight rows whose value just changed via a live stream update,
// so the eye catches what the agent just filled in. Skipped on first load.
const flashKeys = ref<Set<string>>(new Set());
let prevSnapshot: string | null = null;
watch(
  () => travel.requirements.map((r) => `${r.key}=${r.value ?? ''}`).join('|'),
  (snap) => {
    if (prevSnapshot !== null && snap !== prevSnapshot) {
      const prev = new Map(prevSnapshot.split('|').map((p) => p.split('=') as [string, string]));
      const changed: string[] = [];
      for (const part of snap.split('|')) {
        const [key, val] = part.split('=') as [string, string];
        if (val && prev.get(key) !== val) changed.push(key);
      }
      if (changed.length) {
        flashKeys.value = new Set(changed);
        setTimeout(() => { flashKeys.value = new Set(); }, 1600);
      }
    }
    prevSnapshot = snap;
  },
  { immediate: true }
);

const travelersCount = computed(() => {
  const raw = travel.requirements.find((r) => r.key === 'travelers')?.value;
  const n = raw ? parseInt(raw, 10) : NaN;
  return Number.isFinite(n) && n > 0 ? n : null;
});

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
    const plan = await savePlanRemote(conversationId.value, planTitle.value.trim() || undefined);
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
  <aside class="state slim-scroll" :class="{ 'in-drawer': drawer }">
    <header class="panel-head">
      <h3>Trip details</h3>
    </header>
    <section>
      <button class="sec-toggle" @click="toggleReq()" :aria-expanded="reqOpen">
        <i class="pi pi-chevron-down toggle-ic" :class="{ closed: !reqOpen }" />
        Trip requirements
        <span class="count">{{ confirmed.length }}/{{ travel.requirements.length }}</span>
      </button>
      <div class="collapse" :class="{ closed: !reqOpen }">
        <div class="clip">
      <dl>
        <div v-for="r in confirmed" :key="r.key" class="req" :class="{ flash: flashKeys.has(r.key) }">
          <dt>{{ r.label }}</dt>
          <dd>{{ r.value }}</dd>
        </div>
      </dl>
      <div v-if="missing.length" class="missing">
        <p v-if="!confirmed.length" class="empty">Tell me about your trip to get started.</p>
        <p class="missing-title">Not specified</p>
        <ul>
          <li v-for="r in missing" :key="r.key">{{ r.label }}</li>
        </ul>
      </div>
        </div>
      </div>
    </section>

    <section>
      <button class="sec-toggle" @click="togglePlan()" :aria-expanded="planOpen">
        <i class="pi pi-chevron-down toggle-ic" :class="{ closed: !planOpen }" />
        Trip plan
        <span v-if="travel.plan.length" class="count">{{ travel.plan.length }}</span>
      </button>
      <div class="collapse" :class="{ closed: !planOpen }">
        <div class="clip">
          <TripPlanSection
            :items="travel.plan"
            :total="travel.planTotal"
            :currency="travel.planCurrency"
            :budget="travel.planBudget"
            :over-budget="travel.planOverBudget"
            :travelers="travelersCount"
            empty-text="Your picks will land here when you choose options from the chat."
          />
        </div>
      </div>
    </section>

    <div class="save-foot">
      <Button icon="pi pi-bookmark" label="Save plan" class="save-btn" aria-label="Save plan" @click="openSave()" />
    </div>
    <Dialog v-model:visible="showSave" modal header="Save plan" :style="{ width: '26rem' }">
      <p class="muted">This saves a snapshot of the current requirements and trip plan. You can keep chatting afterwards — a new save creates a new plan.</p>
      <label class="fld-label" for="plan-title">Title</label>
      <InputText id="plan-title" v-model="planTitle" class="w-full" @keydown.enter="confirmSave()" />
      <template #footer>
        <Button label="Cancel" severity="secondary" text :disabled="saving" @click="showSave = false" />
        <Button label="Save plan" icon="pi pi-bookmark" :loading="saving" @click="confirmSave()" />
      </template>
    </Dialog>
  </aside>
</template>

<style scoped>
.state {
  width: 100%;
  flex-shrink: 0;
  height: 100%;
  min-height: 0;
  background: transparent;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
/* Centered serif title with a neutral structural hairline */
.panel-head {
  margin: -16px 0 -6px;
  padding: 12px 16px 10px;
  text-align: center;
  border-bottom: 1px solid var(--p-surface-200);
}
.panel-head h3 {
  margin: 0;
  font-family: Georgia, 'Times New Roman', serif;
  font-weight: 400;
  font-size: 1.08rem;
}
/* Collapsible section headers with an accent count pill; sections are
   divided by a neutral hairline. Animation classes in main.css. */
.state section {
  border-bottom: 1px solid var(--p-surface-200);
  padding-bottom: 16px;
}
.state section:last-of-type {
  border-bottom: 0;
  padding-bottom: 0;
}
/* Title-to-upper-rule rhythm: 20px flex gap − 6px = 14px, matching the
   header hairline → first section distance above. */
.state section + section {
  margin-top: -6px;
}
.sec-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  border: 0;
  background: transparent;
  color: var(--p-surface-500);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
  padding: 8px 12px;
  /* Same title-to-content distance as the sidebar group toggles
     (no bottom margin; the flex gap provides the ~2px). */
  margin-bottom: 2px;
  border-radius: 9px;
  cursor: pointer;
  text-align: left;
}
.sec-toggle:hover {
  background: var(--p-surface-100);
  color: inherit;
}
.sec-toggle i {
  font-size: 0.65rem;
}
.sec-toggle .count {
  background: var(--p-primary-600);
  color: #fff;
  border-radius: 10px;
  padding: 1px 8px;
  font-size: 0.7rem;
  letter-spacing: 0;
  margin-left: auto;
}
/* .toggle-ic rotation + .collapse animation live in main.css (shared). */
dl {
  margin: 0;
}
/* Trip requirements definition list */
.req {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 5px 0;
  border-bottom: 1px solid color-mix(in srgb, var(--p-surface-200) 55%, transparent);
  border-radius: 4px;
  font-size: 0.88rem;
}
.req dt {
  color: var(--p-surface-500);
  flex: none;
}
.req dd {
  margin: 0;
  font-weight: 500;
  text-align: right;
  min-width: 0;
}
/* Flash on rows just filled in by a live update. */
.req.flash {
  animation: req-flash 1.6s ease-out;
}
@keyframes req-flash {
  0% { background: color-mix(in srgb, var(--p-primary-500) 25%, transparent); }
  100% { background: transparent; }
}
/* Unspecified requirements */
.missing {
  margin-top: 10px;
}
.empty {
  font-size: 0.85rem;
  color: var(--p-surface-500);
  margin: 0 0 10px;
}
.missing-title {
  font-size: 0.78rem;
  color: var(--p-surface-500);
  margin: 0 0 6px;
}
.missing ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.missing li {
  border: 1px dashed var(--p-surface-300);
  color: var(--p-surface-500);
  border-radius: 99px;
  padding: 3px 10px;
  font-size: 0.8rem;
}
/* Save action pinned to the panel bottom. */
.save-foot {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--p-surface-200);
}
.save-btn {
  width: 100%;
  justify-content: center;
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
/* Narrow variant inside the small-screen drawer */
.in-drawer {
  width: auto;
  border: 0;
  padding: 0;
  overflow: visible;
}
</style>
