<!-- Shared layout for the /conversations and /plans overview pages:
     header (title + subtitle + action slot), dashed empty state,
     and a responsive card grid. Card markup comes from the default
     slot; use class "lib-card" so both pages share the card shell. -->
<script setup lang="ts">
defineProps<{
  title: string;
  subtitle: string;
  emptyTitle: string;
  emptyText: string;
  isEmpty: boolean;
}>();
</script>

<template>
  <div class="lib slim-scroll">
    <div class="lib-head">
      <div>
        <h1>{{ title }}</h1>
        <p class="muted">{{ subtitle }}</p>
      </div>
      <slot name="actions" />
    </div>
    <div v-if="isEmpty" class="lib-empty">
      <b>{{ emptyTitle }}</b>
      <p>{{ emptyText }}</p>
    </div>
    <div v-else class="lib-grid">
      <slot />
    </div>
  </div>
</template>

<style>
.lib {
  max-width: 56rem;
  margin: 0 auto;
  padding: 32px 24px;
  width: 100%;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.lib-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}
.lib-head h1 {
  margin: 0;
  font-size: 1.3rem;
}
.lib-head .muted {
  margin: 4px 0 0;
}
.lib-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}
/* Shared card shell (both pages): only the inner content differs. */
.lib-card {
  border: 1px solid var(--p-surface-200);
  border-radius: 10px;
  padding: 14px 16px;
  background: var(--p-surface-50);
  color: inherit;
  display: block;
}
.lib-card:hover {
  border-color: var(--p-primary-400);
  text-decoration: none;
}
.lib-card strong {
  display: block;
}
.lib-card .meta {
  margin: 4px 0 0;
  font-size: 0.85rem;
  color: var(--p-surface-500);
}
.lib-card .desc {
  margin: 8px 0 0;
  font-size: 0.85rem;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.lib-empty {
  border: 1.5px dashed var(--p-surface-300);
  border-radius: 10px;
  padding: 20px;
}
.lib-empty p {
  margin: 4px 0 0;
  color: var(--p-surface-500);
  font-size: 0.88rem;
}
</style>
