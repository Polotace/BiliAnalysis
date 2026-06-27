<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import TopNav from '@/components/layout/TopNav.vue'
import { bus } from '@/utils/events'

const router = useRouter()
const cachedViews = ['VideoLibraryPage', 'WeeksPage', 'CreatorsPage', 'HomePage']

onMounted(() => {
  bus.on('auth:logout', () => {
    const from = router.currentRoute.value.fullPath
    router.push(`/login?redirect=${encodeURIComponent(from)}`)
  })
  bus.on('app:refresh', () => {
    const route = router.currentRoute.value
    router.replace({ path: route.path, query: { ...route.query, _t: Date.now() } })
  })
})
onUnmounted(() => bus.all.clear())
</script>

<template>
  <div class="h-screen flex flex-col">
    <TopNav />
    <div class="flex-1 min-h-0">
      <router-view v-slot="{ Component }">
        <keep-alive :max="5" :include="cachedViews">
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </div>
  </div>
</template>
