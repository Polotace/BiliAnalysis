# Browse Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 7 browse/discover pages (视频库, 视频详情, 周报, 周报详情, 创作者, 创作者主页, 分区) consuming existing PostgreSQL-backed API endpoints, plus shared UI components and updated TopNav with dropdown navigation.

**Architecture:** Each page fetches its own data via Alova on mount, using infinite scroll (IntersectionObserver) instead of pagination buttons. Components reuse the existing BiliInsight design tokens: blue `#00AEEC`, white cards, `#FAFAFA` background, 12px radius, light shadows, Inter font.

**Tech Stack:** Vue 3 Composition API, TypeScript, Tailwind CSS v4, Alova HTTP, Vue Router 4

---

## File Structure

```
app/ui/src/
├── types/api.ts                          # MODIFY: add 8 new response types
├── composables/useApi.ts                 # MODIFY: add 6 new request functions
├── router/index.ts                       # MODIFY: add 7 new routes
├── components/
│   ├── layout/
│   │   └── TopNav.vue                    # MODIFY: add 浏览 dropdown
│   └── business/
│       ├── VideoCard.vue                 # CREATE
│       ├── CreatorCard.vue               # CREATE
│       ├── WeekCard.vue                  # CREATE
│       ├── SearchBar.vue                 # CREATE
│       ├── SortTabs.vue                  # CREATE
│       └── InfiniteScroll.vue            # CREATE
├── composables/
│   └── useInfiniteScroll.ts              # CREATE
└── pages/
    ├── browse/
    │   ├── VideoLibraryPage.vue          # CREATE  /videos
    │   ├── VideoDetailPage.vue           # CREATE  /videos/:aid
    │   ├── WeeksPage.vue                 # CREATE  /weeks
    │   ├── WeekDetailPage.vue            # CREATE  /weeks/:number
    │   ├── CreatorsPage.vue              # CREATE  /creators
    │   ├── CreatorDetailPage.vue         # CREATE  /creators/:mid
    │   └── CategoriesPage.vue            # CREATE  /categories
```

---

## API Response Types (backend → frontend)

These are the Pydantic models serialized by FastAPI. Types must match exactly:

```typescript
// ── Videos ──
interface VideoSummary {
  aid: number; bvid: string; title: string; cover_url: string | null
  duration: number; pubdate: string; creator_name: string | null
  category_name: string | null; view: number; like_cnt: number
}
interface VideoDetail {
  aid: number; bvid: string; title: string; description: string | null
  duration: number; pubdate: string; cid: number; video_url: string | null
  cover_url: string | null; copyright: number
  creator_mid: number; creator_name: string | null; creator_face: string | null
  category_tid: number; category_name: string | null; category_v2_name: string | null
  view: number; like_cnt: number; coin: number; favorite: number
  share: number; reply: number; danmaku: number
  appeared_weeks: number[]
}
interface PaginatedVideos { videos: VideoSummary[]; total: number; page: number; page_size: number }

// ── Weeks ──
interface WeekItem {
  number: number; subject: string | null; name: string | null; label: string | null
  cover: string | null; start_time: string | null; end_time: string | null; video_count: number
}
interface WeekDetail {
  number: number; subject: string | null; name: string | null; label: string | null
  cover: string | null; start_time: string | null; end_time: string | null
  videos: VideoSummary[]
}

// ── Creators ──
interface CreatorSummary { mid: number; name: string; face: string | null; video_count: number; total_views: number }
interface CreatorDetail {
  mid: number; name: string; face: string | null
  video_count: number; total_views: number; total_likes: number
  total_coins: number; total_favorites: number
  videos: VideoSummary[]
}
interface PaginatedCreators { creators: CreatorSummary[]; total: number; page: number; page_size: number }

// ── Categories ──
interface CategorySummary {
  tid: number; tname: string | null; tid_v2: number | null; tname_v2: string | null
  pid_v2: number | null; pid_name_v2: string | null; video_count: number
}
```

## Route Table

| Path | Name | Component | Lazy |
|------|------|-----------|------|
| `/videos` | `videos` | `VideoLibraryPage.vue` | Yes |
| `/videos/:aid` | `video-detail` | `VideoDetailPage.vue` | Yes |
| `/weeks` | `weeks` | `WeeksPage.vue` | Yes |
| `/weeks/:number` | `week-detail` | `WeekDetailPage.vue` | Yes |
| `/creators` | `creators` | `CreatorsPage.vue` | Yes |
| `/creators/:mid` | `creator-detail` | `CreatorDetailPage.vue` | Yes |
| `/categories` | `categories` | `CategoriesPage.vue` | Yes |

## Alova Request Functions

```typescript
export function fetchVideos(params: {
  page?: number; page_size?: number; week_number?: number
  category_tid?: number; creator_mid?: number; search?: string; sort_by?: string
}) {
  return alova.Get<PaginatedVideos>('/videos', { params })
}
export function fetchVideo(aid: number) {
  return alova.Get<VideoDetail>(`/videos/${aid}`)
}
export function fetchWeeks() {
  return alova.Get<WeekItem[]>('/weeks')
}
export function fetchWeek(number: number) {
  return alova.Get<WeekDetail>(`/weeks/${number}`)
}
export function fetchCreators(params: { page?: number; page_size?: number; sort_by?: string }) {
  return alova.Get<PaginatedCreators>('/creators', { params })
}
export function fetchCreator(mid: number) {
  return alova.Get<CreatorDetail>(`/creators/${mid}`)
}
export function fetchCategories() {
  return alova.Get<CategorySummary[]>('/categories')
}
```

---

### Task 1: TypeScript Types — Add Browse Response Types

**Files:**
- Modify: `app/ui/src/types/api.ts`

- [ ] **Step 1: Append 8 new interfaces to api.ts**

```typescript
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
```

- [ ] **Step 2: Commit**

```bash
git add app/ui/src/types/api.ts
git commit -m "feat: add Video/Week/Creator/Category TypeScript types for browse pages"
```

---

### Task 2: Alova API Functions — Add Browse Endpoints

**Files:**
- Modify: `app/ui/src/composables/useApi.ts`

- [ ] **Step 1: Add 6 typed request functions + 6 composables**

