<!-- Right-column panel of the chat view: trip requirements and trip plan.
      Collapses to a slim toggle strip;
      on narrow screens it renders inside a slide-over drawer instead. -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useLocalStorageToggle } from '../../composables/useLocalStorageToggle';
import { useTravelStore } from '../../stores/travel';
import { formatOptionPrice } from '../chat/richtext';

defineProps<{ drawer?: boolean }>();

const travel = useTravelStore();

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

// Money in the plan currency (formatOptionPrice without per-person math).
const formatMoney = (n: number) =>
  formatOptionPrice({ price: n, currency: travel.planCurrency, per_person: false });
const travelersCount = computed(() => {
  const raw = travel.requirements.find((r) => r.key === 'travelers')?.value;
  const n = raw ? parseInt(raw, 10) : NaN;
  return Number.isFinite(n) && n > 0 ? n : null;
});
// Per-person items show the trip total prominent + the per-person
// breakdown discreet below; everything else shows its price as-is.
const lineTotal = (price: number | null, perPerson: boolean, currency: string | null) =>
  price === null || price === undefined
    ? '—'
    : formatOptionPrice({
        price: perPerson && travelersCount.value ? price * travelersCount.value : price,
        currency: currency ?? travel.planCurrency,
        per_person: false,
      });
const lineDetail = (price: number | null, perPerson: boolean, currency: string | null) =>
  perPerson && travelersCount.value && travelersCount.value > 1 && price !== null && price !== undefined
    ? `${formatOptionPrice({ price, currency: currency ?? travel.planCurrency, per_person: false })} × ${travelersCount.value}`
    : '';
const barPct = computed(() => {
  if (!travel.planBudget) return 0;
  return Math.min(100, Math.round((travel.planTotal / travel.planBudget) * 100));
});

// Category -> inline SVG badge icon (category name stays out of the text:
// the icon says what it is, the subtitle carries dates/details).
const CATEGORY_ICONS: Record<string, string> = {
  transportation:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>',
  accommodation:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
  rental_car:
    '<svg viewBox="0 -960 960 960" fill="currentColor"><path d="M240-200v40q0 17-11.5 28.5T200-120h-40q-17 0-28.5-11.5T120-160v-320l84-240q6-18 21.5-29t34.5-11h440q19 0 34.5 11t21.5 29l84 240v320q0 17-11.5 28.5T800-120h-40q-17 0-28.5-11.5T720-160v-40H240Zm-8-360h496l-42-120H274l-42 120Zm-32 80v200-200Zm100 160q25 0 42.5-17.5T360-380q0-25-17.5-42.5T300-440q-25 0-42.5 17.5T240-380q0 25 17.5 42.5T300-320Zm360 0q25 0 42.5-17.5T720-380q0-25-17.5-42.5T660-440q-25 0-42.5 17.5T600-380q0 25 17.5 42.5T660-320Zm-460 40h560v-200H200v200Z"/></svg>',
  activities:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
};
const iconFor = (category: string) => CATEGORY_ICONS[category] ?? CATEGORY_ICONS.activities;
</script>

<template>
  <aside class="state" :class="{ 'in-drawer': drawer }">
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
          <div v-if="!travel.plan.length" class="plan-empty">
            <b>Your trip plan is empty</b>
            <p>Your picks will land here when you choose options from the chat.</p>
          </div>
          <div v-else class="tl">
            <div v-for="item in travel.plan" :key="`${item.category}:${item.option_id}`" class="tl-item">
              <span class="badge" v-html="iconFor(item.category)" />
              <span class="tx"><b>{{ item.label }}</b><small v-if="item.details">{{ item.details }}</small></span>
              <span class="pr">{{ lineTotal(item.price, item.per_person, item.currency) }}<small v-if="lineDetail(item.price, item.per_person, item.currency)">{{ lineDetail(item.price, item.per_person, item.currency) }}</small></span>
            </div>
          </div>
          <div v-if="travel.plan.length" class="row total">
            <span>Total</span>
            <strong>{{ formatMoney(travel.planTotal) }} <span v-if="travel.planBudget !== null" class="muted">of {{ formatMoney(travel.planBudget) }}</span></strong>
          </div>
          <div v-if="travel.plan.length && travel.planBudget !== null" class="pbar" :class="{ over: travel.planOverBudget }">
            <i :style="{ width: barPct + '%' }" />
          </div>
          <div v-if="travel.plan.length && travel.planBudget !== null" class="row">
            <span class="muted">{{ travel.planOverBudget ? 'Over by' : 'Remaining' }}</span>
            <strong :class="travel.planOverBudget ? 'bad' : 'ok'">{{ formatMoney(Math.abs(travel.planBudget - travel.planTotal)) }}</strong>
          </div>
        </div>
      </div>
    </section>
  </aside>
