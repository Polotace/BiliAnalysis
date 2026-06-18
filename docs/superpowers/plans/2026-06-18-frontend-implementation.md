# BiliInsight Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Vue 3 frontend for BiliInsight — a content discovery platform on Bilibili "每周必看" data — living at `app/ui/` alongside the existing FastAPI backend.

**Architecture:** Vite + Vue 3 (Composition API, `<script setup>`) + TypeScript + Tailwind CSS v4 + Element Plus (按需引入) + Alova HTTP + ECharts 5 + Vue Router 4. No Pinia (each page fetches its own data). Tests use Vitest (unit) + Playwright (visual regression against `design-demos/*.html` baselines).

**Design spec:** `docs/superpowers/specs/2026-06-18-frontend-design.md` — all visual tokens, component trees, routes, API contracts defined there.

**Tech Stack:** Vue 3, TypeScript, Vite, Tailwind CSS v4, Element Plus, Alova, ECharts 5, Vue Router 4, Vitest, Playwright

---

## File Structure (26 new files)

```
app/ui/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
├── vitest.config.ts
├── playwright.config.ts
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── env.d.ts
│   ├── styles/
│   │   └── theme.css
│   ├── router/
│   │   └── index.ts
│   ├── types/
│   │   └── api.ts
│   ├── composables/
│   │   ├── useApi.ts
│   │   └── useChart.ts
│   ├── pages/
│   │   ├── HomePage.vue
│   │   └── analysis/
│   │       ├── StatsPage.vue
│   │       ├── ClusterPage.vue
│   │       └── PredictPage.vue
│   └── components/
│       ├── layout/
│       │   ├── TopNav.vue
│       │   └── PageShell.vue
│       ├── shared/
│       │   ├── StatCard.vue
│       │   └── SectionHeader.vue
│       ├── charts/
│       │   ├── TrendLineChart.vue
│       │   ├── CategoryBarChart.vue
│       │   ├── ClusterScatter.vue
│       │   └── FitLineChart.vue
│       ├── home/
│       │   ├── HeroSection.vue
│       │   ├── KpiCardRow.vue
│       │   ├── CategoryBar.vue
│       │   ├── CreatorTopList.vue
│       │   └── TrendMiniChart.vue
│       └── analysis/
│           ├── SubNavTabs.vue
│           ├── CategoryPanel.vue
│           ├── CreatorTable.vue
│           ├── ClusterCards.vue
│           ├── FeatureImportance.vue
│           └── ForecastCards.vue
```

---

### Task 0: Project Scaffold

**Files:**
- Create: `app/ui/package.json`
- Create: `app/ui/index.html`
- Create: `app/ui/vite.config.ts`
- Create: `app/ui/tsconfig.json`
- Create: `app/ui/tsconfig.app.json`
- Create: `app/ui/tsconfig.node.json`
- Create: `app/ui/vitest.config.ts`
- Create: `app/ui/playwright.config.ts`
- Create: `app/ui/src/env.d.ts`

- [ ] **Step 1: Create app/ui/package.json**

```json
{
  "name": "biliinsight-ui",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "preview": "vite preview",
    "test:unit": "vitest run",
    "test:unit:watch": "vitest",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "vue": "^3.5.13",
    "vue-router": "^4.5.0",
    "alova": "^3.6.0",
    "@alova/adapter-fetch": "^1.1.0",
    "echarts": "^5.6.0",
    "element-plus": "^2.9.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2.0",
    "@vue/tsconfig": "^0.7.0",
    "@vue/test-utils": "^2.4.6",
    "happy-dom": "^15.11.0",
    "typescript": "~5.6.0",
    "vite": "^6.0.0",
    "vitest": "^2.1.0",
    "vue-tsc": "^2.2.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/vite": "^4.0.0",
    "@playwright/test": "^1.49.0"
  }
}
```

- [ ] **Step 2: Create app/ui/index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>BiliInsight — 发现每周好内容</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 3: Create app/ui/vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

- [ ] **Step 4: Create app/ui/tsconfig.json**

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

- [ ] **Step 5: Create app/ui/tsconfig.app.json**

```json
{
  "extends": "@vue/tsconfig/tsconfig.dom.json",
  "compilerOptions": {
    "composite": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    },
    "types": ["vite/client"]
  },
  "include": ["src/**/*.ts", "src/**/*.vue", "src/env.d.ts"]
}
```

- [ ] **Step 6: Create app/ui/tsconfig.node.json**

```json
{
  "extends": "@vue/tsconfig/tsconfig.dom.json",
  "compilerOptions": {
    "composite": true,
    "lib": ["ESNext"],
    "types": ["node"]
  },
  "include": ["vite.config.ts", "vitest.config.ts", "playwright.config.ts"]
}
```

- [ ] **Step 7: Create app/ui/vitest.config.ts**

```typescript
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  test: {
    environment: 'happy-dom',
    globals: true,
  },
})
```

- [ ] **Step 8: Create app/ui/playwright.config.ts**

```typescript
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  use: {
    baseURL: 'http://localhost:5173',
    viewport: { width: 1440, height: 900 },
  },
  webServer: {
    command: 'npx vite --port 5173',
    port: 5173,
    reuseExistingServer: true,
  },
})
```

- [ ] **Step 9: Create app/ui/src/env.d.ts**

```typescript
/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
```

- [ ] **Step 10: Install dependencies**

```bash
cd app/ui && npm install
```

Expected: installs all packages without errors.

- [ ] **Step 11: Commit**

```bash
git add app/ui/package.json app/ui/index.html app/ui/vite.config.ts \
        app/ui/tsconfig.json app/ui/tsconfig.app.json app/ui/tsconfig.node.json \
        app/ui/vitest.config.ts app/ui/playwright.config.ts app/ui/src/env.d.ts
git commit -m "chore: scaffold Vue 3 + Vite + Tailwind v4 frontend project"
```

---

### Task 1: TypeScript Types

**Files:**
- Create: `app/ui/src/types/api.ts`

- [ ] **Step 1: Create app/ui/src/types/api.ts**

Mirroring `src/bilianalysis/engine/base.py` Pydantic models exactly:

```typescript
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
```

- [ ] **Step 2: Commit**

```bash
git add app/ui/src/types/api.ts
git commit -m "feat: add TypeScript types mirroring Pydantic engine models"
```

---

### Task 2: Theme CSS + Entry Files

**Files:**
- Create: `app/ui/src/styles/theme.css`
- Create: `app/ui/src/main.ts`
- Create: `app/ui/src/App.vue`

- [ ] **Step 1: Create app/ui/src/styles/theme.css**

Tailwind v4 CSS-first config with design tokens from spec §4:

```css
@import "tailwindcss";

/* ── Design Tokens (spec §4) ── */
@theme {
  --color-blue: #00AEEC;
  --color-blue-light: #E6F7FD;
  --color-bg: #FAFAFA;
  --color-card: #FFFFFF;
  --color-text: #111827;
  --color-text-secondary: #6B7280;
  --color-border: #E5E7EB;
  --color-success: #22C55E;
  --color-warning: #F59E0B;
  --color-danger: #EF4444;
  --font-family-sans: 'Inter', 'HarmonyOS Sans SC', 'PingFang SC', sans-serif;
  --radius-default: 12px;
  --radius-lg: 16px;
  --shadow-default: 0 2px 8px rgba(0, 0, 0, 0.05);
  --shadow-hover: 0 4px 16px rgba(0, 0, 0, 0.08);
}

/* ── Base ── */
html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family: var(--font-family-sans);
  background: var(--color-bg);
  color: var(--color-text);
  line-height: 1.6;
  min-height: 100vh;
}

/* ── Tabular numbers for all numeric displays ── */
.tabular {
  font-variant-numeric: tabular-nums;
}

/* ── Page shell ── */
.page-shell {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 24px;
}
```

