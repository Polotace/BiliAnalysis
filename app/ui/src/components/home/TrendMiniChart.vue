<script setup lang="ts">
import { computed, ref, type Ref } from 'vue'
import { useChart } from '@/composables/useChart'
import type { WeeklyTrend } from '@/types/api'
import type { EChartsOption } from 'echarts'

const props = defineProps<{ weeks: WeeklyTrend[] }>()

const chartRef: Ref<HTMLElement | null> = ref(null)

const option = computed<EChartsOption>(() => ({
  animation: true,
  animationDuration: 300,
  tooltip: { trigger: 'axis' },
  grid: { left: 8, right: 8, top: 8, bottom: 8 },
  xAxis: { show: false, data: props.weeks.map(w => `第${w.week_number}期`) },
  yAxis: { show: false },
  series: [{
    type: 'line',
    data: props.weeks.map(w => w.avg_view),
    itemStyle: { color: '#00AEEC' },
    areaStyle: { color: 'rgba(0,174,236,0.08)' },
    symbol: 'none',
    smooth: false,
  }],
}))

useChart(chartRef, option)
</script>

<template>
  <div ref="chartRef" class="w-full h-[200px] bg-card rounded-[12px] p-4 shadow-[var(--shadow-default)]" />
</template>
