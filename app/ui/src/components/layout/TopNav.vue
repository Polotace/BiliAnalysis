<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

function isAnalysisActive() {
  return route.path.startsWith('/analysis')
}
function isBrowseActive() {
  return ['/videos', '/weeks', '/creators', '/categories'].some(p => route.path.startsWith(p))
}
</script>

<template>
  <nav class="sticky top-0 z-100 bg-bg/85 backdrop-blur-md border-b border-border">
    <div class="max-w-7xl mx-auto px-6 flex items-center h-14 gap-8">
      <router-link to="/" class="text-lg font-bold text-text no-underline tracking-[-0.01em]">
        Bili<span class="text-blue">Insight</span>
      </router-link>
      <ul class="flex gap-6 list-none">
        <li>
          <router-link
            to="/"
            class="no-underline text-[0.9375rem] font-medium text-text-secondary px-0 py-1
                   transition-colors duration-200 relative
                   hover:text-text"
            :class="{ 'text-text!': route.path === '/' }"
          >
            发现
            <span
              v-if="route.path === '/'"
              class="absolute -bottom-4 left-0 right-0 h-0.5 bg-blue rounded-sm"
            />
          </router-link>
        </li>
        <li>
          <router-link
            to="/analysis/stats"
            class="no-underline text-[0.9375rem] font-medium text-text-secondary px-0 py-1
                   transition-colors duration-200 relative
                   hover:text-text"
            :class="{ 'text-text!': isAnalysisActive() }"
          >
            分析
            <span
              v-if="isAnalysisActive()"
              class="absolute -bottom-4 left-0 right-0 h-0.5 bg-blue rounded-sm"
            />
          </router-link>
        </li>
        <li class="relative group">
          <router-link
            to="/videos"
            class="no-underline text-[0.9375rem] font-medium text-text-secondary px-0 py-1
                   transition-colors duration-200 relative
                   hover:text-text"
            :class="{ 'text-text!': isBrowseActive() }"
          >
            浏览
            <span
              v-if="isBrowseActive()"
              class="absolute -bottom-4 left-0 right-0 h-0.5 bg-blue rounded-sm"
            />
          </router-link>
          <div class="absolute top-full left-1/2 -translate-x-1/2 mt-3
                      bg-card rounded-[12px] shadow-[0_8px_32px_rgba(0,0,0,0.10)]
                      border border-border p-1.5 min-w-32.5 flex flex-col
                      opacity-0 invisible group-hover:opacity-100 group-hover:visible
                      transition-[opacity,visibility] duration-150">
            <router-link to="/videos" class="block px-3.5 py-2 rounded-md text-sm text-text-secondary no-underline transition-colors duration-100 hover:bg-bg hover:text-text">视频库</router-link>
            <router-link to="/weeks" class="block px-3.5 py-2 rounded-md text-sm text-text-secondary no-underline transition-colors duration-100 hover:bg-bg hover:text-text">周报</router-link>
            <router-link to="/creators" class="block px-3.5 py-2 rounded-md text-sm text-text-secondary no-underline transition-colors duration-100 hover:bg-bg hover:text-text">创作者</router-link>
            <router-link to="/categories" class="block px-3.5 py-2 rounded-md text-sm text-text-secondary no-underline transition-colors duration-100 hover:bg-bg hover:text-text">分区</router-link>
          </div>
        </li>
      </ul>
      <router-link
        to="/admin"
        class="ml-auto no-underline text-text-secondary hover:text-text transition-colors"
        :class="{ 'text-blue!': route.path === '/admin' }"
        title="管理后台"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </router-link>
    </div>
  </nav>
</template>
