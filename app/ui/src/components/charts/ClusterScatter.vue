<script setup lang="ts">
import { computed, ref, type Ref } from 'vue'
import { useChart } from '@/composables/useChart'
import type { ClusterGroup } from '@/types/api'
import type { EChartsOption } from 'echarts'

const props = defineProps<{
  scatterData: Record<string, any>
  clusters: ClusterGroup[]
}>()

const chartRef: Ref<HTMLElement | null> = ref(null)

const CLUSTER_COLORS = ['#00AEEC', '#22C55E', '#F59E0B']

const option = computed<EChartsOption>(() => {
  const raw = props.scatterData as { labels?: number[]; x?: number[]; y?: number[] }
  const labels = raw.labels ?? []
  const xs = raw.x ?? []
  const ys = raw.y ?? []
  const total = Math.min(labels.length, xs.length, ys.length)

  if (total === 0) {
    return {
      title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#9CA3AF', fontSize: 14 } },
    }
  }

  // Downsample if too many points (max ~5000 for rendering performance)
  const MAX_POINTS = 5000
  const step = total <= MAX_POINTS ? 1 : Math.ceil(total / MAX_POINTS)
  const pointsByCluster: [number, number][][] = [[], [], []]
  for (let i = 0; i < total; i += step) {
    const c = labels[i]
    if (c >= 0 && c < 3) {
      pointsByCluster[c].push([xs[i], ys[i]])
    }
  }

  const series = CLUSTER_COLORS.map((color, i) => {
    const cluster = props.clusters[i]
    const name = cluster
      ? `${cluster.tag} (${cluster.count})`
      : `Cluster ${i}`
    return {
      name,
      type: 'scatter' as const,
      data: pointsByCluster[i],
      itemStyle: { color, opacity: 0.5 },
      symbolSize: 3,
    }
  })

  return {
    animation: false,
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const tag = props.clusters[params.seriesIndex]?.tag ?? `Cluster ${params.seriesIndex}`
        return `${tag}<br/>PC1: ${params.value[0]?.toFixed(2)}<br/>PC2: ${params.value[1]?.toFixed(2)}`
      },
    },
    legend: { bottom: 0 },
    grid: { left: 48, right: 16, top: 16, bottom: 40 },
    xAxis: {
      type: 'value', name: 'PC1',
      axisLabel: { color: '#6B7280', fontSize: 11 },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value', name: 'PC2',
      axisLabel: { color: '#6B7280', fontSize: 11 },
      splitLine: { show: false },
    },
    series,
  }
})

useChart(chartRef, option)
</script>

<template>
  <div ref="chartRef" class="w-full h-[480px]" />
</template>
