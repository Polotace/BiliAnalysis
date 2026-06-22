<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  VideoPlay, Calendar, User, Grid, DataAnalysis,
  DishDot, TrendCharts, Cloudy, Coin,
} from '@element-plus/icons-vue'

const route = useRoute()

interface NavLink { to: string; label: string }

const BROWSE_LINKS: NavLink[] = [
  { to: '/videos', label: '视频库' },
  { to: '/weeks', label: '周报' },
  { to: '/creators', label: '创作者' },
  { to: '/categories', label: '分区' },
]

const ANALYSIS_LINKS: NavLink[] = [
  { to: '/analysis/stats', label: '统计概览' },
  { to: '/analysis/clusters', label: '聚类分析' },
  { to: '/analysis/predictions', label: '预测分析' },
  { to: '/analysis/keywords', label: '内容洞察' },
  { to: '/analysis/models', label: '模型对比' },
]

const BROWSE_ICONS: Record<string, any> = {
  '/videos': VideoPlay, '/weeks': Calendar, '/creators': User, '/categories': Grid,
}
const ANALYSIS_ICONS: Record<string, any> = {
  '/analysis/stats': DataAnalysis, '/analysis/clusters': DishDot,
  '/analysis/predictions': TrendCharts, '/analysis/keywords': Cloudy, '/analysis/models': Coin,
}

const links = computed<NavLink[]>(() => {
  if (route.path.startsWith('/analysis')) return ANALYSIS_LINKS
  return BROWSE_LINKS
})

const sectionLabel = computed(() => {
  if (route.path.startsWith('/analysis')) return '分析'
  return '浏览'
})

function iconFor(link: NavLink) {
  return (ANALYSIS_ICONS as any)[link.to] ?? (BROWSE_ICONS as any)[link.to]
}
</script>

<template>
  <el-menu
    :default-active="route.path"
    :router="true"
    :ellipsis="false"
    class="sidebar-menu !fixed !left-0 !top-14 !bottom-0 !w-44 !z-30 !bg-bg/95 !backdrop-blur-sm !border-0 !pt-6"
  >
    <el-menu-item-group :title="sectionLabel">
      <el-menu-item
        v-for="link in links"
        :key="link.to"
        :index="link.to"
        class="sidebar-item"
      >
        <el-icon class="!w-4 !h-4 !shrink-0"><component :is="iconFor(link)" /></el-icon>
        <span class="!text-[0.875rem] !font-medium">{{ link.label }}</span>
      </el-menu-item>
    </el-menu-item-group>
  </el-menu>
</template>

<style scoped>
.sidebar-menu {
  --el-menu-bg-color: transparent;
  --el-menu-text-color: var(--color-text-secondary);
  --el-menu-hover-bg-color: transparent;
  --el-menu-active-color: var(--color-blue);
}

.sidebar-menu :deep(.el-menu-item-group__title) {
  padding: 0 12px 16px;
  font-size: 0.6875rem;
  font-weight: 600;
  color: rgba(107, 114, 128, 0.6);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.sidebar-item {
  margin: 0;
  padding: 8px 12px !important;
  height: auto !important;
  line-height: 1.5 !important;
  gap: 12px;
}

.sidebar-item.is-active {
  color: var(--color-blue) !important;
  font-weight: 600;
}
</style>
