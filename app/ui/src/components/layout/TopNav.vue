<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

function isAnalysisActive() {
  return route.path.startsWith('/analysis')
}
</script>

<template>
  <nav class="sticky top-0 z-100 bg-bg/85 backdrop-blur-[12px] border-b border-border">
    <div class="max-w-[1280px] mx-auto px-6 flex items-center h-14 gap-8">
      <router-link to="/" class="text-lg font-bold text-text no-underline tracking-[-0.01em]">
        Bili<span class="text-blue">Insight</span>
      </router-link>
      <ul class="flex gap-6 list-none">
        <li>
          <router-link
            to="/"
            class="no-underline text-[0.9375rem] font-medium text-text-secondary px-0 py-1
                   transition-colors duration-200 relative
                   hover:text-text"
            :class="{ '!text-text': route.path === '/' }"
            active-class="!text-text"
          >
            发现
            <span
              v-if="route.path === '/'"
              class="absolute -bottom-4 left-0 right-0 h-0.5 bg-blue rounded-sm"
            />
          </router-link>
        </li>
        <li>
          <router-link
            to="/analysis/stats"
            class="no-underline text-[0.9375rem] font-medium text-text-secondary px-0 py-1
                   transition-colors duration-200 relative
                   hover:text-text"
            :class="{ '!text-text': isAnalysisActive() }"
          >
            分析
            <span
              v-if="isAnalysisActive()"
              class="absolute -bottom-4 left-0 right-0 h-0.5 bg-blue rounded-sm"
            />
          </router-link>
        </li>
      </ul>
    </div>
  </nav>
</template>