```typescript
import type {
  StatReport, ClusterReport, PredictionReport,
  VideoSummary, VideoDetail, PaginatedVideos,
  WeekItem, WeekDetail,
  CreatorSummary, CreatorDetail, PaginatedCreators,
  CategorySummary,
} from '@/types/api'

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

// ── Composables ──

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
```

- [ ] **Step 2: Run type check**

```bash
cd app/ui && pnpm exec vue-tsc -b --noEmit 2>&1
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/composables/useApi.ts
git commit -m "feat: add Alova request functions for videos/weeks/creators/categories"
```

---

### Task 3: Router — Add 7 Browse Routes

**Files:**
- Modify: `app/ui/src/router/index.ts`

- [ ] **Step 1: Add routes**

```typescript
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('@/pages/HomePage.vue') },
    // Analysis (existing)
    { path: '/analysis/stats', name: 'stats', component: () => import('@/pages/analysis/StatsPage.vue') },
    { path: '/analysis/clusters', name: 'clusters', component: () => import('@/pages/analysis/ClusterPage.vue') },
    { path: '/analysis/predictions', name: 'predict', component: () => import('@/pages/analysis/PredictPage.vue') },
    // Browse (new)
    { path: '/videos', name: 'videos', component: () => import('@/pages/browse/VideoLibraryPage.vue') },
    { path: '/videos/:aid', name: 'video-detail', component: () => import('@/pages/browse/VideoDetailPage.vue') },
    { path: '/weeks', name: 'weeks', component: () => import('@/pages/browse/WeeksPage.vue') },
    { path: '/weeks/:number', name: 'week-detail', component: () => import('@/pages/browse/WeekDetailPage.vue') },
    { path: '/creators', name: 'creators', component: () => import('@/pages/browse/CreatorsPage.vue') },
    { path: '/creators/:mid', name: 'creator-detail', component: () => import('@/pages/browse/CreatorDetailPage.vue') },
    { path: '/categories', name: 'categories', component: () => import('@/pages/browse/CategoriesPage.vue') },
  ],
  scrollBehavior() { return { top: 0 } },
})
```

- [ ] **Step 2: Create directory + stub pages**

```bash
mkdir -p app/ui/src/pages/browse
```

```vue
<!-- VideoLibraryPage.vue -->
<template><div>Video Library</div></template>
```

(Repeat for all 7 stubs)

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/router/index.ts app/ui/src/pages/browse/
git commit -m "feat: add 7 browse routes with page stubs"
```

---

### Task 4: Business Components — VideoCard, CreatorCard, WeekCard

**Files:**
- Create: `app/ui/src/components/business/VideoCard.vue`
- Create: `app/ui/src/components/business/CreatorCard.vue`
- Create: `app/ui/src/components/business/WeekCard.vue`

- [ ] **Step 1: Create VideoCard.vue**

Props: `video: VideoSummary`. Shows cover image + duration badge + title + view/like stats + creator name + category tag. Click emits or navigates to `/videos/{aid}`.

```vue
<script setup lang="ts">
import type { VideoSummary } from '@/types/api'

defineProps<{ video: VideoSummary }>()

function fmt(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(1)}万` : String(n)
}
</script>

<template>
  <router-link
    :to="`/videos/${video.aid}`"
    class="block bg-card rounded-[12px] shadow-[var(--shadow-default)] overflow-hidden
           transition-shadow duration-200 hover:shadow-[var(--shadow-hover)] hover:-translate-y-0.5
           cursor-pointer no-underline"
  >
    <!-- Thumbnail -->
    <div class="relative h-[180px] bg-border overflow-hidden">
      <img
        v-if="video.cover_url"
        :src="video.cover_url"
        :alt="video.title"
        class="w-full h-full object-cover"
        loading="lazy"
      />
      <div v-else class="w-full h-full flex items-center justify-center text-text-secondary text-sm">
        暂无封面
      </div>
      <span
        v-if="video.duration"
        class="absolute bottom-2 right-2 bg-black/75 text-white text-xs px-1.5 py-0.5 rounded tabular"
      >
        {{ video.duration }}
      </span>
    </div>

    <!-- Body -->
    <div class="p-[14px_16px]">
      <h3 class="text-[0.9375rem] font-semibold text-text leading-snug mb-2
                 line-clamp-2">
        {{ video.title }}
      </h3>
      <div class="flex gap-4 text-[0.8125rem] text-text-secondary tabular mb-2">
        <span>▶ {{ fmt(video.view) }}</span>
        <span>👍 {{ fmt(video.like_cnt) }}</span>
      </div>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-between px-4 py-2.5 border-t border-border text-[0.8125rem]">
      <span class="text-text font-medium truncate max-w-[60%]">{{ video.creator_name || '未知' }}</span>
      <span
        v-if="video.category_name"
        class="bg-blue-light text-blue px-2 py-0.5 rounded text-xs"
      >
        {{ video.category_name }}
      </span>
    </div>
  </router-link>
</template>
```

- [ ] **Step 2: Create CreatorCard.vue**

Props: `creator: CreatorSummary`. Shows face, name, video count, total views. Links to `/creators/{mid}`.

```vue
<script setup lang="ts">
import type { CreatorSummary } from '@/types/api'

defineProps<{ creator: CreatorSummary }>()

function fmt(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(1)}万` : String(n)
}
</script>

<template>
  <router-link
    :to="`/creators/${creator.mid}`"
    class="flex items-center gap-4 bg-card rounded-[12px] p-4 shadow-[var(--shadow-default)]
           transition-shadow duration-200 hover:shadow-[var(--shadow-hover)]
           cursor-pointer no-underline"
  >
    <img
      v-if="creator.face"
      :src="creator.face"
      :alt="creator.name"
      class="w-12 h-12 rounded-full object-cover shrink-0"
    />
    <div v-else class="w-12 h-12 rounded-full bg-border shrink-0 flex items-center justify-center text-text-secondary text-xs">
      UP
    </div>
    <div class="flex-1 min-w-0">
      <p class="font-semibold text-text text-sm truncate">{{ creator.name }}</p>
      <p class="text-xs text-text-secondary mt-0.5">
        {{ creator.video_count }} 个视频 · {{ fmt(creator.total_views) }} 总播放
      </p>
    </div>
  </router-link>
