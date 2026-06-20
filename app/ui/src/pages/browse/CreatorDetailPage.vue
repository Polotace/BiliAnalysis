<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCreatorDetail } from '@/composables/useApi'
import { proxyImage } from '@/composables/useImageProxy'
import PageShell from '@/components/layout/PageShell.vue'
import VideoCard from '@/components/business/VideoCard.vue'

const route = useRoute()
const router = useRouter()
const mid = Number(route.params.mid)
const { data, loading, error, send } = useCreatorDetail(mid)

onMounted(() => send())

function fmt(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(1)}万` : String(n)
}
</script>

<template>
  <PageShell>
    <div class="py-2">
      <a href="#" @click.prevent="router.back()" class="inline-flex items-center gap-1.5 text-sm text-text-secondary hover:text-blue transition-colors no-underline">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/></svg>
        返回
      </a>
    </div>
    <div v-if="loading" class="space-y-6 py-8">
      <div class="h-48 bg-card rounded-[16px] animate-pulse" />
      <div class="h-64 bg-card rounded-[12px] animate-pulse" />
    </div>

    <div v-else-if="error" class="py-24 text-center">
      <p class="text-lg font-semibold text-text mb-2">加载失败</p>
      <p class="text-sm text-text-secondary mb-6">{{ (error as Error).message }}</p>
      <button @click="send()" class="px-6 py-2 bg-blue text-white rounded-[12px] font-medium hover:opacity-90">重试</button>
      <button @click="router.back()" class="px-6 py-2 ml-3 border border-border rounded-[12px] text-text-secondary hover:text-text">返回</button>
    </div>

    <template v-else-if="data">
      <div class="bg-card rounded-[16px] p-10 mb-8 shadow-(--shadow-default) flex items-start gap-6">
        <img v-if="proxyImage(data.face)" :src="proxyImage(data.face)!" :alt="data.name"
             class="w-24 h-24 rounded-full object-cover shrink-0" />
        <div v-else class="w-24 h-24 rounded-full bg-border shrink-0 flex items-center justify-center text-text-secondary text-sm">UP</div>
        <div class="flex-1">
          <h1 class="text-[1.75rem] font-bold text-text mb-3">{{ data.name }}</h1>
          <div class="grid grid-cols-5 gap-4 tabular">
            <div><p class="text-2xl font-bold text-text">{{ data.video_count }}</p><p class="text-xs text-text-secondary">视频</p></div>
            <div><p class="text-2xl font-bold text-text">{{ fmt(data.total_views) }}</p><p class="text-xs text-text-secondary">总播放</p></div>
            <div><p class="text-2xl font-bold text-text">{{ fmt(data.total_likes) }}</p><p class="text-xs text-text-secondary">总点赞</p></div>
            <div><p class="text-2xl font-bold text-text">{{ fmt(data.total_coins) }}</p><p class="text-xs text-text-secondary">总投币</p></div>
            <div><p class="text-2xl font-bold text-text">{{ fmt(data.total_favorites) }}</p><p class="text-xs text-text-secondary">总收藏</p></div>
          </div>
        </div>
      </div>

      <h2 class="text-lg font-semibold text-text mb-4">作品</h2>
      <div class="grid grid-cols-3 gap-5 pb-12">
        <VideoCard v-for="v in data.videos" :key="v.aid" :video="v" />
      </div>
    </template>
  </PageShell>
</template>
