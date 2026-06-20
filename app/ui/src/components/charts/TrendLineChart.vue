<script setup lang="ts">
import { computed, ref, type Ref } from 'vue'
import { useChart } from '@/composables/useChart'
import type { WeeklyTrend } from '@/types/api'
import type { EChartsOption } from 'echarts'

const props = defineProps<{ weeks: WeeklyTrend[] }>()

const chartRef: Ref<HTMLElement | null> = ref(null)

const X_LABEL_INTERVAL = computed(() => {
  const n = props.weeks.length
  if (n <= 20) return 0  // show all
  if (n <= 50) return Math.floor(n / 10)
  return Math.floor(n / 15)  // ~15 labels max
})

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
  grid: { left: 60, right: 80, top: 16, bottom: 48 },
  dataZoom: [
    {
      type: 'slider',
      bottom: 8,
      height: 20,
      borderColor: '#E5E7EB',
      fillerColor: 'rgba(0,174,236,0.1)',
      handleStyle: { color: '#00AEEC' },
      textStyle: { color: '#6B7280', fontSize: 10 },
    },
  ],
  xAxis: {
    type: 'category',
    data: props.weeks.map(w => `第${w.week_number}期`),
    axisLabel: {
      color: '#6B7280', fontSize: 11,
      interval: X_LABEL_INTERVAL.value,
    },
  },
  yAxis: [
    {
      type: 'value',
      name: '播放量',
      axisLabel: {
        color: '#00AEEC', fontSize: 11,
        formatter: (v: number) => v >= 10000 ? `${(v / 10000).toFixed(0)}万` : String(v),
      },
    },
    {
      type: 'value',
      name: '互动率',
      axisLabel: {
        color: '#F59E0B', fontSize: 11,
        formatter: (v: number) => `${(v * 100).toFixed(1)}%`,
      },
    },
  ],
  series: [
    {
      name: '平均播放', type: 'line', smooth: false,
      yAxisIndex: 0,
      data: props.weeks.map(w => w.avg_view),
      itemStyle: { color: '#00AEEC' },
      symbol: 'none',
    },
    {
      name: '平均点赞', type: 'line', smooth: false,
      yAxisIndex: 0,
      data: props.weeks.map(w => w.avg_like),
      itemStyle: { color: '#22C55E' },
      symbol: 'none',
    },
    {
      name: '互动率', type: 'line', smooth: false,
      yAxisIndex: 1,
      data: props.weeks.map(w => w.avg_interaction_rate),
      itemStyle: { color: '#F59E0B' },
      symbol: 'none',
    },
  ],
}))

useChart(chartRef, option)
</script>

<template>
  <div ref="chartRef" class="w-full h-[400px]" />
</template>
