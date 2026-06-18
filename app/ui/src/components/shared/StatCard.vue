<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  subLabel?: string
}>()

function fmt(v: string | number): string {
  if (typeof v === 'number') {
    return v >= 10000 ? `${(v / 10000).toFixed(1)}万` : String(v)
  }
  return v
}
</script>

<template>
  <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
    <p class="text-sm font-medium text-text-secondary mb-2">{{ label }}</p>
    <p class="text-[2rem] font-bold text-text tabular leading-tight">{{ fmt(value) }}</p>
    <p v-if="subLabel" class="text-xs text-text-secondary mt-1">{{ subLabel }}</p>
  </div>
</template>
