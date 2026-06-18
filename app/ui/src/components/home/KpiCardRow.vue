<script setup lang="ts">
import StatCard from '@/components/shared/StatCard.vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'
import type { OverallStats } from '@/types/api'

defineProps<{ overall: OverallStats }>()
</script>

<template>
  <section class="py-12">
    <SectionHeader title="平台概览" description="「每周必看」数据全景" />
    <div class="grid grid-cols-4 gap-6">
      <StatCard label="视频总数" :value="overall.total_videos" />
      <StatCard label="平均播放" :value="overall.avg_view" sub-label="每期均值" />
      <StatCard label="平均点赞" :value="overall.avg_like" sub-label="每期均值" />
      <StatCard label="创作者数" :value="overall.total_creators" />
    </div>
  </section>
</template>
