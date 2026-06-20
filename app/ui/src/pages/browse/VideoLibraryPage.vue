<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { fetchVideos } from '@/composables/useApi'
import { useRequest } from 'alova/client'
import { ElScrollbar } from 'element-plus'
import PageShell from '@/components/layout/PageShell.vue'
import SearchBar from '@/components/business/SearchBar.vue'
import SortTabs from '@/components/business/SortTabs.vue'
import VideoCard from '@/components/business/VideoCard.vue'
import type { VideoSummary } from '@/types/api'

const search = ref('')
const sortBy = ref('view')
const SORT_OPTIONS = [
  { key: 'view', label: '按播放量' },
  { key: 'like', label: '按点赞量' },
  { key: 'pubdate', label: '最新发布' },
]

const videos = ref<VideoSummary[]>([])
const currentPage = ref(1)
const total = ref(0)
const PAGE_SIZE = 20
const isLoadingMore = ref(false)

const { loading, send } = useRequest(
  () => fetchVideos({
    page: currentPage.value,
    page_size: PAGE_SIZE,
    search: search.value || undefined,
    sort_by: sortBy.value,
  }),
  { immediate: false },
)

const hasMore = computed(() => videos.value.length < total.value)

async function loadPage() {
  const result = await send()
  if (result) {
    if (currentPage.value === 1) {
      videos.value = result.videos ?? []
    } else {
      videos.value.push(...(result.videos ?? []))
    }
    total.value = result.total ?? 0
  }
}

async function resetAndLoad() {
  currentPage.value = 1
  videos.value = []
  await loadPage()
}

async function loadMore() {
  if (isLoadingMore.value || !hasMore.value) return
  isLoadingMore.value = true
  currentPage.value++
  await loadPage()
  isLoadingMore.value = false
}

onMounted(() => loadPage())
</script>

<template>
  <PageShell class="!py-6 h-full flex flex-col">
    <div class="shrink-0 pb-6">
      <h1 class="text-[1.75rem] font-bold tracking-[-0.02em] text-text mb-1">发现好内容</h1>
      <p class="text-[0.9375rem] text-text-secondary">
        浏览 B站「每周必看」的 <span class="tabular font-semibold text-text">{{ total }}</span> 个精选视频
      </p>
    </div>

    <div class="shrink-0 flex items-center gap-3 pb-4 flex-wrap">
      <SearchBar v-model="search" placeholder="搜索视频标题…" @update:model-value="resetAndLoad" />
      <SortTabs v-model="sortBy" :options="SORT_OPTIONS" @update:model-value="resetAndLoad" />
    </div>

    <div v-if="loading && videos.length === 0" class="grid grid-cols-3 gap-5 pb-8">
      <div v-for="i in 6" :key="i" class="h-80 bg-card rounded-[12px] animate-pulse" />
    </div>

    <div v-else-if="!loading && videos.length === 0 && !hasMore" class="flex-1 flex items-center justify-center">
      <p class="text-text-secondary">暂无视频数据</p>
    </div>

    <template v-else>
      <el-scrollbar class="flex-1" @end-reached="loadMore">
        <div class="grid grid-cols-3 gap-5 pb-4">
          <VideoCard v-for="v in videos" :key="v.aid" :video="v" />
        </div>
        <div class="flex items-center justify-center py-6 gap-2 text-sm text-text-secondary">
          <template v-if="isLoadingMore">
            <div class="w-5 h-5 border-2 border-border border-t-blue rounded-full animate-spin" />
            <span>加载更多…</span>
          </template>
          <span v-else-if="!hasMore">— 没有更多了 —</span>
        </div>
      </el-scrollbar>
    </template>
  </PageShell>
</template>
