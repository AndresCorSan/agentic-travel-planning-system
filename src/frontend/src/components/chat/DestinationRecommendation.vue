<!-- Rich carousel inside assistant messages: candidate destinations as
     tall horizontally-scrollable cards (one per candidate, snap scroll).
     `items` carries backend candidates.
     Card headers show a Wikimedia Commons photo (resolved lazily by
     destination name) with the title overlaid; without a photo the
     plain header is used instead. -->
<script setup lang="ts">
import Button from 'primevue/button';
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { useTravelStore } from '../../stores/travel';
import type { Destination } from '../../types';

const props = defineProps<{ messageId: string; chosen: string | null; items?: Destination[] }>();
const emit = defineEmits<{ choose: [messageId: string, id: string, name: string] }>();

// CONTRACT: `items` carries the backend destination candidates for this turn.
const items = computed(() => props.items ?? []);

// Optimistic vote for this message wins until the confirmed destination
// arrives via requirements (props.chosen).
const travel = useTravelStore();
const effective = computed(() => travel.voted[props.messageId] ?? props.chosen);

// Lock only this carousel when its own card was chosen, so a new round stays selectable.
const locked = computed(
  () => effective.value != null && items.value.some((d) => d.name === effective.value)
);

const track = ref<HTMLElement | null>(null);
const active = ref(0);

function cards(): HTMLElement[] {
  const el = track.value;
  if (!el) return [];
  return [...el.querySelectorAll<HTMLElement>('.dest-card')];
}
// scrollLeft that centers `card` in the track. Rect-based (not offsetLeft,
// which is relative to the offset parent, not the scroll container).
function centeredLeft(el: HTMLElement, card: HTMLElement): number {
  const elRect = el.getBoundingClientRect();
  const cardRect = card.getBoundingClientRect();
  return el.scrollLeft + (cardRect.left - elRect.left) - (el.clientWidth - cardRect.width) / 2;
}
// Center the target card in view; at either end the scroll bounds
// naturally leave the edge card flush against that side.
function step(dir: number) {
  const el = track.value;
  if (!el) return;
  const list = cards();
  if (!list.length) return;
  const next = Math.min(list.length - 1, Math.max(0, active.value + dir));
  el.scrollTo({ left: centeredLeft(el, list[next]), behavior: 'smooth' });
}
function onScroll() {
  const el = track.value;
  if (!el) return;
  updateEdgeFades(el);
  const center = el.scrollLeft + el.clientWidth / 2;
  let best = 0;
  let bestDist = Infinity;
  for (const [i, card] of cards().entries()) {
    const dist = Math.abs(centeredLeft(el, card) + el.clientWidth / 2 - center);
    if (dist < bestDist) {
      bestDist = dist;
      best = i;
    }
  }
  active.value = best;
}

// Edge fades: instead of hard-clipping peeking cards, the track fades out
// on the sides that still hide content (no fade at rest edges or when
// everything fits). Recomputed on scroll, mount, resize and item changes.
const EDGE_PX = 4;
const fadeLeft = ref(false);
const fadeRight = ref(false);
function updateEdgeFades(el: HTMLElement) {
  const max = el.scrollWidth - el.clientWidth;
  fadeLeft.value = el.scrollLeft > EDGE_PX;
  fadeRight.value = el.scrollLeft < max - EDGE_PX;
}
function refreshFades() {
  if (track.value) updateEdgeFades(track.value);
}
onMounted(() => {
  refreshFades();
  window.addEventListener('resize', refreshFades);
});
onUnmounted(() => {
  window.removeEventListener('resize', refreshFades);
});
const RING_CIRC = 2 * Math.PI * 18;
function ringOffset(suitability: number): number {
  const s = Math.min(100, Math.max(0, suitability));
  return RING_CIRC * (1 - s / 100);
}

function hideBrokenFlag(e: Event) {
  ((e.target as HTMLImageElement).style.display = 'none');
}

// Destination photos via Wikipedia pageimages (Wikimedia Commons, CORS
// open). Resolved lazily per card; failures fall back to the plain header.
const images = ref<Record<string, string>>({});
const pending = ref<Record<string, boolean>>({});
const failed = new Set<string>();

async function thumbFor(title: string): Promise<string | null> {
  try {
    const url =
      'https://en.wikipedia.org/w/api.php?action=query&format=json&origin=*&prop=pageimages' +
      `&redirects=1&titles=${encodeURIComponent(title)}&formatversion=2&pithumbsize=600`;
    const res = await fetch(url);
    const data = await res.json();
    const thumb = data?.query?.pages?.[0]?.thumbnail?.source;
    return typeof thumb === 'string' && thumb ? thumb : null;
  } catch {
    return null;
  }
}

