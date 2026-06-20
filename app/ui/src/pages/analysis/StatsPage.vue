<script setup lang="ts">
import { onMounted } from 'vue'
import { useStats } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import SubNavTabs from '@/components/analysis/SubNavTabs.vue'
import StatCard from '@/components/shared/StatCard.vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'
import TrendLineChart from '@/components/charts/TrendLineChart.vue'
import CategoryPanel from '@/components/analysis/CategoryPanel.vue'
import CreatorTable from '@/components/analysis/CreatorTable.vue'

const { data, loading, error, send } = useStats()

onMounted(() => send())
</script>

<template>
  <div class="flex h-full">
    <Sidebar />
    <PageShell class="flex-1 min-w-0">
    <SubNavTabs class="lg:hidden" />

    <template v-if="loading">
      <div class="space-y-8">
        <div class="h-24 bg-card rounded-[12px] animate-pulse" />
        <div class="h-[400px] bg-card rounded-[12px] animate-pulse" />
        <div class="h-[320px] bg-card rounded-[12px] animate-pulse" />
        <div class="h-64 bg-card rounded-[12px] animate-pulse" />
      </div>
    </template>

    <div v-else-if="error" class="py-12 text-center">
      <div class="bg-card rounded-[16px] p-12 shadow-[var(--shadow-default)] max-w-md mx-auto">
        <p class="text-lg font-semibold text-text mb-2">加载失败，请重试</p>
        <p class="text-sm text-text-secondary mb-6">{{ (error as Error).message }}</p>
        <button
          @click="send()"
          class="px-6 py-2 bg-blue text-white rounded-[12px] font-medium
                 border-none cursor-pointer hover:bg-[#0099D6] transition-colors"
        >
          重试
        </button>
      </div>
    </div>

    <template v-else-if="data">
      <div class="grid grid-cols-3 gap-6 mb-8">
        <StatCard label="视频总数" :value="data.overall.total_videos" />
        <StatCard label="创作者数" :value="data.overall.total_creators" />
        <StatCard label="平均互动率" :value="(data.overall.avg_like_rate * 100).toFixed(1) + '%'" />
      </div>

      <section class="py-8">
        <SectionHeader title="趋势分析" description="播放、点赞、互动率随时间变化" />
        <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
          <TrendLineChart :weeks="data.by_week" />
        </div>
      </section>

      <CategoryPanel :categories="data.by_category" />
      <CreatorTable :creators="data.by_creator" />
    </template>

    <div v-else class="py-12 text-center">
      <p class="text-text-secondary">暂无数据，请先触发一次数据采集与分析</p>
    </div>
  </PageShell>
  </div>
</template>