</template>
```

- [ ] **Step 3: Create WeekCard.vue**

Props: `week: WeekItem`. Shows gradient cover + number badge + subject + name + video count.

```vue
<script setup lang="ts">
import type { WeekItem } from '@/types/api'

defineProps<{ week: WeekItem }>()

const COLORS = ['#00AEEC', '#22C55E', '#F59E0B', '#8B5CF6', '#EF4444', '#10B981', '#EC4899', '#6366F1']
</script>

<template>
  <router-link
    :to="`/weeks/${week.number}`"
    class="block bg-card rounded-[16px] shadow-[var(--shadow-default)] overflow-hidden
           transition-shadow duration-200 hover:shadow-[var(--shadow-hover)] hover:-translate-y-0.5
           cursor-pointer no-underline"
  >
    <!-- Cover -->
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

    <!-- Info -->
    <div class="flex items-center justify-between px-5 py-4 gap-3">
      <span class="text-sm text-text-secondary font-medium truncate">{{ week.name || '' }}</span>
      <span class="bg-blue-light text-blue font-semibold px-[10px] py-[3px] rounded-md text-[0.8125rem] tabular">
        {{ week.video_count }} 个视频
      </span>
    </div>
  </router-link>
</template>
```

- [ ] **Step 4: Run type check**

```bash
cd app/ui && pnpm exec vue-tsc -b --noEmit 2>&1
```

Expected: No errors.

- [ ] **Step 5: Commit**

```bash
git add app/ui/src/components/business/VideoCard.vue \
        app/ui/src/components/business/CreatorCard.vue \
        app/ui/src/components/business/WeekCard.vue
git commit -m "feat: add VideoCard, CreatorCard, WeekCard business components"
```

---

### Task 5: Shared Components — SearchBar, SortTabs, InfiniteScroll

**Files:**
- Create: `app/ui/src/components/business/SearchBar.vue`
- Create: `app/ui/src/components/business/SortTabs.vue`
- Create: `app/ui/src/components/business/InfiniteScroll.vue`
- Create: `app/ui/src/composables/useInfiniteScroll.ts`

- [ ] **Step 1: Create useInfiniteScroll composable**

```typescript
import { ref, onMounted, onUnmounted, type Ref } from 'vue'

export function useInfiniteScroll(
  loadMore: () => Promise<void>,
  hasMore: Ref<boolean>,
  loading: Ref<boolean>,
) {
  const sentinelRef = ref<HTMLElement | null>(null)
  let observer: IntersectionObserver | null = null

  onMounted(() => {
    observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && hasMore.value && !loading.value) {
          loadMore()
        }
      },
      { rootMargin: '200px' },
    )
    if (sentinelRef.value) observer.observe(sentinelRef.value)
  })

  onUnmounted(() => {
    observer?.disconnect()
  })

  return { sentinelRef }
}
```

- [ ] **Step 2: Create SearchBar.vue**

Props: `modelValue: string`, `placeholder?: string`. Emits `update:modelValue` with 300ms debounce.

```vue
<script setup lang="ts">
import { ref, watch } from 'vue'

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
  <div class="relative flex-1 min-w-[260px] max-w-[400px]">
    <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary"
         xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
    </svg>
    <input
      v-model="input"
      :placeholder="placeholder"
      class="w-full h-10 pl-10 pr-4 border border-border rounded-[12px]
             text-[0.9375rem] text-text bg-card outline-none
             transition-colors duration-200
             focus:border-blue focus:shadow-[0_0_0_3px_rgba(0,174,236,0.1)]"
    />
  </div>
