# Element Plus Frontend Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the entire Vue3 frontend to use Element Plus components instead of custom-built equivalents, while preserving the existing visual design through CSS variable mapping.

**Architecture:** Two-phase approach. Phase 1 replaces the CSS infrastructure (theme.css variable mapping), global import setup, and shared/layout components. Phase 2 replaces business/analysis components and unifies page states (error/empty/loading). Existing component APIs (props/events) are preserved so consumers see no breaking changes.

**Tech Stack:** Vue 3.5 + Element Plus 2.9 + Tailwind CSS 4 + Vite 6 + Vitest + @element-plus/icons-vue

**Design Spec:** `docs/superpowers/specs/2026-06-22-element-plus-refactor-design.md`

---

## File Structure

```
app/ui/
├── package.json                          # [MODIFY] Add @element-plus/icons-vue
├── src/
│   ├── main.ts                           # [MODIFY] Global ElementPlus import
│   ├── styles/
│   │   └── theme.css                     # [MODIFY] Append CSS variable mapping
│   └── components/
│       ├── layout/
│       │   ├── Sidebar.vue               # [MODIFY] el-menu vertical
│       │   └── TopNav.vue                # [MODIFY] el-menu horizontal + el-button
│       ├── shared/
│       │   ├── StatCard.vue              # [MODIFY] el-statistic + el-card
│       │   ├── SectionHeader.vue         # [MODIFY] Add el-divider
│       │   ├── AnalysisLoading.vue       # [MODIFY] Embed el-skeleton
│       │   └── ReanalyzeButton.vue       # [MODIFY] el-button + el-popover + el-input
│       ├── business/
│       │   ├── SearchBar.vue             # [MODIFY] el-input
│       │   ├── SortTabs.vue              # [MODIFY] el-segmented
│       │   ├── FilterDropdown.vue        # [MODIFY] el-select
│       │   ├── VideoCard.vue             # [MODIFY] el-card wrapper
│       │   ├── WeekCard.vue              # [MODIFY] el-card wrapper
│       │   └── CreatorCard.vue           # [MODIFY] el-card wrapper
│       └── analysis/
│           ├── SubNavTabs.vue            # [MODIFY] el-tabs
│           ├── CreatorTable.vue          # [MODIFY] el-tag for ranks
│           ├── CategoryPanel.vue         # [MODIFY] el-card wrappers
│           ├── ForecastCards.vue         # [MODIFY] el-statistic
│           ├── FeatureImportance.vue     # [MODIFY] el-progress
│           └── ClusterCards.vue          # [MODIFY] el-tag
│       └── pages/
│           ├── HomePage.vue              # [MODIFY] el-skeleton loading, el-button
│           ├── AdminPage.vue             # [MODIFY] el-button, el-input
│           ├── browse/
│           │   ├── VideoLibraryPage.vue  # [MODIFY] el-skeleton, el-empty, el-button
│           │   ├── WeeksPage.vue         # [MODIFY] el-skeleton, el-empty, el-button
│           │   ├── CreatorsPage.vue      # [MODIFY] el-skeleton, el-empty, el-button
│           │   ├── CategoriesPage.vue    # [MODIFY] el-skeleton, el-empty, el-button
│           │   ├── VideoDetailPage.vue   # [MODIFY] el-skeleton, el-result, el-button
│           │   ├── WeekDetailPage.vue    # [MODIFY] el-skeleton, el-result, el-button
│           │   └── CreatorDetailPage.vue # [MODIFY] el-skeleton, el-result, el-button
│           └── analysis/
│               ├── StatsPage.vue         # [MODIFY] el-button
│               ├── ClusterPage.vue       # [MODIFY] el-button
│               ├── PredictPage.vue       # [MODIFY] el-button
│               ├── KeywordsPage.vue      # [MODIFY] el-button, el-segmented for week/category pills
│               └── ModelComparisonPage.vue # [MODIFY] el-button
```

---

## Phase 1 — Infrastructure & Shared/Layout Components

### Task 1: Add @element-plus/icons-vue dependency

**Files:**
- Modify: `app/ui/package.json`

- [ ] **Step 1: Install the icons package**

Run:
```bash
cd app/ui && pnpm add @element-plus/icons-vue
```

Expected: Installs the package and updates `package.json` + `pnpm-lock.yaml`.

- [ ] **Step 2: Verify the install**

Run:
```bash
cd app/ui && node -e "require('@element-plus/icons-vue')" 2>&1 || true
```

Expected: No error (or require of ES module error is fine — the import works in Vite).

- [ ] **Step 3: Commit**

```bash
git add app/ui/package.json app/ui/pnpm-lock.yaml
git commit -m "deps: add @element-plus/icons-vue for Element Plus icon migration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Add Element Plus CSS variable mapping to theme.css

**Files:**
- Modify: `app/ui/src/styles/theme.css`

- [ ] **Step 1: Append CSS variable mapping after the `@theme` block**

Open `app/ui/src/styles/theme.css`. After the closing `}` of `@theme` and before the `/* ── Base ── */` section, insert:

```css
/* ── Element Plus Theme Mapping ── */
:root {
  --el-color-primary: var(--color-blue);
  --el-color-primary-light-3: #33BEF0;
  --el-color-primary-light-5: #66CEF4;
  --el-color-primary-light-7: #99DFF7;
  --el-color-primary-light-8: #B3E8FA;
  --el-color-primary-light-9: #CCF0FC;
  --el-color-primary-dark-2: #008BC0;

  --el-color-success: var(--color-success);
  --el-color-warning: var(--color-warning);
  --el-color-danger: var(--color-danger);
  --el-color-info: var(--color-text-secondary);

  --el-bg-color: var(--color-bg);
  --el-bg-color-overlay: var(--color-card);
  --el-fill-color-blank: var(--color-card);

  --el-text-color-primary: var(--color-text);
  --el-text-color-regular: var(--color-text-secondary);

  --el-border-color: var(--color-border);
  --el-border-radius-base: var(--radius-default);
  --el-border-radius-round: 20px;

  --el-font-family: var(--font-family-sans);
}
```

- [ ] **Step 2: Verify the file builds**

Run:
```bash
cd app/ui && pnpm build 2>&1 | tail -5
```

Expected: Build succeeds. The CSS variables won't be used yet (no Element Plus import), but Tailwind should compile cleanly.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/styles/theme.css
git commit -m "style: map Element Plus CSS variables to project design tokens

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Switch main.ts to global Element Plus import

**Files:**
- Modify: `app/ui/src/main.ts`

- [ ] **Step 1: Replace the scrollbar-only import with global ElementPlus**

Replace the entire content of `app/ui/src/main.ts`:

```ts
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/theme.css'