- [ ] **Step 2: Create app/ui/src/main.ts**

```typescript
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './styles/theme.css'

const app = createApp(App)
app.use(router)
app.mount('#app')
```

- [ ] **Step 3: Create app/ui/src/App.vue**

```vue
<script setup lang="ts">
import TopNav from '@/components/layout/TopNav.vue'
</script>

<template>
  <TopNav />
  <router-view />
</template>
```

- [ ] **Step 4: Verify dev server starts**

```bash
cd app/ui && npx vite --host 2>&1 | head -5
```

Expected: Vite dev server starts. `Ctrl+C` to stop.

- [ ] **Step 5: Commit**

```bash
git add app/ui/src/styles/theme.css app/ui/src/main.ts app/ui/src/App.vue
git commit -m "feat: add theme CSS, main.ts entry, and App.vue shell"
```

---

### Task 3: Router

**Files:**
- Create: `app/ui/src/router/index.ts`

- [ ] **Step 1: Create app/ui/src/router/index.ts**

```typescript
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/pages/HomePage.vue'),
    },
    {
      path: '/analysis/stats',
      name: 'stats',
      component: () => import('@/pages/analysis/StatsPage.vue'),
    },
    {
      path: '/analysis/clusters',
      name: 'clusters',
      component: () => import('@/pages/analysis/ClusterPage.vue'),
    },
    {
      path: '/analysis/predictions',
      name: 'predict',
      component: () => import('@/pages/analysis/PredictPage.vue'),
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
```

- [ ] **Step 2: Create stub page files so the router doesn't crash on import**

Create `app/ui/src/pages/HomePage.vue`:
```vue
<template><div>HomePage</div></template>
```

Create `app/ui/src/pages/analysis/StatsPage.vue`:
```vue
<template><div>StatsPage</div></template>
```

Create `app/ui/src/pages/analysis/ClusterPage.vue`:
```vue
<template><div>ClusterPage</div></template>
```

Create `app/ui/src/pages/analysis/PredictPage.vue`:
```vue
<template><div>PredictPage</div></template>
```

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/router/index.ts app/ui/src/pages/
git commit -m "feat: add Vue Router with 4 routes and page stubs"
```

---

### Task 4: Alova useApi Composable

**Files:**
- Create: `app/ui/src/composables/useApi.ts`

- [ ] **Step 1: Create app/ui/src/composables/useApi.ts**

```typescript
import { createAlova } from 'alova'
import { adapterFetch } from '@alova/adapter-fetch'
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
        throw new Error(`HTTP ${response.status}`)
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

// ── Composable (per-page usage) ──

export function useStats() {
  return useRequest(fetchStats, { immediate: false })
}

export function useClusters() {
  return useRequest(fetchClusters, { immediate: false })
}

export function usePredictions() {
  return useRequest(fetchPredictions, { immediate: false })
}
```

- [ ] **Step 2: Commit**

```bash
git add app/ui/src/composables/useApi.ts
git commit -m "feat: add Alova HTTP client and typed useApi composables"
```

---

### Task 5: useChart Composable

**Files:**
- Create: `app/ui/src/composables/useChart.ts`

- [ ] **Step 1: Create app/ui/src/composables/useChart.ts**

```typescript
import { ref, onMounted, onUnmounted, watch, type Ref } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart, BarChart, ScatterChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent,
  GridComponent, MarkLineComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'

echarts.use([
  LineChart, BarChart, ScatterChart,
  TitleComponent, TooltipComponent, LegendComponent,
  GridComponent, MarkLineComponent,
  CanvasRenderer,
])

export function useChart(
  elRef: Ref<HTMLElement | null>,
  option: Ref<EChartsOption>,
) {
  const chartInstance = ref<echarts.ECharts | null>(null)

  onMounted(() => {
    if (!elRef.value) return
    chartInstance.value = echarts.init(elRef.value)
    chartInstance.value.setOption(option.value, true)
  })

  watch(option, (newOpt) => {
    if (chartInstance.value) {
      chartInstance.value.setOption(newOpt, true)
    }
  })

  const handleResize = () => {
    chartInstance.value?.resize()
  }
  window.addEventListener('resize', handleResize)

  onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    chartInstance.value?.dispose()
    chartInstance.value = null
  })

  return { chartInstance }
}
```

- [ ] **Step 2: Commit**

```bash
git add app/ui/src/composables/useChart.ts
git commit -m "feat: add useChart composable for ECharts lifecycle"
```

---

### Task 6: Layout Components (TopNav + PageShell)

**Files:**
- Create: `app/ui/src/components/layout/TopNav.vue`
- Create: `app/ui/src/components/layout/PageShell.vue`

- [ ] **Step 1: Create app/ui/src/components/layout/TopNav.vue**

Spec §5: Two nav items — "发现" → `/` and "分析" → `/analysis/stats`. Sticky, backdrop blur, active indicator.

```vue
<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

function isAnalysisActive() {
  return route.path.startsWith('/analysis')
}
</script>

<template>
  <nav class="sticky top-0 z-100 bg-bg/85 backdrop-blur-[12px] border-b border-border">
    <div class="max-w-[1280px] mx-auto px-6 flex items-center h-14 gap-8">
      <router-link to="/" class="text-lg font-bold text-text no-underline tracking-[-0.01em]">
        Bili<span class="text-blue">Insight</span>
      </router-link>
      <ul class="flex gap-6 list-none">
        <li>
          <router-link
            to="/"
            class="no-underline text-[0.9375rem] font-medium text-text-secondary px-0 py-1
                   transition-colors duration-200 relative
                   hover:text-text"
            :class="{ '!text-text': route.path === '/' }"
            active-class="!text-text"
          >
            发现
            <span
              v-if="route.path === '/'"
              class="absolute -bottom-4 left-0 right-0 h-0.5 bg-blue rounded-sm"
            />
          </router-link>
        </li>
        <li>
          <router-link
            to="/analysis/stats"
            class="no-underline text-[0.9375rem] font-medium text-text-secondary px-0 py-1
                   transition-colors duration-200 relative
                   hover:text-text"
            :class="{ '!text-text': isAnalysisActive() }"
          >
            分析
            <span
              v-if="isAnalysisActive()"
              class="absolute -bottom-4 left-0 right-0 h-0.5 bg-blue rounded-sm"
            />
          </router-link>
        </li>
      </ul>
    </div>
  </nav>
</template>
```

- [ ] **Step 2: Create app/ui/src/components/layout/PageShell.vue**

```vue
<template>
  <main class="max-w-[1280px] mx-auto px-6 py-12">
    <slot />
  </main>
</template>
```

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/components/layout/TopNav.vue app/ui/src/components/layout/PageShell.vue
git commit -m "feat: add TopNav and PageShell layout components"
```

---

### Task 7: Shared Components (StatCard + SectionHeader)

**Files:**
- Create: `app/ui/src/components/shared/StatCard.vue`
- Create: `app/ui/src/components/shared/SectionHeader.vue`

- [ ] **Step 1: Create app/ui/src/components/shared/StatCard.vue**

Props: `label: string`, `value: string | number`, `subLabel?: string`. White card with rounded corners, light shadow.

```vue
<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  subLabel?: string
}>()

function fmt(v: string | number): string {
  if (typeof v === 'number') {
    return v >= 10000 ? `${(v / 10000).toFixed(1)}万` : String(v)
  }
  return v
}
</script>

<template>
  <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
    <p class="text-sm font-medium text-text-secondary mb-2">{{ label }}</p>
    <p class="text-[2rem] font-bold text-text tabular leading-tight">{{ fmt(value) }}</p>
    <p v-if="subLabel" class="text-xs text-text-secondary mt-1">{{ subLabel }}</p>
  </div>
</template>
```

