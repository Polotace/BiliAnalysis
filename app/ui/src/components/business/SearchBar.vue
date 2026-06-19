<script setup lang="ts">
import { ref, watch } from 'vue'

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
  <div class="relative flex-1 min-w-[260px] max-w-[400px]">
    <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary"
         xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
    </svg>
    <input
      v-model="input"
      :placeholder="placeholder"
      class="w-full h-10 pl-10 pr-4 border border-border rounded-[12px] text-[0.9375rem] text-text bg-card
             outline-none transition-colors duration-200
             focus:border-blue focus:shadow-[0_0_0_3px_rgba(0,174,236,0.1)]"
    />
  </div>
</template>
