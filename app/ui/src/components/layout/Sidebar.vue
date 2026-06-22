<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  VideoPlay, Calendar, User, Grid, DataAnalysis,
  DishDot, TrendCharts, Cloudy, Coin,
} from '@element-plus/icons-vue'

const route = useRoute()

interface NavLink { to: string; label: string; icon: any }

const BROWSE_LINKS: NavLink[] = [
  { to: '/videos', label: '视频库', icon: VideoPlay },
  { to: '/weeks', label: '周报', icon: Calendar },
  { to: '/creators', label: '创作者', icon: User },
  { to: '/categories', label: '分区', icon: Grid },
]

const ANALYSIS_LINKS: NavLink[] = [
  { to: '/analysis/stats', label: '统计概览', icon: DataAnalysis },
  { to: '/analysis/clusters', label: '聚类分析', icon: DishDot },
  { to: '/analysis/predictions', label: '预测分析', icon: TrendCharts },
  { to: '/analysis/keywords', label: '内容洞察', icon: Cloudy },
  { to: '/analysis/models', label: '模型对比', icon: Coin },
]

const links = computed<NavLink[]>(() => {
  if (route.path.startsWith('/analysis')) return ANALYSIS_LINKS
  return BROWSE_LINKS
})

const sectionLabel = computed(() => {
  if (route.path.startsWith('/analysis')) return '分析'
  return '浏览'
})

function isActive(link: NavLink) {
  if (link.to === '/videos') return route.path.startsWith('/videos')
  if (link.to === '/weeks') return route.path.startsWith('/weeks')
  if (link.to === '/creators') return route.path.startsWith('/creators')
  return route.path === link.to
}
</script>

<template>
  <aside class="hidden lg:flex lg:flex-col fixed left-0 top-14 bottom-0 w-44 pt-6 z-30
                bg-bg/95 backdrop-blur-sm">
    <p class="px-3 pb-4 text-[0.6875rem] font-semibold text-text-secondary/60 uppercase tracking-widest">
      {{ sectionLabel }}
    </p>
    <nav class="flex-1 space-y-0">
      <router-link
        v-for="link in links"
        :key="link.to"
        :to="link.to"
        class="group flex items-center gap-3 px-3 py-2 text-[0.875rem] font-medium
               transition-colors duration-100 no-underline relative"
        :class="isActive(link)
          ? 'text-blue font-semibold'
          : 'text-text-secondary/70 hover:text-text'"
      >
        <span
          class="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full transition-all duration-150"
          :class="isActive(link) ? 'bg-blue scale-100' : 'bg-blue/0 scale-0'"
        />
        <el-icon
          class="!w-4 !h-4 !shrink-0"
          :class="isActive(link) ? 'text-blue' : 'text-text-secondary/50'"
        ><component :is="link.icon" /></el-icon>
        <span>{{ link.label }}</span>
      </router-link>
    </nav>
  </aside>
</template>
