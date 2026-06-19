<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useCreatorsList } from '@/composables/useApi'
import { useInfiniteScroll } from '@/composables/useInfiniteScroll'
import PageShell from '@/components/layout/PageShell.vue'
import SortTabs from '@/components/business/SortTabs.vue'
import CreatorCard from '@/components/business/CreatorCard.vue'
import InfiniteScroll from '@/components/business/InfiniteScroll.vue'
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

const { loading, send } = useCreatorsList({
  page: currentPage.value,
  page_size: PAGE_SIZE,
  sort_by: sortBy.value,
})

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
async function loadMore() { currentPage.value++; await loadPage() }
async function safeLoadMore() {
  if (hasMore.value && !loading.value) await loadMore()
}
const { sentinelRef } = useInfiniteScroll(safeLoadMore, hasMore, loading)

onMounted(() => loadPage())
</script>

<template>
  <PageShell>
    <div class="py-10">
      <h1 class="text-[1.75rem] font-bold tracking-[-0.02em] text-text mb-1">创作者</h1>
      <p class="text-[0.9375rem] text-text-secondary">
        <span class="tabular font-semibold text-text">{{ total }}</span> 位创作者上榜「每周必看」
      </p>
    </div>

    <div class="pb-6">
      <SortTabs v-model="sortBy" :options="SORT_OPTIONS" @update:model-value="resetAndLoad" />
    </div>

    <div v-if="loading && creators.length === 0" class="grid grid-cols-3 gap-4 pb-8">
      <div v-for="i in 6" :key="i" class="h-[80px] bg-card rounded-[12px] animate-pulse" />
    </div>

    <div v-else-if="!loading && creators.length === 0 && !hasMore" class="py-24 text-center">
      <p class="text-text-secondary">暂无创作者数据</p>
    </div>

    <template v-else>
      <div class="grid grid-cols-3 gap-4 pb-8">
        <CreatorCard v-for="c in creators" :key="c.mid" :creator="c" />
      </div>
      <div ref="sentinelRef">
        <InfiniteScroll :loading="loading" :has-more="hasMore" />
      </div>
    </template>
  </PageShell>
</template>
