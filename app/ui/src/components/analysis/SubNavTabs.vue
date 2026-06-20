<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const TABS = [
  { key: 'stats', label: '统计概览', path: '/analysis/stats' },
  { key: 'clusters', label: '聚类分析', path: '/analysis/clusters' },
  { key: 'predict', label: '预测分析', path: '/analysis/predictions' },
  { key: 'keywords', label: '内容洞察', path: '/analysis/keywords' },
] as const

const router = useRouter()
const route = useRoute()

const activeKey = computed(() => {
  if (route.path.includes('keywords')) return 'keywords'
  if (route.path.includes('clusters')) return 'clusters'
  if (route.path.includes('predict')) return 'predict'
  return 'stats'
})

function go(key: string) {
  const tab = TABS.find(t => t.key === key)
  if (tab) router.push(tab.path)
}
</script>

<template>
  <div class="flex gap-2 border-b border-border pb-0 mb-8">
    <button
      v-for="tab in TABS"
      :key="tab.key"
      @click="go(tab.key)"
      class="px-5 py-2.5 text-sm font-medium rounded-t-[8px] border-none cursor-pointer
             transition-colors duration-200"
      :class="activeKey === tab.key
        ? 'bg-blue text-white'
        : 'bg-transparent text-text-secondary hover:text-text hover:bg-border/50'"
    >
      {{ tab.label }}
    </button>
  </div>
</template>
