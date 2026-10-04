<!-- Welcome hero for empty threads: greeting + capability chips, a
     suggested-messages section, and a destination-discovery section.
     Clicks fill the composer via draftOverride. -->
<script setup lang="ts">
const emit = defineEmits<{ select: [text: string] }>();

interface Suggestion {
  title: string;
  prompt: string;
  icon: string;
}

const TRIP_SUGGESTIONS: Suggestion[] = [
  {
    title: 'Lisbon getaway',
    prompt: 'The two of us are going to Lisbon from June 12 to 15 and we need flights and a hotel. We do not want to spend more than €800 altogether',
    icon: 'pi pi-building',
  },
  {
    title: 'Hiking in the Dolomites',
    prompt: 'I am hiking the Dolomites on my own from July 18 to 25. What will the weather be like up there? I will also need a hotel — I have got about €1500 to spend',
    icon: 'pi pi-sun',
  },
  {
    title: 'Andalusia road trip',
    prompt: 'Four of us are doing a road trip through Andalusia from September 10 to 15. We need a rental car big enough for everyone, plus hotels and some tours. We have set aside €2500 for the whole thing',
    icon: 'pi pi-car',
  },
];

const DISCOVERY_SUGGESTION: Suggestion = {
  title: 'Destination recommendations',
  prompt: 'We fancy a beach holiday somewhere in Europe in July — two adults and two kids. Our budget is €3000 and we cannot go over it. Where should we go?',
  icon: 'pi pi-compass',
};

const CAPABILITIES: { label: string; icon: string }[] = [
  { label: 'Transport', icon: 'pi pi-send' },
  { label: 'Hotels', icon: 'pi pi-building' },
  { label: 'Activities', icon: 'pi pi-map' },
  { label: 'Rental cars', icon: 'pi pi-car' },
  { label: 'Weather', icon: 'pi pi-cloud' },
  { label: 'Budget', icon: 'pi pi-wallet' },
];
</script>

<template>
  <div class="welcome slim-scroll">
    <div class="hero">
      <h1 class="title">Where do you want <span class="grad">to travel?</span></h1>
      <p class="subtitle">
        Describe your trip in natural language and let me handle the details.
      </p>
      <ul class="caps" aria-label="Capabilities">
        <li v-for="c in CAPABILITIES" :key="c.label" class="cap">
          <i :class="c.icon" aria-hidden="true" />
          <span>{{ c.label }}</span>
        </li>
      </ul>
    </div>
    <section class="section" aria-label="Suggested messages">
      <h2 class="section-title"><span>Suggested messages</span></h2>
      <div class="suggestions">
        <button
          v-for="s in TRIP_SUGGESTIONS"
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
    </section>
    <section class="section" aria-label="Destination recommendations">
      <h2 class="section-title"><span>Not sure about your destination?</span></h2>
      <p class="section-sub">Tell me your budget, dates and tastes and I will recommend alternatives.</p>
      <div class="suggestions">
        <button type="button" class="suggestion" @click="emit('select', DISCOVERY_SUGGESTION.prompt)">
          <span class="suggestion-icon"><i :class="DISCOVERY_SUGGESTION.icon" aria-hidden="true" /></span>
          <span class="suggestion-title">{{ DISCOVERY_SUGGESTION.title }}</span>
          <i class="pi pi-arrow-up-right suggestion-go" aria-hidden="true" />
          <span class="suggestion-prompt">{{ DISCOVERY_SUGGESTION.prompt }}</span>
        </button>
      </div>
    </section>
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
  max-width: 640px;
}
.title {
  margin: 0 0 10px;
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: -0.01em;
  color: var(--p-surface-900);
}
.title .grad {
  background: linear-gradient(100deg, var(--p-primary-400), var(--p-primary-600));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.subtitle {
  margin: 0 auto 18px;
  max-width: 500px;
  font-size: 0.95rem;
  line-height: 1.55;
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
  font-weight: 600;
  color: var(--p-primary-600);
  /* Tinted pills (still plain labels, not buttons): distinct from the
     clickable suggestion cards below. */
  background: color-mix(in srgb, var(--p-primary-600) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--p-primary-600) 28%, transparent);
  border-radius: 999px;
  padding: 5px 12px;
  cursor: default;
  user-select: none;
}
.cap i {
  font-size: 0.78rem;
}
.suggestions {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  width: min(100%, 640px);
}
.section {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  width: min(100%, 640px);
}
/* Ruled headers (option B mockup): the title sits inside the separator. */
.section-title {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--p-surface-500);
}
.section-title::before,
.section-title::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--p-surface-200);
}
.section-title span {
  white-space: nowrap;
}
.section-sub {
  margin: -2px 0 0;
  font-size: 0.83rem;
  color: var(--p-surface-500);
  text-align: center;
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
</style>
