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
  <el-card shadow="never" :body-style="{ padding: '24px' }">
    <el-statistic
      :title="label"
      :value="fmt(value)"
      :value-style="{
        color: 'var(--color-text)',
        fontWeight: 700,
        fontSize: '2rem',
        fontVariantNumeric: 'tabular-nums',
      }"
    />
    <p v-if="subLabel" class="text-xs text-text-secondary mt-1">{{ subLabel }}</p>
  </el-card>
</template>
