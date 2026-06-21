<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, ScatterChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent,
  GridComponent, MarkLineComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useModelComparison } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import SubNavTabs from '@/components/analysis/SubNavTabs.vue'
import StatCard from '@/components/shared/StatCard.vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'
import AnalysisLoading from '@/components/shared/AnalysisLoading.vue'
import type { EChartsOption } from 'echarts'
import type { ModelComparisonReport } from '@/types/api'

echarts.use([
  BarChart, ScatterChart,
  TitleComponent, TooltipComponent, LegendComponent,
  GridComponent, MarkLineComponent, CanvasRenderer,
])

const { data, loading, error, send } = useModelComparison()

onMounted(() => send())

// ── Brand-derived 5-model palette (from #00AEEC) ──
const MODEL_COLORS: Record<string, string> = {
  'XGBoost':           '#00AEEC', // brand blue — winner
  'Random Forest':     '#0EA5E9', // sky — strong runner-up
  'Decision Tree':     '#06B6D4', // cyan — mid-pack
  'AdaBoost':          '#8B5CF6', // violet — lower performer
  'Linear Regression': '#94A3B8', // slate — baseline
}

function modelColor(name: string): string {
  return MODEL_COLORS[name] ?? '#94A3B8'
}

// ── R² Bar Chart (brand palette, tooltip carries full model detail) ──
const r2ChartRef = ref<HTMLElement | null>(null)
let r2Instance: echarts.ECharts | null = null

function renderR2Chart(report: ModelComparisonReport) {
  if (!r2ChartRef.value) return
  if (!r2Instance) r2Instance = echarts.init(r2ChartRef.value)

  const sorted = [...report.models].sort((a, b) => b.r2_mean - a.r2_mean)
  const names = sorted.map(m => m.model_name)
  const r2Vals = sorted.map(m => m.r2_mean)
  const r2Stds = sorted.map(m => m.r2_std)
  const maxR2 = Math.max(...r2Vals)

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#fff',
      borderColor: '#E5E7EB',
      textStyle: { color: '#111827', fontSize: 13 },
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params
        const i = p.dataIndex
        const m = sorted[i]
        return `<div style="font-weight:600;margin-bottom:4px">${m.model_name}</div>
          <div style="display:flex;gap:16px;margin-bottom:2px">
            <span>R²</span><b>${m.r2_mean.toFixed(4)} ± ${m.r2_std.toFixed(4)}</b>
          </div>
          <div style="display:flex;gap:16px;margin-bottom:2px">
            <span>MAE</span><span>${m.mae_mean.toFixed(4)} ± ${m.mae_std.toFixed(4)}</span>
          </div>
          <div style="display:flex;gap:16px;margin-bottom:2px">
            <span>RMSE</span><span>${m.rmse_mean.toFixed(4)} ± ${m.rmse_std.toFixed(4)}</span>
          </div>
          <div style="display:flex;gap:16px">
            <span>训练时间</span><span>${m.train_time_seconds.toFixed(1)}s</span>
          </div>`
      },
    },
    grid: { top: 32, right: 32, bottom: 72, left: 56 },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { rotate: 12, fontSize: 11, color: '#6B7280' },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      name: 'R²',
      nameTextStyle: { color: '#6B7280', fontSize: 12 },
      min: 0,
      max: Math.ceil(maxR2 * 1.3 * 100) / 100,
      axisLabel: { formatter: (v: number) => v.toFixed(3), color: '#6B7280' },
      splitLine: { lineStyle: { type: 'dashed', color: '#E5E7EB' } },
    },
    series: [
      {
        type: 'bar',
        data: r2Vals.map((v, i) => ({
          value: v,
          itemStyle: {
            color: modelColor(names[i]),
            borderRadius: [5, 5, 0, 0],
          },
        })),
        label: {
          show: true,
          position: 'top',
          color: '#374151',
          formatter: (p: any) =>
            `${p.value.toFixed(3)} ± ${r2Stds[p.dataIndex].toFixed(3)}`,
          fontSize: 11,
          fontWeight: 600,
        },
        barMaxWidth: 64,
        emphasis: {
          itemStyle: { opacity: 0.85 },
        },
      },
    ],
  }

  r2Instance.setOption(option, true)
}

// ── Scatter: Predicted vs Actual (no large mode, precise hover) ──
const scatterRef = ref<HTMLElement | null>(null)
let scatterInstance: echarts.ECharts | null = null

