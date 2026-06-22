<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCreatorDetail, fetchCreatorStats } from '@/composables/useApi'
import { proxyImage } from '@/composables/useImageProxy'
import PageShell from '@/components/layout/PageShell.vue'
import VideoCard from '@/components/business/VideoCard.vue'

const route = useRoute()
const router = useRouter()
const mid = Number(route.params.mid)
const { data, loading, error, send } = useCreatorDetail(mid)

const liveStats = ref<{ follower: number; following: number } | null>(null)

onMounted(async () => {
  send()
  try {
    const stats = await fetchCreatorStats(mid)
    liveStats.value = stats as any
  } catch { /* live stats are optional */ }
})

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
      <el-skeleton :rows="4" animated />
    </div>

    <div v-else-if="error" class="py-24">
      <el-result icon="error" title="加载失败" :sub-title="(error as Error).message">
        <template #extra>
          <el-button type="primary" @click="send()">重试</el-button>
          <el-button @click="router.back()">返回</el-button>
        </template>
      </el-result>
    </div>

    <template v-else-if="data">
      <div class="bg-card rounded-[16px] p-10 mb-8 shadow-(--shadow-default) flex items-start gap-6">
        <img v-if="proxyImage(data.face)" :src="proxyImage(data.face)!" :alt="data.name"
             class="w-24 h-24 rounded-full object-cover shrink-0" />
        <div v-else class="w-24 h-24 rounded-full bg-border shrink-0 flex items-center justify-center text-text-secondary text-sm">UP</div>
        <div class="flex-1">
          <h1 class="text-[1.75rem] font-bold text-text mb-3">{{ data.name }}</h1>
          <div class="flex gap-6 tabular flex-wrap">
            <div><p class="text-2xl font-bold text-text">{{ data.video_count }}</p><p class="text-xs text-text-secondary">视频</p></div>
            <div v-if="liveStats"><p class="text-2xl font-bold text-text">{{ fmt(liveStats.follower) }}</p><p class="text-xs text-text-secondary">粉丝</p></div>
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
