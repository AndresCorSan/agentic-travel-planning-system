<!-- Application root: mounts the shell plus the global toast layer. -->
<script setup lang="ts">
import Toast from 'primevue/toast';
import AppShell from './components/layout/AppShell.vue';
</script>

<template>
  <AppShell />
  <Toast position="bottom-right" />
</template>
