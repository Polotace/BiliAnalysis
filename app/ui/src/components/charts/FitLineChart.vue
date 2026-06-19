<script setup lang="ts">
import { computed, ref, type Ref } from 'vue'
import { useChart } from '@/composables/useChart'
import type { PredictionResult } from '@/types/api'
import type { EChartsOption } from 'echarts'

const props = defineProps<{ result: PredictionResult }>()

const chartRef: Ref<HTMLElement | null> = ref(null)

const option = computed<EChartsOption>(() => {
  const fitted = props.result.fitted as { week_number: number; actual: number; predicted: number }[]
  const forecast = props.result.forecast as { week_number: number; predicted: number }[]
  const allWeeks = [...fitted.map(f => f.week_number), ...forecast.map(f => f.week_number)]
  const splitIdx = fitted.length

  return {
    animation: true,
    animationDuration: 300,
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, data: ['实际值', '拟合值', '预测值'] },
    grid: { left: 48, right: 16, top: 16, bottom: 40 },
    xAxis: {
      type: 'category',
      data: allWeeks.map(w => `第${w}期`),
      axisLabel: { color: '#6B7280', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: props.result.target === 'view' ? '播放量' : '点赞量',
      axisLabel: { color: '#6B7280', fontSize: 11 },
    },
    series: [
      {
        name: '实际值', type: 'line',
        data: fitted.map(f => f.actual),
        itemStyle: { color: '#00AEEC' },
        lineStyle: { type: 'solid' },
      },
      {
        name: '拟合值', type: 'line',
        data: fitted.map(f => f.predicted),
        itemStyle: { color: '#22C55E' },
        lineStyle: { type: 'dashed' },
      },
      {
        name: '预测值', type: 'line',
        data: [...new Array(splitIdx).fill(null), ...forecast.map(f => f.predicted)],
        itemStyle: { color: '#F59E0B' },
        lineStyle: { type: 'dashed' },
      },
    ],
  }
})

useChart(chartRef, option)
</script>

<template>
  <div ref="chartRef" class="w-full h-[400px]" />
</template>
