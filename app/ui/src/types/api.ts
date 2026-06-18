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
  fitted: Record<string, any>[]
  forecast: Record<string, any>[]
}

export interface PredictionReport {
  view_predict: PredictionResult
  like_predict: PredictionResult
  duration_seconds: number
}
