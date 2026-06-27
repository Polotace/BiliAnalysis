<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { bus } from '@/utils/events'
import { useKeywords } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import SubNavTabs from '@/components/analysis/SubNavTabs.vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'
import KeywordCloud from '@/components/charts/KeywordCloud.vue'
import AnalysisLoading from '@/components/shared/AnalysisLoading.vue'

const { data, loading, error, send } = useKeywords()

onMounted(() => { send(); bus.on('app:refresh', send) })
onUnmounted(() => bus.off('app:refresh', send))

const selectedWeek = ref<number | null>(null)
const selectedCategory = ref<string | null>(null)
</script>

<template>
  <Sidebar />
  <PageShell sidebar>
    <SubNavTabs class="lg:hidden" />

    <div v-if="loading">
      <AnalysisLoading label="正在提取关键词…" />
    </div>

    <div v-else-if="error" class="py-24">
      <el-result icon="error" title="加载失败" :sub-title="(error as Error).message">
        <template #extra>
          <el-button type="primary" @click="send()">重试</el-button>
        </template>
      </el-result>
    </div>

    <template v-else-if="data">
      <!-- Global Keywords -->
      <section class="py-8">
        <SectionHeader title="全局热词" :description="`TOP ${data.global_.keywords.length} 关键词`" />
        <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
          <KeywordCloud :keywords="data.global_.keywords" />
        </div>
      </section>

      <!-- Weekly Keywords -->
      <section class="py-8">
        <SectionHeader title="每周热词" description="按周报期数查看关键词" />
        <div class="mb-4">
          <el-select v-model="selectedWeek" placeholder="选择一期周报" clearable filterable
                     class="w-56!">
            <el-option v-for="wk in data.by_week" :key="wk.week_number"
                       :label="`第${wk.week_number}期`" :value="wk.week_number" />
          </el-select>
        </div>
        <div v-if="selectedWeek" class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
          <KeywordCloud
            :keywords="data.by_week.find(w => w.week_number === selectedWeek)?.keywords ?? []"
          />
        </div>
        <div v-else class="text-text-secondary text-sm">请选择一期周报</div>
      </section>

      <!-- Category Keywords -->
      <section class="py-8">
        <SectionHeader title="分区热词" description="按内容分区查看关键词" />
        <div class="mb-4">
          <el-select v-model="selectedCategory" placeholder="选择一个分区" clearable filterable
                     class="!w-56">
            <el-option v-for="cat in data.by_category" :key="cat.tname"
                       :label="cat.tname" :value="cat.tname" />
          </el-select>
        </div>
        <div v-if="selectedCategory" class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
          <KeywordCloud
            :keywords="data.by_category.find(c => c.tname === selectedCategory)?.keywords ?? []"
          />
        </div>
        <div v-else class="text-text-secondary text-sm">请选择一个分区</div>
      </section>
    </template>

    <div v-else class="py-12">
      <el-empty description="暂无数据，请先触发一次分析流水线" :image-size="120" />
    </div>
  </PageShell>
</template>
