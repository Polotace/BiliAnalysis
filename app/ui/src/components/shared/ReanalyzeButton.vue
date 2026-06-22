<script setup lang="ts">
import { computed, ref, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import { triggerTask, fetchPipelineHistory } from '@/composables/useApi'

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

const hasKey = ref(!!localStorage.getItem('admin_api_key'))
const showPopover = ref(false)
const keyInput = ref('')

function togglePopover() {
  if (hasKey.value) { run(); return }
  showPopover.value = !showPopover.value
}

function saveKey() {
  const v = keyInput.value.trim()
  if (!v) return
  localStorage.setItem('admin_api_key', v)
  hasKey.value = true
  keyInput.value = ''
  showPopover.value = false
}

const phase = ref<'idle' | 'running' | 'polling'>('idle')
const pollMsg = ref('')
const pollError = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

async function run() {
  if (phase.value !== 'idle' || !taskName.value) return
  phase.value = 'running'
  pollMsg.value = ''
  pollError.value = false
  try {
    await triggerTask(taskName.value)
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
  pollTimer = setInterval(async () => {
    try {
      const history = await fetchPipelineHistory(`_task_${taskName.value}`, 1)
      if (history && history.length > 0) {
        const latest = history[0]
        if (latest.status === 'success') {
          stopPolling()
          pollMsg.value = '✓ 完成'
          phase.value = 'idle'
          emit('done', true)
          setTimeout(() => { pollMsg.value = '' }, 3000)
        } else if (latest.status === 'failed') {
          stopPolling()
          pollMsg.value = '✗ 失败'
          pollError.value = true
          phase.value = 'idle'
          emit('done', false)
        }
      }
    } catch {
      // Network error during poll — keep trying
    }
  }, 2000)
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

    <el-popover
      v-model:visible="showPopover"
      placement="bottom-end"
      :width="288"
      trigger="click"
      :disabled="hasKey"
    >
      <template #reference>
        <el-button
          @click="togglePopover"
          :disabled="phase !== 'idle'"
          :loading="phase !== 'idle'"
          size="small"
          text
        >
          <el-icon v-if="phase === 'idle'" class="!w-3.5 !h-3.5"><Refresh /></el-icon>
          {{ phase === 'polling' ? '分析中…' : '重新分析' }}
        </el-button>
      </template>

      <p class="text-xs text-text-secondary mb-3">
        输入管理员 API Key。Key 在启动服务时自动生成并打印在控制台。
      </p>
      <div class="flex gap-2">
        <el-input
          v-model="keyInput"
          type="password"
          placeholder="粘贴 API Key…"
          @keyup.enter="saveKey"
        />
        <el-button type="primary" :disabled="!keyInput.trim()" @click="saveKey">
          保存
        </el-button>
      </div>
      <el-button link type="info" class="mt-2 text-xs" @click="showPopover = false">
        取消
      </el-button>
    </el-popover>
  </div>
</template>
