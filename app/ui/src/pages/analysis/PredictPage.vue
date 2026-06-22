<script setup lang="ts">
import { onMounted } from 'vue'
import { usePredictions } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import SubNavTabs from '@/components/analysis/SubNavTabs.vue'
import StatCard from '@/components/shared/StatCard.vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'
import ForecastCards from '@/components/analysis/ForecastCards.vue'
import FitLineChart from '@/components/charts/FitLineChart.vue'
import AnalysisLoading from '@/components/shared/AnalysisLoading.vue'

const { data, loading, error, send } = usePredictions()

onMounted(() => send())

function fmtR2(v: number): string {
  return v.toFixed(3)
}
</script>

<template>
    <Sidebar />
    <PageShell sidebar class="flex-1 min-w-0">
    <SubNavTabs class="lg:hidden" />

    <template v-if="loading">
      <AnalysisLoading label="正在训练预测模型…" />
    </template>

    <div v-else-if="error" class="py-12">
      <el-result icon="error" title="加载失败" :sub-title="(error as Error).message">
        <template #extra>
          <el-button type="primary" @click="send()">重试</el-button>
        </template>
      </el-result>
    </div>

    <template v-else-if="data">
      <div class="grid grid-cols-2 gap-6 mb-8">
        <StatCard
          label="播放量预测 R²"
          :value="fmtR2(data.view_predict.r2_score)"
          sub-label="系数越接近1拟合越好"
        />
        <StatCard
          label="点赞量预测 R²"
          :value="fmtR2(data.like_predict.r2_score)"
          sub-label="系数越接近1拟合越好"
        />
      </div>

      <section class="py-8">
        <SectionHeader title="预测拟合" description="实际值 vs 拟合值 vs 预测值" />
        <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
          <FitLineChart :result="data.view_predict" />
        </div>
      </section>

      <ForecastCards :forecast="data.view_predict.forecast" />

      <section class="py-8">
        <SectionHeader title="回归系数" description="各特征对播放量的影响权重" />
        <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)] space-y-3">
          <div
            v-for="[name, coef] in Object.entries(data.view_predict.coefficients)"
            :key="name"
            class="flex items-center gap-4"
          >
            <span class="text-sm text-text-secondary w-24 shrink-0">{{ name }}</span>
            <span class="text-sm font-medium tabular"
              :class="coef > 0 ? 'text-success' : 'text-danger'"
            >
              {{ coef > 0 ? '+' : '' }}{{ coef.toFixed(4) }}
            </span>
          </div>
        </div>
      </section>
    </template>

    <div v-else class="py-12">
      <el-empty description="暂无数据，请先触发一次数据采集与分析" :image-size="120" />
    </div>
  </PageShell>
</template>
