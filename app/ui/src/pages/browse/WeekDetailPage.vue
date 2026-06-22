<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWeekDetail } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import VideoCard from '@/components/business/VideoCard.vue'

const route = useRoute()
const router = useRouter()
const number = Number(route.params.number)
const { data, loading, error, send } = useWeekDetail(number)

onMounted(() => send())
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
      <div class="bg-gradient-to-br from-blue-light to-bg rounded-[16px] p-10 mb-8 shadow-[var(--shadow-default)]">
        <span class="inline-block bg-blue text-white px-4 py-1 rounded-[20px] text-sm font-bold mb-3">
          第 {{ data.number }} 期
        </span>
        <h1 class="text-[2rem] font-bold text-text mb-2">{{ data.subject }}</h1>
        <p class="text-text-secondary">{{ data.name }}</p>
      </div>

      <h2 class="text-lg font-semibold text-text mb-4">{{ data.videos.length }} 个视频</h2>
      <div class="grid grid-cols-3 gap-5 pb-12">
        <VideoCard v-for="v in data.videos" :key="v.aid" :video="v" />
      </div>
    </template>
  </PageShell>
</template>
