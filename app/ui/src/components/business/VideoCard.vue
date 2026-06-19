<script setup lang="ts">
import type { VideoSummary } from '@/types/api'
import { proxyImage } from '@/composables/useImageProxy'

defineProps<{ video: VideoSummary }>()

function fmt(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(1)}万` : String(n)
}
</script>

<template>
  <router-link
    :to="`/videos/${video.aid}`"
    class="block bg-card rounded-[12px] shadow-[var(--shadow-default)] overflow-hidden
           transition-shadow duration-200 hover:shadow-[var(--shadow-hover)] hover:-translate-y-0.5
           cursor-pointer no-underline"
  >
    <div class="relative h-[180px] bg-border overflow-hidden">
      <img
        v-if="proxyImage(video.cover_url)"
        :src="proxyImage(video.cover_url)!"
        :alt="video.title"
        class="w-full h-full object-cover"
        loading="lazy"
      />
      <div v-else class="w-full h-full flex items-center justify-center text-text-secondary text-sm">
        暂无封面
      </div>
      <span
        v-if="video.duration"
        class="absolute bottom-2 right-2 bg-black/75 text-white text-xs px-1.5 py-0.5 rounded tabular"
      >
        {{ video.duration }}
      </span>
    </div>
    <div class="p-[14px_16px]">
      <h3 class="text-[0.9375rem] font-semibold text-text leading-snug mb-2 line-clamp-2">
        {{ video.title }}
      </h3>
      <div class="flex gap-4 text-[0.8125rem] text-text-secondary tabular mb-2">
        <span>&#9654; {{ fmt(video.view) }}</span>
        <span>&#128077; {{ fmt(video.like_cnt) }}</span>
      </div>
    </div>
    <div class="flex items-center justify-between px-4 py-2.5 border-t border-border text-[0.8125rem]">
      <span class="text-text font-medium truncate">{{ video.creator_name || '未知' }}</span>
      <span
        v-if="video.category_name"
        class="bg-blue-light text-blue px-2 py-0.5 rounded text-xs"
      >
        {{ video.category_name }}
      </span>
    </div>
  </router-link>
</template>
