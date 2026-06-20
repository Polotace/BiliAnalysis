<script setup lang="ts">
import { computed } from 'vue'
import TopNav from '@/components/layout/TopNav.vue'

const cachedViews = ['VideoLibraryPage', 'WeeksPage', 'CreatorsPage', 'HomePage']
</script>

<template>
  <TopNav />
  <router-view v-slot="{ Component }">
    <keep-alive :max="5" :include="cachedViews">
      <component :is="Component" />
    </keep-alive>
  </router-view>
</template>
