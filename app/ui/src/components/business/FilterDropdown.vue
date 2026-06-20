<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  label: string
  options: { key: number; label: string; count?: number }[]
  modelValue: number | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
}>()

const open = ref(false)
const root = ref<HTMLElement | null>(null)

function select(key: number) {
  emit('update:modelValue', props.modelValue === key ? null : key)
  open.value = false
}

function clear() {
  emit('update:modelValue', null)
  open.value = false
}

function toggle() {
  open.value = !open.value
}

function onDocClick(e: MouseEvent) {
  if (root.value && !root.value.contains(e.target as Node)) {
    open.value = false
  }
}

onMounted(() => document.addEventListener('click', onDocClick))
onUnmounted(() => document.removeEventListener('click', onDocClick))
</script>

<template>
  <div ref="root" class="filter-dropdown relative">
    <button
      @click="toggle"
      class="flex items-center gap-1.5 px-3 py-1.5 border rounded-[20px] text-xs font-medium
             transition-colors duration-150 cursor-pointer"
      :class="modelValue !== null
        ? 'bg-blue text-white border-blue'
        : 'bg-card text-text-secondary border-border hover:border-blue hover:text-blue'"
    >
      <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 0 1-.659 1.591l-5.432 5.432a2.25 2.25 0 0 0-.659 1.591v2.927a2.25 2.25 0 0 1-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 0 0-.659-1.591L3.659 7.409A2.25 2.25 0 0 1 3 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0 1 12 3Z"/>
      </svg>
      {{ label }}
      <span v-if="modelValue !== null" class="tabular opacity-80">
        · {{ options.find(o => o.key === modelValue)?.label }}
      </span>
      <svg class="w-3 h-3 transition-transform" :class="{ 'rotate-180': open }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5"/>
      </svg>
    </button>

    <!-- Dropdown -->
    <div
      v-if="open"
      class="absolute top-full mt-2 left-0 bg-card rounded-[12px] shadow-[0_8px_32px_rgba(0,0,0,0.10)]
             border border-border p-2 min-w-44 max-h-72 overflow-y-auto z-50"
    >
      <button
        v-if="modelValue !== null"
        @click="clear"
        class="w-full text-left px-3 py-2 rounded-lg text-xs font-medium text-text-secondary
               hover:bg-border/40 transition-colors cursor-pointer bg-transparent border-0 mb-1"
      >
        ✕ 清除筛选
      </button>
      <button
        v-for="opt in options"
        :key="opt.key"
        @click="select(opt.key)"
        class="w-full text-left flex items-center justify-between px-3 py-2 rounded-lg text-xs
               transition-colors cursor-pointer bg-transparent border-0"
        :class="modelValue === opt.key
          ? 'bg-blue-light/60 text-blue font-semibold'
          : 'text-text-secondary hover:bg-border/40 hover:text-text'"
      >
        <span>{{ opt.label }}</span>
        <span v-if="opt.count !== undefined" class="tabular opacity-50">{{ opt.count }}</span>
      </button>
    </div>
  </div>
</template>
