<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useClusters } from '@/composables/useApi'
import { bus } from '@/utils/events'
import PageShell from '@/components/layout/PageShell.vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import SubNavTabs from '@/components/analysis/SubNavTabs.vue'
import StatCard from '@/components/shared/StatCard.vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'
import ClusterCards from '@/components/analysis/ClusterCards.vue'
import FeatureImportance from '@/components/analysis/FeatureImportance.vue'
import ClusterScatter from '@/components/charts/ClusterScatter.vue'
import AnalysisLoading from '@/components/shared/AnalysisLoading.vue'

const { data, loading, error, send } = useClusters()

onMounted(() => { send(); bus.on('app:refresh', send) })
onUnmounted(() => bus.off('app:refresh', send))
</script>

<template>
    <Sidebar />
    <PageShell sidebar class="flex-1 min-w-0">
    <SubNavTabs class="lg:hidden" />

    <template v-if="loading">
      <AnalysisLoading label="正在运行聚类算法…" />
    </template>

    <div v-else-if="error" class="py-12">
      <el-result icon="error" title="加载失败" :sub-title="(error as Error).message">
        <template #extra>
          <el-button type="primary" @click="send()">重试</el-button>
        </template>
      </el-result>
    </div>

    <template v-else-if="data">
      <div class="mb-8">
        <StatCard
          label="轮廓系数"
          :value="data.clusters.silhouette_score.toFixed(3)"
          sub-label="Silhouette Score"
        />
      </div>

      <ClusterCards :clusters="data.clusters.clusters" />
      <FeatureImportance :features="data.clusters.feature_importance" />

      <section class="py-8">
        <SectionHeader title="聚类可视化" description="PCA 降维后的二维散点分布" />
        <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
          <ClusterScatter :scatter-data="data.scatter_data" :clusters="data.clusters.clusters" />
        </div>
      </section>
    </template>

    <div v-else class="py-12">
      <el-empty description="暂无数据，请先触发一次数据采集与分析" :image-size="120" />
    </div>
  </PageShell>
</template>