</template>

<style scoped>
.state {
  width: var(--app-state-width);
  flex-shrink: 0;
  height: 100%;
  min-height: 0;
  background: var(--p-surface-50);
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
/* Section header button (collapsible). Animation classes in main.css. */
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
  padding: 6px 8px;
  margin-bottom: 10px;
  border-radius: 6px;
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
  background: var(--p-surface-100);
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
  border-bottom: 1px dashed var(--p-surface-200);
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
/* Narrow variant inside the small-screen drawer */
.in-drawer {
  width: auto;
  border: 0;
  padding: 0;
  overflow: visible;
}
/* Trip plan empty state: dashed rounded box, no icon */
.plan-empty {
  border: 1.5px dashed var(--p-surface-300);
  border-radius: 10px;
  padding: 12px 14px;
  text-align: left;
}
.plan-empty b {
  display: block;
  font-size: 0.85rem;
}
.plan-empty p {
  margin: 4px 0 0;
  font-size: 0.82rem;
  color: var(--p-surface-500);
}
.row {
  display: flex;
  justify-content: space-between;
  font-size: 0.88rem;
  margin-bottom: 4px;
}
.row.total {
  font-weight: 700;
  margin-top: 6px;
  padding-top: 8px;
  border-top: 1px solid var(--p-surface-200);
}
.tl {
  position: relative;
  margin: 4px 0 4px 15px;
  padding-left: 22px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
/* Vertical line fading out at both ends instead of cutting abruptly. */
.tl::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  background: linear-gradient(
    to bottom,
    transparent,
    color-mix(in srgb, var(--p-primary-500) 25%, transparent) 5%,
    color-mix(in srgb, var(--p-primary-500) 25%, transparent) 95%,
    transparent
  );
}
.tl-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.88rem;
}
.badge {
  position: absolute;
  left: -38px;
  width: 30px;
  height: 30px;
  flex: none;
  border-radius: 9px;
  background: var(--p-surface-0);
  border: 2px solid color-mix(in srgb, var(--p-primary-500) 25%, transparent);
  color: var(--p-primary-600);
  display: flex;
  align-items: center;
  justify-content: center;
}
.badge svg {
  width: 16px;
  height: 16px;
}
/* v-html icons have no scoped attributes: pierce them explicitly. */
.badge :deep(svg) {
  width: 16px;
  height: 16px;
}
.tx {
  flex: 1;
  min-width: 0;
  line-height: 1.3;
}
.tx b {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
}
.tx small {
  color: var(--p-surface-500);
}
.pr {
  font-weight: 700;
  white-space: nowrap;
  text-align: right;
}
.pr small {
  display: block;
  font-weight: 400;
  font-size: 0.72rem;
  color: var(--p-surface-500);
}
.pbar {
  height: 5px;
  border-radius: 99px;
  background: color-mix(in srgb, var(--p-primary-500) 20%, transparent);
  margin: 8px 0;
  overflow: hidden;
}
.pbar i {
  display: block;
  height: 100%;
  background: var(--p-primary-500);
  border-radius: 99px;
}
.pbar.over i {
  background: var(--p-red-500);
}
.ok {
  color: var(--p-green-600);
}
.bad {
  color: var(--p-red-500);
}
</style>
