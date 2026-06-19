<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useWeeksList } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import WeekCard from '@/components/business/WeekCard.vue'
import InfiniteScroll from '@/components/business/InfiniteScroll.vue'
import { useInfiniteScroll } from '@/composables/useInfiniteScroll'
import type { WeekItem } from '@/types/api'

const { data, loading, error, send } = useWeeksList()
const weeks = ref<WeekItem[]>([])
const PAGE_SIZE = 20
const displayCount = ref(PAGE_SIZE)

onMounted(async () => {
  const result = await send()
  if (result) weeks.value = result
})

const displayed = computed(() => weeks.value.slice(0, displayCount.value))
const hasMore = computed(() => displayCount.value < weeks.value.length)

async function loadMore() {
  displayCount.value = Math.min(displayCount.value + PAGE_SIZE, weeks.value.length)
  await new Promise(r => setTimeout(r, 100))
}
async function safeLoadMore() {
  if (hasMore.value && !loading.value) await loadMore()
}
const { sentinelRef } = useInfiniteScroll(safeLoadMore, hasMore, loading)
</script>

<template>
  <PageShell>
    <div class="py-10">
      <h1 class="text-[1.75rem] font-bold tracking-[-0.02em] text-text mb-1">每周必看</h1>
      <p class="text-[0.9375rem] text-text-secondary">
        从 2019 年至今，已收录 <span class="tabular font-semibold text-text">{{ weeks.length }}</span> 期周报
      </p>
    </div>

    <div v-if="loading" class="grid grid-cols-2 gap-6 pb-8">
      <div v-for="i in 4" :key="i" class="h-[280px] bg-card rounded-[16px] animate-pulse" />
    </div>

    <div v-else-if="error" class="py-24 text-center">
      <p class="text-lg font-semibold text-text mb-2">加载失败</p>
      <p class="text-sm text-text-secondary mb-6">{{ (error as Error).message }}</p>
      <button @click="send()" class="px-6 py-2 bg-blue text-white rounded-[12px] font-medium hover:opacity-90">重试</button>
    </div>

    <div v-else-if="weeks.length === 0" class="py-24 text-center">
      <p class="text-text-secondary">暂无周报数据</p>
    </div>

    <template v-else>
      <div class="grid grid-cols-2 gap-6 pb-8">
        <WeekCard v-for="w in displayed" :key="w.number" :week="w" />
      </div>
      <div ref="sentinelRef">
        <InfiniteScroll :loading="false" :has-more="hasMore" />
      </div>
    </template>
  </PageShell>
</template>