</template>
```

- [ ] **Step 3: Create SortTabs.vue**

Props: `options: {key:string, label:string}[]`, `modelValue: string`. Each rendered as pill-shaped toggle.

```vue
<script setup lang="ts">
defineProps<{
  options: { key: string; label: string }[]
  modelValue: string
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <div class="flex gap-2 flex-wrap">
    <button
      v-for="opt in options"
      :key="opt.key"
      @click="emit('update:modelValue', opt.key)"
      class="px-4 py-1.5 border border-border rounded-[20px] text-[0.8125rem] font-medium
             transition-colors duration-150 cursor-pointer
             hover:border-blue hover:text-blue"
      :class="modelValue === opt.key
        ? 'bg-blue text-white border-blue'
        : 'bg-card text-text-secondary'"
    >
      {{ opt.label }}
    </button>
  </div>
</template>
```

- [ ] **Step 4: Create InfiniteScroll.vue**

Thin wrapper: renders a sentinel `<div>` that triggers `loadMore` when visible. Shows spinner while loading, "没有更多了" when done.

```vue
<script setup lang="ts">
defineProps<{ loading: boolean; hasMore: boolean }>()
</script>

<template>
  <div class="flex items-center justify-center py-8 gap-2 text-sm text-text-secondary">
    <template v-if="loading">
      <div class="w-5 h-5 border-2 border-border border-t-blue rounded-full animate-spin" />
      <span>加载更多…</span>
    </template>
    <span v-else-if="!hasMore">— 没有更多了 —</span>
  </div>
</template>
```

- [ ] **Step 5: Run type check**

```bash
cd app/ui && pnpm exec vue-tsc -b --noEmit 2>&1
```

Expected: No errors.

- [ ] **Step 6: Commit**

```bash
git add app/ui/src/components/business/SearchBar.vue \
        app/ui/src/components/business/SortTabs.vue \
        app/ui/src/components/business/InfiniteScroll.vue \
        app/ui/src/composables/useInfiniteScroll.ts
git commit -m "feat: add SearchBar, SortTabs, InfiniteScroll components + useInfiniteScroll"
```

---

### Task 6: Update TopNav — Add 浏览 Dropdown

**Files:**
- Modify: `app/ui/src/components/layout/TopNav.vue`

- [ ] **Step 1: Rewrite TopNav with browse dropdown**

```vue
<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

function isActive(path: string) { return route.path === path }
function isAnalysisActive() { return route.path.startsWith('/analysis') }
function isBrowseActive() {
  return ['/videos', '/weeks', '/creators', '/categories'].some(p => route.path.startsWith(p))
}
</script>

<template>
  <nav class="sticky top-0 z-100 bg-bg/85 backdrop-blur-[12px] border-b border-border">
    <div class="max-w-[1280px] mx-auto px-6 flex items-center h-14 gap-8">
      <router-link to="/" class="text-lg font-bold text-text no-underline tracking-[-0.01em]">
        Bili<span class="text-blue">Insight</span>
      </router-link>

      <ul class="flex gap-6 list-none items-center">
        <!-- 发现 -->
        <li>
          <router-link
            to="/"
            class="nav-link"
            :class="{ '!text-text': isActive('/') }"
          >发现</router-link>
        </li>

        <!-- 分析 -->
        <li>
          <router-link
            to="/analysis/stats"
            class="nav-link"
            :class="{ '!text-text': isAnalysisActive() }"
          >分析</router-link>
        </li>

        <!-- 浏览 ▼ -->
        <li class="relative group">
          <span
            class="nav-link cursor-pointer"
            :class="{ '!text-text': isBrowseActive() }"
          >浏览</span>
          <div class="absolute top-full left-1/2 -translate-x-1/2 mt-3
                      bg-card rounded-[12px] shadow-[0_8px_32px_rgba(0,0,0,0.10)]
                      border border-border p-1.5 min-w-[130px] flex flex-col
                      opacity-0 invisible group-hover:opacity-100 group-hover:visible
                      transition-[opacity,visibility] duration-150">
            <router-link to="/videos" class="dropdown-link" :class="{ '!text-text bg-bg': isActive('/videos') }">视频库</router-link>
            <router-link to="/weeks" class="dropdown-link" :class="{ '!text-text bg-bg': isActive('/weeks') }">周报</router-link>
            <router-link to="/creators" class="dropdown-link" :class="{ '!text-text bg-bg': isActive('/creators') }">创作者</router-link>
            <router-link to="/categories" class="dropdown-link" :class="{ '!text-text bg-bg': isActive('/categories') }">分区</router-link>
          </div>
        </li>
      </ul>
    </div>
  </nav>
</template>

<style scoped>
.nav-link {
  @apply no-underline text-[0.9375rem] font-medium text-text-secondary px-0 py-1
         transition-colors duration-200 relative hover:text-text;
}
.dropdown-link {
  @apply block px-3.5 py-2 rounded-md text-sm text-text-secondary no-underline
         transition-colors duration-100 hover:bg-bg hover:text-text;
}
</style>
```

- [ ] **Step 2: Run type check + tests**

```bash
cd app/ui && pnpm exec vue-tsc -b --noEmit 2>&1 && pnpm exec vitest run 2>&1
```

Expected: TSC passes, 14 tests pass.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/components/layout/TopNav.vue
git commit -m "feat: add 浏览 dropdown to TopNav (视频库/周报/创作者/分区)"
```

---

### Task 7: Video Library Page — /videos

**Files:**
- Create: `app/ui/src/pages/browse/VideoLibraryPage.vue`

- [ ] **Step 1: Write VideoLibraryPage.vue**

Full page: SearchBar + SortTabs + 3-col VideoCard grid + infinite scroll. Accumulates pages client-side.

```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRequest } from 'alova/client'
import { fetchVideos } from '@/composables/useApi'
import { useInfiniteScroll } from '@/composables/useInfiniteScroll'
import PageShell from '@/components/layout/PageShell.vue'
import SearchBar from '@/components/business/SearchBar.vue'
import SortTabs from '@/components/business/SortTabs.vue'
import VideoCard from '@/components/business/VideoCard.vue'
import InfiniteScroll from '@/components/business/InfiniteScroll.vue'
import type { VideoSummary } from '@/types/api'

const search = ref('')
const sortBy = ref('view')
const SORT_OPTIONS = [
  { key: 'view', label: '按播放量' },
  { key: 'like', label: '按点赞量' },
  { key: 'pubdate', label: '最新发布' },
]

const videos = ref<VideoSummary[]>([])
const currentPage = ref(1)
const total = ref(0)
const PAGE_SIZE = 20

const { loading, send } = useRequest(() =>
  fetchVideos({
    page: currentPage.value,
    page_size: PAGE_SIZE,
    search: search.value || undefined,
    sort_by: sortBy.value,
  }),
  { immediate: false },
)

const hasMore = computed(() => videos.value.length < total.value)

async function loadPage() {
  const result = await send().then(r => r.data)
  if (result) {
    if (currentPage.value === 1) {
      videos.value = result.videos
    } else {
      videos.value.push(...result.videos)
    }
    total.value = result.total
  }
}

async function resetAndLoad() {
  currentPage.value = 1
  videos.value = []
  await loadPage()
}

async function loadMore() {
  currentPage.value++
  await loadPage()
}

const { sentinelRef } = useInfiniteScroll(loadMore, hasMore, loading)

onMounted(() => loadPage())
</script>

<template>
  <PageShell>
    <!-- Page Header -->
    <div class="py-10">
      <h1 class="text-[1.75rem] font-bold tracking-[-0.02em] text-text mb-1">发现好内容</h1>
      <p class="text-[0.9375rem] text-text-secondary">
        浏览 B站「每周必看」的 <span class="tabular font-semibold text-text">{{ total }}</span> 个精选视频
      </p>
    </div>

    <!-- Toolbar -->
    <div class="flex items-center gap-3 pb-6 flex-wrap">
      <SearchBar v-model="search" placeholder="搜索视频标题…" @update:model-value="resetAndLoad" />
      <SortTabs v-model="sortBy" :options="SORT_OPTIONS" @update:model-value="resetAndLoad" />
    </div>

    <!-- Loading (first load) -->
    <div v-if="loading && videos.length === 0" class="grid grid-cols-3 gap-5 pb-8">
      <div v-for="i in 6" :key="i" class="h-[320px] bg-card rounded-[12px] animate-pulse" />
    </div>

    <!-- Error -->
    <div v-else-if="!loading && videos.length === 0 && !hasMore" class="py-24 text-center">
      <p class="text-text-secondary">暂无视频数据</p>
    </div>

    <!-- Video Grid -->
    <template v-else>
      <div class="grid grid-cols-3 gap-5 pb-8">
        <VideoCard v-for="v in videos" :key="v.aid" :video="v" />
      </div>

      <div ref="sentinelRef">
        <InfiniteScroll :loading="loading" :has-more="hasMore" />
      </div>
    </template>
  </PageShell>
</template>
```

- [ ] **Step 2: Run type check**

```bash
cd app/ui && pnpm exec vue-tsc -b --noEmit 2>&1
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/pages/browse/VideoLibraryPage.vue
git commit -m "feat: add Video Library page with search, sort, infinite scroll"
```

---

### Task 8: Video Detail Page — /videos/:aid

**Files:**
- Create: `app/ui/src/pages/browse/VideoDetailPage.vue`

- [ ] **Step 1: Write VideoDetailPage.vue**

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useVideo } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import type { WeekItem } from '@/types/api'

