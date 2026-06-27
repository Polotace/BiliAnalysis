<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { usePredictions } from '@/composables/useApi'
import { bus } from '@/utils/events'
import PageShell from '@/components/layout/PageShell.vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import SubNavTabs from '@/components/analysis/SubNavTabs.vue'
import StatCard from '@/components/shared/StatCard.vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'
import ForecastCards from '@/components/analysis/ForecastCards.vue'
import FitLineChart from '@/components/charts/FitLineChart.vue'
import AnalysisLoading from '@/components/shared/AnalysisLoading.vue'
import type { PredictionResult } from '@/types/api'

const { data, loading, error, send } = usePredictions()

onMounted(() => { send(); bus.on('app:refresh', send) })
onUnmounted(() => bus.off('app:refresh', send))

const target = ref<'view' | 'like'>('view')
const active = computed<PredictionResult>(() =>
  target.value === 'view' ? data.value!.view_predict : data.value!.like_predict)

function fmt(v: number, d = 2): string { return v.toFixed(d) }
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
      <!-- Target toggle -->
      <div class="flex items-center gap-3 mb-6">
        <span class="text-sm text-text-secondary">预测目标:</span>
        <el-segmented v-model="target" :options="[
          { label: '播放量', value: 'view' },
          { label: '点赞量', value: 'like' },
        ]" />
      </div>

      <!-- Train / Test metrics -->
      <div class="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="训练 R²" :value="fmt(active.r2_score, 3)" sub-label="越高越好" />
        <StatCard label="训练 RMSE" :value="fmt(active.rmse / 1e4, 1) + '万'" sub-label="均方根误差" />
        <StatCard v-if="active.test_r2_score !== null"
          label="测试 R²" :value="fmt(active.test_r2_score!, 3)"
          sub-label="泛化能力" />
        <StatCard v-if="active.test_rmse !== null"
          label="测试 RMSE" :value="fmt(active.test_rmse! / 1e4, 1) + '万'"
          sub-label="泛化误差" />
      </div>

      <section class="py-8">
        <SectionHeader title="预测拟合" description="实际值 vs 拟合值 vs 预测值" />
        <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
          <FitLineChart :result="active" />
        </div>
      </section>

      <ForecastCards :forecast="active.forecast" />

      <section class="py-8">
        <SectionHeader title="回归系数" description="各特征的影响权重" />
        <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)] space-y-3">
          <div
            v-for="[name, coef] in Object.entries(active.coefficients)"
            :key="name"
            class="flex items-center gap-4"
          >
            <span class="text-sm text-text-secondary w-24 shrink-0">{{ name }}</span>
            <span class="text-sm font-medium tabular"
              :class="coef > 0 ? 'text-success' : 'text-danger'"
            >
              {{ coef > 0 ? '+' : '' }}{{ fmt(coef, 4) }}
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
