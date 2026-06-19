<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRequest } from 'alova/client'
import PageShell from '@/components/layout/PageShell.vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'
import StatCard from '@/components/shared/StatCard.vue'
import {
  fetchCrawlerStatus, triggerCrawler, triggerAnalysis, triggerDbLoad,
  fetchAnalysisOverview, fetchPipelineList, fetchPipelineHistory,
  triggerPipeline,
} from '@/composables/useApi'
import type { CrawlerStatus, AnalysisOverview, PipelineListResponse, RunHistoryItem } from '@/types/api'

// ── Status data ──
const { data: crawlerStatus, loading: csLoading, error: csError, send: csSend } =
  useRequest(fetchCrawlerStatus, { immediate: false })
const { data: analysisOverview, loading: aoLoading, send: aoSend } =
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

// ── Load all on mount ──
onMounted(async () => {
  await Promise.all([csSend(), aoSend(), plSend()])
  await loadHistory()
})

async function doAction(label: string, fn: () => Promise<any>) {
  actionLoading.value = label
  actionResult.value = ''
  actionError.value = ''
  try {
    const r = await fn()
    actionResult.value = `${label} 已触发 (run_id=${r.run_id || 'OK'})`
    // Refresh status after a short delay
    setTimeout(async () => { await Promise.all([csSend(), aoSend()]) }, 1500)
  } catch (e: any) {
    actionError.value = `${label} 失败: ${e.message || e}`
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
</script>

<template>
  <PageShell>
    <div class="py-10">
      <h1 class="text-[1.75rem] font-bold tracking-[-0.02em] text-text mb-1">管理后台</h1>
      <p class="text-[0.9375rem] text-text-secondary">数据采集、分析与入库管理</p>
    </div>

    <!-- ── 仪表盘 ── -->
    <SectionHeader title="仪表盘" description="系统当前状态" />

    <!-- Crawler Status -->
    <div v-if="csLoading" class="grid grid-cols-4 gap-4 mb-8">
      <div v-for="i in 4" :key="i" class="h-24 bg-card rounded-[12px] animate-pulse" />
    </div>
    <div v-else-if="csError" class="text-text-secondary mb-8">状态加载失败: {{ (csError as Error).message }}</div>
    <div v-else-if="crawlerStatus" class="grid grid-cols-4 gap-4 mb-8">
      <StatCard label="数据周次" :value="crawlerStatus.total_weeks" />
      <StatCard label="已爬取" :value="crawlerStatus.crawled" sub-label="成功入库" />
      <StatCard label="失败" :value="Object.keys(crawlerStatus.failed).length" sub-label="待重试" />
      <StatCard
        label="状态"
        :value="crawlerStatus.is_running ? '运行中' : '空闲'"
        :sub-label="crawlerStatus.last_run ? `上次: ${fmtTime(crawlerStatus.last_run)}` : '从未运行'"
      />
    </div>

    <!-- Analysis Status -->
    <div v-if="analysisOverview" class="grid grid-cols-4 gap-4 mb-8">
      <StatCard label="清洗报告" :value="analysisOverview.last_clean ? '✅' : '—'" :sub-label="analysisOverview.last_clean ? `${analysisOverview.last_clean.total_videos} 视频` : '未生成'" />
      <StatCard label="统计报告" :value="analysisOverview.last_stats ? '✅' : '—'" :sub-label="analysisOverview.last_stats ? `${analysisOverview.last_stats.overall.total_videos} 视频` : '未生成'" />
      <StatCard label="聚类报告" :value="analysisOverview.last_cluster ? '✅' : '—'" :sub-label="analysisOverview.last_cluster ? `silhouette=${analysisOverview.last_cluster.clusters.silhouette_score}` : '未生成'" />
      <StatCard label="预测报告" :value="analysisOverview.last_prediction ? '✅' : '—'" :sub-label="analysisOverview.last_prediction ? `view R²=${analysisOverview.last_prediction.view_predict.r2_score}` : '未生成'" />
    </div>

    <!-- ── 操作面板 ── -->
    <SectionHeader title="操作面板" description="手动触发任务" />
    <div class="flex flex-wrap gap-3 mb-2">
      <button
        v-for="btn in [
          {label:'触发爬取', fn:()=>doAction('爬取', ()=>triggerCrawler()), color:'bg-blue'},
          {label:'触发分析', fn:()=>doAction('分析', ()=>triggerAnalysis()), color:'bg-success'},
          {label:'入库 PG', fn:()=>doAction('入库', ()=>triggerDbLoad()), color:'bg-warning'},
        ]"
        :key="btn.label"
        @click="btn.fn"
        :disabled="actionLoading !== ''"
        class="px-5 py-2.5 rounded-[12px] text-white font-medium text-sm border-none cursor-pointer
               transition-opacity duration-200 hover:opacity-85 disabled:opacity-50"
        :class="btn.color"
      >
        <span v-if="actionLoading === btn.label" class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2 align-middle" />
        {{ btn.label }}
      </button>

      <!-- Pipeline trigger buttons -->
      <template v-if="pipelineList">
        <button
          v-for="pl in pipelineList.pipelines"
          :key="pl.name"
          @click="doAction(pl.name, () => triggerPipeline(pl.name))"
          :disabled="actionLoading !== ''"
          class="px-5 py-2.5 rounded-[12px] text-white font-medium text-sm border-none cursor-pointer
                 transition-opacity duration-200 hover:opacity-85 disabled:opacity-50"
          :class="pl.name === 'warehouse' ? 'bg-[#8B5CF6]' : 'bg-text-secondary'"
        >
          <span v-if="actionLoading === pl.name" class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2 align-middle" />
          流水线: {{ pl.name }}
        </button>
      </template>
    </div>

    <!-- Action feedback -->
    <div
      v-if="actionResult"
      class="mb-4 p-3 rounded-[8px] bg-[#ECFDF5] text-success text-sm border border-success/20"
    >{{ actionResult }}</div>
    <div
      v-if="actionError"
      class="mb-4 p-3 rounded-[8px] bg-[#FEF2F2] text-danger text-sm border border-danger/20"
    >{{ actionError }}</div>

    <!-- ── 执行历史 ── -->
    <SectionHeader title="执行历史" description="最近任务执行记录" />
    <div class="flex gap-2 mb-4 flex-wrap">
      <button
        v-for="name in ['crawl', 'analysis', 'warehouse']"
        :key="name"
        @click="switchHistory(name)"
        class="px-4 py-1.5 border rounded-[20px] text-sm font-medium transition-colors cursor-pointer"
        :class="historyPipeline === name
          ? 'bg-blue text-white border-blue'
          : 'bg-card text-text-secondary border-border hover:border-blue hover:text-blue'"
      >
        {{ name }}
      </button>
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
