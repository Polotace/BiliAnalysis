<script setup lang="ts">
import SectionHeader from '@/components/shared/SectionHeader.vue'
import type { CreatorStats } from '@/types/api'

defineProps<{ creators: CreatorStats[] }>()
</script>

<template>
  <section class="py-8">
    <SectionHeader title="头部创作者" description="上榜次数 TOP10" />
    <div class="bg-card rounded-[12px] shadow-[var(--shadow-default)] overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-border text-text-secondary">
            <th class="text-left p-4 font-medium">创作者</th>
            <th class="text-right p-4 font-medium">上榜次数</th>
            <th class="text-right p-4 font-medium">总播放</th>
            <th class="text-right p-4 font-medium">总点赞</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(c, i) in creators.slice(0, 10)"
            :key="c.mid"
            class="border-b border-border last:border-0"
          >
            <td class="p-4">
              <span class="text-text-secondary mr-2">{{ i + 1 }}</span>
              <span class="font-medium text-text">{{ c.name }}</span>
            </td>
            <td class="text-right p-4 tabular">{{ c.appearance_count }}</td>
            <td class="text-right p-4 tabular">{{ (c.total_view / 10000).toFixed(0) }}万</td>
            <td class="text-right p-4 tabular">{{ (c.total_like / 10000).toFixed(0) }}万</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
