<!-- Welcome hero for empty threads: greeting + capability chips + clickable
     prompt suggestions (clicks fill the composer via draftOverride). -->
<script setup lang="ts">
const emit = defineEmits<{ select: [text: string] }>();

const SUGGESTIONS: { title: string; prompt: string; icon: string }[] = [
  {
    title: 'Lisbon getaway',
    prompt: 'I want a 3-day getaway to Lisbon with €800',
    icon: 'pi pi-building',
  },
  {
    title: 'Japan in spring',
    prompt: 'Plan a one-week trip to Japan in spring for 2 people',
    icon: 'pi pi-globe',
  },
  {
    title: 'Paris in June',
    prompt: 'Find me flights and a hotel in Paris for June, 4 nights for 2 people',
    icon: 'pi pi-send',
  },
  {
    title: 'Destination recommendations',
    prompt: 'Where should I go for a beach holiday in Europe in July with around €1500?',
    icon: 'pi pi-compass',
  },
];

const CAPABILITIES: { label: string; icon: string }[] = [
  { label: 'Flights', icon: 'pi pi-send' },
  { label: 'Hotels', icon: 'pi pi-building' },
  { label: 'Tours', icon: 'pi pi-map' },
  { label: 'Cars', icon: 'pi pi-car' },
  { label: 'Budget', icon: 'pi pi-wallet' },
];
</script>

<template>
  <div class="welcome">
    <div class="hero">
      <h1 class="title">Where do you want to travel?</h1>
      <p class="subtitle">
        Describe your trip in natural language — I take care of flights,
        accommodation, activities and budget.
      </p>
      <ul class="caps" aria-label="Capabilities">
        <li v-for="c in CAPABILITIES" :key="c.label" class="cap">
          <i :class="c.icon" aria-hidden="true" />
          <span>{{ c.label }}</span>
        </li>
      </ul>
    </div>
    <div class="suggestions">
      <button
        v-for="s in SUGGESTIONS"
        :key="s.title"
        type="button"
        class="suggestion"
        @click="emit('select', s.prompt)"
      >
        <span class="suggestion-icon"><i :class="s.icon" aria-hidden="true" /></span>
        <span class="suggestion-title">{{ s.title }}</span>
        <i class="pi pi-arrow-up-right suggestion-go" aria-hidden="true" />
        <span class="suggestion-prompt">{{ s.prompt }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.welcome {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 28px;
  padding: 24px 20px 120px;
}
.hero {
  text-align: center;
  max-width: 560px;
}
.title {
  margin: 0 0 8px;
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--p-surface-900);
}
.subtitle {
  margin: 0 0 16px;
  font-size: 0.95rem;
  line-height: 1.5;
  color: var(--p-surface-500);
}
.caps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}
.cap {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--p-surface-400);
  /* Informational only: no button affordance so they read as labels. */
  background: transparent;
  border: 0;
  padding: 2px 4px;
  cursor: default;
  user-select: none;
}
.cap i {
  font-size: 0.78rem;
  color: var(--p-surface-400);
}
.suggestions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  width: min(100%, 560px);
}
.suggestion {
  display: grid;
  grid-template-columns: auto 1fr auto;
  grid-template-rows: auto auto;
  column-gap: 10px;
  align-items: start;
  text-align: left;
  cursor: pointer;
  font-family: inherit;
  color: inherit;
  background: var(--p-surface-0);
  border: 1px solid var(--p-surface-200);
  border-radius: 14px;
  padding: 12px 14px;
  box-shadow: 0 1px 2px rgba(60, 50, 30, 0.06);
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
}
.suggestion:hover {
  border-color: var(--p-primary-500);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--p-primary-500) 25%, transparent), 0 4px 12px rgba(60, 50, 30, 0.1);
  transform: translateY(-1px);
}
.suggestion:focus-visible {
  outline: 2px solid var(--p-primary-500);
  outline-offset: 2px;
}
.suggestion-icon {
  grid-row: span 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--p-primary-600) 12%, transparent);
  color: var(--p-primary-600);
}
.suggestion-icon i {
  font-size: 0.9rem;
}
.suggestion-go {
  font-size: 0.75rem;
  margin-top: 4px;
  color: var(--p-surface-400);
  transition: color 0.15s, transform 0.15s;
}
.suggestion:hover .suggestion-go {
  color: var(--p-primary-600);
  transform: translate(1px, -1px);
}
.suggestion-title {
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--p-surface-900);
  align-self: center;
}
.suggestion-prompt {
  margin-top: 2px;
  font-size: 0.8rem;
  line-height: 1.4;
  color: var(--p-surface-500);
}
/* Dark mode: no warm shadow (faint halo, cf. .float-composer); stronger ring. */
html.dark .suggestion:hover {
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--p-primary-500) 35%, transparent);
}
@media (max-width: 560px) {
  .suggestions {
    grid-template-columns: 1fr;
  }
}
</style>
