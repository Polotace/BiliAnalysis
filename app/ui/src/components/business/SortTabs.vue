<script setup lang="ts">
defineProps<{
  options: { key: string; label: string }[]
  modelValue: string
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <div class="flex gap-2 flex-wrap">
    <button
      v-for="opt in options"
      :key="opt.key"
      @click="emit('update:modelValue', opt.key)"
      class="px-4 py-1.5 border border-border rounded-[20px] text-[0.8125rem] font-medium
             transition-colors duration-150 cursor-pointer
             hover:border-blue hover:text-blue"
      :class="modelValue === opt.key
        ? 'bg-blue text-white border-blue'
        : 'bg-card text-text-secondary'"
    >
      {{ opt.label }}
    </button>
  </div>
</template>
