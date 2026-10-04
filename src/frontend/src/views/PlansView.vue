<!-- Saved-plans overview page (/plans): grid of plan cards linking to detail. -->
<script setup lang="ts">
import Button from 'primevue/button';
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { createConversationId } from '../api/travelService';
import { useLibraryStore } from '../stores/travel';
import LibraryListPage from '../components/library/LibraryListPage.vue';

const library = useLibraryStore();
const router = useRouter();

onMounted(() => {
  if (!library.loaded) void library.load();
});

function subtitle(p: { destination: string; dates: string }): string {
  return [p.destination, p.dates].filter(Boolean).join(' · ') || 'Saved trip';
}
</script>

<template>
  <LibraryListPage
    title="Saved plans"
    subtitle="Snapshots of your conversations, ready to revisit."
    empty-title="No saved plans yet"
    empty-text="Open a conversation, pick some options and press “Save plan”."
    :is-empty="!library.plans.length"
  >
    <template #actions>
      <Button label="New trip" icon="pi pi-plus" @click="router.push(`/trip/${createConversationId()}`)" />
    </template>
    <RouterLink v-for="p in library.plans" :key="p.id" :to="`/plans/${p.id}`" class="lib-card">
      <strong>{{ p.title }}</strong>
      <p class="meta">{{ subtitle(p) }}</p>
      <p v-if="p.description" class="desc">{{ p.description }}</p>
    </RouterLink>
  </LibraryListPage>
</template>
