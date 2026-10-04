<!-- Left navigation sidebar (AppShell rail, overlay drawer on mobile):
     New-trip button, collapsible Conversations / Saved plans groups with
     per-row rename-delete popover, and accent + theme prefs at the bottom.
     Collapsed to a 64px icon rail with popovers instead of groups. -->
<script setup lang="ts">
import Button from 'primevue/button';
import ConfirmDialog from 'primevue/confirmdialog';
import InputText from 'primevue/inputtext';
import Popover from 'primevue/popover';
import { useConfirm } from 'primevue/useconfirm';
import { useToast } from 'primevue/usetoast';
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useLocalStorageToggle } from '../../composables/useLocalStorageToggle';
import { createConversationId } from '../../api/travelService';
import { useLibraryStore, useTravelStore } from '../../stores/travel';
import { useUiStore } from '../../stores/ui';
import { formatUpdatedAt } from '../../utils/datetime';
import AccentPicker from '../chat/AccentPicker.vue';
import ThemeToggle from '../chat/ThemeToggle.vue';

const props = defineProps<{ overlay?: boolean }>();

const library = useLibraryStore();
const travel = useTravelStore();
const ui = useUiStore();
const route = useRoute();
const router = useRouter();
const confirm = useConfirm();
const toast = useToast();

const collapsed = computed(() => ui.sidebarCollapsed && !props.overlay);
const convPop = ref<InstanceType<typeof Popover> | null>(null);
const planPop = ref<InstanceType<typeof Popover> | null>(null);
// Persisted open state for both collapsible groups (shared composable).
const [convOpen, toggleConv] = useLocalStorageToggle('sidebar-conv-open');
const [plansOpen, togglePlans] = useLocalStorageToggle('sidebar-plans-open');

onMounted(() => {
  if (!library.loaded) void library.load();
});

const activeTrip = computed(() => (route.name === 'trip' ? String(route.params.id) : null));
const onPlansRoute = computed(() => String(route.name ?? '').startsWith('plan'));
const onConversationsRoute = computed(() => route.name === 'conversations');
// Sidebar preview cap: both groups show the latest N rows (lists are
// newest-first) and link out to the full overview pages past that.
const SIDEBAR_LIMIT = 8;
const recentConversations = computed(() => library.conversations.slice(0, SIDEBAR_LIMIT));
const recentPlans = computed(() => library.plans.slice(0, SIDEBAR_LIMIT));
const hasMoreConversations = computed(() => library.conversations.length > SIDEBAR_LIMIT);
const hasMorePlans = computed(() => library.plans.length > SIDEBAR_LIMIT);
// Trip switching locks mid-reply (router guard covers direct URL nav).
const navLocked = computed(() => travel.loading);
// Show tooltip on the New trip button when locked
const LOCKED_MSG = 'Reply in progress — wait for the current reply to finish.';
// Locked message first; otherwise the collapsed rail keeps its "New trip" hint.
const newTripTip = computed(() =>
  navLocked.value ? LOCKED_MSG : collapsed.value ? 'New trip' : undefined
);

function notifyLocked() {
  toast.add({
    severity: 'info',
    summary: 'Reply in progress',
    detail: 'Wait for the current reply to finish before switching trips.',
    life: 2500
  });
}

function newTrip() {
  if (navLocked.value) {
    notifyLocked();
    return;
  }
  // Fresh thread without storing anything: rows are created on first send,
  // so empty trips leave no trace.
  const id = createConversationId();
  ui.navOpen = false;
  void router.push(`/trip/${id}`);
}
function openTrip(id: string) {
  if (navLocked.value && id !== activeTrip.value) {
    notifyLocked();
    return;
  }
  ui.navOpen = false;
  convPop.value?.hide();
  void router.push(`/trip/${id}`);
}
function openPlan(id: string) {
  if (navLocked.value) {
    notifyLocked();
    return;
  }
  ui.navOpen = false;
  planPop.value?.hide();
  void router.push(`/plans/${id}`);
}
function openPlans() {
  if (navLocked.value) {
    notifyLocked();
    return;
  }
  planPop.value?.hide();
  void router.push('/plans');
}
function openConversations() {
  if (navLocked.value) {
    notifyLocked();
    return;
  }
  convPop.value?.hide();
  void router.push('/conversations');
}

