<script setup lang="ts">
import { onMounted } from 'vue'
import { useClusters } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import SubNavTabs from '@/components/analysis/SubNavTabs.vue'
import StatCard from '@/components/shared/StatCard.vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'
import ClusterCards from '@/components/analysis/ClusterCards.vue'
import FeatureImportance from '@/components/analysis/FeatureImportance.vue'
import ClusterScatter from '@/components/charts/ClusterScatter.vue'

const { data, loading, error, send } = useClusters()

onMounted(() => send())
</script>

<template>
    <Sidebar />
    <PageShell class="flex-1 min-w-0">
    <SubNavTabs class="lg:hidden" />

    <template v-if="loading">
      <div class="space-y-8">
        <div class="h-24 bg-card rounded-[12px] animate-pulse" />
        <div class="h-64 bg-card rounded-[12px] animate-pulse" />
        <div class="h-[480px] bg-card rounded-[12px] animate-pulse" />
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

    <div v-else class="py-12 text-center">
      <p class="text-text-secondary">暂无数据，请先触发一次数据采集与分析</p>
    </div>
  </PageShell>
</template>
