<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useKeywords } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import SubNavTabs from '@/components/analysis/SubNavTabs.vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'
import KeywordCloud from '@/components/charts/KeywordCloud.vue'
import AnalysisLoading from '@/components/shared/AnalysisLoading.vue'

const { data, loading, error, send } = useKeywords()

onMounted(() => send())

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
        <div class="flex gap-2 flex-wrap mb-4">
          <button
            v-for="wk in data.by_week"
            :key="wk.week_number"
            @click="selectedWeek = wk.week_number"
            class="px-3 py-1.5 border rounded-[20px] text-xs font-medium transition-colors cursor-pointer"
            :class="selectedWeek === wk.week_number
              ? 'bg-blue text-white border-blue'
              : 'bg-card text-text-secondary border-border hover:border-blue hover:text-blue'"
          >
            第{{ wk.week_number }}期
          </button>
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
        <div class="flex gap-2 flex-wrap mb-4">
          <button
            v-for="cat in data.by_category"
            :key="cat.tname"
            @click="selectedCategory = cat.tname"
            class="px-3 py-1.5 border rounded-[20px] text-xs font-medium transition-colors cursor-pointer"
            :class="selectedCategory === cat.tname
              ? 'bg-blue text-white border-blue'
              : 'bg-card text-text-secondary border-border hover:border-blue hover:text-blue'"
          >
            {{ cat.tname }}
          </button>
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