async function searchTitle(d: Destination): Promise<string | null> {
  try {
    const q = d.country ? `${d.name} ${d.country}` : d.name;
    const url =
      'https://en.wikipedia.org/w/api.php?action=query&format=json&origin=*&list=search' +
      `&srsearch=${encodeURIComponent(q)}&srlimit=1&formatversion=2`;
    const res = await fetch(url);
    const data = await res.json();
    const title = data?.query?.search?.[0]?.title;
    return typeof title === 'string' && title ? title : null;
  } catch {
    return null;
  }
}

async function resolveImage(d: Destination) {
  if (!d.name || images.value[d.id] || pending.value[d.id] || failed.has(d.id)) return;
  pending.value[d.id] = true;
  try {
    let thumb = await thumbFor(d.name);
    if (!thumb && d.country) thumb = await thumbFor(`${d.name}, ${d.country}`);
    if (!thumb) {
      const title = await searchTitle(d);
      if (title) thumb = await thumbFor(title);
    }
    if (thumb) images.value[d.id] = thumb;
    else failed.add(d.id);
  } catch {
    failed.add(d.id);
  } finally {
    delete pending.value[d.id];
  }
}
function onPhotoError(d: Destination) {
  failed.add(d.id);
  delete images.value[d.id];
}
watch(
  items,
  (list) => {
    for (const d of list) void resolveImage(d);
    // Card widths change once photos resolve: recompute after layout.
    void nextTick(refreshFades);
  },
  { immediate: true }
);
</script>

<template>
  <div class="dest-carousel">
    <div ref="track" class="dest-track" :class="{ 'fade-left': fadeLeft, 'fade-right': fadeRight }" @scroll.passive="onScroll">
      <div v-for="(d, i) in items" :key="d.id" class="dest-card" :class="{ first: i === 0 && !locked, selected: effective === d.name }">
        <div v-if="images[d.id]" class="hero">
          <img
            class="hero-img"
            :src="images[d.id]"
            :alt="d.name"
            loading="lazy"
            title="Image via Wikimedia Commons"
            @error="onPhotoError(d)"
          >
          <div class="shade" />
          <div class="cap">
            <div>
              <div class="kicker light">
                Candidate {{ i + 1 }}<img
                  v-if="d.country_code"
                  class="flag"
                  :src="`https://flagcdn.com/w40/${d.country_code}.png`"
                  :alt="`${d.country} flag`"
                  loading="lazy"
                  @error="hideBrokenFlag"
                >
              </div>
              <div class="dest-name light">{{ d.name }}<span v-if="d.country">, {{ d.country }}</span></div>
            </div>
            <div class="ring" :title="`${d.suitability}/100 match`">
              <svg width="44" height="44">
                <circle cx="22" cy="22" r="18" fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="3.5" />
                <circle
                  cx="22" cy="22" r="18" fill="none" stroke="var(--p-primary-400)" stroke-width="3.5"
                  :stroke-dasharray="RING_CIRC" :stroke-dashoffset="ringOffset(d.suitability)"
                  stroke-linecap="round"
                />
              </svg>
              <span class="on-photo">{{ d.suitability }}</span>
            </div>
          </div>
        </div>
        <div v-else-if="pending[d.id]" class="hero skeleton" />
        <div v-else class="plain-top">
          <div>
            <div class="kicker">
              Candidate {{ i + 1 }}<img
                v-if="d.country_code"
                class="flag"
                :src="`https://flagcdn.com/w40/${d.country_code}.png`"
                :alt="`${d.country} flag`"
                loading="lazy"
                @error="hideBrokenFlag"
              >
            </div>
            <div class="dest-name">{{ d.name }}<span v-if="d.country">, {{ d.country }}</span></div>
          </div>
          <div class="ring" :title="`${d.suitability}/100 match`">
            <svg width="44" height="44">
              <circle cx="22" cy="22" r="18" fill="none" stroke="var(--p-surface-200)" stroke-width="3.5" />
              <circle
                cx="22" cy="22" r="18" fill="none" stroke="var(--p-primary-600)" stroke-width="3.5"
                :stroke-dasharray="RING_CIRC" :stroke-dashoffset="ringOffset(d.suitability)"
                stroke-linecap="round"
              />
            </svg>
            <span>{{ d.suitability }}</span>
          </div>
        </div>
        <div class="dest-body">
          <p v-if="d.tagline" class="tagline">{{ d.tagline }}</p>
          <p v-if="d.highlights.length" class="subhead">Why it fits</p>
          <ul v-if="d.highlights.length">
            <li v-for="h in d.highlights" :key="h">{{ h }}</li>
          </ul>
          <p v-if="d.drawback" class="warn">Watch out: {{ d.drawback }}</p>
          <div class="dest-foot">
            <Button
            :label="effective === d.name ? 'Selected' : `Choose ${d.name}`"
            size="small"
            :severity="effective === d.name ? 'success' : 'primary'"
            :disabled="locked"
            :icon="effective === d.name ? 'pi pi-check' : undefined"
            @click="emit('choose', messageId, d.id, d.name)"
            />
          </div>
        </div>
      </div>
    </div>
    <div v-if="items.length > 1" class="dest-nav">
      <Button icon="pi pi-chevron-left" text rounded size="small" aria-label="Previous destination" @click="step(-1)" />
      <div class="dots"><span v-for="(_, i) in items" :key="i" :class="{ on: i === active }" /></div>
      <Button icon="pi pi-chevron-right" text rounded size="small" aria-label="Next destination" @click="step(1)" />
    </div>
    <p v-if="Object.keys(images).length" class="photo-credit">Photos: Wikimedia Commons contributors.</p>
  </div>