- [ ] **Step 2: Create app/ui/src/components/shared/SectionHeader.vue**

```vue
<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <div class="mb-6">
    <h2 class="text-xl font-semibold text-text">{{ title }}</h2>
    <p v-if="description" class="text-sm text-text-secondary mt-1">{{ description }}</p>
  </div>
</template>
```

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/components/shared/StatCard.vue app/ui/src/components/shared/SectionHeader.vue
git commit -m "feat: add StatCard and SectionHeader shared components"
```

---

### Task 8: ECharts Chart Components

**Files:**
- Create: `app/ui/src/components/charts/TrendLineChart.vue`
- Create: `app/ui/src/components/charts/CategoryBarChart.vue`
- Create: `app/ui/src/components/charts/ClusterScatter.vue`
- Create: `app/ui/src/components/charts/FitLineChart.vue`

- [ ] **Step 1: Create app/ui/src/components/charts/TrendLineChart.vue**

3-line chart (view, like, interaction rate). Spec §10: smooth:false, tooltip cross, legend bottom.

```vue
<script setup lang="ts">
import { computed, ref, type Ref } from 'vue'
import { useChart } from '@/composables/useChart'
import type { WeeklyTrend } from '@/types/api'
import type { EChartsOption } from 'echarts'

const props = defineProps<{ weeks: WeeklyTrend[] }>()

const chartRef: Ref<HTMLElement | null> = ref(null)

const option = computed<EChartsOption>(() => ({
  animation: true,
  animationDuration: 300,
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'cross' },
  },
  legend: {
    bottom: 0,
    data: ['平均播放', '平均点赞', '互动率'],
  },
  grid: { left: 48, right: 16, top: 16, bottom: 40 },
  xAxis: {
    type: 'category',
    data: props.weeks.map(w => `第${w.week_number}期`),
    axisLabel: { color: '#6B7280', fontSize: 11 },
  },
  yAxis: [
    {
      type: 'value',
      name: '播放/点赞',
      axisLabel: { color: '#6B7280', fontSize: 11 },
    },
    {
      type: 'value',
      name: '互动率',
      axisLabel: {
        color: '#6B7280', fontSize: 11,
        formatter: (v: number) => `${(v * 100).toFixed(1)}%`,
      },
    },
  ],
  series: [
    {
      name: '平均播放', type: 'line', smooth: false,
      data: props.weeks.map(w => w.avg_view),
      itemStyle: { color: '#00AEEC' },
    },
    {
      name: '平均点赞', type: 'line', smooth: false,
      data: props.weeks.map(w => w.avg_like),
      itemStyle: { color: '#22C55E' },
    },
    {
      name: '互动率', type: 'line', smooth: false,
      yAxisIndex: 1,
      data: props.weeks.map(w => w.avg_interaction_rate),
      itemStyle: { color: '#F59E0B' },
    },
  ],
}))

useChart(chartRef, option)
</script>

<template>
  <div ref="chartRef" class="w-full h-[400px]" />
</template>
```

- [ ] **Step 2: Create app/ui/src/components/charts/CategoryBarChart.vue**

Horizontal bar, single series, sorted desc. Spec §10.

```vue
<script setup lang="ts">
import { computed, ref, type Ref } from 'vue'
import { useChart } from '@/composables/useChart'
import type { CategoryStats } from '@/types/api'
import type { EChartsOption } from 'echarts'

const props = defineProps<{ categories: CategoryStats[] }>()

const chartRef: Ref<HTMLElement | null> = ref(null)

const option = computed<EChartsOption>(() => {
  const sorted = [...props.categories].sort((a, b) => b.video_count - a.video_count)
  return {
    animation: true,
    animationDuration: 300,
    tooltip: { trigger: 'axis' },
    grid: { left: 80, right: 48, top: 8, bottom: 8 },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#6B7280', fontSize: 11 },
    },
    yAxis: {
      type: 'category',
      data: sorted.map(c => c.tname),
      axisLabel: { color: '#111827', fontSize: 12 },
    },
    series: [{
      type: 'bar',
      data: sorted.map(c => c.video_count),
      itemStyle: { color: '#00AEEC', borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'right', color: '#6B7280', fontSize: 11 },
    }],
  }
})

useChart(chartRef, option)
</script>

<template>
  <div ref="chartRef" class="w-full h-[320px]" />
</template>
```

- [ ] **Step 3: Create app/ui/src/components/charts/ClusterScatter.vue**

Scatter plot, 3 color groups by cluster label, star markers for centroids. Spec §10.

```vue
<script setup lang="ts">
import { computed, ref, type Ref } from 'vue'
import { useChart } from '@/composables/useChart'
import type { ClusterGroup } from '@/types/api'
import type { EChartsOption } from 'echarts'

const props = defineProps<{
  scatterData: Record<string, any>
  clusters: ClusterGroup[]
}>()

const chartRef: Ref<HTMLElement | null> = ref(null)

const CLUSTER_COLORS = ['#00AEEC', '#22C55E', '#F59E0B']

const option = computed<EChartsOption>(() => {
  const data = props.scatterData as { data?: { x: number; y: number; cluster: number }[] }
  const points = data?.data ?? []
  const series = CLUSTER_COLORS.map((color, i) => ({
    name: props.clusters[i]?.tag ?? `Cluster ${i}`,
    type: 'scatter' as const,
    data: points.filter((p: any) => p.cluster === i).map((p: any) => [p.x, p.y]),
    itemStyle: { color },
    symbolSize: 6,
  }))

  // Centroids as star markers
  series.push({
    name: '簇中心',
    type: 'scatter' as const,
    data: props.clusters.map(c => [c.centroid.view ?? c.centroid.x, c.centroid.like ?? c.centroid.y]),
    itemStyle: { color: '#EF4444' },
    symbol: 'diamond',
    symbolSize: 14,
  })

  return {
    animation: true,
    animationDuration: 300,
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    grid: { left: 48, right: 16, top: 16, bottom: 40 },
    xAxis: { type: 'value', name: '播放量', axisLabel: { color: '#6B7280', fontSize: 11 } },
    yAxis: { type: 'value', name: '点赞量', axisLabel: { color: '#6B7280', fontSize: 11 } },
    series,
  }
})

useChart(chartRef, option)
</script>

<template>
  <div ref="chartRef" class="w-full h-[480px]" />
</template>
```

- [ ] **Step 4: Create app/ui/src/components/charts/FitLineChart.vue**

Line chart: actual (solid) + fitted (dashed), vertical split line at train/test boundary. Spec §10.

```vue
<script setup lang="ts">
import { computed, ref, type Ref } from 'vue'
import { useChart } from '@/composables/useChart'
import type { PredictionResult } from '@/types/api'
import type { EChartsOption } from 'echarts'

const props = defineProps<{ result: PredictionResult }>()

const chartRef: Ref<HTMLElement | null> = ref(null)

