<script setup lang="ts">
withDefaults(defineProps<{
  title: string
  description?: string
  divider?: boolean
}>(), { divider: false })
</script>

<template>
  <div class="mb-6">
    <h2 class="text-xl font-semibold text-text">{{ title }}</h2>
    <p v-if="description" class="text-sm text-text-secondary mt-1">{{ description }}</p>
    <el-divider v-if="divider" style="margin: 12px 0 0 0" />
  </div>
</template>