// Per-row options popover (rename / delete) shared by conversations and plans.
// Targets are { kind, id } objects so both lists share one popover,
// one inline editor and one confirm dialog.
type RowKind = 'conv' | 'plan';
interface RowTarget {
  kind: RowKind;
  id: string;
}
const convOptsPop = ref<InstanceType<typeof Popover> | null>(null);
const menuTarget = ref<RowTarget | null>(null);
const menuOpenTarget = ref<RowTarget | null>(null);
const editingTarget = ref<RowTarget | null>(null);
const draft = ref('');
// Set on Esc so the follow-up blur event doesn't commit the edit.
let suppressBlur = false;

const vFocus = {
  mounted: (el: HTMLInputElement) => {
    el.focus();
    el.select();
  }
};

function isTarget(t: RowTarget | null, kind: RowKind, id: string) {
  return t?.kind === kind && t?.id === id;
}
const isEditing = (kind: RowKind, id: string) => isTarget(editingTarget.value, kind, id);
const isMenuOpen = (kind: RowKind, id: string) => isTarget(menuOpenTarget.value, kind, id);

// Plan rows mirror chat rows: title + saved date below. Plans without
// createdAt fall back to destination · dates there.
function planMeta(p: { createdAt?: string | null; destination: string; dates: string }): string {
  return (
    formatUpdatedAt(p.createdAt) ||
    [p.destination, p.dates].filter(Boolean).join(' · ')
  );
}

// Single lookup for both row kinds.
function getRowItem(kind: RowKind, id: string) {
  return kind === 'conv'
    ? library.conversations.find((c) => c.id === id)
    : library.plans.find((p) => p.id === id);
}

function openRowMenu(event: Event, kind: RowKind, id: string) {
  menuTarget.value = { kind, id };
  menuOpenTarget.value = { kind, id };
  convOptsPop.value?.toggle(event);
}
function onRowMenuHide() {
  menuOpenTarget.value = null;
}
function renameFromMenu() {
  if (menuTarget.value) startRename(menuTarget.value.kind, menuTarget.value.id);
}
function deleteFromMenu() {
  if (menuTarget.value) askDelete(menuTarget.value.kind, menuTarget.value.id);
}
function startRename(kind: RowKind, id: string) {
  const title = getRowItem(kind, id)?.title;
  if (!title) return;
  convOptsPop.value?.hide();
  editingTarget.value = { kind, id };
  draft.value = title;
}
function commitRename() {
  if (suppressBlur) {
    suppressBlur = false;
    return;
  }
  const target = editingTarget.value;
  editingTarget.value = null;
  if (!target) return;
  const title = draft.value.trim();
  if (!title) return;
  if (target.kind === 'conv') library.renameConversation(target.id, title);
  else library.renamePlan(target.id, title);
}
function cancelRename() {
  suppressBlur = true;
  editingTarget.value = null;
}
function askDelete(kind: RowKind, id: string) {
  const isConv = kind === 'conv';
  const title = getRowItem(kind, id)?.title;
  convOptsPop.value?.hide();
  confirm.require({
    header: isConv ? 'Delete conversation' : 'Delete saved plan',
    message: title ? `Delete "${title}"? This cannot be undone.` : 'Delete this item?',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Delete',
    rejectLabel: 'Cancel',
    acceptClass: 'p-button-danger',
    rejectClass: 'p-button-text p-button-secondary',
    accept: () => {
      if (isConv) {
        library.deleteConversation(id);
        // Leaving a deleted conversation? Fall back to the home route.
        if (activeTrip.value === id) void router.push('/');
        toast.add({ severity: 'success', summary: 'Conversation deleted', life: 2500 });
      } else {
        library.deletePlan(id);
        if (String(route.name ?? '').startsWith('plan') && route.params.id === id) void router.push('/plans');
        toast.add({ severity: 'success', summary: 'Plan deleted', life: 2500 });
      }
    }
  });
}
</script>