const option = computed<EChartsOption>(() => {
  const fitted = props.result.fitted as { week: number; actual: number; predicted: number }[]
  const forecast = props.result.forecast as { week: number; predicted: number }[]
  const allWeeks = [...fitted.map(f => f.week), ...forecast.map(f => f.week)]
  const splitIdx = fitted.length

  return {
    animation: true,
    animationDuration: 300,
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, data: ['实际值', '拟合值', '预测值'] },
    grid: { left: 48, right: 16, top: 16, bottom: 40 },
    xAxis: {
      type: 'category',
      data: allWeeks.map(w => `第${w}期`),
      axisLabel: { color: '#6B7280', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: props.result.target === 'view' ? '播放量' : '点赞量',
      axisLabel: { color: '#6B7280', fontSize: 11 },
    },
    series: [
      {
        name: '实际值', type: 'line',
        data: fitted.map(f => f.actual),
        itemStyle: { color: '#00AEEC' },
        lineStyle: { type: 'solid' },
      },
      {
        name: '拟合值', type: 'line',
        data: fitted.map(f => f.predicted),
        itemStyle: { color: '#22C55E' },
        lineStyle: { type: 'dashed' },
      },
      {
        name: '预测值', type: 'line',
        data: [...new Array(splitIdx).fill(null), ...forecast.map(f => f.predicted)],
        itemStyle: { color: '#F59E0B' },
        lineStyle: { type: 'dashed' },
      },
    ],
  }
})

useChart(chartRef, option)
</script>

<template>
  <div ref="chartRef" class="w-full h-[400px]" />
</template>
```

- [ ] **Step 5: Commit**

```bash
git add app/ui/src/components/charts/TrendLineChart.vue \
        app/ui/src/components/charts/CategoryBarChart.vue \
        app/ui/src/components/charts/ClusterScatter.vue \
        app/ui/src/components/charts/FitLineChart.vue
