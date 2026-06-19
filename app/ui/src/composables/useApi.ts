import { createAlova } from 'alova'
import adapterFetch from 'alova/fetch'
import vueHook from 'alova/vue'
import { useRequest } from 'alova/client'
import type {
  StatReport, ClusterReport, PredictionReport,
  VideoSummary, VideoDetail, PaginatedVideos,
  WeekItem, WeekDetail,
  CreatorSummary, CreatorDetail, PaginatedCreators,
  CategorySummary,
} from '@/types/api'

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

// ── Videos ──

export function fetchVideos(params?: Record<string, any>) {
  return alova.Get<PaginatedVideos>('/videos', { params: params ?? {} })
}
export function fetchVideo(aid: number) {
  return alova.Get<VideoDetail>(`/videos/${aid}`)
}

// ── Weeks ──

export function fetchWeeks() {
  return alova.Get<WeekItem[]>('/weeks')
}
export function fetchWeek(number: number) {
  return alova.Get<WeekDetail>(`/weeks/${number}`)
}

// ── Creators ──

export function fetchCreators(params?: Record<string, any>) {
  return alova.Get<PaginatedCreators>('/creators', { params: params ?? {} })
}
export function fetchCreator(mid: number) {
  return alova.Get<CreatorDetail>(`/creators/${mid}`)
}

// ── Categories ──

export function fetchCategories() {
  return alova.Get<CategorySummary[]>('/categories')
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

export function useVideos(params?: Record<string, any>) {
  return useRequest(() => fetchVideos(params), { immediate: false })
}

export function useVideo(aid: number) {
  return useRequest(() => fetchVideo(aid), { immediate: false })
}

export function useWeeksList() {
  return useRequest(fetchWeeks, { immediate: false })
}

export function useWeekDetail(number: number) {
  return useRequest(() => fetchWeek(number), { immediate: false })
}

export function useCreatorsList(params?: Record<string, any>) {
  return useRequest(() => fetchCreators(params), { immediate: false })
}

export function useCreatorDetail(mid: number) {
  return useRequest(() => fetchCreator(mid), { immediate: false })
}

export function useCategoriesList() {
  return useRequest(fetchCategories, { immediate: false })
}
