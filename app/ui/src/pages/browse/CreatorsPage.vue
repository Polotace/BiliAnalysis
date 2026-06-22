<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { fetchCreators } from '@/composables/useApi'
import { useRequest } from 'alova/client'
import PageShell from '@/components/layout/PageShell.vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import SortTabs from '@/components/business/SortTabs.vue'
import CreatorCard from '@/components/business/CreatorCard.vue'
import type { CreatorSummary } from '@/types/api'

const sortBy = ref('video_count')
const SORT_OPTIONS = [
  { key: 'video_count', label: '作品最多' },
  { key: 'total_views', label: '总播放最高' },
  { key: 'name', label: '按名称' },
]

const creators = ref<CreatorSummary[]>([])
const currentPage = ref(1)
const total = ref(0)
const PAGE_SIZE = 24
const isLoadingMore = ref(false)

const { loading, send } = useRequest(
  () => fetchCreators({ page: currentPage.value, page_size: PAGE_SIZE, sort_by: sortBy.value }),
  { immediate: false },
)

const hasMore = computed(() => creators.value.length < total.value)

async function loadPage() {
  const result = await send()
  if (result) {
    if (currentPage.value === 1) creators.value = result.creators ?? []
    else creators.value.push(...(result.creators ?? []))
    total.value = result.total ?? 0
  }
}

async function resetAndLoad() {
  currentPage.value = 1; creators.value = []; await loadPage()
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
  
    <Sidebar />
    <PageShell sidebar class="!py-4 h-full flex flex-col">
    <div class="shrink-0 pb-6">
      <h1 class="text-[1.75rem] font-bold tracking-[-0.02em] text-text mb-1">创作者</h1>
      <p class="text-[0.9375rem] text-text-secondary">
        <span class="tabular font-semibold text-text">{{ total }}</span> 位创作者上榜「每周必看」
      </p>
    </div>

    <div class="shrink-0 pb-4">
      <SortTabs v-model="sortBy" :options="SORT_OPTIONS" @update:model-value="resetAndLoad" />
    </div>

    <div v-if="loading && creators.length === 0" class="grid grid-cols-3 gap-4 pb-8">
      <div v-for="i in 6" :key="i" class="h-20 bg-card rounded-[12px]">
        <el-skeleton animated />
      </div>
    </div>

    <div v-else-if="!loading && creators.length === 0 && !hasMore" class="flex-1 flex items-center justify-center">
      <el-empty description="暂无创作者数据" :image-size="80" />
    </div>

    <template v-else>
      <el-scrollbar class="flex-1" @end-reached="loadMore">
        <div class="grid grid-cols-3 gap-4 pb-4">
          <CreatorCard v-for="c in creators" :key="c.mid" :creator="c" />
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
