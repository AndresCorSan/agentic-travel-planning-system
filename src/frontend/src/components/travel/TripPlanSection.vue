<!-- Trip plan timeline + budget bar, same look as the chat sidebar panel
      (TravelStatePanel). Props take a plan snapshot so both live state and
      saved plans render identically. -->
<script setup lang="ts">
import { computed } from 'vue';
import type { PlanItem } from '../../types';
import { formatOptionPrice, groupLabel } from '../chat/richtext';

const props = withDefaults(
  defineProps<{
    items: PlanItem[];
    total: number;
    currency: string | null;
    budget: number | null;
    overBudget: boolean;
    travelers: number | null;
    emptyText?: string;
  }>(),
  { emptyText: 'No choices in this snapshot.' }
);

// Money in the plan currency (formatOptionPrice without per-person math).
const formatMoney = (n: number) =>
  formatOptionPrice({ price: n, currency: props.currency, per_person: false });
// Per-person items show the trip total prominent + the per-person
// breakdown discreet below; everything else shows its price as-is.
const lineTotal = (price: number | null, perPerson: boolean, currency: string | null) =>
  price === null || price === undefined
    ? '—'
    : formatOptionPrice({
        price: perPerson && props.travelers ? price * props.travelers : price,
        currency: currency ?? props.currency,
        per_person: false,
      });
const lineDetail = (item: PlanItem) => {
  const price = item.price;
  if (price === null || price === undefined) return '';
  const currency = item.currency ?? props.currency;
  // Per-person items show the per-person rate below the trip total,
  // same "/ unit" style as the per-night and per-day hints.
  if (item.per_person && props.travelers && props.travelers > 1) {
    return `${formatOptionPrice({ price, currency, per_person: false })} pp`;
  }
  // Accommodation shows the per-night rate below the stay total.
  if (item.category === 'accommodation') {
    const nights = unitsFor(item, 'nights?');
    if (nights) {
      const displayTotal = item.per_person && props.travelers ? price * props.travelers : price;
      return `${formatOptionPrice({ price: displayTotal / nights, currency, per_person: false })} / night`;
    }
  }
  // Rental cars show the per-day rate below the rental total
  if (item.category === 'rental_car') {
    const days = unitsFor(item, 'days?');
    if (days) {
      const displayTotal = item.per_person && props.travelers ? price * props.travelers : price;
      return `${formatOptionPrice({ price: displayTotal / days, currency, per_person: false })} / day`;
    }
  }
  return '';
};
// Units for the per-night/per-day hints, read only from the option
// details ("7 nights — …", "2 days — …").
const unitsFor = (item: PlanItem, unit: string): number | null => {
  const m = item.details?.match(new RegExp(`(\\d+)\\s*${unit}`, 'i'));
  if (m) {
    const n = parseInt(m[1], 10);
    if (Number.isFinite(n) && n > 0) return n;
  }
  return null;
};
const barPct = computed(() => {
  if (!props.budget) return 0;
  return Math.min(100, Math.round((props.total / props.budget) * 100));
});
// Items without a known price: the total below is partial until they
// are priced. Listed in the footnote tooltip by label.
const unpricedItems = computed(() =>
  props.items.filter((i) => i.price === null || i.price === undefined)
);

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

// Display order: outbound transportation, accommodation, rental car,
// activities, then the remaining transportation legs (return...).
// Within the same slot, save order is preserved (stable sort).
// Group names come from the LLM ("outbound", "outbound leg 1", ...),
// so outbound is matched by prefix, not by exact string.
const OUTBOUND_PREFIXES = ['outbound', 'outward', 'departure'];
const RETURN_PREFIXES = ['return', 'inbound', 'homeward'];
function startsWithWord(text: string, prefix: string): boolean {
  return (
    text === prefix ||
    text.startsWith(prefix + ' ') ||
    text.startsWith(prefix + '_') ||
    text.startsWith(prefix + '-')
  );
}
function isOutboundGroup(group: string): boolean {
  const g = (group ?? '').trim().toLowerCase();
  if (!g) return true;
  if (RETURN_PREFIXES.some((p) => startsWithWord(g, p))) return false;
  return OUTBOUND_PREFIXES.some((p) => startsWithWord(g, p));
}
function planRank(item: PlanItem): [number, string] {
  const group = (item.group ?? '').trim().toLowerCase();
  if (item.category === 'transportation' && !isOutboundGroup(item.group ?? '')) return [4, group];
  switch (item.category) {
    case 'transportation': return [0, group];
    case 'accommodation': return [1, ''];
    case 'rental_car': return [2, ''];
    case 'activities': return [3, ''];
    default: return [5, item.category];
  }
}
const sortedItems = computed(() =>
  props.items
    .map((item, index) => ({ item, index }))
    .sort((a, b) => {
      const [ra, ga] = planRank(a.item);
      const [rb, gb] = planRank(b.item);
      return ra - rb || (ga < gb ? -1 : ga > gb ? 1 : 0) || a.index - b.index;
    })
    .map((e) => e.item)
);
</script>

