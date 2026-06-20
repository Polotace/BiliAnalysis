<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { fetchVideos, fetchCategories } from '@/composables/useApi'
import { useRequest } from 'alova/client'
import { ElScrollbar } from 'element-plus'
import PageShell from '@/components/layout/PageShell.vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import SearchBar from '@/components/business/SearchBar.vue'
import SortTabs from '@/components/business/SortTabs.vue'
import VideoCard from '@/components/business/VideoCard.vue'
import type { VideoSummary, CategorySummary } from '@/types/api'

const CAT_COLORS = [
  '#00AEEC', '#22C55E', '#F59E0B', '#EF4444', '#8B5CF6', '#10B981',
  '#EC4899', '#6366F1', '#F97316', '#06B6D4', '#84CC16', '#D946EF',
]

const search = ref('')
const sortBy = ref('view')
const categoryTid = ref<number | null>(null)
const showAllCategories = ref(false)
const categories = ref<CategorySummary[]>([])
const CAT_VISIBLE = 12

const SORT_OPTIONS = [
  { key: 'view', label: '按播放量' },
  { key: 'like', label: '按点赞量' },
  { key: 'pubdate', label: '最新发布' },
]

const visibleCategories = computed(() =>
  showAllCategories.value ? categories.value : categories.value.slice(0, CAT_VISIBLE))

const activeCategoryName = computed(() => {
  if (categoryTid.value === null) return null
  return categories.value.find(c => c.tid === categoryTid.value)?.tname ?? null
})

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
    category_tid: categoryTid.value ?? undefined,
  }),
  { immediate: false },
)

const { data: categoriesData, send: loadCategories } = useRequest(
  fetchCategories, { immediate: false },
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

function selectCategory(tid: number | null) {
  categoryTid.value = categoryTid.value === tid ? null : tid
  resetAndLoad()
}

onMounted(async () => {
  const cats = await loadCategories()
  if (cats) categories.value = cats as any
  await loadPage()
})
</script>

<template>
  
    <Sidebar />
    <PageShell class="!py-4 h-full flex flex-col">
    <div class="shrink-0 pb-6">
      <h1 class="text-[1.75rem] font-bold tracking-[-0.02em] text-text mb-1">发现好内容</h1>
      <p class="text-[0.9375rem] text-text-secondary">
        <template v-if="activeCategoryName">
          分区「<span class="text-text font-medium">{{ activeCategoryName }}</span>」·
        </template>
        <span class="tabular font-semibold text-text">{{ total }}</span> 个精选视频
      </p>
    </div>

    <div class="shrink-0 flex items-center gap-3 pb-3 flex-wrap">
      <SearchBar v-model="search" placeholder="搜索视频标题…" @update:model-value="resetAndLoad" />
      <SortTabs v-model="sortBy" :options="SORT_OPTIONS" @update:model-value="resetAndLoad" />
    </div>
    <div class="shrink-0 flex gap-2 pb-4 flex-wrap items-center">
      <button
        v-for="(cat, i) in visibleCategories"
        :key="cat.tid"
        @click="selectCategory(cat.tid)"
        class="flex items-center gap-1.5 px-3 py-1.5 border rounded-[20px] text-xs font-medium transition-all duration-150 cursor-pointer"
        :class="categoryTid === cat.tid
          ? 'text-white border-transparent shadow-sm'
          : 'bg-card text-text-secondary border-border hover:border-[color:hsl(from_var(--c)_h_s_l)] hover:text-text'"
        :style="{
          '--c': CAT_COLORS[i % CAT_COLORS.length],
          ...(categoryTid === cat.tid
            ? { backgroundColor: CAT_COLORS[i % CAT_COLORS.length], borderColor: CAT_COLORS[i % CAT_COLORS.length] }
            : {}),
        }"
      >
        <span
          class="w-1.5 h-1.5 rounded-full shrink-0"
          :style="{ backgroundColor: CAT_COLORS[i % CAT_COLORS.length] }"
          :class="{ '!bg-white': categoryTid === cat.tid }"
        />
        {{ cat.tname || cat.tid }}
        <span class="tabular opacity-60">{{ cat.video_count }}</span>
      </button>
      <button
        v-if="categories.length > CAT_VISIBLE"
        @click="showAllCategories = !showAllCategories"
        class="px-3 py-1.5 text-xs font-medium text-text-secondary hover:text-text
               transition-colors cursor-pointer bg-transparent border-0"
      >
        {{ showAllCategories ? '收起 ▲' : `更多 ${categories.length - CAT_VISIBLE} 个 ▼` }}
      </button>
    </div>

    <div v-if="loading && videos.length === 0" class="grid grid-cols-3 gap-5 pb-8">
      <div v-for="i in 6" :key="i" class="h-80 bg-card rounded-[12px] animate-pulse" />
    </div>

    <div v-else-if="!loading && videos.length === 0 && !hasMore" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <p class="text-text-secondary mb-1">
          <template v-if="categoryTid || search">没有匹配的视频</template>
          <template v-else>暂无视频数据</template>
        </p>
        <button
          v-if="categoryTid || search"
          @click="categoryTid = null; search = ''; resetAndLoad()"
          class="text-sm text-blue hover:underline bg-transparent border-0 cursor-pointer"
        >清除筛选</button>
      </div>
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
