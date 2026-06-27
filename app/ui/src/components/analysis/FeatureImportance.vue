<script setup lang="ts">
import { computed } from 'vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'

const props = defineProps<{ features: Record<string, number> }>()

const ranked = computed(() => {
  const entries = Object.entries(props.features).sort(([, a], [, b]) => b - a)
  const total = entries.reduce((s, [, v]) => s + v, 0) || 1
  return entries.map(([k, v]) => [k, v / total] as const)
})
</script>

<template>
  <section class="py-8">
    <SectionHeader title="特征重要性" description="各维度对聚类结果的贡献度" />
    <div class="bg-card rounded-[12px] p-5 shadow-[var(--shadow-default)] space-y-2">
      <div v-for="[name, score] in ranked" :key="name" class="flex items-center gap-3">
        <span class="text-xs text-text-secondary w-12 shrink-0">{{ name }}</span>
        <div class="flex-1 h-5 bg-bg rounded-full overflow-hidden">
          <div class="h-full bg-blue rounded-full transition-all duration-500"
               :style="{ width: `${score * 100}%` }" />
        </div>
        <span class="text-xs tabular text-text w-10 text-right">{{ (score * 100).toFixed(0) }}%</span>
      </div>
    </div>
  </section>
</template>
