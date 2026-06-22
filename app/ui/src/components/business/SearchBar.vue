<script setup lang="ts">
import { ref, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  modelValue: string
  placeholder?: string
}>(), { placeholder: '搜索…' })

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const input = ref(props.modelValue)
let timer: ReturnType<typeof setTimeout> | null = null

watch(input, (v) => {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => emit('update:modelValue', v), 300)
})
</script>

<template>
  <el-input
    v-model="input"
    :placeholder="placeholder"
    :prefix-icon="Search"
    clearable
    class="search-bar-input"
  />
</template>

<style scoped>
.search-bar-input {
  flex: 1;
  min-width: 260px;
  max-width: 400px;
  --el-input-border-radius: 12px;
  --el-input-border-color: var(--color-border);
  --el-input-bg-color: var(--color-card);
  --el-input-text-color: var(--color-text);
  --el-input-placeholder-color: var(--color-text-secondary);
  --el-input-hover-border-color: var(--color-blue);
  --el-input-focus-border-color: var(--color-blue);
  --el-input-clear-hover-color: var(--color-text-secondary);
}

.search-bar-input :deep(.el-input__wrapper) {
  height: 40px;
  padding-left: 40px;
  padding-right: 12px;
  box-shadow: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.search-bar-input :deep(.el-input__wrapper:hover) {
  box-shadow: none;
}

.search-bar-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 3px rgba(0, 174, 236, 0.1);
}

.search-bar-input :deep(.el-input__inner) {
  font-size: 0.9375rem;
}

.search-bar-input :deep(.el-input__prefix) {
  left: 14px;
}

.search-bar-input :deep(.el-input__prefix .el-icon) {
  font-size: 16px;
  color: var(--color-text-secondary);
}
</style>
