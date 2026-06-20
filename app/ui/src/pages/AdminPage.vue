<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRequest } from 'alova/client'
import PageShell from '@/components/layout/PageShell.vue'
import StatCard from '@/components/shared/StatCard.vue'
import {
  fetchCrawlerStatus, fetchAnalysisOverview, fetchPipelineList,
  fetchPipelineHistory, triggerPipeline,
} from '@/composables/useApi'
import type {
  CrawlerStatus, AnalysisOverview, RunHistoryItem, PipelineInfo,
} from '@/types/api'

// ── Status data ──
const { data: crawlerStatus, loading: csLoading, error: csError, send: csSend } =
  useRequest(fetchCrawlerStatus, { immediate: false })
const { data: analysisOverview, send: aoSend } =
  useRequest(fetchAnalysisOverview, { immediate: false })
const { data: pipelineList, send: plSend } =
  useRequest(fetchPipelineList, { immediate: false })

// ── Action state ──
const actionLoading = ref('')
const actionResult = ref('')
const actionError = ref('')

// ── History ──
const history = ref<RunHistoryItem[]>([])
const historyLoading = ref(false)
const historyPipeline = ref('crawl')

// ── Pipeline colors ──
const PIPELINE_COLORS: Record<string, string> = {
  crawl: 'bg-blue',
  analysis: 'bg-success',
  warehouse: 'bg-[#F59E0B]',
  db_load: 'bg-[#8B5CF6]',
}
const PIPELINE_ICONS: Record<string, string> = {
  crawl: '☁',
  analysis: '📊',
  warehouse: '🏗',
  db_load: '🗄',
}

// ── Load on mount ──
onMounted(async () => {
  await Promise.all([csSend(), aoSend(), plSend()])
  await loadHistory()
})

async function doAction(pl: PipelineInfo) {
  actionLoading.value = pl.name
  actionResult.value = ''
  actionError.value = ''
  try {
    const r = await triggerPipeline(pl.name)
    actionResult.value = `✓ 流水线 ${pl.name} 已触发 (run_id=${(r as any).run_id ?? 'OK'})`
    setTimeout(async () => { await Promise.all([csSend(), aoSend()]) }, 1500)
  } catch (e: any) {
    actionError.value = `流水线 ${pl.name} 失败: ${e.message || e}`
  } finally {
    actionLoading.value = ''
  }
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const r = await fetchPipelineHistory(historyPipeline.value, 30)
    history.value = r ?? []
  } catch { history.value = [] }
  finally { historyLoading.value = false }
}

function switchHistory(name: string) {
  historyPipeline.value = name
  loadHistory()
}

function fmtTime(ts: string | null): string {
  if (!ts) return '—'
  return new Date(ts).toLocaleString('zh-CN')
}
function statusClass(s: string): string {
  return s === 'success' ? 'text-success' : s === 'running' ? 'text-warning' : 'text-danger'
}
function pipelineColor(name: string): string {
  return PIPELINE_COLORS[name] ?? 'bg-text-secondary'
}
</script>

