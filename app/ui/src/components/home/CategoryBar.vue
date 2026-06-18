<script setup lang="ts">
import SectionHeader from '@/components/shared/SectionHeader.vue'
import type { CategoryStats } from '@/types/api'

defineProps<{ categories: CategoryStats[] }>()

const COLORS = ['#00AEEC', '#22C55E', '#F59E0B', '#EF4444', '#8B5CF6']
</script>

<template>
  <section class="py-12">
    <SectionHeader title="热门分区" description="视频数量 TOP5" />
    <div class="grid grid-cols-5 gap-4">
      <div
        v-for="(c, i) in categories.slice(0, 5)"
        :key="c.tname"
        class="bg-card rounded-[12px] p-5 shadow-[var(--shadow-default)]
               border-t-[3px]"
        :style="{ borderTopColor: COLORS[i] }"
      >
        <p class="text-sm font-medium text-text-secondary mb-1">{{ c.tname }}</p>
        <p class="text-2xl font-bold tabular text-text">{{ c.video_count }}</p>
        <p class="text-xs text-text-secondary mt-2">
          均播 {{ (c.avg_view / 10000).toFixed(1) }}万 · 赞 {{ (c.avg_like / 10000).toFixed(1) }}万
        </p>
      </div>
    </div>
  </section>
</template>
