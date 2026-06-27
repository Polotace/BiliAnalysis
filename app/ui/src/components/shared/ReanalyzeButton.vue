<script setup lang="ts">
import { computed, ref, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import { triggerTask, fetchRunStatus } from '@/composables/useApi'

const emit = defineEmits<{ done: [success: boolean] }>()

const route = useRoute()
const TASK_FOR_PATH: Record<string, string> = {
  '/analysis/stats': 'statistics',
  '/analysis/clusters': 'clustering',
  '/analysis/predictions': 'prediction',
  '/analysis/keywords': 'keywords',
  '/analysis/models': 'model_comparison',
}
const taskName = computed(() => TASK_FOR_PATH[route.path] ?? '')

const phase = ref<'idle' | 'running' | 'polling'>('idle')
const pollMsg = ref('')
const pollError = ref(false)
let currentRunId = ''
let pollTimer: ReturnType<typeof setInterval> | null = null

async function run() {
  if (phase.value !== 'idle' || !taskName.value) return
  phase.value = 'running'
  pollMsg.value = ''
  pollError.value = false
  try {
    const r: any = await triggerTask(taskName.value)
    currentRunId = r?.run_id ?? ''
    phase.value = 'polling'
    pollMsg.value = '分析中…'
    startPolling()
  } catch (e: any) {
    pollMsg.value = `✗ ${e.message || e}`
    pollError.value = true
    phase.value = 'idle'
  }
}

function startPolling() {
  if (!currentRunId) return
  pollTimer = setInterval(async () => {
    try {
      const record = await fetchRunStatus(currentRunId)
      if (!record) return
      if (record.status === 'success') {
        stopPolling()
        pollMsg.value = '✓ 完成'
        phase.value = 'idle'
        emit('done', true)
        setTimeout(() => { pollMsg.value = '' }, 3000)
      } else if (record.status === 'failed') {
        stopPolling()
        pollMsg.value = '✗ 失败'
        pollError.value = true
        phase.value = 'idle'
        emit('done', false)
      }
    } catch {
      // Network error during poll — keep trying
    }
  }, 5000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onUnmounted(() => stopPolling())
</script>

<template>
  <div v-if="taskName" class="inline-flex items-center gap-2">
    <span
      v-if="pollMsg"
      class="text-xs font-medium"
      :class="pollError ? 'text-danger' : phase === 'polling' ? 'text-blue' : 'text-success'"
    >{{ pollMsg }}</span>

    <el-button
      @click="run"
      :disabled="phase !== 'idle'"
      :loading="phase !== 'idle'"
      size="small"
      text
    >
      <el-icon v-if="phase === 'idle'" class="!w-3.5 !h-3.5"><Refresh /></el-icon>
      {{ phase === 'polling' ? '分析中…' : '重新分析' }}
    </el-button>
  </div>
</template>
