<script setup lang="ts">
import { computed } from 'vue'
import TopNav from '@/components/layout/TopNav.vue'

const cachedViews = ['VideoLibraryPage', 'WeeksPage', 'CreatorsPage', 'HomePage']
</script>

<template>
  <div class="h-screen flex flex-col overflow-hidden">
    <TopNav />
    <div class="flex-1 overflow-hidden">
      <router-view v-slot="{ Component }">
        <keep-alive :max="5" :include="cachedViews">
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </div>
  </div>
</template>