const app = createApp(App)
app.use(ElementPlus)
app.use(router)
app.mount('#app')
```

The old line `import 'element-plus/es/components/scrollbar/style/css'` is removed. The `theme.css` import comes **after** `element-plus/dist/index.css` so our variable overrides take priority.

- [ ] **Step 2: Remove manual ElScrollbar imports from page components**

The pages `VideoLibraryPage.vue`, `WeeksPage.vue`, and `CreatorsPage.vue` each have `import { ElScrollbar } from 'element-plus'`. Since we now use `app.use(ElementPlus)`, the global registration makes these manual imports unnecessary. Remove these lines:

In `app/ui/src/pages/browse/VideoLibraryPage.vue` (line 6):
```ts
// REMOVE this line:
import { ElScrollbar } from 'element-plus'
```

In `app/ui/src/pages/browse/WeeksPage.vue` — if it has the same import, remove it. (Check first.)

In `app/ui/src/pages/browse/CreatorsPage.vue` — if it has the same import, remove it. (Check first.)

- [ ] **Step 3: Build check**

Run:
```bash
cd app/ui && pnpm build 2>&1 | tail -10
```

Expected: Build succeeds.

- [ ] **Step 4: Run unit tests**

```bash
cd app/ui && pnpm test:unit 2>&1 | tail -20
```

Expected: All existing tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/ui/src/main.ts app/ui/src/pages/browse/VideoLibraryPage.vue
# Add WeeksPage.vue and CreatorsPage.vue if they had ElScrollbar imports
git commit -m "refactor: switch to global Element Plus import, remove per-file scrollbar imports

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Refactor StatCard to use el-statistic + el-card

**Files:**
- Modify: `app/ui/src/components/shared/StatCard.vue`

**Important:** Keep the same props API (`label`, `value`, `subLabel?`). The existing test checks for `1.2万` formatting, so we keep the `fmt()` function. The test checks rendered text — it must still pass.

- [ ] **Step 1: Rewrite StatCard.vue**

Replace the entire file content of `app/ui/src/components/shared/StatCard.vue`:

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
  <el-card shadow="never" :body-style="{ padding: '24px' }">
    <el-statistic
      :title="label"
      :value="fmt(value)"
      :value-style="{
        color: 'var(--color-text)',
        fontWeight: 700,
        fontSize: '2rem',
        fontVariantNumeric: 'tabular-nums',
      }"
    />
    <p v-if="subLabel" class="text-xs text-text-secondary mt-1">{{ subLabel }}</p>
  </el-card>
</template>
```

- [ ] **Step 2: Run StatCard tests to verify they pass**

```bash
cd app/ui && pnpm test:unit -- --reporter=verbose src/components/shared/__tests__/StatCard.spec.ts 2>&1
```

Expected: All 4 tests pass. The `el-statistic` component renders `label` as title and `fmt(value)` as the value.

- [ ] **Step 3: Run full test suite**

```bash
cd app/ui && pnpm test:unit 2>&1 | tail -15
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add app/ui/src/components/shared/StatCard.vue
git commit -m "refactor(StatCard): replace Tailwind card with el-statistic + el-card

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Refactor SectionHeader to add optional el-divider

**Files:**
- Modify: `app/ui/src/components/shared/SectionHeader.vue`

**Important:** The existing test checks that when `description` is omitted, there are 0 `<p>` elements. The test must still pass.

- [ ] **Step 1: Rewrite SectionHeader.vue**

Replace the entire file content of `app/ui/src/components/shared/SectionHeader.vue`:

```vue
<script setup lang="ts">
withDefaults(defineProps<{
  title: string
  description?: string
  divider?: boolean
}>(), { divider: false })
</script>

<template>
  <div class="mb-6">
    <h2 class="text-xl font-semibold text-text">{{ title }}</h2>
    <p v-if="description" class="text-sm text-text-secondary mt-1">{{ description }}</p>
    <el-divider v-if="divider" style="margin: 12px 0 0 0" />
  </div>
</template>
```

The `divider` prop is optional (defaults to `false`) — no existing consumers break. Pages that want a divider add `<SectionHeader divider />`.

- [ ] **Step 2: Run SectionHeader tests**

```bash
cd app/ui && pnpm test:unit -- --reporter=verbose src/components/shared/__tests__/SectionHeader.spec.ts 2>&1
```

Expected: All 3 tests pass (title rendering, description rendering, no `<p>` when description omitted).

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/components/shared/SectionHeader.vue
git commit -m "refactor(SectionHeader): add optional el-divider prop

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Refactor AnalysisLoading to embed el-skeleton

**Files:**
- Modify: `app/ui/src/components/shared/AnalysisLoading.vue`

The scanner-line animation is a signature UI element — we preserve it intact. We only add `el-skeleton` rows below the scanner box to give structured loading feedback.

- [ ] **Step 1: Rewrite AnalysisLoading.vue**

Replace the entire file content of `app/ui/src/components/shared/AnalysisLoading.vue`:

```vue
<script setup lang="ts">
defineProps<{
  label?: string
}>()
</script>

<template>
  <div class="al-root">
    <div class="al-body">
      <!-- Scanner line container — preserved exactly as-is -->
      <div class="al-scanner-box">
        <div class="al-beam" />
        <div class="al-grid" />
        <div class="al-ghost-bars">
          <div class="al-bar" style="height:28px" />
          <div class="al-bar" style="height:56px" />
          <div class="al-bar" style="height:18px" />
          <div class="al-bar" style="height:72px" />
          <div class="al-bar" style="height:44px" />
          <div class="al-bar" style="height:64px" />
          <div class="al-bar" style="height:10px" />
        </div>
      </div>

      <div class="al-label-row">
        <span class="al-label-text">{{ label ?? '分析中…' }}</span>
        <div class="al-dots">
          <span class="al-dot" style="--dot-delay: 0s" />
          <span class="al-dot" style="--dot-delay: 0.25s" />
          <span class="al-dot" style="--dot-delay: 0.5s" />
        </div>
      </div>

      <!-- NEW: Structured skeleton rows below the scanner -->
      <div class="w-full max-w-[360px] space-y-3">
        <el-skeleton :rows="1" animated />
        <el-skeleton :rows="1" animated />
        <el-skeleton :rows="1" animated />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── Root ── */
