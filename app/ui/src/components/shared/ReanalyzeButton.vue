<script setup lang="ts">
import { computed, ref, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import { triggerTask, fetchRunStatus } from '@/composables/useApi'
import { useAuthStore } from '@/stores/auth'

const emit = defineEmits<{ done: [success: boolean] }>()

const route = useRoute()
const auth = useAuthStore()
const TASK_FOR_PATH: Record<string, string> = {
  '/analysis/stats': 'statistics',
  '/analysis/clusters': 'clustering',
  '/analysis/predictions': 'prediction',
  '/analysis/keywords': 'keywords',
  '/analysis/models': 'model_comparison',
}
const taskName = computed(() => TASK_FOR_PATH[route.path] ?? '')

// ── API Key state ──
const hasKey = computed(() => !!auth.apiKey)
const showPopover = ref(false)
const keyInput = ref('')

function togglePopover() {
  if (hasKey.value) { run(); return }
  showPopover.value = !showPopover.value
  if (showPopover.value) keyInput.value = ''
}

function saveKeyAndRun() {
  const v = keyInput.value.trim()
  if (!v) return
  auth.setKey(v)
  keyInput.value = ''
  showPopover.value = false
  run()
}

// ── Task execution ──
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
    const msg = e.message || e
    pollMsg.value = `✗ ${msg}`
    pollError.value = true
    phase.value = 'idle'
    // If auth error, open the popover so user can re-enter the API key
    if (/401|403|unauthor|auth|key|token|denied/i.test(String(msg))) {
      keyInput.value = auth.apiKey
      showPopover.value = true
    }
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

    <el-popover
      v-model:visible="showPopover"
      placement="bottom-start"
      :width="320"
      trigger="manual"
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
          @keyup.enter="saveKeyAndRun"
        />
        <el-button type="primary" :disabled="!keyInput.trim()" @click="saveKeyAndRun">
          保存并运行
        </el-button>
      </div>
      <el-button link type="info" class="mt-2 text-xs" @click="showPopover = false">
        取消
      </el-button>
    </el-popover>
  </div>
</template>
