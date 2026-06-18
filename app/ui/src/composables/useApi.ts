import { createAlova } from 'alova'
import adapterFetch from 'alova/fetch'
import vueHook from 'alova/vue'
import { useRequest } from 'alova/client'
import type { StatReport, ClusterReport, PredictionReport } from '@/types/api'

const alova = createAlova({
  baseURL: '/api',
  statesHook: vueHook,
  requestAdapter: adapterFetch(),
  responded: {
    onSuccess: async (response) => {
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(
          (body as { detail?: string }).detail ?? `HTTP ${response.status}`,
        )
      }
      return response.json()
    },
  },
})

// ── Typed request functions ──

export function fetchStats() {
  return alova.Get<StatReport>('/analysis/stats')
}

export function fetchClusters() {
  return alova.Get<ClusterReport>('/analysis/clusters')
}

export function fetchPredictions() {
  return alova.Get<PredictionReport>('/analysis/predictions')
}

// ── Composables (per-page usage) ──

export function useStats() {
  return useRequest(fetchStats, { immediate: false })
}

export function useClusters() {
  return useRequest(fetchClusters, { immediate: false })
}

export function usePredictions() {
  return useRequest(fetchPredictions, { immediate: false })
}
