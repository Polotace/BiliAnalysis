<script setup lang="ts">
import { onMounted } from 'vue'
import { useCategoriesList } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import type { CategorySummary } from '@/types/api'

const { data, loading, error, send } = useCategoriesList()

onMounted(() => send())

const COLORS = [
  '#00AEEC', '#22C55E', '#F59E0B', '#EF4444', '#8B5CF6', '#10B981',
  '#EC4899', '#6366F1', '#F97316', '#06B6D4', '#84CC16', '#D946EF',
]
</script>

<template>
  
    <Sidebar />
    <PageShell class="flex-1 min-w-0">
    <div class="pb-10">
      <h1 class="text-[1.75rem] font-bold tracking-[-0.02em] text-text mb-1">内容分区</h1>
      <p class="text-[0.9375rem] text-text-secondary">
        覆盖 <span class="tabular font-semibold text-text">{{ data?.length ?? 0 }}</span> 个分区
      </p>
    </div>

    <div v-if="loading" class="grid grid-cols-4 gap-4 pb-8">
      <div v-for="i in 8" :key="i" class="h-30 bg-card rounded-[12px] animate-pulse" />
    </div>

    <div v-else-if="error" class="py-24 text-center">
      <p class="text-lg font-semibold text-text mb-2">加载失败</p>
      <p class="text-sm text-text-secondary mb-6">{{ (error as Error).message }}</p>
      <button @click="send()" class="px-6 py-2 bg-blue text-white rounded-[12px] font-medium hover:opacity-90">重试</button>
    </div>

    <div v-else-if="data" class="grid grid-cols-4 gap-4 pb-12">
      <div
        v-for="(c, i) in data"
        :key="c.tid"
        class="bg-card rounded-[12px] p-6 shadow-(--shadow-default)
               border-t-[3px] transition-shadow duration-200 hover:shadow-(--shadow-hover)"
        :style="{ borderTopColor: COLORS[i % COLORS.length] }"
      >
        <p class="text-base font-semibold text-text mb-2">{{ c.tname || `分区 ${c.tid}` }}</p>
        <p class="text-[1.5rem] font-bold tabular text-text">{{ c.video_count }}</p>
        <p class="text-xs text-text-secondary mt-1">个视频</p>
        <p v-if="c.tname_v2" class="text-xs text-text-secondary mt-2">{{ c.tname_v2 }}</p>
      </div>
    </div>
  </PageShell>
  </div>
</template>
