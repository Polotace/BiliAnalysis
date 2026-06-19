<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { fetchVideos } from '@/composables/useApi'
import { useRequest } from 'alova/client'
import { useInfiniteScroll } from '@/composables/useInfiniteScroll'
import PageShell from '@/components/layout/PageShell.vue'
import SearchBar from '@/components/business/SearchBar.vue'
import SortTabs from '@/components/business/SortTabs.vue'
import VideoCard from '@/components/business/VideoCard.vue'
import InfiniteScroll from '@/components/business/InfiniteScroll.vue'
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
  currentPage.value++
  await loadPage()
}

async function safeLoadMore() {
  if (hasMore.value && !loading.value) await loadMore()
}
const { sentinelRef } = useInfiniteScroll(safeLoadMore, hasMore, loading)

onMounted(() => loadPage())
</script>

<template>
  <PageShell>
    <div class="py-10">
      <h1 class="text-[1.75rem] font-bold tracking-[-0.02em] text-text mb-1">发现好内容</h1>
      <p class="text-[0.9375rem] text-text-secondary">
        浏览 B站「每周必看」的 <span class="tabular font-semibold text-text">{{ total }}</span> 个精选视频
      </p>
    </div>

    <div class="flex items-center gap-3 pb-6 flex-wrap">
      <SearchBar v-model="search" placeholder="搜索视频标题…" @update:model-value="resetAndLoad" />
      <SortTabs v-model="sortBy" :options="SORT_OPTIONS" @update:model-value="resetAndLoad" />
    </div>

    <div v-if="loading && videos.length === 0" class="grid grid-cols-3 gap-5 pb-8">
      <div v-for="i in 6" :key="i" class="h-[320px] bg-card rounded-[12px] animate-pulse" />
    </div>

    <div v-else-if="!loading && videos.length === 0 && !hasMore" class="py-24 text-center">
      <p class="text-text-secondary">暂无视频数据</p>
    </div>

    <template v-else>
      <div class="grid grid-cols-3 gap-5 pb-8">
        <VideoCard v-for="v in videos" :key="v.aid" :video="v" />
      </div>
      <div ref="sentinelRef">
        <InfiniteScroll :loading="loading" :has-more="hasMore" />
      </div>
    </template>
  </PageShell>
</template>
