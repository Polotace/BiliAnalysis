<script setup lang="ts">
withDefaults(defineProps<{ sidebar?: boolean }>(), { sidebar: false })
</script>

<template>
  <main :class="['max-w-7xl mx-auto px-6 py-4', { 'lg:ml-44': sidebar }]">
    <slot />
  </main>
</template>
