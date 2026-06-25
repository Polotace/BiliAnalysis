import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<{ username: string; role: string; must_change_password: boolean } | null>(null)
  const loading = ref(true)

  const isLoggedIn = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const mustChangePassword = computed(() => user.value?.must_change_password ?? false)

  async function fetchMe() {
    try {
      const r = await fetch('/api/auth/me')
      const data = await r.json()
      if (data.logged_in) {
        user.value = {
          username: data.username,
          role: data.role,
          must_change_password: data.must_change_password,
        }
      } else {
        user.value = null
      }
    } catch {
      user.value = null
    } finally {
      loading.value = false
    }
  }

  async function login(username: string, password: string) {
    const r = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!r.ok) {
      const d = await r.json()
      throw new Error(d.detail ?? 'Login failed')
    }
    return r.json()
  }

  async function logout() {
    await fetch('/api/auth/logout', { method: 'POST' })
    user.value = null
  }

  async function changePassword(oldPassword: string, newPassword: string) {
    const r = await fetch('/api/auth/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    })
    if (!r.ok) {
      const d = await r.json()
      throw new Error(d.detail ?? 'Failed')
    }
    if (user.value) user.value.must_change_password = false
  }

  // API Key (backward compat)
  const apiKey = ref(localStorage.getItem('admin_api_key') ?? '')
  function setKey(key: string) { apiKey.value = key; localStorage.setItem('admin_api_key', key) }
  function clearKey() { apiKey.value = ''; localStorage.removeItem('admin_api_key') }

  return { user, loading, isLoggedIn, isAdmin, mustChangePassword,
           fetchMe, login, logout, changePassword, apiKey, setKey, clearKey }
})
