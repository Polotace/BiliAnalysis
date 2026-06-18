<script setup lang="ts">
import { onMounted } from 'vue'
import { useStats } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import HeroSection from '@/components/home/HeroSection.vue'
import KpiCardRow from '@/components/home/KpiCardRow.vue'
import CategoryBar from '@/components/home/CategoryBar.vue'
import CreatorTopList from '@/components/home/CreatorTopList.vue'
import TrendMiniChart from '@/components/home/TrendMiniChart.vue'

const { data, loading, error, send } = useStats()

onMounted(() => send())
</script>

<template>
  <PageShell>
    <HeroSection />

    <template v-if="loading">
      <div class="space-y-8 py-12">
        <div class="h-32 bg-card rounded-[12px] animate-pulse" />
        <div class="h-48 bg-card rounded-[12px] animate-pulse" />
        <div class="h-48 bg-card rounded-[12px] animate-pulse" />
        <div class="h-56 bg-card rounded-[12px] animate-pulse" />
      </div>
    </template>

    <div v-else-if="error" class="py-12 text-center">
      <div class="bg-card rounded-[16px] p-12 shadow-[var(--shadow-default)] max-w-md mx-auto">
        <p class="text-lg font-semibold text-text mb-2">加载失败</p>
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
      <KpiCardRow :overall="data.overall" />
      <CategoryBar :categories="data.by_category" />
      <CreatorTopList :creators="data.by_creator" />
      <TrendMiniChart :weeks="data.by_week.slice(-10)" />
    </template>

    <div v-else class="py-12 text-center">
      <p class="text-text-secondary">暂无数据，请先触发一次数据采集与分析</p>
    </div>
  </PageShell>
</template>
