<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  label: string
  options: { key: number; label: string; count?: number }[]
  modelValue: number | null
}>()

const emit = defineEmits<{ 'update:modelValue': [value: number | null] }>()

const selectedLabel = computed(() => {
  if (props.modelValue === null) return props.label
  return props.options.find(o => o.key === props.modelValue)?.label ?? props.label
})
</script>

<template>
  <el-popover placement="bottom-start" :width="240" trigger="click">
    <div class="max-h-72 overflow-y-auto">
      <div class="px-3 py-2 border-b border-border text-xs text-text-secondary font-medium">
        {{ label }}
      </div>
      <div
        class="px-3 py-2 text-sm cursor-pointer transition-colors hover:bg-bg flex justify-between"
        :class="{ 'text-blue font-semibold': modelValue === null }"
        @click="emit('update:modelValue', null)"
      >
        <span>全部</span>
      </div>
      <div
        v-for="opt in options" :key="opt.key"
        class="px-3 py-2 text-sm cursor-pointer transition-colors hover:bg-bg flex justify-between"
        :class="{ 'text-blue font-semibold': modelValue === opt.key }"
        @click="emit('update:modelValue', opt.key)"
      >
        <span>{{ opt.label }}</span>
        <span v-if="opt.count !== undefined" class="text-text-secondary text-xs tabular">{{ opt.count }}</span>
      </div>
    </div>

    <template #reference>
      <button class="filter-btn" :class="{ 'filter-btn--active': modelValue !== null }">
        <span class="truncate max-w-28">{{ selectedLabel }}</span>
        <span class="filter-btn__arrow">▾</span>
      </button>
    </template>
  </el-popover>
</template>

<style scoped>
.filter-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 4px 16px;
  border-radius: 20px;
  border: 1px solid var(--color-border);
  background: var(--color-card);
  color: var(--color-text-secondary);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
  white-space: nowrap;
}
.filter-btn:hover {
  border-color: var(--color-blue);
  color: var(--color-blue);
}
.filter-btn--active {
  background: var(--color-blue);
  border-color: var(--color-blue);
  color: white;
}
.filter-btn--active:hover {
  background: var(--color-blue);
  color: white;
}
.filter-btn__arrow {
  font-size: 9px;
  transition: transform 0.15s;
}
</style>
