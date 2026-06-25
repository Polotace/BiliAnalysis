<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const error = ref('')
const submitting = ref(false)

async function doChange() {
  error.value = ''
  if (newPassword.value !== confirmPassword.value) {
    error.value = '两次输入的新密码不一致'
    return
  }
  if (newPassword.value.length < 4) {
    error.value = '密码长度至少 4 位'
    return
  }
  submitting.value = true
  try {
    await auth.changePassword(oldPassword.value, newPassword.value)
    router.replace('/')
  } catch (e: any) {
    error.value = e.message || '修改失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-bg">
    <div class="bg-card rounded-[12px] shadow-[var(--shadow-default)] p-8 w-full max-w-sm">
      <h1 class="text-xl font-bold text-text mb-2 text-center">修改密码</h1>
      <p class="text-sm text-text-secondary text-center mb-6">首次登录，请设置新密码</p>
      <form @submit.prevent="doChange" class="space-y-4">
        <div>
          <label class="block text-sm text-text-secondary mb-1">原密码</label>
          <input v-model="oldPassword" type="password" required
                 class="w-full px-3 py-2 border border-border rounded-lg bg-bg text-text
                        focus:outline-none focus:ring-2 focus:ring-blue/30" />
        </div>
        <div>
          <label class="block text-sm text-text-secondary mb-1">新密码</label>
          <input v-model="newPassword" type="password" required
                 class="w-full px-3 py-2 border border-border rounded-lg bg-bg text-text
                        focus:outline-none focus:ring-2 focus:ring-blue/30" />
        </div>
        <div>
          <label class="block text-sm text-text-secondary mb-1">确认新密码</label>
          <input v-model="confirmPassword" type="password" required
                 class="w-full px-3 py-2 border border-border rounded-lg bg-bg text-text
                        focus:outline-none focus:ring-2 focus:ring-blue/30" />
        </div>
        <div v-if="error" class="text-sm text-[#DC2626]">{{ error }}</div>
        <button type="submit" :disabled="submitting"
                class="w-full py-2 bg-blue text-white rounded-lg font-medium
                       hover:opacity-90 disabled:opacity-50 transition-opacity">
          {{ submitting ? '提交中…' : '确认修改' }}
        </button>
      </form>
    </div>
  </div>
</template>
