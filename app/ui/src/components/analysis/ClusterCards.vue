<script setup lang="ts">
import SectionHeader from '@/components/shared/SectionHeader.vue'
import type { ClusterGroup } from '@/types/api'

defineProps<{ clusters: ClusterGroup[] }>()

const CLUSTER_COLORS: Record<number, string> = {
  0: '#00AEEC', 1: '#22C55E', 2: '#F59E0B',
}
</script>

<template>
  <section class="py-8">
    <SectionHeader title="内容聚类" description="基于播放、点赞、投币等特征的 3 类内容群体" />
    <div class="grid grid-cols-3 gap-6">
      <div
        v-for="c in clusters"
        :key="c.label"
        class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]
               border-t-[4px]"
        :style="{ borderTopColor: CLUSTER_COLORS[c.label] ?? '#6B7280' }"
      >
        <p class="text-lg font-bold text-text mb-1">{{ c.tag }}</p>
        <p class="text-sm text-text-secondary mb-4">{{ c.count }} 个视频</p>
        <div class="space-y-2 text-sm tabular">
          <div class="flex justify-between">
            <span class="text-text-secondary">平均播放</span>
            <span class="font-medium text-text">{{ (c.avg_view / 10000).toFixed(1) }}万</span>
          </div>
          <div class="flex justify-between">
            <span class="text-text-secondary">平均点赞</span>
            <span class="font-medium text-text">{{ (c.avg_like / 10000).toFixed(1) }}万</span>
          </div>
          <div class="flex justify-between">
            <span class="text-text-secondary">平均投币</span>
            <span class="font-medium text-text">{{ (c.avg_coin / 10000).toFixed(1) }}万</span>
          </div>
          <div class="flex justify-between">
            <span class="text-text-secondary">平均收藏</span>
            <span class="font-medium text-text">{{ (c.avg_favorite / 10000).toFixed(1) }}万</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