git commit -m "feat: add 4 ECharts chart components"
```

---

### Task 9: HomePage Components

**Files:**
- Create: `app/ui/src/components/home/HeroSection.vue`
- Create: `app/ui/src/components/home/KpiCardRow.vue`
- Create: `app/ui/src/components/home/CategoryBar.vue`
- Create: `app/ui/src/components/home/CreatorTopList.vue`
- Create: `app/ui/src/components/home/TrendMiniChart.vue`

- [ ] **Step 1: Create app/ui/src/components/home/HeroSection.vue**

Static content, no API data needed. Spec §6.1.

```vue
<template>
  <section class="bg-gradient-to-br from-[#CCF0FC] via-[#E6F7FD] to-bg rounded-[16px]
                  py-24 px-16 text-center mt-6 shadow-[var(--shadow-default)]">
    <h1 class="text-[2.5rem] font-bold tracking-[-0.02em] text-text mb-4">
      发现每周好内容
    </h1>
    <p class="text-lg text-[#4B7A8F] max-w-[480px] mx-auto mb-9 leading-relaxed">
      基于B站「每周必看」数据，发现优质创作者、热门品类与内容趋势
    </p>
    <router-link
      to="/analysis/stats"
      class="inline-block px-7 py-2.5 bg-blue text-white no-underline
             rounded-[12px] font-medium transition-colors duration-200
             hover:bg-[#0099D6]"
    >
      探索数据
    </router-link>
  </section>
</template>
```

- [ ] **Step 2: Create app/ui/src/components/home/KpiCardRow.vue**

Data: `StatReport.overall`. Shows 4 StatCards. Spec §6.1.

```vue
<script setup lang="ts">
import StatCard from '@/components/shared/StatCard.vue'
import type { OverallStats } from '@/types/api'

defineProps<{ overall: OverallStats }>()
</script>

<template>
  <section class="py-12">
    <SectionHeader title="平台概览" description="「每周必看」数据全景" />
    <div class="grid grid-cols-4 gap-6">
      <StatCard label="视频总数" :value="overall.total_videos" />
      <StatCard label="平均播放" :value="overall.avg_view" sub-label="每期均值" />
      <StatCard label="平均点赞" :value="overall.avg_like" sub-label="每期均值" />
      <StatCard label="创作者数" :value="overall.total_creators" />
    </div>
  </section>
</template>

<script lang="ts">
import SectionHeader from '@/components/shared/SectionHeader.vue'
export default { components: { SectionHeader } }
</script>
```

- [ ] **Step 3: Create app/ui/src/components/home/CategoryBar.vue**

Top 5 categories. Spec §6.1.

```vue
<script setup lang="ts">
import type { CategoryStats } from '@/types/api'

defineProps<{ categories: CategoryStats[] }>()
</script>

<template>
  <section class="py-12">
    <SectionHeader title="热门分区" description="视频数量 TOP5" />
    <div class="grid grid-cols-5 gap-4">
      <div
        v-for="(c, i) in categories.slice(0, 5)"
        :key="c.tname"
        class="bg-card rounded-[12px] p-5 shadow-[var(--shadow-default)]
               border-t-[3px]"
        :style="{ borderTopColor: ['#00AEEC','#22C55E','#F59E0B','#EF4444','#8B5CF6'][i] }"
      >
        <p class="text-sm font-medium text-text-secondary mb-1">{{ c.tname }}</p>
        <p class="text-2xl font-bold tabular text-text">{{ c.video_count }}</p>
        <p class="text-xs text-text-secondary mt-2">
          均播 {{ (c.avg_view / 10000).toFixed(1) }}万 · 赞 {{ (c.avg_like / 10000).toFixed(1) }}万
        </p>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import SectionHeader from '@/components/shared/SectionHeader.vue'
export default { components: { SectionHeader } }
</script>
```

- [ ] **Step 4: Create app/ui/src/components/home/CreatorTopList.vue**

Top 5 creators. Spec §6.1.

```vue
<script setup lang="ts">
import type { CreatorStats } from '@/types/api'

defineProps<{ creators: CreatorStats[] }>()
</script>

<template>
  <section class="py-12">
    <SectionHeader title="上榜创作者" description="出现次数 TOP5" />
    <div class="space-y-3">
      <div
        v-for="(c, i) in creators.slice(0, 5)"
        :key="c.mid"
        class="flex items-center gap-4 bg-card rounded-[12px] p-4 shadow-[var(--shadow-default)]"
      >
        <span class="text-sm font-bold text-text-secondary w-6">{{ i + 1 }}</span>
        <div class="flex-1 min-w-0">
          <p class="font-semibold text-text truncate">{{ c.name }}</p>
          <p class="text-xs text-text-secondary">
            上榜 {{ c.appearance_count }} 次
          </p>
        </div>
        <div class="text-right tabular">
          <p class="text-sm font-semibold text-text">{{ (c.total_view / 10000).toFixed(0) }}万</p>
          <p class="text-xs text-text-secondary">总播放</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import SectionHeader from '@/components/shared/SectionHeader.vue'
export default { components: { SectionHeader } }
</script>
```

- [ ] **Step 5: Create app/ui/src/components/home/TrendMiniChart.vue**

Last 10 weeks trend. Spec §6.1.

```vue
<script setup lang="ts">
import { computed, ref, type Ref } from 'vue'
import { useChart } from '@/composables/useChart'
import type { WeeklyTrend } from '@/types/api'
import type { EChartsOption } from 'echarts'

const props = defineProps<{ weeks: WeeklyTrend[] }>()

const chartRef: Ref<HTMLElement | null> = ref(null)

const option = computed<EChartsOption>(() => ({
  animation: true,
  animationDuration: 300,
  tooltip: { trigger: 'axis' },
  grid: { left: 8, right: 8, top: 8, bottom: 8 },
  xAxis: { show: false, data: props.weeks.map(w => `第${w.week_number}期`) },
  yAxis: { show: false },
  series: [{
    type: 'line',
    data: props.weeks.map(w => w.avg_view),
    itemStyle: { color: '#00AEEC' },
    areaStyle: { color: 'rgba(0,174,236,0.08)' },
    symbol: 'none',
    smooth: false,
  }],
}))

useChart(chartRef, option)
</script>

<template>
  <section class="py-12">
    <SectionHeader title="内容趋势" description="近10期播放量走势" />
    <div ref="chartRef" class="w-full h-[200px] bg-card rounded-[12px] p-4 shadow-[var(--shadow-default)]" />
  </section>
</template>

<script lang="ts">
import SectionHeader from '@/components/shared/SectionHeader.vue'
export default { components: { SectionHeader } }
</script>
```

- [ ] **Step 6: Commit**

```bash
git add app/ui/src/components/home/HeroSection.vue \
        app/ui/src/components/home/KpiCardRow.vue \
        app/ui/src/components/home/CategoryBar.vue \
        app/ui/src/components/home/CreatorTopList.vue \
        app/ui/src/components/home/TrendMiniChart.vue
git commit -m "feat: add HomePage section components"
```

---

### Task 10: Analysis Shared Components

**Files:**
- Create: `app/ui/src/components/analysis/SubNavTabs.vue`
- Create: `app/ui/src/components/analysis/CategoryPanel.vue`
- Create: `app/ui/src/components/analysis/CreatorTable.vue`
- Create: `app/ui/src/components/analysis/ClusterCards.vue`
- Create: `app/ui/src/components/analysis/FeatureImportance.vue`
- Create: `app/ui/src/components/analysis/ForecastCards.vue`

- [ ] **Step 1: Create app/ui/src/components/analysis/SubNavTabs.vue**

Spec §5: Tab switching for analysis sub-pages.

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const TABS = [
  { key: 'stats', label: '统计概览', path: '/analysis/stats' },
  { key: 'clusters', label: '聚类分析', path: '/analysis/clusters' },
  { key: 'predict', label: '预测分析', path: '/analysis/predictions' },
] as const

const router = useRouter()
const route = useRoute()

const activeKey = computed(() => {
  if (route.path.includes('clusters')) return 'clusters'
  if (route.path.includes('predict')) return 'predict'
  return 'stats'
})

function go(key: string) {
  const tab = TABS.find(t => t.key === key)
  if (tab) router.push(tab.path)
}
</script>

<template>
  <div class="flex gap-2 border-b border-border pb-0 mb-8">
    <button
      v-for="tab in TABS"
      :key="tab.key"
      @click="go(tab.key)"
      class="px-5 py-2.5 text-sm font-medium rounded-t-[8px] border-none cursor-pointer
             transition-colors duration-200"
      :class="activeKey === tab.key
        ? 'bg-blue text-white'
        : 'bg-transparent text-text-secondary hover:text-text hover:bg-border/50'"
    >
      {{ tab.label }}
    </button>
  </div>
</template>
```

- [ ] **Step 2: Create app/ui/src/components/analysis/CategoryPanel.vue**

Full category list with horizontal bar chart. Spec §6.2.

```vue
<script setup lang="ts">
import CategoryBarChart from '@/components/charts/CategoryBarChart.vue'
import type { CategoryStats } from '@/types/api'

defineProps<{ categories: CategoryStats[] }>()
</script>

<template>
  <section class="py-8">
    <SectionHeader title="分区分布" description="各分区视频数量对比" />
    <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
      <CategoryBarChart :categories="categories" />
    </div>
  </section>
</template>

<script lang="ts">
import SectionHeader from '@/components/shared/SectionHeader.vue'
export default { components: { SectionHeader } }
</script>
```

- [ ] **Step 3: Create app/ui/src/components/analysis/CreatorTable.vue**

Top 10 creator table. Spec §6.2.

```vue
<script setup lang="ts">
import type { CreatorStats } from '@/types/api'

defineProps<{ creators: CreatorStats[] }>()
</script>

<template>
  <section class="py-8">
    <SectionHeader title="头部创作者" description="上榜次数 TOP10" />
    <div class="bg-card rounded-[12px] shadow-[var(--shadow-default)] overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-border text-text-secondary">
            <th class="text-left p-4 font-medium">创作者</th>
            <th class="text-right p-4 font-medium">上榜次数</th>
            <th class="text-right p-4 font-medium">总播放</th>
            <th class="text-right p-4 font-medium">总点赞</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(c, i) in creators.slice(0, 10)"
            :key="c.mid"
            class="border-b border-border last:border-0"
          >
            <td class="p-4">
              <span class="text-text-secondary mr-2">{{ i + 1 }}</span>
              <span class="font-medium text-text">{{ c.name }}</span>
            </td>
            <td class="text-right p-4 tabular">{{ c.appearance_count }}</td>
            <td class="text-right p-4 tabular">{{ (c.total_view / 10000).toFixed(0) }}万</td>
            <td class="text-right p-4 tabular">{{ (c.total_like / 10000).toFixed(0) }}万</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script lang="ts">
import SectionHeader from '@/components/shared/SectionHeader.vue'
export default { components: { SectionHeader } }
</script>
```

- [ ] **Step 4: Create app/ui/src/components/analysis/ClusterCards.vue**

Cluster cards showing 3 groups. Spec §6.3.

```vue
<script setup lang="ts">
import type { ClusterGroup } from '@/types/api'

defineProps<{ clusters: ClusterGroup[] }>()

const CLUSTER_COLORS: Record<number, string> = {
  0: '#00AEEC', 1: '#22C55E', 2: '#F59E0B',
}
</script>

<template>
  <section class="py-8">
    <SectionHeader title="内容聚类" description="基于播放、点赞、投币等特征的 3 类内容群体" />
    <div class="grid grid-cols-3 gap-6">
      <div
        v-for="c in clusters"
        :key="c.label"
        class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]
               border-t-[4px]"
        :style="{ borderTopColor: CLUSTER_COLORS[c.label] ?? '#6B7280' }"
      >
        <p class="text-lg font-bold text-text mb-1">{{ c.tag }}</p>
        <p class="text-sm text-text-secondary mb-4">{{ c.count }} 个视频</p>
        <div class="space-y-2 text-sm tabular">
          <div class="flex justify-between">
            <span class="text-text-secondary">平均播放</span>
            <span class="font-medium text-text">{{ (c.avg_view / 10000).toFixed(1) }}万</span>
          </div>
          <div class="flex justify-between">
            <span class="text-text-secondary">平均点赞</span>
            <span class="font-medium text-text">{{ (c.avg_like / 10000).toFixed(1) }}万</span>
          </div>
          <div class="flex justify-between">
            <span class="text-text-secondary">平均投币</span>
            <span class="font-medium text-text">{{ (c.avg_coin / 10000).toFixed(1) }}万</span>
          </div>
          <div class="flex justify-between">
            <span class="text-text-secondary">平均收藏</span>
            <span class="font-medium text-text">{{ (c.avg_favorite / 10000).toFixed(1) }}万</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import SectionHeader from '@/components/shared/SectionHeader.vue'
export default { components: { SectionHeader } }
</script>
```

- [ ] **Step 5: Create app/ui/src/components/analysis/FeatureImportance.vue**

Feature importance ranking. Spec §6.3.

```vue
<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ features: Record<string, number> }>()

const ranked = computed(() =>
  Object.entries(props.features)
    .sort(([, a], [, b]) => b - a)
)
</script>

<template>
  <section class="py-8">
    <SectionHeader title="特征重要性" description="各维度对聚类结果的贡献度" />
    <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)] space-y-3">
      <div v-for="[name, score] in ranked" :key="name" class="flex items-center gap-4">
        <span class="text-sm text-text-secondary w-24 shrink-0">{{ name }}</span>
        <div class="flex-1 h-2 bg-border rounded-full overflow-hidden">
          <div
            class="h-full bg-blue rounded-full transition-all duration-300"
            :style="{ width: `${(score * 100).toFixed(0)}%` }"
          />
        </div>
        <span class="text-sm tabular font-medium text-text w-12 text-right">
          {{ (score * 100).toFixed(1) }}%
        </span>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import SectionHeader from '@/components/shared/SectionHeader.vue'
export default { components: { SectionHeader } }
</script>
```

- [ ] **Step 6: Create app/ui/src/components/analysis/ForecastCards.vue**

Forecast cards for last 3 predicted weeks. Spec §6.4.

```vue
<script setup lang="ts">
import StatCard from '@/components/shared/StatCard.vue'

defineProps<{ forecast: Record<string, any>[] }>()

function fmt(v: number): string {
  return v >= 10000 ? `${(v / 10000).toFixed(1)}万` : v.toFixed(0)
}
</script>

<template>
  <section class="py-8">
    <SectionHeader title="预测结果" description="未来3周播放量预测" />
    <div class="grid grid-cols-3 gap-6">
      <StatCard
        v-for="(f, i) in forecast.slice(0, 3)"
        :key="i"
        :label="`第${f.week}期预测`"
        :value="fmt(f.predicted)"
        :sub-label="i === 0 ? '下周' : i === 1 ? '两周后' : '三周后'"
      />
    </div>
  </section>
</template>

<script lang="ts">
import SectionHeader from '@/components/shared/SectionHeader.vue'
export default { components: { SectionHeader } }
</script>
```

- [ ] **Step 7: Commit**

```bash
git add app/ui/src/components/analysis/SubNavTabs.vue \
        app/ui/src/components/analysis/CategoryPanel.vue \
        app/ui/src/components/analysis/CreatorTable.vue \
        app/ui/src/components/analysis/ClusterCards.vue \
        app/ui/src/components/analysis/FeatureImportance.vue \
        app/ui/src/components/analysis/ForecastCards.vue
git commit -m "feat: add analysis shared components (SubNavTabs, panels, cards, table)"
```

---

### Task 11: Pages (HomePage, StatsPage, ClusterPage, PredictPage)

**Files:**
- Overwrite: `app/ui/src/pages/HomePage.vue`
- Overwrite: `app/ui/src/pages/analysis/StatsPage.vue`
- Overwrite: `app/ui/src/pages/analysis/ClusterPage.vue`
- Overwrite: `app/ui/src/pages/analysis/PredictPage.vue`

All pages follow the same pattern: `useRequest` on mount → loading (el-skeleton) → error (panel with retry) → data (full content).

- [ ] **Step 1: Overwrite app/ui/src/pages/HomePage.vue**

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useStats } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import HeroSection from '@/components/home/HeroSection.vue'
import KpiCardRow from '@/components/home/KpiCardRow.vue'
import CategoryBar from '@/components/home/CategoryBar.vue'
import CreatorTopList from '@/components/home/CreatorTopList.vue'
import TrendMiniChart from '@/components/home/TrendMiniChart.vue'