.al-root {
  position: relative;
  width: 100%;
  overflow: hidden;
  border-radius: 16px;
  border: 1px solid var(--color-border, #E5E7EB);
  background: linear-gradient(180deg, #FAFBFC 0%, #F4F6F8 100%);
  user-select: none;
}

/* ── Body ── */
.al-body {
  padding: 20px 24px;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
}

/* ── Scanner box ── */
.al-scanner-box {
  position: relative;
  width: 100%;
  max-width: 360px;
  height: 128px;
  margin: 0 auto;
  overflow: hidden;
  border-radius: 8px;
  background: linear-gradient(180deg, #F0F2F5 0%, #E8EBEF 100%);
}

/* ── Scanning beam ── */
.al-beam {
  position: absolute;
  left: 0;
  width: 100%;
  height: 1.5px;
  pointer-events: none;
  background: linear-gradient(90deg,
    transparent 0%,
    rgba(0,174,236,0.15) 15%,
    rgba(0,174,236,0.55) 35%,
    rgba(0,174,236,0.8) 50%,
    rgba(0,174,236,0.55) 65%,
    rgba(0,174,236,0.15) 85%,
    transparent 100%
  );
  box-shadow: 0 0 12px rgba(0,174,236,0.25), 0 0 2px rgba(0,174,236,0.4);
  animation: al-sweep 2.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

/* ── Grid ── */
.al-grid {
  position: absolute;
  inset: 0;
  opacity: 0.04;
  pointer-events: none;
  background-image:
    repeating-linear-gradient(0deg, transparent, transparent 19px, #000 19px, #000 20px),
    repeating-linear-gradient(90deg, transparent, transparent 39px, #000 39px, #000 40px);
}

/* ── Ghost bars ── */
.al-ghost-bars {
  position: absolute;
  bottom: 16px;
  left: 24px;
  right: 24px;
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  gap: 12px;
  opacity: 0.12;
}

.al-bar {
  width: 20px;
  border-radius: 2px 2px 0 0;
  background: #00AEEC;
}

/* ── Label ── */
.al-label-row {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.al-label-text {
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: 0.025em;
  color: #00AEEC;
  animation: al-breathe 2.8s ease-in-out infinite;
}

/* ── Dots ── */
.al-dots {
  display: flex;
  align-items: center;
  gap: 4px;
}

.al-dot {
  display: inline-block;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #00AEEC;
  opacity: 0;
  animation: al-dot-pulse 1.6s ease-in-out infinite;
  animation-delay: var(--dot-delay, 0s);
}

/* ── Keyframes ── */
@keyframes al-sweep {
  0%   { top: -2px; opacity: 0; }
  8%   { top: -2px; opacity: 1; }
  45%  { top: calc(100% + 2px); opacity: 1; }
  55%  { top: calc(100% + 2px); opacity: 0; }
  100% { top: calc(100% + 2px); opacity: 0; }
}

@keyframes al-breathe {
  0%, 100% { opacity: 0.5; }
  50%      { opacity: 1; }
}

@keyframes al-dot-pulse {
  0%, 100% { opacity: 0.15; }
  50%      { opacity: 0.8; }
}
</style>
```

- [ ] **Step 2: Build check**

```bash
cd app/ui && pnpm build 2>&1 | tail -5
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/components/shared/AnalysisLoading.vue
git commit -m "refactor(AnalysisLoading): embed el-skeleton rows below scanner animation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Refactor Sidebar to use el-menu

**Files:**
- Modify: `app/ui/src/components/layout/Sidebar.vue`

**Critical constraint:** Must preserve the exact layout positioning: `fixed left-0 top-14 bottom-0 w-44` (176px wide, starts below the 56px TopNav). The el-menu must not break the `lg:ml-[max(11rem,calc((100%-80rem)/2))]` centering logic in PageShell.

- [ ] **Step 1: Rewrite Sidebar.vue**

Replace the entire file content of `app/ui/src/components/layout/Sidebar.vue`:

```vue
<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { useRoute } from 'vue-router'
import {
  VideoPlay, Calendar, User, Grid, DataAnalysis,
  ScatterPlot, TrendCharts, Cloudy, Coin,
} from '@element-plus/icons-vue'

const route = useRoute()

interface NavLink { to: string; label: string; icon: ReturnType<typeof shallowRef> }

const iconMap: Record<string, any> = {
  video: VideoPlay,
  calendar: Calendar,
  users: User,
  grid: Grid,
  chart: DataAnalysis,
  scatter: ScatterPlot,
  trend: TrendCharts,
  cloud: Cloudy,
  experiment: Coin,
}

const BROWSE_LINKS: NavLink[] = [
  { to: '/videos', label: '视频库', icon: VideoPlay },
  { to: '/weeks', label: '周报', icon: Calendar },
  { to: '/creators', label: '创作者', icon: User },
  { to: '/categories', label: '分区', icon: Grid },
]

const ANALYSIS_LINKS: NavLink[] = [
  { to: '/analysis/stats', label: '统计概览', icon: DataAnalysis },
  { to: '/analysis/clusters', label: '聚类分析', icon: ScatterPlot },
  { to: '/analysis/predictions', label: '预测分析', icon: TrendCharts },
  { to: '/analysis/keywords', label: '内容洞察', icon: Cloudy },
  { to: '/analysis/models', label: '模型对比', icon: Coin },
]

const links = computed<NavLink[]>(() => {
  if (route.path.startsWith('/analysis')) return ANALYSIS_LINKS
  return BROWSE_LINKS
})

const sectionLabel = computed(() => {
  if (route.path.startsWith('/analysis')) return '分析'
  return '浏览'
})

function isActive(link: NavLink) {
  if (link.to === '/videos') return route.path.startsWith('/videos')
  if (link.to === '/weeks') return route.path.startsWith('/weeks')
  if (link.to === '/creators') return route.path.startsWith('/creators')
  return route.path === link.to
}
</script>

<template>
  <el-menu
    :default-active="route.path"
    :router="true"
    :ellipsis="false"
    class="sidebar-menu !fixed !left-0 !top-14 !bottom-0 !w-44 !z-30 !bg-bg/95 !backdrop-blur-sm !border-0 !pt-6"
  >
    <el-menu-item-group :title="sectionLabel">
      <el-menu-item
        v-for="link in links"
        :key="link.to"
        :index="link.to"
        class="sidebar-item"
      >
        <el-icon class="!w-4 !h-4 !shrink-0"><component :is="link.icon" /></el-icon>
        <span class="!text-[0.875rem] !font-medium">{{ link.label }}</span>
      </el-menu-item>
    </el-menu-item-group>
  </el-menu>
</template>

<style scoped>
/* Match original Sidebar visual style */
.sidebar-menu {
  --el-menu-bg-color: transparent;
  --el-menu-text-color: var(--color-text-secondary);
  --el-menu-hover-bg-color: transparent;
  --el-menu-active-color: var(--color-blue);

  /* Override el-menu-item-group title style */
  :deep(.el-menu-item-group__title) {
    padding: 0 12px 16px;
    font-size: 0.6875rem;
    font-weight: 600;
    color: rgba(107, 114, 128, 0.6);
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
}

.sidebar-item {
  margin: 0;
  padding: 8px 12px !important;
  height: auto !important;
  line-height: 1.5 !important;
  gap: 12px;
}

.sidebar-item.is-active {
  color: var(--color-blue) !important;
  font-weight: 600;
}
</style>
```

- [ ] **Step 2: Build check**

```bash
cd app/ui && pnpm build 2>&1 | tail -10
```

Expected: Build succeeds with no new errors.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/components/layout/Sidebar.vue
git commit -m "refactor(Sidebar): replace custom nav with el-menu vertical + router mode

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Refactor TopNav to use el-menu horizontal mode

**Files:**
- Modify: `app/ui/src/components/layout/TopNav.vue`

**Important:** The existing test checks for "BiliInsight" text, link count ≥2, and active route uses `!text-text`. Must keep the test passing.

- [ ] **Step 1: Rewrite TopNav.vue**

Replace the entire file content of `app/ui/src/components/layout/TopNav.vue`:

```vue
<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { Setting } from '@element-plus/icons-vue'
import ReanalyzeButton from '@/components/shared/ReanalyzeButton.vue'

const route = useRoute()
const router = useRouter()

function isAnalysisActive() {
  return route.path.startsWith('/analysis')
}
function isBrowseActive() {
  return ['/videos', '/weeks', '/creators', '/categories'].some(p => route.path.startsWith(p))
}

function onReanalyzeDone(success: boolean) {
  if (success) router.replace(route.fullPath)
}
</script>

<template>
  <nav class="sticky top-0 z-100 bg-bg/85 backdrop-blur-md border-b border-border">
    <div class="max-w-7xl mx-auto px-6 flex items-center h-14 gap-8">
      <!-- Logo -->
      <router-link to="/" class="text-lg font-bold text-text no-underline tracking-[-0.01em] shrink-0">
        Bili<span class="text-blue">Insight</span>
      </router-link>

      <!-- Desktop nav via el-menu horizontal -->
      <div class="hidden lg:flex flex-1 items-center">
        <el-menu
          mode="horizontal"
          :default-active="route.path"
          :router="true"
          :ellipsis="false"
          class="topnav-menu !border-0 !bg-transparent !flex-1"
        >
          <el-menu-item index="/" class="topnav-item">发现</el-menu-item>
          <el-menu-item index="/analysis/stats" class="topnav-item">分析</el-menu-item>
          <el-menu-item index="/videos" class="topnav-item">浏览</el-menu-item>
        </el-menu>
      </div>

      <!-- Mobile nav (3 links, Browse has dropdown) -->
      <ul class="flex gap-6 list-none lg:hidden">
        <li>
          <router-link
            to="/"
            class="no-underline text-[0.9375rem] font-medium text-text-secondary px-0 py-1
                   transition-colors duration-200 relative hover:text-text"
            :class="{ 'text-text!': route.path === '/' }"
          >
            发现
            <span v-if="route.path === '/'" class="absolute -bottom-4 left-0 right-0 h-0.5 bg-blue rounded-sm" />
          </router-link>
        </li>
        <li>
          <router-link
            to="/analysis/stats"
            class="no-underline text-[0.9375rem] font-medium text-text-secondary px-0 py-1
                   transition-colors duration-200 relative hover:text-text"
            :class="{ 'text-text!': isAnalysisActive() }"
          >
            分析
            <span v-if="isAnalysisActive()" class="absolute -bottom-4 left-0 right-0 h-0.5 bg-blue rounded-sm" />
          </router-link>
        </li>
        <li class="relative group">
          <router-link
            to="/videos"
            class="no-underline text-[0.9375rem] font-medium text-text-secondary px-0 py-1
                   transition-colors duration-200 relative hover:text-text"
            :class="{ 'text-text!': isBrowseActive() }"
          >
            浏览
            <span v-if="isBrowseActive()" class="absolute -bottom-4 left-0 right-0 h-0.5 bg-blue rounded-sm" />
          </router-link>
          <div class="absolute top-full left-1/2 -translate-x-1/2 mt-3
                      bg-card rounded-[12px] shadow-[0_8px_32px_rgba(0,0,0,0.10)]
                      border border-border p-1.5 min-w-32.5 flex flex-col
                      opacity-0 invisible group-hover:opacity-100 group-hover:visible
                      transition-[opacity,visibility] duration-150">
            <router-link to="/videos" class="block px-3.5 py-2 rounded-md text-sm text-text-secondary no-underline transition-colors duration-100 hover:bg-bg hover:text-text">视频库</router-link>
            <router-link to="/weeks" class="block px-3.5 py-2 rounded-md text-sm text-text-secondary no-underline transition-colors duration-100 hover:bg-bg hover:text-text">周报</router-link>
            <router-link to="/creators" class="block px-3.5 py-2 rounded-md text-sm text-text-secondary no-underline transition-colors duration-100 hover:bg-bg hover:text-text">创作者</router-link>
            <router-link to="/categories" class="block px-3.5 py-2 rounded-md text-sm text-text-secondary no-underline transition-colors duration-100 hover:bg-bg hover:text-text">分区</router-link>
          </div>
        </li>
      </ul>

      <!-- Right side actions -->
      <ReanalyzeButton v-if="isAnalysisActive()" class="ml-auto" @done="onReanalyzeDone" />
      <router-link
        to="/admin"
        class="no-underline text-text-secondary hover:text-text transition-colors"
        :class="[{ 'ml-auto': !isAnalysisActive(), 'text-blue!': route.path === '/admin' }]"
        title="管理后台"
      >
        <el-icon class="!w-5 !h-5"><Setting /></el-icon>
      </router-link>
    </div>
  </nav>
</template>

<style scoped>
.topnav-menu {
  --el-menu-bg-color: transparent;
  --el-menu-text-color: var(--color-text-secondary);
  --el-menu-hover-text-color: var(--color-text);
  --el-menu-active-color: var(--color-text);
  --el-menu-horizontal-sub-item-height: 56px;
}

.topnav-item {
  font-size: 0.9375rem !important;
  font-weight: 500 !important;
  height: 56px !important;
  line-height: 56px !important;
  padding: 0 12px !important;
  border-bottom-color: var(--color-blue) !important;
}

.topnav-item:hover {
  color: var(--color-text) !important;
}

/* Hide el-menu's default border-bottom */
:deep(.el-menu--horizontal) {
  border-bottom: none !important;
}
</style>
```

**Note on tests:** The existing TopNav test checks for:
1. "BiliInsight" text — preserved in logo `<router-link>`
2. Link count ≥2 — desktop el-menu + mobile `<ul>` both have ≥2 links
3. Active route class `!text-text` — mobile links still use this class

- [ ] **Step 2: Run TopNav tests**

```bash
cd app/ui && pnpm test:unit -- --reporter=verbose src/components/layout/__tests__/TopNav.spec.ts 2>&1
```

Expected: All 3 tests pass.

- [ ] **Step 3: Build check**

```bash
cd app/ui && pnpm build 2>&1 | tail -10
```

Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add app/ui/src/components/layout/TopNav.vue
git commit -m "refactor(TopNav): use el-menu horizontal for desktop nav, el-button for admin link

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Refactor ReanalyzeButton to use el-button + el-popover + el-input

**Files:**
- Modify: `app/ui/src/components/shared/ReanalyzeButton.vue`

This component currently has hand-rolled button, popover, input, and click-outside logic. Replace with Element Plus equivalents.

- [ ] **Step 1: Rewrite ReanalyzeButton.vue**

Replace the entire file content of `app/ui/src/components/shared/ReanalyzeButton.vue`:

```vue
<script setup lang="ts">
import { computed, ref, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import { triggerTask, fetchPipelineHistory } from '@/composables/useApi'

const emit = defineEmits<{ done: [success: boolean] }>()

const route = useRoute()
const TASK_FOR_PATH: Record<string, string> = {
  '/analysis/stats': 'statistics',
  '/analysis/clusters': 'clustering',
  '/analysis/predictions': 'prediction',
  '/analysis/keywords': 'keywords',
  '/analysis/models': 'model_comparison',
}
const taskName = computed(() => TASK_FOR_PATH[route.path] ?? '')

const hasKey = ref(!!localStorage.getItem('admin_api_key'))
const showPopover = ref(false)
const keyInput = ref('')

function togglePopover() {
  if (hasKey.value) { run(); return }
  showPopover.value = !showPopover.value
}

function saveKey() {
  const v = keyInput.value.trim()
  if (!v) return
  localStorage.setItem('admin_api_key', v)
  hasKey.value = true
  keyInput.value = ''
  showPopover.value = false
}

// ── Run + poll ──
const phase = ref<'idle' | 'running' | 'polling'>('idle')
const pollMsg = ref('')
const pollError = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

async function run() {
  if (phase.value !== 'idle' || !taskName.value) return
  phase.value = 'running'
  pollMsg.value = ''
  pollError.value = false
  try {
    await triggerTask(taskName.value)
    phase.value = 'polling'
    pollMsg.value = '分析中…'
    startPolling()
  } catch (e: any) {
    pollMsg.value = `✗ ${e.message || e}`
    pollError.value = true
    phase.value = 'idle'
  }
}

function startPolling() {
  pollTimer = setInterval(async () => {
    try {
      const history = await fetchPipelineHistory(`_task_${taskName.value}`, 1)
      if (history && history.length > 0) {
        const latest = history[0]
        if (latest.status === 'success') {
          stopPolling()
          pollMsg.value = '✓ 完成'
          phase.value = 'idle'
          emit('done', true)
          setTimeout(() => { pollMsg.value = '' }, 3000)
        } else if (latest.status === 'failed') {
          stopPolling()
          pollMsg.value = '✗ 失败'
          pollError.value = true
          phase.value = 'idle'
          emit('done', false)
        }
      }
    } catch {
      // Network error during poll — keep trying
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onUnmounted(() => stopPolling())
</script>

<template>
  <div v-if="taskName" class="inline-flex items-center gap-2">
    <span
      v-if="pollMsg"
      class="text-xs font-medium"
      :class="pollError ? 'text-danger' : phase === 'polling' ? 'text-blue' : 'text-success'"
    >{{ pollMsg }}</span>

    <el-popover
      v-model:visible="showPopover"
      placement="bottom-end"
      :width="288"
      trigger="click"
      :disabled="hasKey"
    >
      <template #reference>
        <el-button
          @click="togglePopover"
          :disabled="phase !== 'idle'"
          :loading="phase !== 'idle'"
          size="small"
          text
        >
          <el-icon v-if="phase === 'idle'" class="!w-3.5 !h-3.5"><Refresh /></el-icon>
          {{ phase === 'polling' ? '分析中…' : '重新分析' }}
        </el-button>
      </template>

      <p class="text-xs text-text-secondary mb-3">
        输入管理员 API Key。Key 在启动服务时自动生成并打印在控制台。
      </p>
      <div class="flex gap-2">
        <el-input
          v-model="keyInput"
          type="password"
          placeholder="粘贴 API Key…"
          @keyup.enter="saveKey"
        />
        <el-button type="primary" :disabled="!keyInput.trim()" @click="saveKey">
          保存
        </el-button>
      </div>
      <el-button link type="info" class="mt-2 text-xs" @click="showPopover = false">
        取消
      </el-button>
    </el-popover>
  </div>
</template>
```

- [ ] **Step 2: Build check**

```bash
cd app/ui && pnpm build 2>&1 | tail -10
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/components/shared/ReanalyzeButton.vue
git commit -m "refactor(ReanalyzeButton): replace hand-rolled popover/input/button with el-popover + el-input + el-button

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Phase 1 verification — full build + tests + visual check

- [ ] **Step 1: Run full unit test suite**

```bash
cd app/ui && pnpm test:unit 2>&1
```

Expected: All tests pass. Zero failures.

- [ ] **Step 2: Run production build**

```bash
cd app/ui && pnpm build 2>&1
```

Expected: Build succeeds with no errors.

- [ ] **Step 3: Visual dev server check**

```bash
cd app/ui && pnpm dev
```

Expected: Dev server starts. Manually verify at least these pages:
- HomePage (`/`) — StatCard numbers are correct, TopNav has BiliInsight logo
- VideoLibraryPage (`/videos`) — el-scrollbar still works, VideoCards render
- StatsPage (`/analysis/stats`) — Sidebar shows el-menu items, StatCards render
- AdminPage (`/admin`) — buttons work

- [ ] **Step 4: Commit (if any minor fixes)**

```bash
git add -A
git commit -m "chore: Phase 1 verification fixes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

Or if no changes needed, proceed to Phase 2.

---

## Phase 2 — Business & Analysis Components + Page States

### Task 11: Refactor SearchBar to use el-input

**Files:**
- Modify: `app/ui/src/components/business/SearchBar.vue`

- [ ] **Step 1: Rewrite SearchBar.vue**

Replace the entire file content:

```vue
<script setup lang="ts">
import { ref, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  modelValue: string
  placeholder?: string
}>(), { placeholder: '搜索…' })

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const input = ref(props.modelValue)
let timer: ReturnType<typeof setTimeout> | null = null

watch(input, (v) => {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => emit('update:modelValue', v), 300)
})
</script>

<template>
  <el-input
    v-model="input"
    :placeholder="placeholder"
    :prefix-icon="Search"
    clearable
    class="search-bar-input"
  />
</template>

<style scoped>
.search-bar-input {
  flex: 1;
  min-width: 260px;
  max-width: 400px;
  --el-input-border-radius: 12px;
  --el-input-border-color: var(--color-border);
  --el-input-bg-color: var(--color-card);
}
</style>
```

- [ ] **Step 2: Build check**

```bash
cd app/ui && pnpm build 2>&1 | tail -10
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/components/business/SearchBar.vue
git commit -m "refactor(SearchBar): replace custom input with el-input search mode

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: Refactor SortTabs to use el-segmented

**Files:**
- Modify: `app/ui/src/components/business/SortTabs.vue`

**Important:** The `options` prop type changes from `{ key: string; label: string }[]` to the format `el-segmented` expects, which is `{ label: string; value: string }[]`. The `modelValue` and `update:modelValue` semantics are preserved.

- [ ] **Step 1: Rewrite SortTabs.vue**

Replace the entire file content:

```vue
<script setup lang="ts">
defineProps<{
  options: { key: string; label: string }[]
  modelValue: string
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <el-segmented
    :model-value="modelValue"
    :options="options.map(o => ({ label: o.label, value: o.key }))"
    @update:model-value="emit('update:modelValue', $event as string)"
  />
</template>
```

- [ ] **Step 2: Build check**

```bash
cd app/ui && pnpm build 2>&1 | tail -10
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/components/business/SortTabs.vue
git commit -m "refactor(SortTabs): replace pill buttons with el-segmented

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: Refactor FilterDropdown to use el-select

**Files:**
- Modify: `app/ui/src/components/business/FilterDropdown.vue`

This is the biggest single code reduction — from ~92 lines to ~25 lines. The click-outside, toggle, open/close hand-rolled logic is replaced by `el-select`.

- [ ] **Step 1: Rewrite FilterDropdown.vue**

Replace the entire file content:

```vue
<script setup lang="ts">
defineProps<{
  label: string
  options: { key: number; label: string; count?: number }[]
  modelValue: number | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
}>()
</script>

<template>
  <el-select
    :model-value="modelValue"
    :placeholder="label"
    clearable
    class="filter-select"
    @update:model-value="emit('update:modelValue', $event as number | null)"
  >
    <el-option
      v-for="opt in options"
      :key="opt.key"
      :label="opt.label"
      :value="opt.key"
    >
      <span>{{ opt.label }}</span>
      <span v-if="opt.count !== undefined" class="tabular opacity-50 float-right ml-2">{{ opt.count }}</span>
    </el-option>
  </el-select>
</template>

<style scoped>
.filter-select {
  --el-border-radius-base: 20px;
  --el-border-color: var(--color-border);
}
</style>
```

- [ ] **Step 2: Build check**

```bash
cd app/ui && pnpm build 2>&1 | tail -10
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/components/business/FilterDropdown.vue
git commit -m "refactor(FilterDropdown): replace 90-line custom dropdown with el-select (~25 lines)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 14: Refactor SubNavTabs to use el-tabs

**Files:**
- Modify: `app/ui/src/components/analysis/SubNavTabs.vue`

- [ ] **Step 1: Rewrite SubNavTabs.vue**

Replace the entire file content:

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { TabsPaneContext } from 'element-plus'

const TABS = [
  { key: 'stats', label: '统计概览', path: '/analysis/stats' },
  { key: 'clusters', label: '聚类分析', path: '/analysis/clusters' },
  { key: 'predict', label: '预测分析', path: '/analysis/predictions' },
  { key: 'keywords', label: '内容洞察', path: '/analysis/keywords' },
  { key: 'models', label: '模型对比', path: '/analysis/models' },
] as const

const router = useRouter()
const route = useRoute()

const activeKey = computed(() => {
  if (route.path.includes('keywords')) return 'keywords'
  if (route.path.includes('models')) return 'models'
  if (route.path.includes('clusters')) return 'clusters'
  if (route.path.includes('predict')) return 'predict'
  return 'stats'
})

function go(tab: TabsPaneContext) {
  const key = tab.paneName as string
  const found = TABS.find(t => t.key === key)
  if (found) router.push(found.path)
}
</script>

<template>
  <el-tabs
    :model-value="activeKey"
    @tab-click="go"
    class="mb-8 subnav-tabs"
  >
    <el-tab-pane
      v-for="tab in TABS"
      :key="tab.key"
      :label="tab.label"
      :name="tab.key"
    />
  </el-tabs>
</template>

<style scoped>
.subnav-tabs {
  --el-tabs-header-height: 44px;
}
</style>
```

- [ ] **Step 2: Build check**

```bash
cd app/ui && pnpm build 2>&1 | tail -10
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/components/analysis/SubNavTabs.vue
git commit -m "refactor(SubNavTabs): replace custom tab buttons with el-tabs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 15: Refactor VideoCard, WeekCard, CreatorCard to use el-card

**Files:**
- Modify: `app/ui/src/components/business/VideoCard.vue`
- Modify: `app/ui/src/components/business/WeekCard.vue`
- Modify: `app/ui/src/components/business/CreatorCard.vue`

For all three cards, wrap the outermost element with `<el-card>` and adjust shadow/hover behavior to use Element Plus's built-in `shadow` prop.

- [ ] **Step 1: Rewrite VideoCard.vue**

Replace the entire file content:

```vue
<script setup lang="ts">
import type { VideoSummary } from '@/types/api'
import { proxyImage } from '@/composables/useImageProxy'
import { VideoPlay } from '@element-plus/icons-vue'

const props = defineProps<{ video: VideoSummary }>()

function fmt(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(1)}万` : String(n)
}

function openBili() {
  if (props.video.bvid) {
    window.open(`https://www.bilibili.com/video/${props.video.bvid}`, '_blank')
  }
}
</script>

<template>
  <router-link
    :to="`/videos/${video.aid}`"
    class="group block cursor-pointer no-underline"
  >
    <el-card shadow="hover" :body-style="{ padding: '0' }" class="video-card">
      <div class="relative h-45 bg-border overflow-hidden">
        <img
          v-if="proxyImage(video.cover_url)"
          :src="proxyImage(video.cover_url)!"
          :alt="video.title"
          class="w-full h-full object-cover"
          loading="lazy"
        />
        <div v-else class="w-full h-full flex items-center justify-center text-text-secondary text-sm">
          暂无封面
        </div>
        <!-- B站跳转按钮 -->
        <span
          v-if="video.bvid"
          @click.prevent.stop="openBili"
          class="absolute top-2 right-2 bg-white/90 hover:bg-white text-blue text-xs
                 w-6 h-6 rounded-full flex items-center justify-center cursor-pointer
                 opacity-0 group-hover:opacity-100 transition-opacity duration-150
                 shadow-sm"
          title="在B站观看"
        >
          <el-icon class="!w-3 !h-3"><VideoPlay /></el-icon>
        </span>
        <span
          v-if="video.duration"
          class="absolute bottom-2 right-2 bg-black/75 text-white text-xs px-1.5 py-0.5 rounded tabular"
        >
          {{ video.duration }}
        </span>
      </div>
      <div class="p-[14px_16px]">
        <h3 class="text-[0.9375rem] font-semibold text-text leading-snug mb-2 line-clamp-2">
          {{ video.title }}
        </h3>
        <div class="flex gap-4 text-[0.8125rem] text-text-secondary tabular mb-2">
          <span>&#9654; {{ fmt(video.view) }}</span>
          <span>&#128077; {{ fmt(video.like_cnt) }}</span>
        </div>
      </div>
      <div class="flex items-center justify-between px-4 py-2.5 border-t border-border text-[0.8125rem]">
        <span class="text-text font-medium truncate">{{ video.creator_name || '未知' }}</span>
        <span v-if="video.category_name" class="bg-blue-light text-blue px-2 py-0.5 rounded text-xs">
          {{ video.category_name }}
        </span>
      </div>
    </el-card>
  </router-link>
</template>

<style scoped>
.video-card {
  --el-card-border-radius: 12px;
  --el-card-border-color: transparent;
}
</style>
```

- [ ] **Step 2: Rewrite WeekCard.vue**

Replace the entire file content:

```vue
<script setup lang="ts">
import type { WeekItem } from '@/types/api'

defineProps<{ week: WeekItem }>()

const COLORS = ['#00AEEC', '#22C55E', '#F59E0B', '#8B5CF6', '#EF4444', '#10B981', '#EC4899', '#6366F1']
</script>

<template>
  <router-link
    :to="`/weeks/${week.number}`"
    class="block cursor-pointer no-underline"
  >
    <el-card shadow="hover" :body-style="{ padding: '0' }" class="week-card">
      <div
        class="h-[200px] relative overflow-hidden"
        :style="{ background: `linear-gradient(135deg, ${COLORS[week.number % COLORS.length]}, ${COLORS[(week.number + 1) % COLORS.length]})` }"
      >
        <div class="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
        <span class="absolute top-4 left-4 bg-white/90 backdrop-blur px-[14px] py-1 rounded-[20px]
                     text-[0.8125rem] font-bold text-blue tracking-[-0.01em]">
          第 {{ week.number }} 期
        </span>
        <h3 class="absolute bottom-4 left-4 right-4 text-white text-lg font-bold leading-snug
                   drop-shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
          {{ week.subject || '无主题' }}
        </h3>
      </div>
      <div class="flex items-center justify-between px-5 py-4 gap-3">
        <span class="text-sm text-text-secondary font-medium truncate">{{ week.name || '' }}</span>
        <span class="bg-blue-light text-blue font-semibold px-[10px] py-[3px] rounded-md text-[0.8125rem] tabular">
          {{ week.video_count }} 个视频
        </span>
      </div>
    </el-card>
  </router-link>
</template>

<style scoped>
.week-card {
  --el-card-border-radius: 16px;
  --el-card-border-color: transparent;
}
</style>
```

- [ ] **Step 3: Rewrite CreatorCard.vue**

Replace the entire file content:

```vue
<script setup lang="ts">
import type { CreatorSummary } from '@/types/api'
import { proxyImage } from '@/composables/useImageProxy'
import { User } from '@element-plus/icons-vue'

defineProps<{ creator: CreatorSummary }>()

function fmt(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(1)}万` : String(n)
}
</script>

<template>
  <router-link
    :to="`/creators/${creator.mid}`"
    class="cursor-pointer no-underline"
  >
    <el-card shadow="hover" :body-style="{ padding: '16px' }" class="creator-card">
      <div class="flex items-center gap-4">
        <img
          v-if="proxyImage(creator.face)"
          :src="proxyImage(creator.face)!"
          :alt="creator.name"
          class="w-12 h-12 rounded-full object-cover shrink-0"
        />
        <div v-else class="w-12 h-12 rounded-full bg-border shrink-0 flex items-center justify-center text-text-secondary text-xs">
          <el-icon class="!w-5 !h-5"><User /></el-icon>
        </div>
        <div class="flex-1 min-w-0">
          <p class="font-semibold text-text text-sm truncate">{{ creator.name }}</p>
          <p class="text-xs text-text-secondary mt-0.5">
            {{ creator.video_count }} 个视频 &middot; {{ fmt(creator.total_views) }} 总播放
          </p>
        </div>
      </div>
    </el-card>
  </router-link>
</template>

<style scoped>
.creator-card {
  --el-card-border-radius: 12px;
  --el-card-border-color: transparent;
}
</style>
```

- [ ] **Step 4: Build check**

```bash
cd app/ui && pnpm build 2>&1 | tail -10
```

Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
git add app/ui/src/components/business/VideoCard.vue app/ui/src/components/business/WeekCard.vue app/ui/src/components/business/CreatorCard.vue
git commit -m "refactor(cards): wrap VideoCard/WeekCard/CreatorCard with el-card, use el-icon

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 16: Refactor analysis components (CreatorTable, CategoryPanel, ForecastCards, FeatureImportance, ClusterCards)

**Files:**
- Modify: `app/ui/src/components/analysis/CreatorTable.vue`
- Modify: `app/ui/src/components/analysis/CategoryPanel.vue`
- Modify: `app/ui/src/components/analysis/ForecastCards.vue`
- Modify: `app/ui/src/components/analysis/FeatureImportance.vue`
- Modify: `app/ui/src/components/analysis/ClusterCards.vue`

These are lighter changes — replace `<table>` internals with `el-tag` for ranks, custom progress bars with `el-progress`, etc.

- [ ] **Step 1: Rewrite CreatorTable.vue** — replace rank numbers with el-tag

Replace the entire file content:

```vue
<script setup lang="ts">
import SectionHeader from '@/components/shared/SectionHeader.vue'
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
              <el-tag size="small" :type="i < 3 ? 'primary' : 'info'" class="mr-2">{{ i + 1 }}</el-tag>
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
```

- [ ] **Step 2: Rewrite CategoryPanel.vue** — no structural change needed (already minimal)

No changes needed — this component already uses SectionHeader and CategoryBarChart only.

- [ ] **Step 3: Rewrite ForecastCards.vue** — pass-through to StatCard

No changes needed — it already uses StatCard which was refactored in Phase 1.

- [ ] **Step 4: Rewrite FeatureImportance.vue** — use el-progress

Replace the entire file content:

```vue
<script setup lang="ts">
import { computed } from 'vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'

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
        <div class="flex-1">
          <el-progress
            :percentage="Number((score * 100).toFixed(1))"
            :stroke-width="8"
            :show-text="false"
            color="var(--color-blue)"
          />
        </div>
        <span class="text-sm tabular font-medium text-text w-12 text-right">
          {{ (score * 100).toFixed(1) }}%
        </span>
      </div>
    </div>
  </section>
</template>
```

- [ ] **Step 5: Rewrite ClusterCards.vue** — use el-tag for labels

Replace the entire file content:

```vue
<script setup lang="ts">
import SectionHeader from '@/components/shared/SectionHeader.vue'
import type { ClusterGroup } from '@/types/api'

defineProps<{ clusters: ClusterGroup[] }>()

const CLUSTER_COLORS: Record<number, string> = {
  0: '#00AEEC', 1: '#22C55E', 2: '#F59E0B',
}
const TAG_TYPES: Record<number, '' | 'success' | 'warning'> = {
  0: '', 1: 'success', 2: 'warning',
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
        <p class="text-lg font-bold text-text mb-1">
          <el-tag :type="TAG_TYPES[c.label] ?? 'info'" size="small" effect="dark" class="mr-2">{{ c.tag }}</el-tag>
        </p>
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
```

- [ ] **Step 6: Build check**

```bash
cd app/ui && pnpm build 2>&1 | tail -10
```

Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
git add app/ui/src/components/analysis/CreatorTable.vue app/ui/src/components/analysis/FeatureImportance.vue app/ui/src/components/analysis/ClusterCards.vue
git commit -m "refactor(analysis): use el-tag/el-progress in CreatorTable, FeatureImportance, ClusterCards

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 17: Unify page states — el-result, el-empty, el-skeleton across all pages

**Files:**
- Modify: `app/ui/src/pages/HomePage.vue`
- Modify: `app/ui/src/pages/browse/VideoLibraryPage.vue`
- Modify: `app/ui/src/pages/browse/WeeksPage.vue`
- Modify: `app/ui/src/pages/browse/CreatorsPage.vue`
- Modify: `app/ui/src/pages/browse/CategoriesPage.vue`
- Modify: `app/ui/src/pages/browse/VideoDetailPage.vue`
- Modify: `app/ui/src/pages/browse/WeekDetailPage.vue`
- Modify: `app/ui/src/pages/browse/CreatorDetailPage.vue`
- Modify: `app/ui/src/pages/analysis/StatsPage.vue`
- Modify: `app/ui/src/pages/analysis/ClusterPage.vue`
- Modify: `app/ui/src/pages/analysis/PredictPage.vue`
- Modify: `app/ui/src/pages/analysis/KeywordsPage.vue`
- Modify: `app/ui/src/pages/analysis/ModelComparisonPage.vue`
- Modify: `app/ui/src/pages/AdminPage.vue`

This is a mechanical replacement across all pages. The pattern is consistent across all pages:

**Error states:** Replace custom error divs with:
```vue
<el-result icon="error" title="加载失败" :sub-title="(error as Error).message">
  <template #extra>
    <el-button type="primary" @click="send()">重试</el-button>
  </template>
</el-result>
```

**Loading skeleton states (browse pages):** Replace `animate-pulse` divs with:
```vue
<el-skeleton :rows="6" animated />
```

**Empty states:** Replace custom empty divs with:
```vue
<el-empty :description="categoryTid || search ? '没有匹配的视频' : '暂无视频数据'">
  <template #extra v-if="categoryTid || search">
    <el-button link type="primary" @click="categoryTid = null; search = ''; resetAndLoad()">清除筛选</el-button>
  </template>
</el-empty>
```

- [ ] **Step 1: Rewrite error states in all 5 analysis pages**

Open each analysis page and replace the error block. The pattern for all 5 (StatsPage, ClusterPage, PredictPage, KeywordsPage, ModelComparisonPage) is identical:

Find the pattern:
```vue
<div v-else-if="error" class="py-12 text-center">
  <div class="bg-card rounded-[16px] p-12 shadow-(--shadow-default) max-w-md mx-auto">
    <p class="text-lg font-semibold text-text mb-2">加载失败，请重试</p>
    <p class="text-sm text-text-secondary mb-6">{{ (error as Error).message }}</p>
    <button @click="send()" class="...">重试</button>
  </div>
</div>
```

Replace with:
```vue
<div v-else-if="error" class="py-12">
  <el-result icon="error" title="加载失败" :sub-title="(error as Error).message">
    <template #extra>
      <el-button type="primary" @click="send()">重试</el-button>
    </template>
  </el-result>
</div>
```

- [ ] **Step 2: Rewrite empty states in all 5 analysis pages**

Find the pattern:
```vue
<div v-else class="py-12 text-center">
  <p class="text-text-secondary">暂无数据，请先触发一次数据采集与分析</p>
</div>
```

Replace with:
```vue
<div v-else class="py-12">
  <el-empty description="暂无数据，请先触发一次数据采集与分析" :image-size="120" />
</div>
```

- [ ] **Step 3: Rewrite browse pages — VideoLibraryPage, WeeksPage, CreatorsPage, CategoriesPage**

For browse pages, replace the loading skeleton and empty states.

VideoLibraryPage loading skeleton — replace:
```vue
<div v-if="loading && videos.length === 0" class="grid grid-cols-3 gap-5 pb-8">
  <div v-for="i in 6" :key="i" class="h-80 bg-card rounded-[12px] animate-pulse" />
</div>
```

With:
```vue
<div v-if="loading && videos.length === 0" class="pb-8">
  <el-skeleton :rows="6" animated />
</div>
```

Same pattern for WeeksPage and CreatorsPage.

For CategoriesPage — if it has similar patterns, apply same replacement.

- [ ] **Step 4: Rewrite detail pages — VideoDetailPage, WeekDetailPage, CreatorDetailPage**

In VideoDetailPage, replace the loading skeleton:
```vue
<div v-if="loading" class="space-y-6 py-8">
  <div class="h-[400px] bg-card rounded-[16px] animate-pulse" />
  <div class="h-32 bg-card rounded-[12px] animate-pulse" />
</div>
```

With:
```vue
<div v-if="loading" class="py-8">
  <el-skeleton :rows="4" animated />
</div>
```

Replace the error block:
```vue
<div v-else-if="error" class="py-24 text-center">
  <p class="text-lg font-semibold text-text mb-2">加载失败</p>
  <p class="text-sm text-text-secondary mb-6">{{ (error as Error).message }}</p>
  <button @click="send()" class="...">重试</button>
  <button @click="router.back()" class="...">返回</button>
</div>
```

With:
```vue
<div v-else-if="error" class="py-24">
  <el-result icon="error" title="加载失败" :sub-title="(error as Error).message">
    <template #extra>
      <el-button type="primary" @click="send()">重试</el-button>
      <el-button @click="router.back()">返回</el-button>
    </template>
  </el-result>
</div>
```

Apply the same patterns to WeekDetailPage and CreatorDetailPage.

- [ ] **Step 5: Rewrite AdminPage** buttons

Replace all `<button>` elements in AdminPage with `<el-button>`:
- `<button @click="..." class="px-6 py-2 bg-blue text-white rounded-[12px] font-medium ...">` → `<el-button type="primary" @click="...">`
- `<button @click="..." class="px-6 py-2 ... border border-border rounded-[12px] ...">` → `<el-button @click="...">`

Replace the API Key `<input>` with `<el-input v-model="..." type="password" placeholder="...">`.

- [ ] **Step 6: Rewrite KeywordsPage** pill buttons

The week selector and category selector in KeywordsPage use custom pill buttons. Replace with `<el-segmented>`:

```vue
<!-- Week selector -->
<el-segmented
  :model-value="selectedWeek"
  :options="data.by_week.map(w => ({ label: `第${w.week_number}期`, value: w.week_number }))"
  @update:model-value="selectedWeek = $event as number"
/>

<!-- Category selector -->
<el-segmented
  :model-value="selectedCategory"
  :options="data.by_category.map(c => ({ label: c.tname, value: c.tname }))"
  @update:model-value="selectedCategory = $event as string"
/>
```

- [ ] **Step 7: Build check**

```bash
cd app/ui && pnpm build 2>&1 | tail -10
```

Expected: Build succeeds.

- [ ] **Step 8: Run full test suite**

```bash
cd app/ui && pnpm test:unit 2>&1 | tail -15
```

Expected: All tests pass.

- [ ] **Step 9: Commit**

```bash
git add app/ui/src/pages/
git commit -m "refactor(pages): unify error/empty/loading states with el-result/el-empty/el-skeleton, replace buttons with el-button

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 18: Final verification — full build + all tests + visual check

- [ ] **Step 1: Run full unit test suite**

```bash
cd app/ui && pnpm test:unit 2>&1
```

Expected: All tests pass. 0 failures.

- [ ] **Step 2: Run production build**

```bash
cd app/ui && pnpm build 2>&1
```

Expected: Build succeeds cleanly.

- [ ] **Step 3: Visual check — dev server**

```bash
cd app/ui && pnpm dev
```

Manually check every page at both desktop and mobile (375px) widths:
- [ ] `/` — HomePage: HeroSection, KpiCardRow, CategoryBar, CreatorTopList, TrendMiniChart
- [ ] `/videos` — VideoLibraryPage: SearchBar, SortTabs, FilterDropdown, VideoCards, el-scrollbar infinite scroll
- [ ] `/weeks` — WeeksPage: WeekCards, el-scrollbar
- [ ] `/creators` — CreatorsPage: CreatorCards, SortTabs, el-scrollbar
- [ ] `/categories` — CategoriesPage
- [ ] `/videos/:aid` — VideoDetailPage
- [ ] `/weeks/:number` — WeekDetailPage
- [ ] `/creators/:mid` — CreatorDetailPage
- [ ] `/analysis/stats` — StatsPage: SubNavTabs, StatCards, charts
- [ ] `/analysis/clusters` — ClusterPage: el-progress, el-tag
- [ ] `/analysis/predictions` — PredictPage
- [ ] `/analysis/keywords` — KeywordsPage: el-segmented selectors
- [ ] `/analysis/models` — ModelComparisonPage
- [ ] `/admin` — AdminPage: el-button, el-input

- [ ] **Step 4: Commit any visual regression fixes**

```bash
git add -A
git commit -m "fix: Phase 2 visual regression fixes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Summary

| Metric | Before | After |
|--------|--------|-------|
| Element Plus components used | 1 (`el-scrollbar`) | 15+ |
| Hand-rolled interactive logic | FilterDropdown (90 lines), ReanalyzeButton click-outside, SearchBar debounce | Replaced by EP built-ins |
| Inline SVG icons | ~15 distinct SVGs embedded in templates | `el-icon` + `@element-plus/icons-vue` |
| CSS variable source | Tailwind `@theme` only | Tailwind `@theme` + Element Plus `:root` mapping |
| Error/empty/loading pattern | Per-page ad-hoc | `el-result` / `el-empty` / `el-skeleton` |
