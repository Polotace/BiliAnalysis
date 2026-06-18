<script setup lang="ts">
import SectionHeader from '@/components/shared/SectionHeader.vue'
import CategoryBarChart from '@/components/charts/CategoryBarChart.vue'
import type { CategoryStats } from '@/types/api'

defineProps<{ categories: CategoryStats[] }>()
</script>

<template>
  <section class="py-8">
    <SectionHeader title="分区分布" description="各分区视频数量对比" />
    <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
      <CategoryBarChart :categories="categories" />
    </div>
  </section>
</template>
