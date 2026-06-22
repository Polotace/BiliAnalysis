<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { TabsPaneContext } from 'element-plus'

const TABS = [
  { key: 'stats', label: '统计概览', path: '/analysis/stats' },
  { key: 'clusters', label: '聚类分析', path: '/analysis/clusters' },
  { key: 'predict', label: '预测分析', path: '/analysis/predictions' },
  { key: 'keywords', label: '内容洞察', path: '/analysis/keywords' },
  { key: 'models', label: '模型对比', path: '/analysis/models' },
] as const

const router = useRouter()
const route = useRoute()

const activeKey = computed(() => {
  if (route.path.includes('keywords')) return 'keywords'
  if (route.path.includes('models')) return 'models'
  if (route.path.includes('clusters')) return 'clusters'
  if (route.path.includes('predict')) return 'predict'
  return 'stats'
})

function go(tab: TabsPaneContext) {
  const key = tab.paneName as string
  const found = TABS.find(t => t.key === key)
  if (found) router.push(found.path)
}
</script>

<template>
  <el-tabs
    :model-value="activeKey"
    @tab-click="go"
    class="mb-8 subnav-tabs"
  >
    <el-tab-pane
      v-for="tab in TABS"
      :key="tab.key"
      :label="tab.label"
      :name="tab.key"
    />
  </el-tabs>
</template>

<style scoped>
.subnav-tabs {
  --el-tabs-header-height: 44px;
}
</style>
