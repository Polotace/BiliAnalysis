<script setup lang="ts">
defineProps<{
  options: { key: string; label: string }[]
  modelValue: string
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <el-segmented
    :model-value="modelValue"
    :options="options.map(o => ({ label: o.label, value: o.key }))"
    @update:model-value="emit('update:modelValue', $event as string)"
  />
</template>
