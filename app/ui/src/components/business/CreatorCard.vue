<script setup lang="ts">
import type { CreatorSummary } from '@/types/api'
import { proxyImage } from '@/composables/useImageProxy'

defineProps<{ creator: CreatorSummary }>()

function fmt(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(1)}万` : String(n)
}
</script>

<template>
  <router-link
    :to="`/creators/${creator.mid}`"
    class="flex items-center gap-4 bg-card rounded-[12px] p-4 shadow-[var(--shadow-default)]
           transition-shadow duration-200 hover:shadow-[var(--shadow-hover)]
           cursor-pointer no-underline"
  >
    <img
      v-if="proxyImage(creator.face)"
      :src="proxyImage(creator.face)!"
      :alt="creator.name"
      class="w-12 h-12 rounded-full object-cover shrink-0"
    />
    <div v-else class="w-12 h-12 rounded-full bg-border shrink-0 flex items-center justify-center text-text-secondary text-xs">
      UP
    </div>
    <div class="flex-1 min-w-0">
      <p class="font-semibold text-text text-sm truncate">{{ creator.name }}</p>
      <p class="text-xs text-text-secondary mt-0.5">
        {{ creator.video_count }} 个视频 &middot; {{ fmt(creator.total_views) }} 总播放
      </p>
    </div>
  </router-link>
</template>
