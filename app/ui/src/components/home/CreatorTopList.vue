<script setup lang="ts">
import SectionHeader from '@/components/shared/SectionHeader.vue'
import type { CreatorStats } from '@/types/api'

defineProps<{ creators: CreatorStats[] }>()
</script>

<template>
  <section class="py-12">
    <SectionHeader title="上榜创作者" description="出现次数 TOP5" />
    <div class="space-y-3">
      <div
        v-for="(c, i) in creators.slice(0, 5)"
        :key="c.mid"
        class="flex items-center gap-4 bg-card rounded-[12px] p-4 shadow-[var(--shadow-default)]"
      >
        <span class="text-sm font-bold text-text-secondary w-6">{{ i + 1 }}</span>
        <div class="flex-1 min-w-0">
          <p class="font-semibold text-text truncate">{{ c.name }}</p>
          <p class="text-xs text-text-secondary">
            上榜 {{ c.appearance_count }} 次
          </p>
        </div>
        <div class="text-right tabular">
          <p class="text-sm font-semibold text-text">{{ (c.total_view / 10000).toFixed(0) }}万</p>
          <p class="text-xs text-text-secondary">总播放</p>
        </div>
      </div>
    </div>
  </section>
</template>
