import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  /** Incremented after reanalysis completes — pages watch this to refresh */
  const refreshKey = ref(0)

  function triggerRefresh() {
    refreshKey.value++
  }

  return { refreshKey, triggerRefresh }
})