<template>
  <div>
    <div v-if="!items.length" class="plan-empty">
      <b>Your trip plan is empty</b>
      <p>{{ emptyText }}</p>
    </div>
    <div v-else class="tl">
      <div v-for="item in sortedItems" :key="`${item.category}:${item.group ?? ''}:${item.option_id}`" class="tl-item">
        <span class="badge" v-html="iconFor(item.category)" />
        <span class="tx"><b>{{ item.label }}<span v-if="item.group" class="grp">{{ groupLabel(item.group) }}</span></b><small v-if="item.details">{{ item.details }}</small></span>
        <span class="pr">{{ lineTotal(item.price, item.per_person, item.currency) }}<small v-if="lineDetail(item)">{{ lineDetail(item) }}</small></span>
      </div>
    </div>
    <div v-if="items.length" class="row total">
      <span>Total</span>
      <strong>{{ formatMoney(total) }}<template v-if="unpricedItems.length"> *</template> <span v-if="budget !== null" class="muted">of {{ formatMoney(budget) }}</span></strong>
    </div>
    <p v-if="unpricedItems.length" class="footnote">* Excludes {{ unpricedItems.length }} item<template v-if="unpricedItems.length !== 1">s</template> with unknown price
      <span class="tip" tabindex="0" aria-label="Items with unknown price">
        <i class="pi pi-info-circle" />
        <span class="tipbox" role="tooltip"><b>Unknown price</b><span v-for="u in unpricedItems" :key="`${u.category}:${u.option_id}`" class="tipitem">{{ u.label }}</span></span>
      </span>
    </p>
    <div v-if="items.length && budget !== null" class="pbar" :class="{ over: overBudget }">
      <i :style="{ width: barPct + '%' }" />
    </div>
    <div v-if="items.length && budget !== null" class="row">
      <span class="muted">{{ overBudget ? 'Over by' : 'Remaining' }}</span>
      <strong :class="overBudget ? 'bad' : 'ok'">{{ formatMoney(Math.abs(budget - total)) }}</strong>
    </div>
  </div>
</template>

<style scoped>
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
.footnote {
  margin: 2px 0 6px;
  font-size: 0.75rem;
  color: var(--p-surface-500);
}
.footnote i {
  font-size: 0.72rem;
  vertical-align: -1px;
  cursor: help;
}
/* Custom tooltip (one row per unpriced item): dark card opening upwards,
   shown on hover or keyboard focus. Fixed colors so it reads well in
   both light and dark mode. */
.tip {
  position: relative;
  display: inline-block;
  outline: none;
}
.tipbox {
  display: none;
  position: absolute;
  right: -6px;
  bottom: calc(100% + 8px);
  min-width: 190px;
  max-width: 250px;
  background: #1c2029;
  color: #eef0f4;
  border: 1px solid #2f3541;
  border-radius: 9px;
  padding: 8px 12px 10px;
  font-size: 0.75rem;
  font-weight: 400;
  line-height: 1.45;
  box-shadow: 0 8px 24px rgb(0 0 0 / 0.3);
  z-index: 50;
  white-space: normal;
  cursor: default;
}
.tipbox::after {
  content: "";
  position: absolute;
  top: 100%;
  right: 12px;
  border: 6px solid transparent;
  border-top-color: #1c2029;
}
.tip:hover .tipbox,
.tip:focus-within .tipbox {
  display: block;
}
.tipbox b {
  display: block;
  margin-bottom: 3px;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  opacity: 0.7;
}
.tipitem {
  display: block;
  padding-left: 12px;
  position: relative;
}
.tipitem::before {
  content: "•";
  position: absolute;
  left: 2px;
  color: var(--p-primary-500);
}
.tl {
  position: relative;
  margin: 4px 0 4px 15px;
  padding-left: 22px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
/* Vertical line fading out at both ends instead of cutting abruptly.
   left:-2px centers the 2px line on the badge midpoint: badges sit at
   padding-left(22px) + left(-38px) + width/2(15px) = x -1px. */
.tl::before {
  content: "";
  position: absolute;
  left: -2px;
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
.grp {
  display: inline-block;
  font-size: 0.68rem;
  font-weight: 700;
  color: var(--p-primary-600);
  background: color-mix(in srgb, var(--p-primary-600) 12%, transparent);
  border-radius: 99px;
  padding: 1px 8px;
  margin-left: 6px;
  vertical-align: 1px;
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