function renderScatter(report: ModelComparisonReport) {
  if (!scatterRef.value) return
  if (!scatterInstance) scatterInstance = echarts.init(scatterRef.value)

  const pts: [number, number][] = report.predicted_vs_actual.map(
    p => [p.actual, p.predicted],
  )
  const allVals = pts.flat()
  const rangeMin = Math.floor(Math.min(...allVals) * 10) / 10
  const rangeMax = Math.ceil(Math.max(...allVals) * 10) / 10

  const option: EChartsOption = {
    tooltip: {
      trigger: 'item',
      backgroundColor: '#fff',
      borderColor: '#E5E7EB',
      textStyle: { color: '#111827', fontSize: 13 },
      formatter: (p: any) => {
        const d = p.data as [number, number]
        const residual = d[0] - d[1]
        return `<div style="font-weight:600;margin-bottom:2px">数据点</div>
          实际 <b>${d[0].toFixed(4)}</b><br/>
          预测 <b>${d[1].toFixed(4)}</b><br/>
          残差 <span style="color:${residual > 0 ? '#22C55E' : '#EF4444'}">${residual > 0 ? '+' : ''}${residual.toFixed(4)}</span>`
      },
    },
    grid: { top: 16, right: 32, bottom: 56, left: 56 },
    xAxis: {
      type: 'value',
      name: '实际 log(1+view)',
      nameTextStyle: { color: '#6B7280', fontSize: 12 },
      min: rangeMin,
      max: rangeMax,
      splitLine: { lineStyle: { type: 'dashed', color: '#E5E7EB' } },
      axisLabel: { color: '#6B7280' },
    },
    yAxis: {
      type: 'value',
      name: '预测 log(1+view)',
      nameTextStyle: { color: '#6B7280', fontSize: 12 },
      min: rangeMin,
      max: rangeMax,
      splitLine: { lineStyle: { type: 'dashed', color: '#E5E7EB' } },
      axisLabel: { color: '#6B7280' },
    },
    series: [
      {
        type: 'scatter',
        data: pts,
        symbolSize: 4,
        itemStyle: { color: '#00AEEC', opacity: 0.18 },
      },
      {
        type: 'line',
        data: [
          [rangeMin, rangeMin],
          [rangeMax, rangeMax],
        ],
        lineStyle: { color: '#EF4444', type: 'dashed', width: 2 },
        symbol: 'none',
        z: 10,
        silent: true,
      },
    ],
  }

  scatterInstance.setOption(option, true)
}

// ── Residual Histogram ──
const residualRef = ref<HTMLElement | null>(null)
let residualInstance: echarts.ECharts | null = null

function renderResiduals(report: ModelComparisonReport) {
  if (!residualRef.value) return
  if (!residualInstance) residualInstance = echarts.init(residualRef.value)

  const residuals = report.predicted_vs_actual.map(p => p.residual)
  const rMin = Math.min(...residuals)
  const rMax = Math.max(...residuals)
  const binCount = 50
  const binWidth = (rMax - rMin) / binCount || 0.01
  const bins: number[] = new Array(binCount).fill(0)
  const labels: string[] = []
  for (let i = 0; i < binCount; i++) {
    labels.push((rMin + i * binWidth).toFixed(2))
  }
  for (const r of residuals) {
    const idx = Math.min(Math.floor((r - rMin) / binWidth), binCount - 1)
    bins[idx]++
  }

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#fff',
      borderColor: '#E5E7EB',
      textStyle: { color: '#111827', fontSize: 13 },
      formatter: (p: any) => {
        const d = Array.isArray(p) ? p[0] : p
        return `残差 ≈ ${labels[d.dataIndex]}<br/>频数 <b>${d.value}</b>`
      },
    },
    grid: { top: 16, right: 32, bottom: 56, left: 56 },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: { interval: 9, rotate: 30, fontSize: 10, color: '#6B7280' },
      axisTick: { show: false },
      name: '残差 (实际 − 预测)',
      nameTextStyle: { color: '#6B7280', fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      name: '频数',
      nameTextStyle: { color: '#6B7280', fontSize: 12 },
      splitLine: { lineStyle: { type: 'dashed', color: '#E5E7EB' } },
      axisLabel: { color: '#6B7280' },
    },
    series: [
      {
        type: 'bar',
        data: bins,
        itemStyle: {
          color: '#00AEEC',
          opacity: 0.7,
          borderRadius: [2, 2, 0, 0],
        },
        barMaxWidth: '100%',
        barGap: 0,
        barCategoryGap: 0,
      },
      {
        type: 'line',
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: '#EF4444', type: 'dashed', width: 2 },
          label: { color: '#EF4444', fontSize: 11, fontWeight: 600 },
          data: [
            { xAxis: labels[Math.floor(binCount / 2)], label: { formatter: '零线' } },
          ],
        },
      },
    ],
  }

  residualInstance.setOption(option, true)
}

// ── Feature Importance (ECharts horizontal bar, not FeatureImportance.vue) ──
const fiChartRef = ref<HTMLElement | null>(null)
let fiInstance: echarts.ECharts | null = null

