<script setup lang="ts">
defineProps<{ loading: boolean; hasMore: boolean }>()
</script>

<template>
  <div class="flex items-center justify-center py-8 gap-2 text-sm text-text-secondary">
    <template v-if="loading">
      <div class="w-5 h-5 border-2 border-border border-t-blue rounded-full animate-spin" />
      <span>加载更多…</span>
    </template>
    <span v-else-if="!hasMore">— 没有更多了 —</span>
  </div>
</template>
