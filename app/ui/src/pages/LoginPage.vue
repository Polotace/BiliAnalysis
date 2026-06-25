<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const username = ref('')
const password = ref('')
const error = ref('')
const submitting = ref(false)

async function doLogin() {
  error.value = ''
  submitting.value = true
  try {
    const r = await auth.login(username.value, password.value)
    await auth.fetchMe()
    if (r.must_change_password) router.replace('/change-password')
    else router.replace('/')
  } catch (e: any) {
    error.value = e.message || '登录失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-bg">
    <div class="bg-card rounded-[12px] shadow-[var(--shadow-default)] p-8 w-full max-w-sm">
      <h1 class="text-xl font-bold text-text mb-6 text-center">
        Bili<span class="text-blue">Insight</span>
      </h1>
      <form @submit.prevent="doLogin" class="space-y-4">
        <div>
          <label class="block text-sm text-text-secondary mb-1">用户名</label>
          <input v-model="username" type="text" required
                 class="w-full px-3 py-2 border border-border rounded-lg bg-bg text-text
                        focus:outline-none focus:ring-2 focus:ring-blue/30" />
        </div>
        <div>
          <label class="block text-sm text-text-secondary mb-1">密码</label>
          <input v-model="password" type="password" required
                 class="w-full px-3 py-2 border border-border rounded-lg bg-bg text-text
                        focus:outline-none focus:ring-2 focus:ring-blue/30" />
        </div>
        <div v-if="error" class="text-sm text-[#DC2626]">{{ error }}</div>
        <button type="submit" :disabled="submitting"
                class="w-full py-2 bg-blue text-white rounded-lg font-medium
                       hover:opacity-90 disabled:opacity-50 transition-opacity">
          {{ submitting ? '登录中…' : '登录' }}
        </button>
        <p class="text-xs text-text-secondary text-center mt-4">
          匿名用户可直接浏览数据看板
        </p>
      </form>
    </div>
  </div>
</template>
