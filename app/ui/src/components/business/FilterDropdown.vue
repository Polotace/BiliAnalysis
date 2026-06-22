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
  --el-fill-color-blank: var(--color-card);
  --el-text-color-regular: var(--color-text-secondary);
  --el-text-color-placeholder: var(--color-text-secondary);
}

.filter-select :deep(.el-input__wrapper) {
  height: 32px;
  padding: 4px 16px;
  box-shadow: none;
  font-size: 0.8125rem;
  font-weight: 500;
  border-radius: 20px;
  transition: border-color 0.15s, color 0.15s;
}

.filter-select :deep(.el-input__wrapper:hover) {
  border-color: var(--color-blue);
  box-shadow: none;
}

.filter-select :deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-blue);
  box-shadow: none;
}

.filter-select :deep(.el-input__inner) {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text-secondary);
}

/* When a value is selected, show blue style */
.filter-select :deep(.el-input__inner:not(:placeholder-shown)) {
  color: white;
}

.filter-select :deep(.el-select__caret) {
  font-size: 10px;
}
</style>
