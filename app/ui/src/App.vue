<script setup lang="ts">
import TopNav from '@/components/layout/TopNav.vue'
import { useAppStore } from '@/stores/app'

const cachedViews = ['VideoLibraryPage', 'WeeksPage', 'CreatorsPage', 'HomePage']
const app = useAppStore()

function onReanalyzeDone(success: boolean) {
  if (success) app.triggerRefresh()
}
</script>

<template>
  <div class="h-screen flex flex-col">
    <TopNav @reanalyze-done="onReanalyzeDone" />
    <div class="flex-1 min-h-0">
      <router-view v-slot="{ Component }">
        <keep-alive :max="5" :include="cachedViews">
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </div>
  </div>
</template>
