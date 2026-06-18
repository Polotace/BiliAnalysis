# BiliInsight Frontend Design Spec

**Date**: 2026-06-18  
**Status**: Approved  
**Design mockups**: `design-demos/homepage-v1.html`, `stats-v1.html`, `cluster-v1.html`, `predict-v1.html`

---

## 1. Overview

Build the Vue3 frontend for BiliInsight — a content discovery and trend insight platform based on Bilibili's "每周必看" data. The frontend lives at `app/ui/` alongside the existing `app/api/` and `app/cli/`.

**Product identity**: Content discovery platform, NOT an admin dashboard. Users browse content first, see data second, charts last. Priority: 内容 > 数据 > 图表.

**MVP scope**: HomePage + 3 analysis sub-pages (Stats / Clusters / Predictions). Video library and detail pages deferred until video-level API endpoints are built.

---

## 2. Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Framework | Vue 3 (Composition API, `<script setup>`) | Project requirement |
| Language | TypeScript | Project requirement |
| Build | Vite | Fast dev server, HMR, proxy to FastAPI |
| CSS | Tailwind CSS v4 | Maps directly to design tokens (8px grid, colors, radii) |
| Component library | Element Plus (按需引入) | Complex interactive components only (select, dialog, skeleton). Visual layer controlled by Tailwind, not ElPlus defaults. |
| HTTP client | Alova | Project requirement, lighter than axios |
| Charts | ECharts 5 | Project requirement |
| Router | Vue Router 4 | SPA routing |

**Why Tailwind + ElPlus, not pure ElPlus**: Element Plus's default visual language is admin-dashboard — left sidebar menus, dense tables, heavy borders. The design spec explicitly forbids this. Tailwind controls the visual layer so every pixel matches the spec; ElPlus provides battle-tested complex components (select dropdowns, modals, skeleton loaders) with their default styles overridden where needed.

---

## 3. Directory Structure

```
app/ui/
├── index.html
├── package.json
├── vite.config.ts              # proxy /api → localhost:8000
├── tailwind.config.ts
├── tsconfig.json
├── src/
│   ├── main.ts                 # createApp, router, global styles
│   ├── App.vue                 # <TopNav> + <router-view>
│   ├── styles/
│   │   └── theme.css           # Tailwind base + CSS variables
│   ├── router/
│   │   └── index.ts            # route definitions
│   ├── pages/
│   │   ├── HomePage.vue
│   │   └── analysis/
│   │       ├── StatsPage.vue
│   │       ├── ClusterPage.vue
│   │       └── PredictPage.vue
│   ├── components/
│   │   ├── layout/
│   │   │   ├── TopNav.vue
│   │   │   └── PageShell.vue   # max-width:1280px centered container
│   │   ├── home/
│   │   │   ├── HeroSection.vue
│   │   │   ├── KpiCardRow.vue
│   │   │   ├── CategoryBar.vue
│   │   │   ├── CreatorTopList.vue
│   │   │   └── TrendMiniChart.vue
│   │   ├── analysis/
│   │   │   ├── SubNavTabs.vue
│   │   │   ├── CategoryPanel.vue
│   │   │   ├── CreatorTable.vue
│   │   │   ├── ClusterCards.vue
│   │   │   ├── FeatureImportance.vue
│   │   │   └── ForecastCards.vue
│   │   ├── charts/
│   │   │   ├── TrendLineChart.vue
│   │   │   ├── CategoryBarChart.vue
│   │   │   ├── ClusterScatter.vue
│   │   │   └── FitLineChart.vue
│   │   └── shared/
│   │       ├── StatCard.vue
│   │       └── SectionHeader.vue
│   ├── composables/
│   │   ├── useApi.ts           # Alova instance + typed request functions
│   │   └── useChart.ts         # ECharts init/resize/dispose lifecycle
│   └── types/
│       └── api.ts              # TypeScript types mirroring backend Pydantic schemas
```

---

## 4. Visual Design Tokens

All values extracted from `docs/BiliAnalysis UI Design Specification v1.0.docx`.

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| Primary (Bilibili Blue) | `#00AEEC` | Links, active states, chart lines, accent elements |
| Page background | `#FAFAFA` | `<body>` background |
| Card background | `#FFFFFF` | All cards and panels |
| Main text | `#111827` | Headings, body text |
| Secondary text | `#6B7280` | Labels, descriptions, metadata |
| Border | `#E5E7EB` | Dividers, card borders |
| Success | `#22C55E` | Positive metrics, R² scores |
| Warning | `#F59E0B` | Medium scores, cluster popular |
| Danger | `#EF4444` | Cluster burst, negative coefficients |

### Typography

```css
font-family: 'Inter', 'HarmonyOS Sans SC', 'PingFang SC', sans-serif;
font-variant-numeric: tabular-nums;  /* all numbers */
```

### Spacing (8px grid)

`8 / 16 / 24 / 32 / 48 / 64 / 80 / 96`

