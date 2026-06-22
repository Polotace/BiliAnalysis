<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { Setting } from '@element-plus/icons-vue'
import ReanalyzeButton from '@/components/shared/ReanalyzeButton.vue'

const route = useRoute()
const router = useRouter()

function isAnalysisActive() {
  return route.path.startsWith('/analysis')
}
function isBrowseActive() {
  return ['/videos', '/weeks', '/creators', '/categories'].some(p => route.path.startsWith(p))
}

function onReanalyzeDone(success: boolean) {
  if (success) router.replace(route.fullPath)
}
</script>

<template>
  <nav class="sticky top-0 z-100 bg-bg/85 backdrop-blur-md border-b border-border">
    <div class="max-w-7xl mx-auto px-6 flex items-center h-14 gap-8">
      <router-link to="/" class="text-lg font-bold text-text no-underline tracking-[-0.01em] shrink-0">
        Bili<span class="text-blue">Insight</span>
      </router-link>

      <div class="hidden lg:flex flex-1 items-center">
        <el-menu
          mode="horizontal"
          :default-active="route.path"
          :router="true"
          :ellipsis="false"
          class="topnav-menu !border-0 !bg-transparent !flex-1"
        >
          <el-menu-item index="/" class="topnav-item">发现</el-menu-item>
          <el-menu-item index="/analysis/stats" class="topnav-item">分析</el-menu-item>
          <el-menu-item index="/videos" class="topnav-item">浏览</el-menu-item>
        </el-menu>
      </div>

      <ul class="flex gap-6 list-none lg:hidden">
        <li>
          <router-link
            to="/"
            class="no-underline text-[0.9375rem] font-medium text-text-secondary px-0 py-1
                   transition-colors duration-200 relative hover:text-text"
            :class="{ 'text-text!': route.path === '/' }"
          >
            发现
            <span v-if="route.path === '/'" class="absolute -bottom-4 left-0 right-0 h-0.5 bg-blue rounded-sm" />
          </router-link>
        </li>
        <li>
          <router-link
            to="/analysis/stats"
            class="no-underline text-[0.9375rem] font-medium text-text-secondary px-0 py-1
                   transition-colors duration-200 relative hover:text-text"
            :class="{ 'text-text!': isAnalysisActive() }"
          >
            分析
            <span v-if="isAnalysisActive()" class="absolute -bottom-4 left-0 right-0 h-0.5 bg-blue rounded-sm" />
          </router-link>
        </li>
        <li class="relative group">
          <router-link
            to="/videos"
            class="no-underline text-[0.9375rem] font-medium text-text-secondary px-0 py-1
                   transition-colors duration-200 relative hover:text-text"
            :class="{ 'text-text!': isBrowseActive() }"
          >
            浏览
            <span v-if="isBrowseActive()" class="absolute -bottom-4 left-0 right-0 h-0.5 bg-blue rounded-sm" />
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

      <ReanalyzeButton v-if="isAnalysisActive()" class="ml-auto" @done="onReanalyzeDone" />
      <router-link
        to="/admin"
        class="no-underline text-text-secondary hover:text-text transition-colors"
        :class="[{ 'ml-auto': !isAnalysisActive(), 'text-blue!': route.path === '/admin' }]"
        title="管理后台"
      >
        <el-icon class="!w-5 !h-5"><Setting /></el-icon>
      </router-link>
    </div>
  </nav>
</template>

<style scoped>
.topnav-menu {
  --el-menu-bg-color: transparent;
  --el-menu-text-color: var(--color-text-secondary);
  --el-menu-hover-text-color: var(--color-text);
  --el-menu-active-color: var(--color-text);
  --el-menu-horizontal-sub-item-height: 56px;
}

.topnav-item {
  font-size: 0.9375rem !important;
  font-weight: 500 !important;
  height: 56px !important;
  line-height: 56px !important;
  padding: 0 12px !important;
  border-bottom-color: var(--color-blue) !important;
}

.topnav-item:hover {
  color: var(--color-text) !important;
}

:deep(.el-menu--horizontal) {
  border-bottom: none !important;
}
</style>
