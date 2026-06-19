<script setup lang="ts">
import SectionHeader from '@/components/shared/SectionHeader.vue'
import StatCard from '@/components/shared/StatCard.vue'

defineProps<{ forecast: Record<string, any>[] }>()

function fmt(v: number): string {
  return v >= 10000 ? `${(v / 10000).toFixed(1)}万` : v.toFixed(0)
}
</script>

<template>
  <section class="py-8">
    <SectionHeader title="预测结果" description="未来3周播放量预测" />
    <div class="grid grid-cols-3 gap-6">
      <StatCard
        v-for="(f, i) in forecast.slice(0, 3)"
        :key="i"
        :label="`第${f.week_number}期预测`"
        :value="fmt(f.predicted)"
        :sub-label="i === 0 ? '下周' : i === 1 ? '两周后' : '三周后'"
      />
    </div>
  </section>
</template>
