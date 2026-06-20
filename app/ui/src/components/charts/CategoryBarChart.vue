<script setup lang="ts">
import { computed, ref, type Ref } from 'vue'
import { useChart } from '@/composables/useChart'
import type { CategoryStats } from '@/types/api'
import type { EChartsOption } from 'echarts'

const props = defineProps<{ categories: CategoryStats[] }>()

const chartRef: Ref<HTMLElement | null> = ref(null)

const MAX_SHOW = 12
const BAR_HEIGHT = 28 // px per bar

const option = computed<EChartsOption>(() => {
  const sorted = [...props.categories].sort((a, b) => b.video_count - a.video_count)
  const top = sorted.slice(0, MAX_SHOW)
  const rest = sorted.slice(MAX_SHOW)
  const restCount = rest.reduce((s, c) => s + c.video_count, 0)

  const names = top.map(c => {
    const name = c.tname.length > 6 ? c.tname.slice(0, 5) + '…' : c.tname
    return name
  })
  const values = top.map(c => c.video_count)

  // Append "其他" if there are remaining categories
  if (rest.length > 0) {
    names.push(`其他 ${rest.length} 个分区`)
    values.push(restCount)
  }

  const chartHeight = names.length * BAR_HEIGHT + 40

  return {
    animation: true,
    animationDuration: 300,
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const d = Array.isArray(params) ? params[0] : params
        const idx = d.dataIndex
        const realName = idx < MAX_SHOW ? top[idx].tname : `其他 ${rest.length} 个分区`
        return `${realName}<br/>视频数: ${d.value}`
      },
    },
    grid: { left: 100, right: 48, top: 4, bottom: 4 },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#6B7280', fontSize: 11 },
      splitLine: { lineStyle: { color: '#E5E7EB', type: 'dashed' } },
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: { color: '#111827', fontSize: 12 },
      inverse: true,
    },
    series: [{
      type: 'bar',
      data: values,
      itemStyle: {
        color: (params: any) => {
          if (params.dataIndex >= MAX_SHOW) return '#9CA3AF'
          return '#00AEEC'
        },
        borderRadius: [0, 4, 4, 0],
      },
      label: {
        show: true,
        position: 'right',
        color: '#6B7280',
        fontSize: 11,
        formatter: (p: any) => p.value >= 1000 ? `${(p.value / 1000).toFixed(0)}k` : String(p.value),
      },
      barMaxWidth: 22,
    }],
  }
})

const chartHeight = computed(() => {
  const n = Math.min(props.categories.length, MAX_SHOW)
  const hasRest = props.categories.length > MAX_SHOW
  return (hasRest ? n + 1 : n) * BAR_HEIGHT + 40
})

useChart(chartRef, option)
</script>

<template>
  <div ref="chartRef" :style="{ width: '100%', height: `${chartHeight}px` }" />
</template>
