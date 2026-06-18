<script setup lang="ts">
import { computed, ref, type Ref } from 'vue'
import { useChart } from '@/composables/useChart'
import type { CategoryStats } from '@/types/api'
import type { EChartsOption } from 'echarts'

const props = defineProps<{ categories: CategoryStats[] }>()

const chartRef: Ref<HTMLElement | null> = ref(null)

const option = computed<EChartsOption>(() => {
  const sorted = [...props.categories].sort((a, b) => b.video_count - a.video_count)
  return {
    animation: true,
    animationDuration: 300,
    tooltip: { trigger: 'axis' },
    grid: { left: 80, right: 48, top: 8, bottom: 8 },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#6B7280', fontSize: 11 },
    },
    yAxis: {
      type: 'category',
      data: sorted.map(c => c.tname),
      axisLabel: { color: '#111827', fontSize: 12 },
    },
    series: [{
      type: 'bar',
      data: sorted.map(c => c.video_count),
      itemStyle: { color: '#00AEEC', borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'right', color: '#6B7280', fontSize: 11 },
    }],
  }
})

useChart(chartRef, option)
</script>

<template>
  <div ref="chartRef" class="w-full h-[320px]" />
</template>
