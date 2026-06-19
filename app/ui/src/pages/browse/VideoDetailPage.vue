<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useVideo } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'

const route = useRoute()
const router = useRouter()
const aid = Number(route.params.aid)
const { data, loading, error, send } = useVideo(aid)

onMounted(() => send())

function fmt(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(1)}万` : String(n)
}
function fmtDuration(secs: number): string {
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${m}:${String(s).padStart(2, '0')}`
}
</script>

<template>
  <PageShell>
    <div v-if="loading" class="space-y-6 py-8">
      <div class="h-[400px] bg-card rounded-[16px] animate-pulse" />
      <div class="h-32 bg-card rounded-[12px] animate-pulse" />
    </div>

    <div v-else-if="error" class="py-24 text-center">
      <p class="text-lg font-semibold text-text mb-2">加载失败</p>
      <p class="text-sm text-text-secondary mb-6">{{ (error as Error).message }}</p>
      <button @click="send()" class="px-6 py-2 bg-blue text-white rounded-[12px] font-medium hover:opacity-90">重试</button>
      <button @click="router.back()" class="px-6 py-2 ml-3 border border-border rounded-[12px] text-text-secondary hover:text-text">返回</button>
    </div>

    <template v-else-if="data">
      <div class="relative h-[400px] rounded-[16px] overflow-hidden mb-8 bg-border">
        <img v-if="data.cover_url" :src="data.cover_url" :alt="data.title"
             class="w-full h-full object-cover" />
        <div v-else class="w-full h-full flex items-center justify-center text-text-secondary">暂无封面</div>
        <div class="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
        <div class="absolute bottom-0 left-0 right-0 p-8">
          <h1 class="text-2xl font-bold text-white mb-3 leading-snug">{{ data.title }}</h1>
          <div class="flex items-center gap-6 text-sm text-white/80">
            <router-link :to="`/creators/${data.creator_mid}`" class="flex items-center gap-2 hover:text-white no-underline">
              <img v-if="data.creator_face" :src="data.creator_face" class="w-6 h-6 rounded-full" />
              <span>{{ data.creator_name }}</span>
            </router-link>
            <span>{{ fmtDuration(data.duration) }}</span>
            <span v-if="data.category_name">{{ data.category_name }}</span>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-4 gap-6 mb-8">
        <div class="bg-card rounded-[12px] p-5 shadow-[var(--shadow-default)]">
          <p class="text-xs text-text-secondary mb-1">播放量</p>
          <p class="text-2xl font-bold tabular text-text">{{ fmt(data.view) }}</p>
        </div>
        <div class="bg-card rounded-[12px] p-5 shadow-[var(--shadow-default)]">
          <p class="text-xs text-text-secondary mb-1">点赞</p>
          <p class="text-2xl font-bold tabular text-text">{{ fmt(data.like_cnt) }}</p>
        </div>
        <div class="bg-card rounded-[12px] p-5 shadow-[var(--shadow-default)]">
          <p class="text-xs text-text-secondary mb-1">弹幕</p>
          <p class="text-2xl font-bold tabular text-text">{{ fmt(data.danmaku) }}</p>
        </div>
        <div class="bg-card rounded-[12px] p-5 shadow-[var(--shadow-default)]">
          <p class="text-xs text-text-secondary mb-1">收藏</p>
          <p class="text-2xl font-bold tabular text-text">{{ fmt(data.favorite) }}</p>
        </div>
      </div>

      <div class="grid grid-cols-3 gap-4 mb-8 text-center">
        <div v-for="item in [{label:'投币',v:data.coin},{label:'分享',v:data.share},{label:'评论',v:data.reply}]"
             :key="item.label" class="bg-card rounded-[12px] p-4 shadow-[var(--shadow-default)]">
          <p class="text-xl font-bold tabular text-text">{{ fmt(item.v) }}</p>
          <p class="text-xs text-text-secondary mt-1">{{ item.label }}</p>
        </div>
      </div>

      <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)] mb-8">
        <h2 class="text-lg font-semibold text-text mb-4">出现周次</h2>
        <div class="flex flex-wrap gap-2">
          <router-link
            v-for="wn in data.appeared_weeks"
            :key="wn"
            :to="`/weeks/${wn}`"
            class="px-3 py-1.5 bg-blue-light text-blue rounded-md text-sm font-medium no-underline hover:bg-blue hover:text-white transition-colors"
          >
            第 {{ wn }} 期
          </router-link>
        </div>
      </div>

      <div v-if="data.description" class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
        <h2 class="text-lg font-semibold text-text mb-4">简介</h2>
        <p class="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">{{ data.description }}</p>
      </div>
    </template>
  </PageShell>
</template>