const route = useRoute()
const router = useRouter()
const aid = Number(route.params.aid)
const { data, loading, error, send } = useVideo(aid)

onMounted(() => send())

function fmt(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(1)}万` : String(n)
}
function fmtDuration(secs: number): string {
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${m}:${String(s).padStart(2, '0')}`
}
</script>

<template>
  <PageShell>
    <!-- Loading -->
    <div v-if="loading" class="space-y-6 py-8">
      <div class="h-[400px] bg-card rounded-[12px] animate-pulse" />
      <div class="h-32 bg-card rounded-[12px] animate-pulse" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="py-24 text-center">
      <p class="text-lg font-semibold text-text mb-2">加载失败</p>
      <p class="text-sm text-text-secondary mb-6">{{ (error as Error).message }}</p>
      <button @click="send()" class="px-6 py-2 bg-blue text-white rounded-[12px] font-medium hover:opacity-90">重试</button>
      <button @click="router.back()" class="px-6 py-2 ml-3 border border-border rounded-[12px] text-text-secondary hover:text-text">返回</button>
    </div>

    <!-- Data -->
    <template v-else-if="data">
      <!-- Hero Cover -->
      <div class="relative h-[400px] rounded-[16px] overflow-hidden mb-8 bg-border">
        <img v-if="data.cover_url" :src="data.cover_url" :alt="data.title"
             class="w-full h-full object-cover" />
        <div v-else class="w-full h-full flex items-center justify-center text-text-secondary">暂无封面</div>
        <div class="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
        <div class="absolute bottom-0 left-0 right-0 p-8">
          <h1 class="text-2xl font-bold text-white mb-3 leading-snug">{{ data.title }}</h1>
          <div class="flex items-center gap-6 text-sm text-white/80">
            <router-link :to="`/creators/${data.creator_mid}`" class="flex items-center gap-2 hover:text-white no-underline">
              <img v-if="data.creator_face" :src="data.creator_face" class="w-6 h-6 rounded-full" />
              <span>{{ data.creator_name }}</span>
            </router-link>
            <span>{{ fmtDuration(data.duration) }}</span>
            <span v-if="data.category_name">{{ data.category_name }}</span>
          </div>
        </div>
      </div>

      <!-- Stats Panel -->
      <div class="grid grid-cols-4 gap-6 mb-8">
        <div class="bg-card rounded-[12px] p-5 shadow-[var(--shadow-default)]">
          <p class="text-xs text-text-secondary mb-1">播放量</p>
          <p class="text-2xl font-bold tabular text-text">{{ fmt(data.view) }}</p>
        </div>
        <div class="bg-card rounded-[12px] p-5 shadow-[var(--shadow-default)]">
          <p class="text-xs text-text-secondary mb-1">点赞</p>
          <p class="text-2xl font-bold tabular text-text">{{ fmt(data.like_cnt) }}</p>
        </div>
        <div class="bg-card rounded-[12px] p-5 shadow-[var(--shadow-default)]">
          <p class="text-xs text-text-secondary mb-1">弹幕</p>
          <p class="text-2xl font-bold tabular text-text">{{ fmt(data.danmaku) }}</p>
        </div>
        <div class="bg-card rounded-[12px] p-5 shadow-[var(--shadow-default)]">
          <p class="text-xs text-text-secondary mb-1">收藏</p>
          <p class="text-2xl font-bold tabular text-text">{{ fmt(data.favorite) }}</p>
        </div>
      </div>

      <!-- Extended stats -->
      <div class="grid grid-cols-6 gap-4 mb-8 text-center">
        <div v-for="item in [
          {label:'投币',v:data.coin},{label:'分享',v:data.share},{label:'评论',v:data.reply},
        ]" :key="item.label" class="bg-card rounded-[12px] p-4 shadow-[var(--shadow-default)]">
          <p class="text-xl font-bold tabular text-text">{{ fmt(item.v) }}</p>
          <p class="text-xs text-text-secondary mt-1">{{ item.label }}</p>
        </div>
      </div>

      <!-- Appeared Weeks -->
      <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)] mb-8">
        <h2 class="text-lg font-semibold text-text mb-4">出现周次</h2>
        <div class="flex flex-wrap gap-2">
          <router-link
            v-for="wn in data.appeared_weeks"
            :key="wn"
            :to="`/weeks/${wn}`"
            class="px-3 py-1.5 bg-blue-light text-blue rounded-md text-sm font-medium no-underline hover:bg-blue hover:text-white transition-colors"
          >
            第 {{ wn }} 期
          </router-link>
        </div>
      </div>

      <!-- Description -->
      <div v-if="data.description" class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
        <h2 class="text-lg font-semibold text-text mb-4">简介</h2>
        <p class="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">{{ data.description }}</p>
      </div>
    </template>
  </PageShell>
</template>
```

- [ ] **Step 2: Run type check**

```bash
cd app/ui && pnpm exec vue-tsc -b --noEmit 2>&1
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/pages/browse/VideoDetailPage.vue
git commit -m "feat: add Video Detail page with stats panel and appeared weeks"
```

---

### Task 9: Weeks Page — /weeks

**Files:**
- Create: `app/ui/src/pages/browse/WeeksPage.vue`

- [ ] **Step 1: Write WeeksPage.vue**

2-col grid of WeekCards, infinite scroll.

```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useWeeksList } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import WeekCard from '@/components/business/WeekCard.vue'
import InfiniteScroll from '@/components/business/InfiniteScroll.vue'
import { useInfiniteScroll } from '@/composables/useInfiniteScroll'
import type { WeekItem } from '@/types/api'

