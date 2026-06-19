// ── Statistics ──

export interface OverallStats {
  total_videos: number
  total_creators: number
  avg_view: number
  avg_like: number
  avg_coin: number
  avg_favorite: number
  avg_share: number
  avg_danmaku: number
  avg_like_rate: number
  avg_coin_rate: number
  avg_favorite_rate: number
}

export interface CategoryStats {
  tname: string
  video_count: number
  avg_view: number
  avg_like: number
  avg_interaction_rate: number
}

export interface CreatorStats {
  mid: number
  name: string
  appearance_count: number
  total_view: number
  total_like: number
  total_favorite: number
}

export interface WeeklyTrend {
  week_number: number
  video_count: number
  avg_view: number
  avg_like: number
  avg_interaction_rate: number
}

export interface StatReport {
  overall: OverallStats
  by_category: CategoryStats[]
  by_creator: CreatorStats[]
  by_week: WeeklyTrend[]
}

// ── Clustering ──

export interface ClusterGroup {
  label: number
  tag: string
  count: number
  centroid: Record<string, number>
  avg_view: number
  avg_like: number
  avg_coin: number
  avg_favorite: number
  sample_ids: number[]
}

export interface ClusterResult {
  k: number
  clusters: ClusterGroup[]
  silhouette_score: number
  feature_importance: Record<string, number>
}

export interface ClusterReport {
  clusters: ClusterResult
  scatter_data: Record<string, any>
  duration_seconds: number
}

// ── Prediction ──

export interface PredictionResult {
  model_type: string
  target: string
  r2_score: number
  mae: number
  coefficients: Record<string, number>
  intercept: number
  fitted: { week_number: number; actual: number; predicted: number }[]
  forecast: { week_number: number; predicted: number }[]
}

export interface PredictionReport {
  view_predict: PredictionResult
  like_predict: PredictionResult
  duration_seconds: number
}

// ── Videos (browse) ──

export interface VideoSummary {
  aid: number
  bvid: string
  title: string
  cover_url: string | null
  duration: number
  pubdate: string
  creator_name: string | null
  category_name: string | null
  view: number
  like_cnt: number
}

export interface VideoDetail {
  aid: number
  bvid: string
  title: string
  description: string | null
  duration: number
  pubdate: string
  cid: number
  video_url: string | null
  cover_url: string | null
  copyright: number
  creator_mid: number
  creator_name: string | null
  creator_face: string | null
  category_tid: number
  category_name: string | null
  category_v2_name: string | null
  view: number
  like_cnt: number
  coin: number
  favorite: number
  share: number
  reply: number
  danmaku: number
  appeared_weeks: number[]
}

export interface PaginatedVideos {
  videos: VideoSummary[]
  total: number
  page: number
  page_size: number
}

// ── Weeks (browse) ──

export interface WeekItem {
  number: number
  subject: string | null
  name: string | null
  label: string | null
  cover: string | null
  start_time: string | null
  end_time: string | null
  video_count: number
}

export interface WeekDetail {
  number: number
  subject: string | null
  name: string | null
  label: string | null
  cover: string | null
  start_time: string | null
  end_time: string | null
  videos: VideoSummary[]
}

// ── Creators (browse) ──

export interface CreatorSummary {
  mid: number
  name: string
  face: string | null
  video_count: number
  total_views: number
}

export interface CreatorDetail {
  mid: number
  name: string
  face: string | null
  video_count: number
  total_views: number
  total_likes: number
  total_coins: number
  total_favorites: number
  videos: VideoSummary[]
}

export interface PaginatedCreators {
  creators: CreatorSummary[]
  total: number
  page: number
  page_size: number
}

// ── Categories (browse) ──

export interface CategorySummary {
  tid: number
  tname: string | null
  tid_v2: number | null
  tname_v2: string | null
  pid_v2: number | null
  pid_name_v2: string | null
  video_count: number
}

// ── Admin ──

export interface CrawlerStatus {
  total_weeks: number
  crawled: number
  failed: Record<number, string>
  last_run: string | null
  is_running: boolean
}

export interface TaskTriggerResponse {
  run_id: string
  pipeline: string
  status: string
}

export interface PipelineInfo {
  name: string
  schedule: string
  steps: string[]
  step_failure: string
}

export interface PipelineListResponse {
  pipelines: PipelineInfo[]
}

export interface RunHistoryItem {
  run_id: string
  pipeline: string
  trigger: string
  started_at: string
  finished_at: string | null
  status: string
  step_count: number
  failed_step: string | null
}

export interface AnalysisOverview {
  last_clean: Record<string, any> | null
  last_stats: Record<string, any> | null
  last_cluster: Record<string, any> | null
  last_prediction: Record<string, any> | null
}

export interface AppConfigData {
  crawler: Record<string, any>
  analysis: Record<string, any>
  data: Record<string, any>
  scheduler: Record<string, any>
}
