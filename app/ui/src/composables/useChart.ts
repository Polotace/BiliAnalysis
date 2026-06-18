import { ref, onMounted, onUnmounted, watch, type Ref } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart, BarChart, ScatterChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent,
  GridComponent, MarkLineComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'

echarts.use([
  LineChart, BarChart, ScatterChart,
  TitleComponent, TooltipComponent, LegendComponent,
  GridComponent, MarkLineComponent,
  CanvasRenderer,
])

export function useChart(
  elRef: Ref<HTMLElement | null>,
  option: Ref<EChartsOption>,
): { chartInstance: Ref<any> } {
  const chartInstance = ref<echarts.ECharts | null>(null)

  onMounted(() => {
    if (!elRef.value) return
    chartInstance.value = echarts.init(elRef.value)
    chartInstance.value.setOption(option.value, true)
  })

  watch(option, (newOpt) => {
    if (chartInstance.value) {
      chartInstance.value.setOption(newOpt, true)
    }
  })

  const handleResize = () => {
    chartInstance.value?.resize()
  }
  window.addEventListener('resize', handleResize)

  onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    chartInstance.value?.dispose()
    chartInstance.value = null
  })

  return { chartInstance }
}
