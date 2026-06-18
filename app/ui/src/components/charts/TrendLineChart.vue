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
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'cross' },
  },
  legend: {
    bottom: 0,
    data: ['平均播放', '平均点赞', '互动率'],
  },
  grid: { left: 48, right: 16, top: 16, bottom: 40 },
  xAxis: {
    type: 'category',
    data: props.weeks.map(w => `第${w.week_number}期`),
    axisLabel: { color: '#6B7280', fontSize: 11 },
  },
  yAxis: [
    {
      type: 'value',
      name: '播放/点赞',
      axisLabel: { color: '#6B7280', fontSize: 11 },
    },
    {
      type: 'value',
      name: '互动率',
      axisLabel: {
        color: '#6B7280', fontSize: 11,
        formatter: (v: number) => `${(v * 100).toFixed(1)}%`,
      },
    },
  ],
  series: [
    {
      name: '平均播放', type: 'line', smooth: false,
      data: props.weeks.map(w => w.avg_view),
      itemStyle: { color: '#00AEEC' },
    },
    {
      name: '平均点赞', type: 'line', smooth: false,
      data: props.weeks.map(w => w.avg_like),
      itemStyle: { color: '#22C55E' },
    },
    {
      name: '互动率', type: 'line', smooth: false,
      yAxisIndex: 1,
      data: props.weeks.map(w => w.avg_interaction_rate),
      itemStyle: { color: '#F59E0B' },
    },
  ],
}))

useChart(chartRef, option)
</script>

<template>
  <div ref="chartRef" class="w-full h-[400px]" />
</template>
