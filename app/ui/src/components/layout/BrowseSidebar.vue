<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const LINKS = [
  { to: '/videos', label: '视频库' },
  { to: '/weeks', label: '周报' },
  { to: '/creators', label: '创作者' },
  { to: '/categories', label: '分区' },
]

function isActive(path: string) {
  if (path === '/videos') return route.path.startsWith('/videos')
  if (path === '/weeks') return route.path.startsWith('/weeks')
  if (path === '/creators') return route.path.startsWith('/creators')
  return route.path === path
}
</script>

<template>
  <aside class="hidden lg:block w-44 shrink-0 pt-10">
    <nav class="sticky top-20 space-y-1">
      <router-link
        v-for="link in LINKS"
        :key="link.to"
        :to="link.to"
        class="block px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-100 no-underline"
        :class="isActive(link.to)
          ? 'bg-blue-light text-blue'
          : 'text-text-secondary hover:text-text hover:bg-bg'"
      >
        {{ link.label }}
      </router-link>
    </nav>
  </aside>
</template>
