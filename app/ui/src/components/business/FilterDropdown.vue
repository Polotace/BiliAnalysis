<script setup lang="ts">
defineProps<{
  label: string
  options: { key: number; label: string; count?: number }[]
  modelValue: number | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
}>()
</script>

<template>
  <el-select
    :model-value="modelValue"
    :placeholder="label"
    clearable
    class="filter-select"
    @update:model-value="emit('update:modelValue', $event as number | null)"
  >
    <el-option
      v-for="opt in options"
      :key="opt.key"
      :label="opt.label"
      :value="opt.key"
    >
      <span>{{ opt.label }}</span>
      <span v-if="opt.count !== undefined" class="tabular opacity-50 float-right ml-2">{{ opt.count }}</span>
    </el-option>
  </el-select>
</template>

<style scoped>
.filter-select {
  --el-border-radius-base: 20px;
  --el-border-color: var(--color-border);
}
</style>
