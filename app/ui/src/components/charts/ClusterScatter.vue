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

  // Convert parallel arrays to points grouped by cluster
  const pointsByCluster: [number, number][][] = [[], [], []]
  for (let i = 0; i < Math.min(labels.length, xs.length, ys.length); i++) {
    const c = labels[i]
    if (c >= 0 && c < 3) {
      pointsByCluster[c].push([xs[i], ys[i]])
    }
  }

  const series = CLUSTER_COLORS.map((color, i) => ({
    name: props.clusters[i]?.tag ?? `Cluster ${i}`,
    type: 'scatter' as const,
    data: pointsByCluster[i],
    itemStyle: { color },
    symbolSize: 6,
  }))

  series.push({
    name: '簇中心',
    type: 'scatter' as const,
    data: props.clusters.map(c => [c.centroid.view ?? c.centroid.x, c.centroid.like ?? c.centroid.y]),
    itemStyle: { color: '#EF4444' },
    symbol: 'diamond',
    symbolSize: 14,
  } as any)

  return {
    animation: true,
    animationDuration: 300,
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const ci = params.seriesIndex
        const tag = props.clusters[ci]?.tag ?? `Cluster ${ci}`
        return `${tag}<br/>x: ${params.value[0]?.toFixed(2)}<br/>y: ${params.value[1]?.toFixed(2)}`
      },
    },
    legend: { bottom: 0 },
    grid: { left: 48, right: 16, top: 16, bottom: 40 },
    xAxis: { type: 'value', name: 'PCA 维度1', axisLabel: { color: '#6B7280', fontSize: 11 } },
    yAxis: { type: 'value', name: 'PCA 维度2', axisLabel: { color: '#6B7280', fontSize: 11 } },
    series,
  }
})

useChart(chartRef, option)
</script>

<template>
  <div ref="chartRef" class="w-full h-[480px]" />
</template>