const { data, loading, error, send } = useWeeksList()
const weeks = ref<WeekItem[]>([])
const PAGE_SIZE = 20
const displayCount = ref(PAGE_SIZE)

onMounted(async () => {
  const result = await send().then(r => r.data)
  if (result) weeks.value = result
})

const displayed = computed(() => weeks.value.slice(0, displayCount.value))
const hasMore = computed(() => displayCount.value < weeks.value.length)

async function loadMore() {
  displayCount.value = Math.min(displayCount.value + PAGE_SIZE, weeks.value.length)
  await new Promise(r => setTimeout(r, 100)) // small delay for spinner visibility
}

const { sentinelRef } = useInfiniteScroll(loadMore, hasMore, loading)
</script>

<template>
  <PageShell>
    <div class="py-10">
      <h1 class="text-[1.75rem] font-bold tracking-[-0.02em] text-text mb-1">每周必看</h1>
      <p class="text-[0.9375rem] text-text-secondary">
        从 2019 年至今，已收录 <span class="tabular font-semibold text-text">{{ weeks.length }}</span> 期周报
      </p>
    </div>

    <div v-if="loading" class="grid grid-cols-2 gap-6 pb-8">
      <div v-for="i in 4" :key="i" class="h-[280px] bg-card rounded-[16px] animate-pulse" />
    </div>

    <div v-else-if="error" class="py-24 text-center">
      <p class="text-lg font-semibold text-text mb-2">加载失败</p>
      <p class="text-sm text-text-secondary mb-6">{{ (error as Error).message }}</p>
      <button @click="send()" class="px-6 py-2 bg-blue text-white rounded-[12px] font-medium hover:opacity-90">重试</button>
    </div>

    <div v-else-if="weeks.length === 0" class="py-24 text-center">
      <p class="text-text-secondary">暂无周报数据</p>
    </div>

    <template v-else>
      <div class="grid grid-cols-2 gap-6 pb-8">
        <WeekCard v-for="w in displayed" :key="w.number" :week="w" />
      </div>
      <div ref="sentinelRef">
        <InfiniteScroll :loading="false" :has-more="hasMore" />
      </div>
    </template>
  </PageShell>
</template>
```

- [ ] **Step 2: Run type check**

```bash
cd app/ui && pnpm exec vue-tsc -b --noEmit 2>&1
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/pages/browse/WeeksPage.vue
git commit -m "feat: add Weeks Browse page with infinite scroll week cards"
```

---

### Task 10: Week Detail Page — /weeks/:number

**Files:**
- Create: `app/ui/src/pages/browse/WeekDetailPage.vue`

- [ ] **Step 1: Write WeekDetailPage.vue**

Shows week header + ranked video list sorted by view count.

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWeekDetail } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import VideoCard from '@/components/business/VideoCard.vue'

const route = useRoute()
const router = useRouter()
const number = Number(route.params.number)
const { data, loading, error, send } = useWeekDetail(number)

onMounted(() => send())
</script>

<template>
  <PageShell>
    <div v-if="loading" class="space-y-6 py-8">
      <div class="h-48 bg-card rounded-[16px] animate-pulse" />
      <div class="h-64 bg-card rounded-[12px] animate-pulse" />
    </div>

    <div v-else-if="error" class="py-24 text-center">
      <p class="text-lg font-semibold text-text mb-2">加载失败</p>
      <p class="text-sm text-text-secondary mb-6">{{ (error as Error).message }}</p>
      <button @click="send()" class="px-6 py-2 bg-blue text-white rounded-[12px] font-medium hover:opacity-90">重试</button>
      <button @click="router.back()" class="px-6 py-2 ml-3 border border-border rounded-[12px] text-text-secondary hover:text-text">返回</button>
    </div>

    <template v-else-if="data">
      <!-- Header -->
      <div class="bg-gradient-to-br from-blue-light to-bg rounded-[16px] p-10 mb-8 shadow-[var(--shadow-default)]">
        <span class="inline-block bg-blue text-white px-4 py-1 rounded-[20px] text-sm font-bold mb-3">
          第 {{ data.number }} 期
        </span>
        <h1 class="text-[2rem] font-bold text-text mb-2">{{ data.subject }}</h1>
        <p class="text-text-secondary">{{ data.name }}</p>
      </div>

      <!-- Videos -->
      <h2 class="text-lg font-semibold text-text mb-4">{{ data.videos.length }} 个视频</h2>
      <div class="grid grid-cols-3 gap-5 pb-12">
        <VideoCard v-for="v in data.videos" :key="v.aid" :video="v" />
      </div>
    </template>
  </PageShell>
</template>
```

- [ ] **Step 2: Run type check**

```bash
cd app/ui && pnpm exec vue-tsc -b --noEmit 2>&1
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/pages/browse/WeekDetailPage.vue
git commit -m "feat: add Week Detail page with video ranking"
```

---

### Task 11: Creators Page — /creators

**Files:**
- Create: `app/ui/src/pages/browse/CreatorsPage.vue`

- [ ] **Step 1: Write CreatorsPage.vue**

3-col grid of CreatorCards with sort tabs and infinite scroll.

