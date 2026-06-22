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
}
</style>