<template>
  <div class="sidebar" :class="{ collapsed: collapsed }">
    <div class="top" :class="{ centered: collapsed }">
      <Button
        v-if="!overlay"
        :icon="collapsed ? 'pi pi-angle-right' : 'pi pi-angle-left'"
        severity="secondary"
        text
        rounded
        aria-label="Toggle sidebar"
        @click="ui.toggleSidebar()"
      />
      <span v-if="!(collapsed)" class="brand"><span class="brand-row">Travel<span class="brand-dot"> · </span>Intelligence</span><span class="brand-u" aria-hidden="true" /></span>
    </div>

    <div class="action">
      <Button icon="pi pi-plus" :label="collapsed ? undefined : 'New trip'" class="new-btn" @click="newTrip()" v-tooltip="newTripTip" />
    </div>

    <nav v-if="!collapsed" class="groups slim-scroll">
      <button class="group-toggle" @click="toggleConv()" :aria-expanded="convOpen">
        <i class="pi pi-chevron-down toggle-ic" :class="{ closed: !convOpen }" />
        Conversations
        <span class="count">{{ library.conversations.length }}</span>
      </button>
      <div class="collapse" :class="{ closed: !convOpen }">
        <div class="clip">
      <div v-if="!library.conversations.length" class="group-empty">
        <b>Nothing here yet</b>
        <p>No conversations yet. Start a new trip and it will show up here.</p>
      </div>
      <ul v-else>
        <li v-for="c in recentConversations" :key="c.id">
          <div
            class="row"
            :class="{ active: activeTrip === c.id, locked: navLocked && activeTrip !== c.id }"
            :title="navLocked && activeTrip !== c.id ? LOCKED_MSG : c.title"
            tabindex="0"
            role="button"
            @click="openTrip(c.id)"
            @keyup.enter="openTrip(c.id)"
          >
            <i class="pi pi-comments" />
            <span v-if="!isEditing('conv', c.id)" class="row-text">
              <span class="row-title">{{ c.title }}</span>
              <span class="meta">{{ formatUpdatedAt(c.updatedAt) }}</span>
            </span>
            <InputText
              v-else
              v-focus
              v-model="draft"
              class="rename-input"
              @click.stop
              @keyup.enter="commitRename()"
              @keydown.esc="cancelRename()"
              @blur="commitRename()"
            />
            <button
              v-if="!isEditing('conv', c.id)"
              class="row-menu"
              :class="{ open: isMenuOpen('conv', c.id) }"
              aria-label="Conversation options"
              title="Conversation options"
              @click.stop="openRowMenu($event, 'conv', c.id)"
            >
              <i class="pi pi-ellipsis-h" />
            </button>
          </div>
        </li>
      </ul>
      <button v-if="hasMoreConversations" class="group-footer" @click="openConversations()">View all conversations <i class="pi pi-arrow-right" /></button>
        </div>
      </div>

      <div class="group-sep" aria-hidden="true" />
      <button class="group-toggle" @click="togglePlans()" :aria-expanded="plansOpen">
        <i class="pi pi-chevron-down toggle-ic" :class="{ closed: !plansOpen }" />
        Saved plans
        <span class="count">{{ library.plans.length }}</span>
      </button>
      <div class="collapse" :class="{ closed: !plansOpen }">
        <div class="clip">
      <div v-if="!library.plans.length" class="group-empty">
        <b>No saved plans</b>
        <p>Plans you save from the chat will appear here.</p>
      </div>
      <ul v-else>
        <li v-for="p in recentPlans" :key="p.id">
          <div
            class="row"
            :class="{ locked: navLocked }"
            :title="navLocked ? LOCKED_MSG : p.title"
            tabindex="0"
            role="button"
            @click="openPlan(p.id)"
            @keyup.enter="openPlan(p.id)"
          >
            <i class="pi pi-bookmark" />
            <span v-if="!isEditing('plan', p.id)" class="row-text">
              <span class="row-title">{{ p.title }}</span>
              <span class="meta">{{ planMeta(p) }}</span>
            </span>
            <InputText
              v-else
              v-focus
              v-model="draft"
              class="rename-input"
              @click.stop
              @keyup.enter="commitRename()"
              @keydown.esc="cancelRename()"
              @blur="commitRename()"
            />
            <button
              v-if="!isEditing('plan', p.id)"
              class="row-menu"
              :class="{ open: isMenuOpen('plan', p.id) }"
              aria-label="Plan options"
              title="Plan options"
              @click.stop="openRowMenu($event, 'plan', p.id)"
            >
              <i class="pi pi-ellipsis-h" />
            </button>
          </div>
        </li>
      </ul>
      <button v-if="hasMorePlans" class="group-footer" @click="openPlans()">View all saved plans <i class="pi pi-arrow-right" /></button>
        </div>
      </div>
    </nav>

    <div v-else class="rail-lists">
      <button
        class="rail-btn"
        :class="{ active: route.name === 'trip' || onConversationsRoute }"
        aria-label="Conversations"
        v-tooltip.right="'Conversations'"
        @click="convPop?.toggle($event)"
      >
        <i class="pi pi-comments" />
      </button>
      <Popover ref="convPop">
        <p class="pop-title">Recent conversations</p>
        <ul class="pop-list">
          <li v-for="c in recentConversations" :key="c.id">
            <button class="pop-row" :class="{ sel: activeTrip === c.id, locked: navLocked && activeTrip !== c.id }" :title="navLocked && activeTrip !== c.id ? LOCKED_MSG : c.title" @click="openTrip(c.id)">
              <span class="pop-text">
                <span class="pop-item-title">{{ c.title }}</span>
                <span class="meta">{{ formatUpdatedAt(c.updatedAt) }}</span>
              </span>
            </button>
          </li>
        </ul>
        <p v-if="!library.conversations.length" class="meta">No conversations yet.</p>
        <button v-if="hasMoreConversations" class="pop-footer" @click="openConversations()">View all conversations <i class="pi pi-arrow-right" /></button>
      </Popover>

      <button
        class="rail-btn"
        :class="{ active: onPlansRoute }"
        aria-label="Saved plans"
        v-tooltip.right="'Saved plans'"
        @click="planPop?.toggle($event)"
      >
        <i class="pi pi-bookmark" />
      </button>
      <Popover ref="planPop">
        <p class="pop-title">Saved plans</p>
        <ul class="pop-list">
          <li v-for="p in recentPlans" :key="p.id">
            <button class="pop-row" :class="{ locked: navLocked }" :title="navLocked ? LOCKED_MSG : p.title" @click="openPlan(p.id)">
              <span class="pop-text">
                <span class="pop-item-title">{{ p.title }}</span>
                <span class="meta">{{ planMeta(p) }}</span>
              </span>
            </button>
          </li>
        </ul>
        <p v-if="!library.plans.length" class="meta">No saved plans yet.</p>
        <button v-if="hasMorePlans" class="pop-footer" :class="{ locked: navLocked }" :title="navLocked ? LOCKED_MSG : undefined" @click="openPlans()">View all saved plans <i class="pi pi-arrow-right" /></button>
      </Popover>
    </div>

    <div class="prefs" :class="{ collapsed: collapsed }">
      <AccentPicker :variant="collapsed ? 'circle' : 'menu'" />
      <ThemeToggle :variant="collapsed ? 'cycle' : 'pill'" />
    </div>

    <Popover ref="convOptsPop" class="conv-opts" @hide="onRowMenuHide()">
      <ul class="pop-list opts-list">
        <li>
          <button class="pop-row opt-row" @click="renameFromMenu()">
            <i class="pi pi-pencil" /> Rename
          </button>
        </li>
        <li>
          <button class="pop-row opt-row danger" @click="deleteFromMenu()">
            <i class="pi pi-trash" /> Delete
          </button>
        </li>
      </ul>
    </Popover>
    <ConfirmDialog />
  </div>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 12px 10px;
  gap: 8px;
}
.top {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 4px 6px;
  flex-shrink: 0;
}
.top.centered {
  justify-content: center;
  padding: 2px 0 6px;
}
/* Hairline under the brand (expanded sidebar only). */
.sidebar:not(.collapsed) .top {
  border-bottom: 1px solid var(--p-surface-200);
  padding-bottom: 12px;
}
.sidebar:not(.collapsed) .action {
  margin-top: 4px;
}
.brand {
  display: inline-flex;
  flex-direction: column;
  width: fit-content;
  font-family: Georgia, 'Times New Roman', serif;
  font-weight: 400;
  font-size: 1.05rem;
  letter-spacing: -0.01em;
  white-space: nowrap;
  color: var(--p-surface-900);
}
.brand-row {
  line-height: normal;
}
.brand-dot {
  color: var(--p-primary-600);
}
.brand-u {
  display: block;
  height: 2px;
  border-radius: 99px;
  margin-top: 3px;
  background: var(--p-primary-600);
}
.new-btn {
  width: 100%;
  justify-content: center;
}
.collapsed .action {
  display: flex;
  justify-content: center;
}
.collapsed .new-btn {
  width: 40px;
  height: 40px;
  padding: 0;
}
.groups {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
/* Hairline dividing Conversations from Saved plans. */
.group-sep {
  border-top: 1px solid var(--p-surface-200);
  /* 4px + the toggle's margin-top (10px) = 14px, same title-to-rule
     rhythm as the state panel sections. */
  margin: 10px 12px 4px;
}
/* Group toggle (collapsible section header) with accent count pill. */
.group-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  border: 0;
  background: transparent;
  color: var(--p-surface-500);
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
  padding: 8px 12px;
  margin-top: 10px;
  border-radius: 9px;
  cursor: pointer;
  text-align: left;
}
.group-toggle:first-child {
  /* 8px sidebar gap + 6px = 14px from the New trip button,
     the shared header-to-upper-element rhythm. */
  margin-top: 6px;
}
.group-toggle:hover {
  background: var(--p-surface-100);
  color: inherit;
}
.group-toggle i {
  font-size: 0.65rem;
}
/* .toggle-ic rotation + .collapse animation live in main.css (shared). */
.group-toggle .count {
  margin-left: auto;
  font-size: 0.7rem;
  background: var(--p-primary-600);
  color: #fff;
  border-radius: 10px;
  padding: 1px 8px;
  letter-spacing: 0;
}
ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
/* Empty state for collapsible groups */
.group-empty {
  border: 1.5px dashed var(--p-surface-300);
  border-radius: 10px;
  padding: 10px 12px;
  margin: 2px 2px 8px;
  text-align: left;
}
.group-empty b {
  display: block;
  font-size: 0.83rem;
}
.group-empty p {
  margin: 2px 0 0;
  font-size: 0.8rem;
  color: var(--p-surface-500);
  line-height: 1.45;
}
/* "View all …" links (expanded groups + collapsed-rail popovers).
   Arrow nudges right on hover. Only the outer margins differ. */
