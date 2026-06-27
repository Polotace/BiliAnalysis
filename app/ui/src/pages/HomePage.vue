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
        <el-skeleton :rows="3" animated />
        <el-skeleton :rows="3" animated />
        <el-skeleton :rows="3" animated />
        <el-skeleton :rows="3" animated />
      </div>
    </template>

    <div v-else-if="error" class="py-12">
      <el-result icon="error" title="加载失败" :sub-title="(error as Error).message">
        <template #extra>
          <el-button type="primary" @click="send()">重试</el-button>
        </template>
      </el-result>
    </div>

    <template v-else-if="data">
      <KpiCardRow :overall="data.overall" />
      <CategoryBar :categories="data.by_category" />
      <CreatorTopList :creators="data.by_creator" />
      <TrendMiniChart :weeks="data.by_week.slice(-10)" />
    </template>

    <div v-else class="py-12">
      <el-empty description="暂无数据，请先触发一次数据采集与分析" :image-size="120" />
    </div>
  </PageShell>
</template>