```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useCreatorsList } from '@/composables/useApi'
import { useInfiniteScroll } from '@/composables/useInfiniteScroll'
import PageShell from '@/components/layout/PageShell.vue'
import SortTabs from '@/components/business/SortTabs.vue'
import CreatorCard from '@/components/business/CreatorCard.vue'
import InfiniteScroll from '@/components/business/InfiniteScroll.vue'
import type { CreatorSummary } from '@/types/api'

const sortBy = ref('video_count')
const SORT_OPTIONS = [
  { key: 'video_count', label: '作品最多' },
  { key: 'total_views', label: '总播放最高' },
  { key: 'name', label: '按名称' },
]

const creators = ref<CreatorSummary[]>([])
const currentPage = ref(1)
const total = ref(0)
const PAGE_SIZE = 24

const { loading, send } = useCreatorsList({ page: currentPage.value, page_size: PAGE_SIZE, sort_by: sortBy.value })
const hasMore = computed(() => creators.value.length < total.value)

async function loadPage() {
  const result = await send().then(r => r.data)
  if (result) {
    if (currentPage.value === 1) creators.value = result.creators
    else creators.value.push(...result.creators)
    total.value = result.total
  }
}

async function resetAndLoad() {
  currentPage.value = 1; creators.value = []; await loadPage()
}
async function loadMore() { currentPage.value++; await loadPage() }
const { sentinelRef } = useInfiniteScroll(loadMore, hasMore, loading)

onMounted(() => loadPage())
</script>

<template>
  <PageShell>
    <div class="py-10">
      <h1 class="text-[1.75rem] font-bold tracking-[-0.02em] text-text mb-1">创作者</h1>
      <p class="text-[0.9375rem] text-text-secondary">
        <span class="tabular font-semibold text-text">{{ total }}</span> 位创作者上榜「每周必看」
      </p>
    </div>

    <div class="pb-6">
      <SortTabs v-model="sortBy" :options="SORT_OPTIONS" @update:model-value="resetAndLoad" />
    </div>

    <div v-if="loading && creators.length === 0" class="grid grid-cols-3 gap-4 pb-8">
      <div v-for="i in 6" :key="i" class="h-[80px] bg-card rounded-[12px] animate-pulse" />
    </div>

    <div v-else-if="!loading && creators.length === 0 && !hasMore" class="py-24 text-center">
      <p class="text-text-secondary">暂无创作者数据</p>
    </div>

    <template v-else>
      <div class="grid grid-cols-3 gap-4 pb-8">
        <CreatorCard v-for="c in creators" :key="c.mid" :creator="c" />
      </div>
      <div ref="sentinelRef">
        <InfiniteScroll :loading="loading" :has-more="hasMore" />
      </div>
    </template>
  </PageShell>
</template>
```

- [ ] **Step 2: Run type check**

```bash
cd app/ui && pnpm exec vue-tsc -b --noEmit 2>&1
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/pages/browse/CreatorsPage.vue
git commit -m "feat: add Creators page with sort and infinite scroll"
```

---

### Task 12: Creator Detail Page — /creators/:mid

**Files:**
- Create: `app/ui/src/pages/browse/CreatorDetailPage.vue`

- [ ] **Step 1: Write CreatorDetailPage.vue**

Profile header with face + name + stats + video grid.

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCreatorDetail } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import VideoCard from '@/components/business/VideoCard.vue'

const route = useRoute()
const router = useRouter()
const mid = Number(route.params.mid)
const { data, loading, error, send } = useCreatorDetail(mid)

onMounted(() => send())

function fmt(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(1)}万` : String(n)
}
</script>

<template>
  <PageShell>
    <div v-if="loading" class="space-y-6 py-8">
      <div class="h-48 bg-card rounded-[16px] animate-pulse" />
      <div class="h-64 bg-card rounded-[12px] animate-pulse" />
    </div>

    <div v-else-if="error" class="py-24 text-center">
      <p class="text-lg font-semibold text-text mb-2">加载失败</p>
      <p class="text-sm text-text-secondary mb-6">{{ (error as Error).message }}</p>
      <button @click="send()" class="px-6 py-2 bg-blue text-white rounded-[12px] font-medium hover:opacity-90">重试</button>
      <button @click="router.back()" class="px-6 py-2 ml-3 border border-border rounded-[12px] text-text-secondary hover:text-text">返回</button>
    </div>

    <template v-else-if="data">
      <!-- Profile Header -->
      <div class="bg-card rounded-[16px] p-10 mb-8 shadow-[var(--shadow-default)] flex items-start gap-6">
        <img v-if="data.face" :src="data.face" :alt="data.name"
             class="w-24 h-24 rounded-full object-cover shrink-0" />
        <div v-else class="w-24 h-24 rounded-full bg-border shrink-0 flex items-center justify-center text-text-secondary text-sm">UP</div>
        <div class="flex-1">
          <h1 class="text-[1.75rem] font-bold text-text mb-3">{{ data.name }}</h1>
          <div class="grid grid-cols-5 gap-4">
            <div>
              <p class="text-2xl font-bold tabular text-text">{{ data.video_count }}</p>
              <p class="text-xs text-text-secondary">视频</p>
            </div>
            <div>
              <p class="text-2xl font-bold tabular text-text">{{ fmt(data.total_views) }}</p>
              <p class="text-xs text-text-secondary">总播放</p>
            </div>
            <div>
              <p class="text-2xl font-bold tabular text-text">{{ fmt(data.total_likes) }}</p>
              <p class="text-xs text-text-secondary">总点赞</p>
            </div>
            <div>
              <p class="text-2xl font-bold tabular text-text">{{ fmt(data.total_coins) }}</p>
              <p class="text-xs text-text-secondary">总投币</p>
            </div>
            <div>
              <p class="text-2xl font-bold tabular text-text">{{ fmt(data.total_favorites) }}</p>
              <p class="text-xs text-text-secondary">总收藏</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Videos -->
      <h2 class="text-lg font-semibold text-text mb-4">作品</h2>
      <div class="grid grid-cols-3 gap-5 pb-12">
        <VideoCard v-for="v in data.videos" :key="v.aid" :video="v" />
      </div>
    </template>
  </PageShell>
</template>
```

- [ ] **Step 2: Run type check**

```bash
cd app/ui && pnpm exec vue-tsc -b --noEmit 2>&1
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/pages/browse/CreatorDetailPage.vue
git commit -m "feat: add Creator Detail page with stats and video grid"
```

---

### Task 13: Categories Page — /categories

**Files:**
- Create: `app/ui/src/pages/browse/CategoriesPage.vue`

- [ ] **Step 1: Write CategoriesPage.vue**

Colored category cards grid (sorted by video_count desc).

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useCategoriesList } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import type { CategorySummary } from '@/types/api'

const { data, loading, error, send } = useCategoriesList()

onMounted(() => send())

const COLORS = ['#00AEEC','#22C55E','#F59E0B','#EF4444','#8B5CF6','#10B981','#EC4899','#6366F1',
                '#F97316','#06B6D4','#84CC16','#D946EF']
</script>