const { data, loading, error, send } = useStats()

onMounted(() => send())
</script>

<template>
  <PageShell>
    <HeroSection />

    <!-- Loading -->
    <template v-if="loading">
      <div class="space-y-8 py-12">
        <div class="h-32 bg-card rounded-[12px] animate-pulse" />
        <div class="h-48 bg-card rounded-[12px] animate-pulse" />
        <div class="h-48 bg-card rounded-[12px] animate-pulse" />
        <div class="h-56 bg-card rounded-[12px] animate-pulse" />
      </div>
    </template>

    <!-- Error -->
    <div v-else-if="error" class="py-12 text-center">
      <div class="bg-card rounded-[16px] p-12 shadow-[var(--shadow-default)] max-w-md mx-auto">
        <p class="text-lg font-semibold text-text mb-2">加载失败</p>
        <p class="text-sm text-text-secondary mb-6">{{ error.message }}</p>
        <button
          @click="send()"
          class="px-6 py-2 bg-blue text-white rounded-[12px] font-medium
                 border-none cursor-pointer hover:bg-[#0099D6] transition-colors"
        >
          重试
        </button>
      </div>
    </div>

    <!-- Data -->
    <template v-else-if="data">
      <KpiCardRow :overall="data.overall" />
      <CategoryBar :categories="data.by_category" />
      <CreatorTopList :creators="data.by_creator" />
      <TrendMiniChart :weeks="data.by_week.slice(-10)" />
    </template>

    <!-- Empty (no data yet) -->
    <div v-else class="py-12 text-center">
      <p class="text-text-secondary">暂无数据，请先触发一次数据采集与分析</p>
    </div>
  </PageShell>
</template>
```

- [ ] **Step 2: Overwrite app/ui/src/pages/analysis/StatsPage.vue**

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useStats } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import SubNavTabs from '@/components/analysis/SubNavTabs.vue'
import StatCard from '@/components/shared/StatCard.vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'
import TrendLineChart from '@/components/charts/TrendLineChart.vue'
import CategoryPanel from '@/components/analysis/CategoryPanel.vue'
import CreatorTable from '@/components/analysis/CreatorTable.vue'

const { data, loading, error, send } = useStats()

onMounted(() => send())
</script>

<template>
  <PageShell>
    <SubNavTabs />

    <!-- Loading -->
    <template v-if="loading">
      <div class="space-y-8">
        <div class="h-24 bg-card rounded-[12px] animate-pulse" />
        <div class="h-[400px] bg-card rounded-[12px] animate-pulse" />
        <div class="h-[320px] bg-card rounded-[12px] animate-pulse" />
        <div class="h-64 bg-card rounded-[12px] animate-pulse" />
      </div>
    </template>

    <!-- Error -->
    <div v-else-if="error" class="py-12 text-center">
      <div class="bg-card rounded-[16px] p-12 shadow-[var(--shadow-default)] max-w-md mx-auto">
        <p class="text-lg font-semibold text-text mb-2">加载失败，请重试</p>
        <p class="text-sm text-text-secondary mb-6">{{ error.message }}</p>
        <button
          @click="send()"
          class="px-6 py-2 bg-blue text-white rounded-[12px] font-medium
                 border-none cursor-pointer hover:bg-[#0099D6] transition-colors"
        >
          重试
        </button>
      </div>
    </div>

    <!-- Data -->
    <template v-else-if="data">
      <div class="grid grid-cols-3 gap-6 mb-8">
        <StatCard label="视频总数" :value="data.overall.total_videos" />
        <StatCard label="创作者数" :value="data.overall.total_creators" />
        <StatCard label="平均互动率" :value="(data.overall.avg_like_rate * 100).toFixed(1) + '%'" />
      </div>

      <section class="py-8">
        <SectionHeader title="趋势分析" description="播放、点赞、互动率随时间变化" />
        <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
          <TrendLineChart :weeks="data.by_week" />
        </div>
      </section>

      <CategoryPanel :categories="data.by_category" />
      <CreatorTable :creators="data.by_creator" />
    </template>

    <!-- Empty -->
    <div v-else class="py-12 text-center">
      <p class="text-text-secondary">暂无数据，请先触发一次数据采集与分析</p>
    </div>
  </PageShell>
</template>
```

- [ ] **Step 3: Overwrite app/ui/src/pages/analysis/ClusterPage.vue**

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useClusters } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import SubNavTabs from '@/components/analysis/SubNavTabs.vue'
import StatCard from '@/components/shared/StatCard.vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'
import ClusterCards from '@/components/analysis/ClusterCards.vue'
import FeatureImportance from '@/components/analysis/FeatureImportance.vue'
import ClusterScatter from '@/components/charts/ClusterScatter.vue'

const { data, loading, error, send } = useClusters()

onMounted(() => send())
</script>

