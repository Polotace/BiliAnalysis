<script setup lang="ts">
import type { VideoSummary } from '@/types/api'
import { proxyImage } from '@/composables/useImageProxy'

const props = defineProps<{ video: VideoSummary }>()

function fmt(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(1)}万` : String(n)
}

function openBili() {
  if (props.video.bvid) {
    window.open(`https://www.bilibili.com/video/${props.video.bvid}`, '_blank')
  }
}
</script>

<template>
  <router-link
    :to="`/videos/${video.aid}`"
    class="group block bg-card rounded-[12px] shadow-[var(--shadow-default)] overflow-hidden
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
      <!-- B站跳转按钮 -->
      <span
        v-if="video.bvid"
        @click.stop="openBili"
        class="absolute top-2 right-2 bg-white/90 hover:bg-white text-blue text-xs
               w-6 h-6 rounded-full flex items-center justify-center cursor-pointer
               opacity-0 group-hover:opacity-100 transition-opacity duration-150
               shadow-sm"
        title="在B站观看"
      >
        <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
          <path d="M11.176 14.717a.527.527 0 0 1-.533.531h-2.128a.533.533 0 0 1-.533-.531V9.24c0-.295.24-.533.533-.533h2.128c.295 0 .533.24.533.533v5.477zm3.062-3.527-1.645 3.43a.535.535 0 0 1-.484.301.5.5 0 0 1-.195-.038.53.53 0 0 1-.297-.68l1.676-3.466-1.659-3.466a.533.533 0 0 1 .969-.428l1.635 3.435a.6.6 0 0 1 0 .48v.432zM2 5.006C2 3.346 3.346 2 5.006 2h13.988C20.654 2 22 3.346 22 5.006v13.988A3.006 3.006 0 0 1 18.994 22H5.006A3.006 3.006 0 0 1 2 18.994V5.006zM5.006 4h13.988C19.55 4 20 4.45 20 5.006v13.988c0 .557-.45 1.006-1.006 1.006H5.006C4.45 20 4 19.55 4 18.994V5.006C4 4.45 4.45 4 5.006 4z" fill-rule="evenodd"/>
        </svg>
      </span>
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