<template>
  <PageShell>
    <div class="py-10">
      <h1 class="text-[1.75rem] font-bold tracking-[-0.02em] text-text mb-1">内容分区</h1>
      <p class="text-[0.9375rem] text-text-secondary">
        覆盖 <span class="tabular font-semibold text-text">{{ data?.length ?? 0 }}</span> 个分区
      </p>
    </div>

    <div v-if="loading" class="grid grid-cols-4 gap-4 pb-8">
      <div v-for="i in 8" :key="i" class="h-[120px] bg-card rounded-[12px] animate-pulse" />
    </div>

    <div v-else-if="error" class="py-24 text-center">
      <p class="text-lg font-semibold text-text mb-2">加载失败</p>
      <p class="text-sm text-text-secondary mb-6">{{ (error as Error).message }}</p>
      <button @click="send()" class="px-6 py-2 bg-blue text-white rounded-[12px] font-medium hover:opacity-90">重试</button>
    </div>

    <div v-else-if="data" class="grid grid-cols-4 gap-4 pb-12">
      <div
        v-for="(c, i) in data"
        :key="c.tid"
        class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]
               border-t-[3px] transition-shadow duration-200 hover:shadow-[var(--shadow-hover)]"
        :style="{ borderTopColor: COLORS[i % COLORS.length] }"
      >
        <p class="text-base font-semibold text-text mb-2">{{ c.tname || `分区 ${c.tid}` }}</p>
        <p class="text-[1.5rem] font-bold tabular text-text">{{ c.video_count }}</p>
        <p class="text-xs text-text-secondary mt-1">个视频</p>
        <p v-if="c.tname_v2" class="text-xs text-text-secondary mt-2">{{ c.tname_v2 }}</p>
      </div>
    </div>
  </PageShell>
</template>
```

- [ ] **Step 2: Run type check**

```bash
cd app/ui && pnpm exec vue-tsc -b --noEmit 2>&1
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add app/ui/src/pages/browse/CategoriesPage.vue
git commit -m "feat: add Categories page with color-coded cards"
```

---

### Task 14: Unit Tests

**Files:**
- Create: `app/ui/src/components/business/__tests__/VideoCard.spec.ts`
- Create: `app/ui/src/components/business/__tests__/CreatorCard.spec.ts`
- Create: `app/ui/src/components/business/__tests__/WeekCard.spec.ts`

- [ ] **Step 1: Write VideoCard test**

```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import VideoCard from '@/components/business/VideoCard.vue'
import type { VideoSummary } from '@/types/api'

const video: VideoSummary = {
  aid: 12345, bvid: 'BV1xx', title: '测试视频标题',
  cover_url: null, duration: 360, pubdate: '2024-01-01',
  creator_name: '测试UP主', category_name: '知识', view: 1234567, like_cnt: 89000,
}

describe('VideoCard', () => {
  it('renders title, creator, stats', async () => {
    const router = createRouter({ history: createWebHistory(), routes: [] })
    const wrapper = mount(VideoCard, { props: { video }, global: { plugins: [router] } })
    expect(wrapper.text()).toContain('测试视频标题')
    expect(wrapper.text()).toContain('测试UP主')
    expect(wrapper.text()).toContain('123.5万')
    expect(wrapper.text()).toContain('8.9万')
  })

  it('links to video detail', () => {
    const router = createRouter({ history: createWebHistory(), routes: [] })
    const wrapper = mount(VideoCard, { props: { video }, global: { plugins: [router] } })
    const link = wrapper.find('a')
    expect(link.attributes('href')).toBe('/videos/12345')
  })
})
```

- [ ] **Step 2: Write CreatorCard test**

```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import CreatorCard from '@/components/business/CreatorCard.vue'
import type { CreatorSummary } from '@/types/api'

const creator: CreatorSummary = { mid: 100, name: '测试UP主', face: null, video_count: 15, total_views: 5000000 }

describe('CreatorCard', () => {
  it('renders name and stats', () => {
    const router = createRouter({ history: createWebHistory(), routes: [] })
    const wrapper = mount(CreatorCard, { props: { creator }, global: { plugins: [router] } })
    expect(wrapper.text()).toContain('测试UP主')
    expect(wrapper.text()).toContain('15')
    expect(wrapper.text()).toContain('500.0万')
  })
})
```

- [ ] **Step 3: Write WeekCard test**

```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import WeekCard from '@/components/business/WeekCard.vue'
import type { WeekItem } from '@/types/api'

const week: WeekItem = { number: 100, subject: '测试主题', name: '2024第10期', label: '第10期', cover: null, start_time: '2024-01', end_time: '2024-02', video_count: 30 }

describe('WeekCard', () => {
  it('renders subject and number', () => {
    const router = createRouter({ history: createWebHistory(), routes: [] })
    const wrapper = mount(WeekCard, { props: { week }, global: { plugins: [router] } })
    expect(wrapper.text()).toContain('测试主题')
    expect(wrapper.text()).toContain('第 100 期')
    expect(wrapper.text()).toContain('30 个视频')
  })
})
```

- [ ] **Step 4: Run tests**

```bash
cd app/ui && pnpm exec vitest run 2>&1
```

Expected: All tests pass (17 tests across 8 files).

- [ ] **Step 5: Commit**

```bash
git add app/ui/src/components/business/__tests__/
git commit -m "test: add VideoCard, CreatorCard, WeekCard unit tests"
```

---

### Task 15: Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Type check**

```bash
cd app/ui && pnpm exec vue-tsc -b --noEmit 2>&1
```

Expected: No errors.

- [ ] **Step 2: Run all unit tests**

```bash
cd app/ui && pnpm exec vitest run 2>&1
```

Expected: All pass (17 tests).

- [ ] **Step 3: Build for production**

```bash
cd app/ui && pnpm exec vite build 2>&1
```

Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "chore: final verification — typecheck + tests + build all pass"
```

---

## Parallel Execution Guide

```
Task 1 (types) → Task 2 (useApi) → Task 3 (router)
                                        ↓
Task 4 (VideoCard/CreatorCard/WeekCard)  ← can start in parallel with 1-3
Task 5 (SearchBar/SortTabs/InfiniteScroll) ← ditto
                                        ↓
Task 6 (TopNav)                          ← depends on router
                                        ↓
Task 7-13 (7 pages)                      ← ALL can run in parallel
                                        ↓
Task 14 (tests)                          ← depends on 4-5
                                        ↓
Task 15 (verification)
```
