<!-- Conversations overview page (/conversations): grid of conversation
     cards linking back to the chat, sharing the LibraryListPage shell
     with the saved-plans page. -->
<script setup lang="ts">
import Button from 'primevue/button';
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { createConversationId } from '../api/travelService';
import { useLibraryStore } from '../stores/travel';
import { formatUpdatedAt } from '../utils/datetime';
import LibraryListPage from '../components/library/LibraryListPage.vue';

const library = useLibraryStore();
const router = useRouter();

onMounted(() => {
  if (!library.loaded) void library.load();
});
</script>

<template>
  <LibraryListPage
    title="Conversations"
    subtitle="All your trips, most recent first."
    empty-title="No conversations yet"
    empty-text="Start a new trip and it will show up here."
    :is-empty="!library.conversations.length"
  >
    <template #actions>
      <Button label="New trip" icon="pi pi-plus" @click="router.push(`/trip/${createConversationId()}`)" />
    </template>
    <RouterLink
      v-for="c in library.conversations"
      :key="c.id"
      :to="`/trip/${c.id}`"
      class="lib-card"
    >
      <strong>{{ c.title }}</strong>
      <p class="meta">{{ formatUpdatedAt(c.updatedAt) }}</p>
    </RouterLink>
  </LibraryListPage>
</template>
