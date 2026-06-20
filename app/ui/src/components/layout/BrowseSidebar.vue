<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const LINKS = [
  { to: '/videos', label: '视频库', icon: 'videos' },
  { to: '/weeks', label: '周报', icon: 'weeks' },
  { to: '/creators', label: '创作者', icon: 'creators' },
  { to: '/categories', label: '分区', icon: 'categories' },
]

function isActive(path: string) {
  if (path === '/videos') return route.path.startsWith('/videos')
  if (path === '/weeks') return route.path.startsWith('/weeks')
  if (path === '/creators') return route.path.startsWith('/creators')
  return route.path === path
}
</script>

<template>
  <aside class="hidden lg:flex lg:flex-col w-48 shrink-0 pt-10 border-r border-border min-h-0">
    <p class="px-4 pb-3 text-[0.6875rem] font-semibold text-text-secondary uppercase tracking-wider">
      浏览
    </p>
    <nav class="flex-1 space-y-0.5 px-2">
      <router-link
        v-for="link in LINKS"
        :key="link.to"
        :to="link.to"
        class="flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[0.875rem] font-medium
               transition-all duration-100 no-underline group"
        :class="isActive(link.to)
          ? 'bg-blue-light/60 text-blue font-semibold'
          : 'text-text-secondary hover:text-text hover:bg-border/40'"
      >
        <!-- Video icon -->
        <svg v-if="link.icon === 'videos'" class="w-4 h-4 shrink-0" :class="isActive(link.to) ? 'text-blue' : 'text-text-secondary/60'" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z"/>
        </svg>
        <!-- Calendar/week icon -->
        <svg v-else-if="link.icon === 'weeks'" class="w-4 h-4 shrink-0" :class="isActive(link.to) ? 'text-blue' : 'text-text-secondary/60'" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5"/>
        </svg>
        <!-- User/creator icon -->
        <svg v-else-if="link.icon === 'creators'" class="w-4 h-4 shrink-0" :class="isActive(link.to) ? 'text-blue' : 'text-text-secondary/60'" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z"/>
        </svg>
        <!-- Grid/category icon -->
        <svg v-else class="w-4 h-4 shrink-0" :class="isActive(link.to) ? 'text-blue' : 'text-text-secondary/60'" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6Zm0 9.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6Zm0 9.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z"/>
        </svg>
        <span>{{ link.label }}</span>
      </router-link>
    </nav>
  </aside>
</template>