function renderFeatureImportance(report: ModelComparisonReport) {
  if (!fiChartRef.value) return
  if (!fiInstance) fiInstance = echarts.init(fiChartRef.value)

  const items = [...report.feature_importance].reverse() // bottom→top

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#fff',
      borderColor: '#E5E7EB',
      textStyle: { color: '#111827', fontSize: 13 },
      formatter: (p: any) => {
        const d = Array.isArray(p) ? p[0] : p
        return `<b>${d.name}</b><br/>重要性 ${(d.value * 100).toFixed(2)}%`
      },
    },
    grid: { top: 8, right: 48, bottom: 24, left: 160 },
    xAxis: {
      type: 'value',
      name: '重要性',
      nameTextStyle: { color: '#6B7280', fontSize: 12 },
      axisLabel: {
        formatter: (v: number) => `${(v * 100).toFixed(0)}%`,
        color: '#6B7280',
      },
      splitLine: { lineStyle: { type: 'dashed', color: '#E5E7EB' } },
    },
    yAxis: {
      type: 'category',
      data: items.map(fi => fi.feature),
      axisLabel: { fontSize: 12, color: '#374151' },
      axisTick: { show: false },
      inverse: true,
    },
    series: [
      {
        type: 'bar',
        data: items.map(fi => ({
          value: fi.importance,
          itemStyle: {
            color: '#00AEEC',
            borderRadius: [0, 4, 4, 0],
          },
        })),
        barMaxWidth: 20,
        label: {
          show: true,
          position: 'right',
          color: '#6B7280',
          formatter: (p: any) => `${(p.value * 100).toFixed(2)}%`,
          fontSize: 11,
        },
      },
    ],
  }

  fiInstance.setOption(option, true)
}

// ── Resize ──
function handleResize() {
  r2Instance?.resize()
  scatterInstance?.resize()
  residualInstance?.resize()
  fiInstance?.resize()
}

watch(data, (report) => {
  if (!report) return
  nextTick(() => {
    renderR2Chart(report)
    renderScatter(report)
    renderResiduals(report)
    renderFeatureImportance(report)
    window.addEventListener('resize', handleResize)
  })
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  r2Instance?.dispose()
  scatterInstance?.dispose()
  residualInstance?.dispose()
  fiInstance?.dispose()
})
</script>

<template>
  <Sidebar />
  <PageShell sidebar class="flex-1 min-w-0">
    <SubNavTabs class="lg:hidden" />

    <!-- Loading -->
    <template v-if="loading">
      <AnalysisLoading label="正在训练并对比 5 个模型…" />
    </template>

    <!-- Error -->
    <div v-else-if="error" class="py-12 text-center">
      <div class="bg-card rounded-[16px] p-12 shadow-[var(--shadow-default)] max-w-md mx-auto">
        <p class="text-lg font-semibold text-text mb-2">加载失败，请重试</p>
        <p class="text-sm text-text-secondary mb-6">{{ (error as Error).message }}</p>
        <button
          @click="send()"
          class="px-6 py-2 bg-blue text-white rounded-[12px] font-medium
                 border-none cursor-pointer hover:brightness-90 transition-all"
        >
          重试
        </button>
      </div>
    </div>

    <!-- Data -->
    <template v-else-if="data">
      <!-- Stat cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
        <StatCard
          label="最优模型"
          :value="data.best_model"
          sub-label="5-Fold CV 综合最优"
        />
        <StatCard
          label="最优 R²"
          :value="(data.models.find(m => m.model_name === data.best_model)?.r2_mean ?? 0).toFixed(4)"
          sub-label="越接近 1 拟合越好"
        />
        <StatCard
          label="样本数"
          :value="String(data.n_samples)"
          sub-label="清洗后有效视频"
        />
        <StatCard
          label="特征数"
          :value="String(data.n_features)"
          sub-label="含 One-Hot 编码分区"
        />
      </div>

      <!-- R² Comparison -->
      <section class="py-8">
        <SectionHeader
          title="模型对比 · 交叉验证 R²"
          description="5 个回归模型按 R² 降序排列，hover 查看 MAE / RMSE / 训练时间明细"
        />
        <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
          <div ref="r2ChartRef" class="w-full h-[420px]" />
        </div>
      </section>

      <!-- Predicted vs Actual Scatter -->
      <section class="py-8">
        <SectionHeader
          title="预测 vs 实际"
          description="最优模型全量样本散点图，红色虚线为理想 y=x 参考线"
        />
        <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
          <div ref="scatterRef" class="w-full h-[480px]" />
        </div>
      </section>

      <!-- Residual Histogram -->
      <section class="py-8">
        <SectionHeader
          title="残差分布"
          description="预测残差直方图，红色虚线标注零点"
        />
        <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
          <div ref="residualRef" class="w-full h-80" />
        </div>
      </section>

      <!-- Feature Importance -->
      <section class="py-8">
        <SectionHeader
          title="特征重要性 Top 15"
          description="最优模型 ({{ data.best_model }}) 的 feature importance"
        />
        <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
          <div ref="fiChartRef" class="w-full h-[420px]" />
        </div>
      </section>
    </template>

    <!-- Empty -->
    <div v-else class="py-12 text-center">
      <p class="text-text-secondary">
        暂无模型对比数据，请在管理页面触发分析流水线（包含 model_comparison 步骤）
      </p>
    </div>
  </PageShell>
</template>