<template>
  <PageShell>
    <div class="py-10">
      <h1 class="text-[1.75rem] font-bold tracking-[-0.02em] text-text mb-1">管理后台</h1>
      <p class="text-[0.9375rem] text-text-secondary">数据采集、分析与入库管理</p>
    </div>

    <!-- ── 系统状态 ── -->
    <h2 class="text-[1.0625rem] font-semibold text-text mb-4">系统状态</h2>

    <div v-if="csLoading" class="grid grid-cols-4 gap-4 mb-4">
      <div v-for="i in 4" :key="i" class="h-24 bg-card rounded-[12px] animate-pulse" />
    </div>
    <div v-else-if="csError" class="text-text-secondary mb-4">状态加载失败: {{ (csError as Error).message }}</div>
    <div v-else-if="crawlerStatus" class="grid grid-cols-4 gap-4 mb-4">
      <StatCard label="数据周次" :value="crawlerStatus.total_weeks" />
      <StatCard label="已爬取" :value="crawlerStatus.crawled" sub-label="成功" />
      <StatCard label="失败" :value="Object.keys(crawlerStatus.failed).length" sub-label="待重试" />
      <StatCard
        label="状态"
        :value="crawlerStatus.is_running ? '运行中' : '空闲'"
        :sub-label="crawlerStatus.last_run ? `上次: ${fmtTime(crawlerStatus.last_run)}` : '从未运行'"
      />
    </div>

    <div v-if="analysisOverview" class="flex gap-2 flex-wrap mb-6">
      <span
        v-for="item in [
          {ready:!!analysisOverview.last_clean,label:'清洗报告',sub:analysisOverview.last_clean?.total_videos+' 视频'},
          {ready:!!analysisOverview.last_stats,label:'统计报告',sub:analysisOverview.last_stats?.overall.total_videos+' 视频'},
          {ready:!!analysisOverview.last_cluster,label:'聚类报告',sub:'silhouette='+analysisOverview.last_cluster?.clusters.silhouette_score},
          {ready:!!analysisOverview.last_prediction,label:'预测报告',sub:'view R²='+analysisOverview.last_prediction?.view_predict.r2_score},
        ]"
        :key="item.label"
        class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium"
        :class="item.ready ? 'bg-[#ECFDF5] text-[#166534]' : 'bg-[#F3F4F6] text-text-secondary'"
      >
        {{ item.ready ? '✓' : '—' }} {{ item.label }}
        <span class="opacity-60 font-normal">· {{ item.sub }}</span>
      </span>
    </div>

    <!-- ── 操作面板 ── -->
    <h2 class="text-[1.0625rem] font-semibold text-text mb-4">操作面板</h2>
    <div class="flex flex-wrap gap-3 mb-3">
      <template v-if="pipelineList">
        <button
          v-for="pl in pipelineList.pipelines"
          :key="pl.name"
          @click="doAction(pl)"
          :disabled="actionLoading !== ''"
          class="px-5 py-3 rounded-[12px] text-white font-semibold text-sm border-none cursor-pointer
                 transition-opacity duration-200 hover:opacity-85 disabled:opacity-50 text-left"
          :class="pipelineColor(pl.name)"
        >
          <span v-if="actionLoading === pl.name" class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2 align-middle" />
          {{ PIPELINE_ICONS[pl.name] ?? '▶' }} 流水线: {{ pl.name }}
          <span class="block text-[0.6875rem] font-normal opacity-70 mt-0.5">{{ pl.steps.join(' → ') || '手动触发' }}</span>
        </button>
      </template>
      <p v-else class="text-text-secondary text-sm">加载流水线列表…</p>
    </div>

    <div v-if="actionResult" class="mb-3 p-3 rounded-lg bg-[#ECFDF5] text-[#166534] text-sm border border-[#A7F3D0] font-medium">
      {{ actionResult }}
    </div>
    <div v-if="actionError" class="mb-3 p-3 rounded-lg bg-[#FEF2F2] text-[#991B1B] text-sm border border-[#FECACA] font-medium">
      {{ actionError }}
    </div>

    <!-- ── 执行历史 ── -->
    <h2 class="text-[1.0625rem] font-semibold text-text mb-4">执行历史</h2>
    <div class="flex gap-2 mb-4 flex-wrap">
      <template v-if="pipelineList">
        <button
          v-for="pl in pipelineList.pipelines"
          :key="pl.name"
          @click="switchHistory(pl.name)"
          class="px-4 py-1.5 border rounded-[20px] text-sm font-medium transition-colors cursor-pointer"
          :class="historyPipeline === pl.name
            ? 'bg-blue text-white border-blue'
            : 'bg-card text-text-secondary border-border hover:border-blue hover:text-blue'"
        >
          {{ pl.name }}
        </button>
      </template>
    </div>

    <div v-if="historyLoading" class="text-text-secondary text-sm py-4">加载中…</div>
    <div v-else-if="history.length === 0" class="text-text-secondary text-sm py-4">暂无记录</div>
    <div v-else class="bg-card rounded-[12px] shadow-[var(--shadow-default)] overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-border text-text-secondary">
            <th class="text-left p-3 font-medium">时间</th>
            <th class="text-left p-3 font-medium">触发</th>
            <th class="text-left p-3 font-medium">状态</th>
            <th class="text-left p-3 font-medium">步骤</th>
            <th class="text-left p-3 font-medium">失败步骤</th>
            <th class="text-left p-3 font-medium">耗时</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="h in history" :key="h.run_id" class="border-b border-border last:border-0">
            <td class="p-3 tabular text-text-secondary">{{ fmtTime(h.started_at) }}</td>
            <td class="p-3">{{ h.trigger }}</td>
            <td class="p-3 tabular" :class="statusClass(h.status)">{{ h.status }}</td>
            <td class="p-3 tabular">{{ h.step_count }}</td>
            <td class="p-3 text-text-secondary">{{ h.failed_step || '—' }}</td>
            <td class="p-3 tabular text-text-secondary">
              {{ h.finished_at
                  ? ((new Date(h.finished_at).getTime() - new Date(h.started_at).getTime()) / 1000).toFixed(0) + 's'
                  : '—' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="h-16" />
  </PageShell>
</template>