.group-footer,
.pop-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px 4px;
  border: 0;
  border-top: 1px solid var(--p-surface-200);
  border-radius: 0 0 8px 8px;
  background: none;
  color: var(--p-primary-600);
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.group-footer {
  margin: 2px 0 8px;
}
.pop-footer {
  margin-top: 6px;
}
.group-footer i,
.pop-footer i {
  font-size: 0.75rem;
  transition: transform 0.18s ease;
}
.group-footer:hover,
.pop-footer:hover {
  background: color-mix(in srgb, var(--p-primary-600) 8%, transparent);
  color: var(--p-primary-700);
}
.group-footer:hover i,
.pop-footer:hover i {
  transform: translateX(3px);
}
.group-footer:active i,
.pop-footer:active i {
  transform: translateX(5px);
}
/* Sidebar rows (conversations + plans). Divs with role=button so the
   per-row options button can nest inside with valid HTML. */
.row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 0.88rem;
  text-align: left;
  text-decoration: none;
}
.row:hover {
  background: var(--p-surface-100);
  text-decoration: none;
}
.row.active {
  /* Same treatment as the collapsed rail icons (.rail-btn.active):
     tinted tile + accent text, in both modes. */
  background: color-mix(in srgb, var(--p-primary-600) 12%, transparent);
  color: var(--p-primary-600);
}
/* Locked (mid-reply) rows: non-active trips are not clickable —
   no dimming, just the not-allowed cursor (title attr explains why). */