</template>

<style scoped>
.dest-carousel {
  margin: 6px 0 4px;
}
.dest-track {
  --fade: 32px;
  display: flex;
  gap: 12px;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  padding-bottom: 8px;
}
/* Edge fade instead of a hard clip on peeking cards. Mask only (no
   layout change), vendor-prefixed for Safari. */
.dest-track.fade-left {
  -webkit-mask-image: linear-gradient(to right, transparent, black var(--fade));
  mask-image: linear-gradient(to right, transparent, black var(--fade));
}
.dest-track.fade-right {
  -webkit-mask-image: linear-gradient(to left, transparent, black var(--fade));
  mask-image: linear-gradient(to left, transparent, black var(--fade));
}
.dest-track.fade-left.fade-right {
  -webkit-mask-image: linear-gradient(to right, transparent, black var(--fade), black calc(100% - var(--fade)), transparent);
  mask-image: linear-gradient(to right, transparent, black var(--fade), black calc(100% - var(--fade)), transparent);
}
.dest-card {
  flex: 0 0 82%;
  scroll-snap-align: center;
  border: 1px solid var(--p-surface-200);
  border-radius: 12px;
  background: var(--p-surface-50);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.dest-card.first {
  border-color: var(--p-primary-400);
}
.dest-card.selected {
  border-color: var(--p-primary-400);
  box-shadow: 0 0 0 1px var(--p-primary-400);
}
/* Photo hero (G3): fixed height + skeleton reserve the space so the
   card doesn't jump when the photo arrives. */
.hero {
  position: relative;
  height: 150px;
  flex-shrink: 0;
  background: var(--p-surface-200);
}
.hero.skeleton {
  background: linear-gradient(100deg, var(--p-surface-100) 40%, var(--p-surface-200) 50%, var(--p-surface-100) 60%);
  background-size: 200% 100%;
  animation: shimmer 1.2s infinite;
}
@keyframes shimmer {
  to { background-position: -200% 0; }
}
.hero-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.shade {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(15, 23, 42, 0.78), rgba(15, 23, 42, 0.15));
}
.cap {
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}
.plain-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 14px 16px 0;
}
.dest-body {
  padding: 0 16px 14px;
}
/* Hero cards already have top spacing from the photo; plain cards
   get it from the header padding above. */
.hero + .dest-body .tagline {
  margin-top: 12px;
}
.plain-top + .dest-body .tagline {
  margin-top: 10px;
}
.kicker {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  line-height: 1;
  color: var(--p-primary-600);
}
.kicker.light {
  /* Soft accent tone tied to the theme's actual primary. */
  color: color-mix(in srgb, var(--p-primary-600) 55%, white);
}
.dest-name {
  font-family: Georgia, serif;
  font-size: 1.5rem;
  margin: 0;
}
.dest-name.light {
  color: #fff;
}
.flag {
  width: 18px;
  height: auto;
  border-radius: 2px;
  vertical-align: -1px;
  margin-left: 6px;
}
.ring {
  position: relative;
  width: 44px;
  height: 44px;
  flex-shrink: 0;
}
.ring svg {
  transform: rotate(-90deg);
  display: block;
}
.ring span {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.68rem;
  font-weight: 800;
  color: var(--p-primary-700);
  /* Digits carry descender space below the glyphs, so they render
     slightly high: nudge down to optical center. */
  transform: translateY(1px);
}
.ring span.on-photo {
  color: #fff;
}
.tagline {
  margin: 0 0 8px;
  font-size: 0.9rem;
  line-height: 1.6;
}
.subhead {
  font-weight: 600;
  font-size: 0.85rem;
  margin: 10px 0 6px;
}
.dest-card ul {
  margin: 0 0 10px;
  padding-left: 18px;
  font-size: 0.87rem;
}
.dest-card li {
  margin: 2px 0;
}
.warn {
  font-size: 0.83rem;
  color: var(--p-surface-500);
  border-left: 3px solid var(--p-surface-300);
  padding-left: 10px;
  margin: 0 0 14px;
}
.dest-foot {
  margin-top: auto;
  padding-top: 4px;
}
.dest-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}
.dots {
  display: flex;
  gap: 6px;
  margin: 0 auto;
}
.dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--p-surface-300);
}
.dots span.on {
  background: var(--p-primary-600);
}
.photo-credit {
  font-size: 0.68rem;
  color: var(--p-surface-500);
  text-align: center;
  margin: 2px 0 0;
}
</style>