### Border radius

- Default cards: `12px`
- Large cards (Hero, panels): `16px`

### Shadows

- Default: `0 2px 8px rgba(0,0,0,0.05)`
- Hover: `0 4px 16px rgba(0,0,0,0.08)`
- **No heavy shadows** (spec section 4.3)

### Page width

- Max: `1440px` (absolute cap)
- Recommended content width: `1280px` (centered)

### Animation

- Duration: `150ms ~ 250ms`
- Allowed: fade, scale, slide
- Forbidden: bounce, rotate, particles, cyberpunk effects

---

## 5. Routes

| Path | Page | Component | Data Source |
|------|------|-----------|-------------|
| `/` | HomePage | `HomePage.vue` | `GET /api/analysis/stats` |
| `/analysis/stats` | StatsPage | `StatsPage.vue` | `GET /api/analysis/stats` |
| `/analysis/clusters` | ClusterPage | `ClusterPage.vue` | `GET /api/analysis/clusters` |
| `/analysis/predictions` | PredictPage | `PredictPage.vue` | `GET /api/analysis/predictions` |

**Navigation**: `TopNav` has two items — "发现" (→ `/`) and "分析" (→ `/analysis/stats`). Analysis sub-pages use `SubNavTabs` (统计概览 / 聚类分析 / 预测分析) with local tab switching.

**Scroll behavior**: `scrollBehavior` returns `{ top: 0 }` for all navigations.

---

## 6. Component Tree & Data Flow

### 6.1 HomePage

```
HomePage.vue  ← GET /api/analysis/stats → StatReport
├── TopNav.vue (sticky, present on all pages via App.vue)
├── HeroSection.vue (static content, no API data needed)
├── KpiCardRow.vue
│   └── StatCard.vue ×4
│       Props: label, value, subLabel
│       Data: StatReport.overall.total_videos, .avg_view, .avg_like, .total_creators
├── CategoryBar.vue
│   Props: categories: CategoryStats[]
│   Data: StatReport.by_category (top 5)
├── CreatorTopList.vue
│   Props: creators: CreatorStats[]
│   Data: StatReport.by_creator (top 5)
└── TrendMiniChart.vue
    Props: weeks: WeeklyTrend[]
    Data: StatReport.by_week (last 10)
```

### 6.2 StatsPage

```
StatsPage.vue  ← GET /api/analysis/stats → StatReport
├── SubNavTabs.vue (统计概览 active)
├── StatCard.vue ×3 (total_videos, total_creators, avg_like_rate)
├── TrendLineChart.vue (ECharts)
│   Props: weeks: WeeklyTrend[]
│   Data: StatReport.by_week → 3-line chart (view, like, interaction rate)
├── CategoryPanel.vue
│   Props: categories: CategoryStats[]
│   Data: StatReport.by_category → horizontal bar chart
└── CreatorTable.vue
    Props: creators: CreatorStats[]
    Data: StatReport.by_creator → top 10 table
```

### 6.3 ClusterPage

```
ClusterPage.vue  ← GET /api/analysis/clusters → ClusterReport
├── SubNavTabs.vue (聚类分析 active)
├── SilhouetteScore.vue
│   Data: ClusterReport.clusters.silhouette_score
├── FeatureImportance.vue
│   Data: ClusterReport.clusters.feature_importance
├── ClusterCards.vue
│   └── ClusterCard.vue ×3
│       Props: cluster: ClusterGroup
│       Data: ClusterReport.clusters.clusters[]
└── ClusterScatter.vue (ECharts)
    Data: ClusterReport.scatter_data
```

### 6.4 PredictPage

```
PredictPage.vue  ← GET /api/analysis/predictions → PredictionReport
├── SubNavTabs.vue (预测分析 active)
├── ModelScoreCard.vue ×2 (view R², like R²)
│   Data: PredictionReport.view_predict / .like_predict (.r2_score, .mae)
├── CoefficientsTable.vue
│   Data: PredictionReport.view_predict.coefficients + .intercept
├── ForecastCards.vue
│   Data: PredictionReport.view_predict.forecast[] (last 3)
└── FitLineChart.vue (ECharts)
    Data: PredictionReport.view_predict.fitted[] + .forecast[]
```

---

## 7. State Management

**No Pinia needed for MVP**. Each page fetches its own data via Alova on mount. No cross-page shared state.

### State per page

Every page follows the same pattern:

```typescript
const { loading, data, error, send } = useRequest(() => api.getStats())
onMounted(() => send())
```

Three states handled in template:
- **Loading**: `<el-skeleton>` with card-shaped placeholders matching the layout
- **Error**: Simple error panel with retry button — "加载失败，请重试"
- **Empty** (no data yet): "暂无数据，请先触发一次数据采集与分析"

---

## 8. API Integration

### Alova instance

