<script setup lang="ts">
import type { WeekItem } from '@/types/api'

defineProps<{ week: WeekItem }>()

const COLORS = ['#00AEEC', '#22C55E', '#F59E0B', '#8B5CF6', '#EF4444', '#10B981', '#EC4899', '#6366F1']
</script>

<template>
  <router-link
    :to="`/weeks/${week.number}`"
    class="block cursor-pointer no-underline"
  >
    <el-card shadow="hover" :body-style="{ padding: '0' }" class="week-card">
      <div
        class="h-[200px] relative overflow-hidden"
        :style="{ background: `linear-gradient(135deg, ${COLORS[week.number % COLORS.length]}, ${COLORS[(week.number + 1) % COLORS.length]})` }"
      >
        <div class="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
        <span class="absolute top-4 left-4 bg-white/90 backdrop-blur px-[14px] py-1 rounded-[20px]
                     text-[0.8125rem] font-bold text-blue tracking-[-0.01em]">
          第 {{ week.number }} 期
        </span>
        <h3 class="absolute bottom-4 left-4 right-4 text-white text-lg font-bold leading-snug
                   drop-shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
          {{ week.subject || '无主题' }}
        </h3>
      </div>
      <div class="flex items-center justify-between px-5 py-4 gap-3">
        <span class="text-sm text-text-secondary font-medium truncate">{{ week.name || '' }}</span>
        <span class="bg-blue-light text-blue font-semibold px-[10px] py-[3px] rounded-md text-[0.8125rem] tabular">
          {{ week.video_count }} 个视频
        </span>
      </div>
    </el-card>
  </router-link>
</template>

<style scoped>
.week-card {
  --el-card-border-radius: 16px;
  --el-card-border-color: transparent;
}
</style>