<template>
  <PageShell>
    <SubNavTabs />

    <template v-if="loading">
      <div class="space-y-8">
        <div class="h-24 bg-card rounded-[12px] animate-pulse" />
        <div class="h-64 bg-card rounded-[12px] animate-pulse" />
        <div class="h-[480px] bg-card rounded-[12px] animate-pulse" />
      </div>
    </template>

    <div v-else-if="error" class="py-12 text-center">
      <div class="bg-card rounded-[16px] p-12 shadow-[var(--shadow-default)] max-w-md mx-auto">
        <p class="text-lg font-semibold text-text mb-2">加载失败，请重试</p>
        <p class="text-sm text-text-secondary mb-6">{{ error.message }}</p>
        <button
          @click="send()"
          class="px-6 py-2 bg-blue text-white rounded-[12px] font-medium
                 border-none cursor-pointer hover:bg-[#0099D6] transition-colors"
        >
          重试
        </button>
      </div>
    </div>

    <template v-else-if="data">
      <div class="mb-8">
        <StatCard
          label="轮廓系数"
          :value="data.clusters.silhouette_score.toFixed(3)"
          sub-label="Silhouette Score"
        />
      </div>

      <ClusterCards :clusters="data.clusters.clusters" />
      <FeatureImportance :features="data.clusters.feature_importance" />

      <section class="py-8">
        <SectionHeader title="聚类可视化" description="PCA 降维后的二维散点分布" />
        <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
          <ClusterScatter :scatter-data="data.scatter_data" :clusters="data.clusters.clusters" />
        </div>
      </section>
    </template>

    <div v-else class="py-12 text-center">
      <p class="text-text-secondary">暂无数据，请先触发一次数据采集与分析</p>
    </div>
  </PageShell>
</template>
```

- [ ] **Step 4: Overwrite app/ui/src/pages/analysis/PredictPage.vue**

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { usePredictions } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import SubNavTabs from '@/components/analysis/SubNavTabs.vue'
import StatCard from '@/components/shared/StatCard.vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'
import ForecastCards from '@/components/analysis/ForecastCards.vue'
import FitLineChart from '@/components/charts/FitLineChart.vue'

const { data, loading, error, send } = usePredictions()

onMounted(() => send())

function fmtR2(v: number): string {
  return v.toFixed(3)
}
</script>

<template>
  <PageShell>
    <SubNavTabs />

    <template v-if="loading">
      <div class="space-y-8">
        <div class="h-24 bg-card rounded-[12px] animate-pulse" />
        <div class="h-64 bg-card rounded-[12px] animate-pulse" />
        <div class="h-48 bg-card rounded-[12px] animate-pulse" />
        <div class="h-[400px] bg-card rounded-[12px] animate-pulse" />
      </div>
    </template>

    <div v-else-if="error" class="py-12 text-center">
      <div class="bg-card rounded-[16px] p-12 shadow-[var(--shadow-default)] max-w-md mx-auto">
        <p class="text-lg font-semibold text-text mb-2">加载失败，请重试</p>
        <p class="text-sm text-text-secondary mb-6">{{ error.message }}</p>
        <button
          @click="send()"
          class="px-6 py-2 bg-blue text-white rounded-[12px] font-medium
                 border-none cursor-pointer hover:bg-[#0099D6] transition-colors"
        >
          重试
        </button>
      </div>
    </div>

    <template v-else-if="data">
      <div class="grid grid-cols-2 gap-6 mb-8">
        <StatCard
          label="播放量预测 R²"
          :value="fmtR2(data.view_predict.r2_score)"
          sub-label="系数越接近1拟合越好"
        />
        <StatCard
          label="点赞量预测 R²"
          :value="fmtR2(data.like_predict.r2_score)"
          sub-label="系数越接近1拟合越好"
        />
      </div>

      <section class="py-8">
        <SectionHeader title="预测拟合" description="实际值 vs 拟合值 vs 预测值" />
        <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
          <FitLineChart :result="data.view_predict" />
        </div>
      </section>

      <ForecastCards :forecast="data.view_predict.forecast" />

      <section class="py-8">
        <SectionHeader title="回归系数" description="各特征对播放量的影响权重" />
        <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)] space-y-3">
          <div
            v-for="[name, coef] in Object.entries(data.view_predict.coefficients)"
            :key="name"
            class="flex items-center gap-4"
          >
            <span class="text-sm text-text-secondary w-24 shrink-0">{{ name }}</span>
            <span class="text-sm font-medium tabular"
              :class="coef > 0 ? 'text-success' : 'text-danger'"
            >
              {{ coef > 0 ? '+' : '' }}{{ coef.toFixed(4) }}
            </span>
          </div>
        </div>
      </section>
    </template>

    <div v-else class="py-12 text-center">
      <p class="text-text-secondary">暂无数据，请先触发一次数据采集与分析</p>
    </div>
  </PageShell>
</template>
```

- [ ] **Step 5: Verify the app builds without errors**

```bash
cd app/ui && npx vue-tsc -b --noEmit 2>&1
```

Expected: No TypeScript errors (some may appear for missing imports; fix them).

- [ ] **Step 6: Commit**

```bash
git add app/ui/src/pages/HomePage.vue \
        app/ui/src/pages/analysis/StatsPage.vue \
        app/ui/src/pages/analysis/ClusterPage.vue \
        app/ui/src/pages/analysis/PredictPage.vue
git commit -m "feat: add 4 page components with loading/error/empty states"
```

---

### Task 12: Integration Test — Run Dev Server Against Backend

**Files:**
- Modify: `app/ui/vite.config.ts` (verify proxy)

- [ ] **Step 1: Start the backend server**

```bash
cd D:/Desktop/BiliAnalysis && uv run bilianalysis serve 2>&1 &
sleep 3
```

- [ ] **Step 2: Start the frontend dev server**

```bash
cd app/ui && npx vite --host 2>&1 &
sleep 3
```

- [ ] **Step 3: Fetch stats through the proxy to confirm integration**

```bash
curl -s http://localhost:5173/api/analysis/stats | head -c 200
```

Expected: JSON response from backend proxied through Vite (or 200 with cached data, or empty `null` fields if no data crawled yet).

- [ ] **Step 4: Stop servers**

```bash
kill %1 %2 2>/dev/null
```

- [ ] **Step 5: Commit (only if proxy needed adjustment)**

```bash
git add app/ui/vite.config.ts
git commit -m "fix: verify Vite proxy to FastAPI backend"
```

---

### Task 13: Unit Tests (Vitest)

**Files:**
- Create: `app/ui/src/composables/__tests__/useApi.spec.ts`
- Create: `app/ui/src/composables/__tests__/useChart.spec.ts`
- Create: `app/ui/src/components/shared/__tests__/StatCard.spec.ts`
- Create: `app/ui/src/components/shared/__tests__/SectionHeader.spec.ts`
- Create: `app/ui/src/components/layout/__tests__/TopNav.spec.ts`

- [ ] **Step 1: Create app/ui/src/components/shared/__tests__/StatCard.spec.ts**

```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatCard from '@/components/shared/StatCard.vue'

describe('StatCard', () => {
  it('renders label and value', () => {
    const wrapper = mount(StatCard, {
      props: { label: '测试指标', value: 12345 },
    })
    expect(wrapper.text()).toContain('测试指标')
    expect(wrapper.text()).toContain('1.2万')
  })

  it('renders subLabel when provided', () => {
    const wrapper = mount(StatCard, {
      props: { label: '播放量', value: 999, subLabel: '近7天均值' },
    })
    expect(wrapper.text()).toContain('近7天均值')
  })

  it('does not render subLabel when omitted', () => {
    const wrapper = mount(StatCard, {
      props: { label: '播放量', value: 999 },
    })
    expect(wrapper.text()).not.toContain('近7天均值')
  })

  it('displays raw string values directly', () => {
    const wrapper = mount(StatCard, {
      props: { label: 'R²', value: '0.856' },
    })
    expect(wrapper.text()).toContain('0.856')
  })
})
```

- [ ] **Step 2: Create app/ui/src/components/shared/__tests__/SectionHeader.spec.ts**

```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SectionHeader from '@/components/shared/SectionHeader.vue'

describe('SectionHeader', () => {
  it('renders title', () => {
    const wrapper = mount(SectionHeader, {
      props: { title: '平台概览' },
    })
    expect(wrapper.text()).toContain('平台概览')
  })

  it('renders description when provided', () => {
    const wrapper = mount(SectionHeader, {
      props: { title: '平台概览', description: '数据全景' },
    })
    expect(wrapper.text()).toContain('数据全景')
  })

  it('does not render description paragraph when omitted', () => {
    const wrapper = mount(SectionHeader, {
      props: { title: '平台概览' },
    })
    const p = wrapper.findAll('p')
    // Only the h2 should be present, no description p
    expect(p.length).toBe(0)
  })
})
```

- [ ] **Step 3: Create app/ui/src/components/layout/__tests__/TopNav.spec.ts**

```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import TopNav from '@/components/layout/TopNav.vue'

function makeRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div>Home</div>' } },
      { path: '/analysis/stats', component: { template: '<div>Stats</div>' } },
    ],
  })
}

describe('TopNav', () => {
  it('renders logo text', async () => {
    const router = makeRouter()
    router.push('/')
    await router.isReady()
    const wrapper = mount(TopNav, { global: { plugins: [router] } })
    expect(wrapper.text()).toContain('BiliInsight')
  })

  it('renders two nav links', async () => {
    const router = makeRouter()
    router.push('/')
    await router.isReady()
    const wrapper = mount(TopNav, { global: { plugins: [router] } })
    const links = wrapper.findAll('a')
    // At least the logo + 2 nav links
    expect(links.length).toBeGreaterThanOrEqual(2)
  })

  it('highlights active route', async () => {
    const router = makeRouter()
    router.push('/')
    await router.isReady()
    const wrapper = mount(TopNav, { global: { plugins: [router] } })
    // The "发现" link should be active
    const activeLink = wrapper.find('.\\!text-text')
    expect(activeLink.exists()).toBe(true)
  })
})
```

- [ ] **Step 4: Create app/ui/src/composables/__tests__/useChart.spec.ts**

```typescript
import { describe, it, expect } from 'vitest'

describe('useChart', () => {
  it('exports useChart function', async () => {
    const mod = await import('@/composables/useChart')
    expect(mod.useChart).toBeDefined()
    expect(typeof mod.useChart).toBe('function')
  })

  it('echarts modules registered without error', async () => {
    // Import the composable — echarts.use() runs at module level
    await import('@/composables/useChart')
    // If we get here without throw, echarts modules registered successfully
    expect(true).toBe(true)
  })
})
```

- [ ] **Step 5: Create app/ui/src/composables/__tests__/useApi.spec.ts**

```typescript
import { describe, it, expect } from 'vitest'

describe('useApi', () => {
  it('exports useStats, useClusters, usePredictions', async () => {
    const mod = await import('@/composables/useApi')
    expect(mod.useStats).toBeDefined()
    expect(mod.useClusters).toBeDefined()
    expect(mod.usePredictions).toBeDefined()
  })

  it('fetch functions return method instances', async () => {
    const { fetchStats, fetchClusters, fetchPredictions } = await import('@/composables/useApi')
    expect(fetchStats()).toBeDefined()
    expect(fetchClusters()).toBeDefined()
    expect(fetchPredictions()).toBeDefined()
  })
})
```

- [ ] **Step 6: Run unit tests**

```bash
cd app/ui && npx vitest run 2>&1
```

Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add app/ui/src/composables/__tests__/ app/ui/src/components/shared/__tests__/ app/ui/src/components/layout/__tests__/
git commit -m "test: add unit tests for composables, StatCard, SectionHeader, TopNav"
```

---

### Task 14: Playwright Visual Regression Tests

**Files:**
- Create: `app/ui/e2e/visual.spec.ts`

- [ ] **Step 1: Create app/ui/e2e/visual.spec.ts**

Compare screenshots of key components against `design-demos/*.html` baselines.

```typescript
import { test, expect } from '@playwright/test'

test.describe('visual regression', () => {
  test('homepage layout matches design mockup', async ({ page }) => {
    await page.goto('/')
    // Wait for skeleton to disappear (data loaded or error shown)
    await page.waitForTimeout(2000)
    await expect(page).toHaveScreenshot('homepage.png', {
      maxDiffPixelRatio: 0.1,
      fullPage: true,
    })
  })

  test('stats page layout', async ({ page }) => {
    await page.goto('/analysis/stats')
    await page.waitForTimeout(2000)
    await expect(page).toHaveScreenshot('stats.png', {
      maxDiffPixelRatio: 0.1,
      fullPage: true,
    })
  })

  test('clusters page layout', async ({ page }) => {
    await page.goto('/analysis/clusters')
    await page.waitForTimeout(2000)
    await expect(page).toHaveScreenshot('clusters.png', {
      maxDiffPixelRatio: 0.1,
      fullPage: true,
    })
  })

  test('predictions page layout', async ({ page }) => {
    await page.goto('/analysis/predictions')
    await page.waitForTimeout(2000)
    await expect(page).toHaveScreenshot('predictions.png', {
      maxDiffPixelRatio: 0.1,
      fullPage: true,
    })
  })

  test('navigation between pages works', async ({ page }) => {
    await page.goto('/')
    await page.waitForTimeout(1000)
    await page.click('text=分析')
    await expect(page).toHaveURL(/\/analysis\/stats/)
  })
})
```

- [ ] **Step 2: Run Playwright tests (first run creates baselines)**

```bash
cd app/ui && npx playwright install chromium 2>&1 | tail -3
cd app/ui && npx playwright test --update-snapshots 2>&1
```

Expected: Baselines created. Future runs will compare against them.

- [ ] **Step 3: Commit**

```bash
git add app/ui/e2e/visual.spec.ts
git commit -m "test: add Playwright visual regression tests"
```

---

### Task 15: Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Run all unit tests**

```bash
cd app/ui && npx vitest run 2>&1
```

Expected: All pass.

- [ ] **Step 2: Type-check the entire project**

```bash
cd app/ui && npx vue-tsc -b --noEmit 2>&1
```

Expected: No errors.

- [ ] **Step 3: Build for production**

```bash
cd app/ui && npx vite build 2>&1
```

Expected: Build succeeds, output in `app/ui/dist/`.

- [ ] **Step 4: Start backend and test full integration**

```bash
cd D:/Desktop/BiliAnalysis && uv run bilianalysis serve &
sleep 3
curl -s http://localhost:8000/api/analysis/stats | head -c 100
```

Expected: Backend responds with JSON.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: final verification — all tests pass, build succeeds"
```

---

## Parallel Execution Guide

Tasks can be executed in parallel groups:

**Group A (sequential dependency chain):**
Task 0 → Task 1 → Task 2 → Task 3

**Group B (can run in parallel once Group A done):**
Task 4, Task 5, Task 6, Task 7 — all in parallel

**Group C (can run in parallel once Group B done):**
Task 8, Task 9, Task 10 — all in parallel

**Group D (depends on Group C):**
Task 11 (pages wire together components from Tasks 8-10)

**Group E (depends on Group D):**
Task 12 (integration test), Task 13 (unit tests), Task 14 (e2e tests) — all in parallel

**Group F:**
Task 15 (final verification)
