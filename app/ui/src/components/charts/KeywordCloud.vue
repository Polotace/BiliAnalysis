<script setup lang="ts">
import { computed, ref, type Ref } from 'vue'
import { useChart } from '@/composables/useChart'
import type { KeywordItem } from '@/types/api'
import type { EChartsOption } from 'echarts'
import 'echarts-wordcloud'

const props = defineProps<{ keywords: KeywordItem[] }>()

const chartRef: Ref<HTMLElement | null> = ref(null)

const option = computed<EChartsOption>(() => {
  const data = props.keywords.map(k => ({
    name: k.word,
    value: Math.round(k.weight * 10000),
  }))

  if (data.length === 0) {
    return {
      title: { text: '暂无数据', left: 'center', top: 'center',
               textStyle: { color: '#9CA3AF', fontSize: 14 } },
    }
  }

  return {
    tooltip: {
      show: true,
      formatter: (params: any) => `${params.name}: ${params.value}`,
    },
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      left: 'center',
      top: 'center',
      width: '90%',
      height: '90%',
      sizeRange: [14, 48],
      rotationRange: [-45, 45],
      rotationStep: 15,
      gridSize: 8,
      drawOutOfBound: false,
      layoutAnimation: true,
      textStyle: {
        fontFamily: 'Inter, "HarmonyOS Sans SC", "PingFang SC", sans-serif',
        fontWeight: 'normal',
        color: () => {
          const colors = ['#00AEEC', '#22C55E', '#F59E0B', '#8B5CF6',
                          '#EF4444', '#10B981', '#EC4899', '#6366F1']
          return colors[Math.floor(Math.random() * colors.length)]
        },
      },
      emphasisStyle: {
        fontWeight: 'bold',
        color: '#00AEEC',
      },
      data,
    } as any],
  }
})

useChart(chartRef, option)
</script>

<template>
  <div ref="chartRef" class="w-full h-[400px]" />
</template>
