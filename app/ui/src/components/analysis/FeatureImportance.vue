<script setup lang="ts">
import { computed } from 'vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'

const props = defineProps<{ features: Record<string, number> }>()

const ranked = computed(() =>
  Object.entries(props.features)
    .sort(([, a], [, b]) => b - a)
)
</script>

<template>
  <section class="py-8">
    <SectionHeader title="特征重要性" description="各维度对聚类结果的贡献度" />
    <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)] space-y-3">
      <div v-for="[name, score] in ranked" :key="name" class="flex items-center gap-4">
        <span class="text-sm text-text-secondary w-24 shrink-0">{{ name }}</span>
        <div class="flex-1">
          <el-progress
            :percentage="Number((score * 100).toFixed(1))"
            :stroke-width="8"
            :show-text="false"
            color="var(--color-blue)"
          />
        </div>
        <span class="text-sm tabular font-medium text-text w-12 text-right">
          {{ (score * 100).toFixed(1) }}%
        </span>
      </div>
    </div>
  </section>
</template>
