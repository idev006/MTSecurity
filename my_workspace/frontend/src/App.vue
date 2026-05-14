<template>
  <RouterView />
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import { useThemeStore } from '@/stores/theme'

// Instantiate the store — the module-level IIFE already applied the saved theme,
// but creating the store here ensures Pinia tracks it from the very first render.
useThemeStore()
</script>
