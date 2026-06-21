<script setup lang="ts">
withDefaults(defineProps<{ sidebar?: boolean }>(), { sidebar: false })
</script>

<template>
  <!--
    sidebar=true: on lg+ screens, margin-left = max(sidebar_width, (100% - 1280px) / 2).
    On wide screens (>1632px) the natural centering margin already clears the fixed
    Sidebar, so max() returns the centering value → content is centered. On narrower
    screens max() floors at 176px, preventing overlap.

    sidebar=false: classic max-w-7xl mx-auto centering.
  -->
  <main
    class="max-w-7xl mx-auto px-6 py-4"
    :class="{ 'lg:ml-[max(11rem,calc((100%-80rem)/2))]': sidebar }"
  >
    <slot />
  </main>
</template>