```typescript
// composables/useApi.ts
const alova = createAlova({
  baseURL: '/api',
  statesHook: VueHook,
  requestAdapter: GlobalFetch(),
  responded: {
    onSuccess: async (response) => response.json(),
  }
})
```

### Typed request functions

```typescript
export const api = {
  getStats:       () => alova.Get<StatReport>('/analysis/stats'),
  getClusters:    () => alova.Get<ClusterReport>('/analysis/clusters'),
  getPredictions: () => alova.Get<PredictionReport>('/analysis/predictions'),
}
```

### Vite proxy

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: { '/api': 'http://localhost:8000' }
  }
})
```

### TypeScript types (`types/api.ts`)

Mirror the backend Pydantic schemas:

```typescript
interface OverallStats {
  total_videos: number; total_creators: number;
  avg_view: number; avg_like: number; avg_coin: number;
  avg_favorite: number; avg_share: number; avg_danmaku: number;
  avg_like_rate: number; avg_coin_rate: number; avg_favorite_rate: number;
}
interface CategoryStats { tname: string; video_count: number; avg_view: number; avg_like: number; avg_interaction_rate: number; }
interface CreatorStats { mid: number; name: string; appearance_count: number; total_view: number; total_like: number; total_favorite: number; }
interface WeeklyTrend { week_number: number; video_count: number; avg_view: number; avg_like: number; avg_interaction_rate: number; }
interface StatReport { overall: OverallStats; by_category: CategoryStats[]; by_creator: CreatorStats[]; by_week: WeeklyTrend[]; }

interface ClusterGroup { label: number; tag: string; count: number; centroid: Record<string,number>; avg_view: number; avg_like: number; avg_coin: number; avg_favorite: number; sample_ids: number[]; }
interface ClusterResult { k: number; clusters: ClusterGroup[]; silhouette_score: number; feature_importance: Record<string,number>; }
interface ClusterReport { clusters: ClusterResult; scatter_data: Record<string,any>; duration_seconds: number; }

interface PredictionResult { model_type: string; target: string; r2_score: number; mae: number; coefficients: Record<string,number>; intercept: number; fitted: Record<string,any>[]; forecast: Record<string,any>[]; }
interface PredictionReport { view_predict: PredictionResult; like_predict: PredictionResult; duration_seconds: number; }
```

---

## 9. Forbidden Patterns (from UI spec §3)

The following MUST NOT appear in any page or component:

- ❌ Left sidebar menu layout
- ❌ Element Plus / Ant Design default admin layouts
- ❌ Menu items named "首页 用户管理 角色管理 系统管理"
- ❌ Dark-blue big-screen style (DataV / 智慧城市 / 工业监控)
- ❌ Sci-fi borders, glowing lines, digital number scroll animations
- ❌ Pages that are only: search form + table + pagination
- ❌ 3D charts, flashy animated charts, complex dashboards
- ❌ Heavy box-shadows
- ❌ High-saturation gradient backgrounds
- ❌ Bounce / rotate / particle animations

---

## 10. ECharts Chart Specifications

| Chart | Type | Config Notes |
|-------|------|-------------|
| TrendLineChart | `line` | 3 series (view/like/interaction), smooth:false, tooltip cross, legend bottom |
| CategoryBarChart | `bar` | Horizontal, sorted desc, single series, show value labels |
| ClusterScatter | `scatter` | 3 color groups by cluster label, star markers for centroids, x=view y=like |
| FitLineChart | `line` | 2 series (actual solid, fitted dashed), vertical split line at train/test boundary |

All charts: `animation: true`, `animationDuration: 300`, no 3D, no `gl` extensions.

---

## 11. Testing Strategy

| Layer | Tool | Scope |
|-------|------|-------|
| Component rendering | Vitest + Vue Test Utils | Each component renders with props, emits events correctly |
| API composable | Vitest + Alova mock | useApi returns typed data, handles loading/error states |
| ECharts wrapper | Vitest | useChart inits/disposes without leaks |
| Visual regression | Playwright screenshot | Compare against `design-demos/*.png` baselines |
| Integration | Playwright | Navigate between pages, verify API calls, check tab switching |

---

## 12. Scope & Deferred Items

### In scope (MVP)
- HomePage with KPI overview, category bar, creator list, trend mini-chart
- StatsPage with full trend line chart, category panel, creator table
- ClusterPage with silhouette score, cluster cards, scatter plot
- PredictPage with R² scores, coefficients, forecast, fit chart
- TopNav + SubNavTabs navigation
- Loading / error / empty states for all pages

### Deferred (requires backend work first)
- Video library page (`GET /api/videos` endpoint needed)
- Video detail page (`GET /api/videos/{aid}` endpoint needed)
- Weekly browsing page (`GET /api/weeks` endpoint needed)
- Dark/light theme toggle (sticking with light theme per design spec §5)

### NOT in scope
- User authentication / login
- Real-time data streaming / WebSocket
- Mobile responsive (desktop-first, 1280px optimized)
- i18n (Chinese only)
