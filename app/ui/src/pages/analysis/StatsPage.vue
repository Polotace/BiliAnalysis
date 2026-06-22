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
import AnalysisLoading from '@/components/shared/AnalysisLoading.vue'

const { data, loading, error, send } = useStats()

onMounted(() => send())
</script>

<template>
  
    <Sidebar />
    <PageShell sidebar class="flex-1 min-w-0">
    <SubNavTabs class="lg:hidden" />

    <template v-if="loading">
      <AnalysisLoading label="正在计算统计数据…" />
    </template>

    <div v-else-if="error" class="py-12">
      <el-result icon="error" title="加载失败" :sub-title="(error as Error).message">
        <template #extra>
          <el-button type="primary" @click="send()">重试</el-button>
        </template>
      </el-result>
    </div>

    <template v-else-if="data">
      <div class="grid grid-cols-3 gap-6 mb-8">
        <StatCard label="视频总数" :value="data.overall.total_videos" />
        <StatCard label="创作者数" :value="data.overall.total_creators" />
        <StatCard label="平均互动率" :value="(data.overall.avg_like_rate * 100).toFixed(1) + '%'" />
      </div>

      <section class="py-8">
        <SectionHeader title="趋势分析" description="播放、点赞、互动率随时间变化" />
        <div class="bg-card rounded-[12px] p-6 shadow-(--shadow-default)">
          <TrendLineChart :weeks="data.by_week" />
        </div>
      </section>

      <CategoryPanel :categories="data.by_category" />
      <CreatorTable :creators="data.by_creator" />
    </template>

    <div v-else class="py-12">
      <el-empty description="暂无数据，请先触发一次数据采集与分析" :image-size="120" />
    </div>
  </PageShell>
</template>
