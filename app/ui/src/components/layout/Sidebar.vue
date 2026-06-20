<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

interface NavLink { to: string; label: string; icon: string }

const BROWSE_LINKS: NavLink[] = [
  { to: '/videos', label: '视频库', icon: 'video' },
  { to: '/weeks', label: '周报', icon: 'calendar' },
  { to: '/creators', label: '创作者', icon: 'users' },
  { to: '/categories', label: '分区', icon: 'grid' },
]

const ANALYSIS_LINKS: NavLink[] = [
  { to: '/analysis/stats', label: '统计概览', icon: 'chart' },
  { to: '/analysis/clusters', label: '聚类分析', icon: 'scatter' },
  { to: '/analysis/predictions', label: '预测分析', icon: 'trend' },
  { to: '/analysis/keywords', label: '内容洞察', icon: 'cloud' },
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
        <!-- Video -->
        <svg v-if="link.icon === 'video'" class="w-4 h-4 shrink-0" :class="isActive(link) ? 'text-blue' : 'text-text-secondary/50'" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z"/>
        </svg>
        <!-- Calendar -->
        <svg v-else-if="link.icon === 'calendar'" class="w-4 h-4 shrink-0" :class="isActive(link) ? 'text-blue' : 'text-text-secondary/50'" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5"/>
        </svg>
        <!-- Users -->
        <svg v-else-if="link.icon === 'users'" class="w-4 h-4 shrink-0" :class="isActive(link) ? 'text-blue' : 'text-text-secondary/50'" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z"/>
        </svg>
        <!-- Grid -->
        <svg v-else-if="link.icon === 'grid'" class="w-4 h-4 shrink-0" :class="isActive(link) ? 'text-blue' : 'text-text-secondary/50'" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6Zm0 9.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6Zm0 9.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z"/>
        </svg>
        <!-- Chart/bar -->
        <svg v-else-if="link.icon === 'chart'" class="w-4 h-4 shrink-0" :class="isActive(link) ? 'text-blue' : 'text-text-secondary/50'" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z"/>
        </svg>
        <!-- Scatter/dots -->
        <svg v-else-if="link.icon === 'scatter'" class="w-4 h-4 shrink-0" :class="isActive(link) ? 'text-blue' : 'text-text-secondary/50'" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <circle cx="7" cy="7" r="2" fill="currentColor"/>
          <circle cx="17" cy="10" r="2" fill="currentColor"/>
          <circle cx="12" cy="17" r="2" fill="currentColor"/>
          <path stroke-linecap="round" d="M7 7h.01M17 10h.01M12 17h.01"/>
        </svg>
        <!-- Trend/line -->
        <svg v-else-if="link.icon === 'trend'" class="w-4 h-4 shrink-0" :class="isActive(link) ? 'text-blue' : 'text-text-secondary/50'" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3l-1.5 15M3.75 3h16.5M3.75 3l16.5 18M21 3v11.25A2.25 2.25 0 0 1 18.75 16.5h-2.25M21 3l1.5 15M21 3 4.5 21"/>
        </svg>
        <!-- Cloud -->
        <svg v-else-if="link.icon === 'cloud'" class="w-4 h-4 shrink-0" :class="isActive(link) ? 'text-blue' : 'text-text-secondary/50'" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15a4.5 4.5 0 0 0 4.5 4.5H18a3.75 3.75 0 0 0 1.332-7.257 3 3 0 0 0-3.758-3.848 5.25 5.25 0 0 0-10.233 2.33A4.502 4.502 0 0 0 2.25 15Z"/>
        </svg>
        <span>{{ link.label }}</span>
      </router-link>
    </nav>
  </aside>
</template>
