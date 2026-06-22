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
    <PageShell sidebar class="flex-1 min-w-0">
    <div class="pb-10">
      <h1 class="text-[1.75rem] font-bold tracking-[-0.02em] text-text mb-1">内容分区</h1>
      <p class="text-[0.9375rem] text-text-secondary">
        覆盖 <span class="tabular font-semibold text-text">{{ data?.length ?? 0 }}</span> 个分区
      </p>
    </div>

    <div v-if="loading" class="grid grid-cols-4 gap-4 pb-8">
      <div v-for="i in 8" :key="i" class="h-30 bg-card rounded-[12px]">
        <el-skeleton animated />
      </div>
    </div>

    <div v-else-if="error" class="py-24">
      <el-result icon="error" title="加载失败" :sub-title="(error as Error).message">
        <template #extra>
          <el-button type="primary" @click="send()">重试</el-button>
        </template>
      </el-result>
    </div>

    <div v-else-if="data" class="grid grid-cols-4 gap-4 pb-12">
      <router-link
        v-for="(c, i) in data"
        :key="c.tid"
        :to="`/videos?category_tid=${c.tid}`"
        class="group bg-card rounded-[12px] p-6 shadow-(--shadow-default)
               border-t-[3px] transition-all duration-200 hover:shadow-(--shadow-hover)
               hover:-translate-y-0.5 cursor-pointer no-underline block"
        :style="{ borderTopColor: COLORS[i % COLORS.length] }"
      >
        <div class="flex items-start justify-between mb-2">
          <p class="text-base font-semibold text-text group-hover:text-blue transition-colors">{{ c.tname || `分区 ${c.tid}` }}</p>
          <svg class="w-4 h-4 text-text-secondary/30 group-hover:text-blue group-hover:translate-x-0.5 transition-all shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5"/>
          </svg>
        </div>
        <p class="text-[1.5rem] font-bold tabular text-text">{{ c.video_count }}</p>
        <p class="text-xs text-text-secondary mt-1">个视频</p>
        <p v-if="c.tname_v2" class="text-xs text-text-secondary mt-2 group-hover:text-text transition-colors">{{ c.tname_v2 }}</p>
      </router-link>
    </div>
  </PageShell>
</template>