.row.locked {
  cursor: not-allowed;
}
/* Dark selected states live in main.css (shared with rail/popover rows). */
.row i {
  font-size: 0.95rem;
  flex-shrink: 0;
}
.row-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}
.row-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* Per-row "···" options button: only visible on hover/focus/open. */
.row-menu {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--p-surface-500);
  cursor: pointer;
  opacity: 0;
}
.row:hover .row-menu,
.row:focus-within .row-menu,
.row-menu.open {
  opacity: 1;
}
.row-menu:hover {
  background: var(--p-surface-200);
  color: inherit;
}
/* Inline rename editor (replaces the row text while editing). */
.rename-input {
  flex: 1;
  min-width: 0;
  font-size: 0.88rem;
  padding: 4px 8px;
}
/* Collapsed rail: icon buttons opening popovers instead of the groups. */
.rail-lists {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding-top: 4px;
}
.rail-btn {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 1rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.rail-btn:hover {
  background: var(--p-surface-100);
}
.rail-btn.active {
  /* Same treatment as the suggestion icons (WelcomeHero .suggestion-icon):
     tinted tile + accent icon, in both modes. */
  background: color-mix(in srgb, var(--p-primary-600) 12%, transparent);
  color: var(--p-primary-600);
}
.pop-list {
  min-width: 220px;
  max-width: 280px;
}
/* .pop-row.sel selected tint lives in main.css (shared). */
/* Locked (mid-reply) popover rows: not clickable, no dimming. */
.pop-row.locked,
.pop-footer.locked {
  cursor: not-allowed;
}
.pop-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
/* Rename/Delete options popover (compact variant of the shared pop-row). */
.opts-list {
  min-width: 150px;
}
.opt-row {
  align-items: center;
  gap: 10px;
  font-size: 0.85rem;
  padding: 5px 10px;
}
.opt-row i {
  font-size: 0.9rem;
  color: var(--p-surface-500);
}
.opt-row:hover i {
  color: inherit;
}
.opt-row.danger,
.opt-row.danger i {
  color: var(--p-red-500);
}
.opt-row.danger:hover {
  background: color-mix(in srgb, var(--p-red-500) 10%, transparent);
  color: var(--p-red-500);
}
.opt-row.danger:hover i {
  color: var(--p-red-500);
}
.pop-item-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* Bottom prefs: accent picker + theme toggle. */
.prefs {
  border-top: 1px solid var(--p-surface-200);
  padding: 12px 8px 4px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 14px;
}
.prefs.collapsed {
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 12px 0 4px;
}
</style>
