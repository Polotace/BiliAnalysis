<script setup lang="ts">
import { computed } from 'vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'
import CategoryBarChart from '@/components/charts/CategoryBarChart.vue'
import type { CategoryStats } from '@/types/api'

const props = defineProps<{ categories: CategoryStats[] }>()

const desc = computed(() => {
  if (props.categories.length <= 12) return `共 ${props.categories.length} 个分区`
  return `TOP 12（共 ${props.categories.length} 个分区）`
})
</script>

<template>
  <section class="py-8">
    <SectionHeader title="分区分布" :description="desc" />
    <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
      <CategoryBarChart :categories="categories" />
    </div>
  </section>
</template>
