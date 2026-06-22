# Element Plus Frontend Refactor — Design Spec

**Date**: 2026-06-22
**Status**: Approved
**Branch**: master

## 1. Motivation

The project has `element-plus@^2.9.0` installed but barely uses it — only `el-scrollbar` is imported in 3 pages. The frontend instead relies on ~15 custom components built with raw HTML + Tailwind CSS, many of which duplicate Element Plus component functionality. This spec defines a comprehensive refactor to properly leverage Element Plus while preserving the existing visual identity.

## 2. Design Principles

1. **Element Plus provides interaction logic; Tailwind + CSS variable mapping preserves visual style.**
2. **Existing component API signatures (props/events) are preserved** — internal implementation switches to Element Plus, but consumers (pages) see no breaking changes.
3. **Phase 1 delivers global impact with low risk** (CSS variables + shared/layout components). **Phase 2** does page-by-page refinement.
4. **No UI regression** — every replaced component must visually match the current appearance at all viewport sizes.

## 3. Component Mapping

### 3.1 Shared Components

| Current | Replace With | Phase |
|---------|-------------|-------|
| `StatCard` | `el-statistic` (wrapped in `el-card`) | 1 |
| `SectionHeader` | Keep as thin wrapper, add `el-divider` | 1 |
| `AnalysisLoading` | Keep scanner animation, embed `el-skeleton` inside | 1 |
| Custom `<button>` elements | `el-button` (type="primary") | 1 |
| Inline SVG icons | `el-icon` + `@element-plus/icons-vue` | 1 |

### 3.2 Layout Components

| Current | Replace With | Phase |
|---------|-------------|-------|
| `Sidebar` | `el-menu` (vertical, fixed, router mode) | 1 |
| `TopNav` | `el-menu` (horizontal mode) + `el-button` | 1 |
| `PageShell` | Keep layout logic, no Element Plus replacement needed | — |

### 3.3 Business Components

| Current | Replace With | Phase |
|---------|-------------|-------|
| `SearchBar` | `el-input` (search mode, clearable) | 2 |
| `SortTabs` | `el-segmented` | 2 |
| `FilterDropdown` | `el-select` (clearable) | 2 |
| `VideoCard` / `WeekCard` / `CreatorCard` | `el-card` wrapper + Tailwind internals | 2 |

### 3.4 Analysis Components

| Current | Replace With | Phase |
|---------|-------------|-------|
| `SubNavTabs` | `el-tabs` | 2 |
| `CreatorTable` | `el-progress` (progress bars), `el-tag` (ranks) | 2 |
| `CategoryPanel` | `el-card` wrappers | 2 |
| `ForecastCards` | `el-statistic`, `el-icon` | 2 |
| `FeatureImportance` | `el-progress` (percentage mode) | 2 |
| `ClusterCards` | `el-tag` (cluster labels) | 2 |

### 3.5 Page States (All Pages)

| Current | Replace With | Phase |
|---------|-------------|-------|
| Custom error divs | `el-result` (icon="error") | 2 |
| Custom empty divs | `el-empty` | 2 |
| `animate-pulse` skeleton divs | `el-skeleton` | 2 |

## 4. CSS Variable Mapping (theme.css)

The core mechanism for visual consistency. Project design tokens are defined in a Tailwind `@theme` block. Element Plus CSS variables are mapped to these tokens via `:root`:

```css
:root {
  --el-color-primary: var(--color-blue);              /* #00AEEC → primary */
  --el-color-primary-light-3: #33BEF0;
  --el-color-primary-light-5: #66CEF4;
  --el-color-primary-light-7: #99DFF7;
  --el-color-primary-light-8: #B3E8FA;
  --el-color-primary-light-9: #CCF0FC;
  --el-color-primary-dark-2: #008BC0;

  --el-color-success: var(--color-success);           /* #22C55E */
  --el-color-warning: var(--color-warning);            /* #F59E0B */
  --el-color-danger: var(--color-danger);              /* #EF4444 */
  --el-color-info: var(--color-text-secondary);        /* #6B7280 */

  --el-bg-color: var(--color-bg);                     /* #FAFAFA */
  --el-bg-color-overlay: var(--color-card);           /* #FFFFFF */
  --el-fill-color-blank: var(--color-card);

  --el-text-color-primary: var(--color-text);         /* #111827 */
  --el-text-color-regular: var(--color-text-secondary); /* #6B7280 */

  --el-border-color: var(--color-border);             /* #E5E7EB */
  --el-border-radius-base: var(--radius-default);     /* 12px */
  --el-border-radius-round: 20px;                     /* Match pill buttons */

  --el-font-family: var(--font-family-sans);
}
```

## 5. main.ts Changes

Before:
```ts
import 'element-plus/es/components/scrollbar/style/css'
```

After:
```ts
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// ...
app.use(ElementPlus)
```

Add `@element-plus/icons-vue` to `package.json` dependencies.

## 6. Implementation Plan

### Phase 1 — Infrastructure & Shared Components (estimated: foundational, touches ~15 files)

1. **`theme.css`** — Append Element Plus CSS variable mapping after `@theme` block
2. **`main.ts`** — Global import ElementPlus + dist CSS, remove scrollbar-only import
3. **`package.json`** — Add `@element-plus/icons-vue`
4. **`SectionHeader`** — Add optional `el-divider`
5. **`StatCard`** — Replace internals with `el-statistic` + `el-card`, keep props API
6. **`AnalysisLoading`** — Embed `el-skeleton` inside scanner animation
7. **`Sidebar`** — Replace `<nav>` with `el-menu` vertical + router mode
8. **`TopNav`** — Replace `<ul>` with `el-menu` horizontal mode
9. **All inline SVG icons** — Replace with `el-icon` + `@element-plus/icons-vue`
10. **All `<button>` elements** — Replace with `el-button`

### Phase 2 — Business & Analysis Components + Page States (estimated: touches ~25 files)

11. **`SearchBar`** → `el-input` (keep v-model API)
12. **`SortTabs`** → `el-segmented` (keep v-model API)
13. **`FilterDropdown`** → `el-select` (keep v-model API, ~40 lines removed)
14. **`SubNavTabs`** → `el-tabs`
15. **`VideoCard` / `WeekCard` / `CreatorCard`** → `el-card` wrappers
16. **`CreatorTable`** → internal `el-progress` + `el-tag`
17. **`CategoryPanel`** → `el-card` wrappers
18. **`ForecastCards`** → `el-statistic` + `el-icon`
19. **`FeatureImportance`** → `el-progress` percentage mode
20. **`ClusterCards`** → `el-tag` for cluster labels
21. **All pages** — Replace error states with `el-result`, empty states with `el-empty`, loading skeletons with `el-skeleton`

## 7. Risk Mitigation

| Risk | Severity | Mitigation |
|------|----------|------------|
| `el-menu` styles conflict with Sidebar layout | High | Use `!important` Tailwind utilities; preserve `lg:ml-[max(…)]` centering logic in PageShell |
| CSS variable mapping produces unexpected colors | Medium | Only map core variables; let Element Plus auto-derive light/dark variants from `--el-color-primary` |
| `el-select` popover behavior differs from FilterDropdown | Low | Element Plus 2.9 popovers are well-tested; `clearable` + `filterable` cover all FilterDropdown use cases |
| Icon SVG → el-icon mapping errors | Low | Limited scope (~15 distinct SVG icons); verify each manually |
| Bundle size increase from global import | Low | Element Plus tree-shakes unused components in production builds; global CSS is ~200KB gzipped (~30KB) |

## 8. Verification

- **Visual regression**: After each Phase 1 step, run `pnpm dev` and manually verify HomePage, VideoLibraryPage, and StatsPage at desktop + mobile viewports (Playwright screenshots optional)
- **Automated tests**: Run `pnpm test:unit` to ensure existing Vitest tests pass
- **Build check**: `pnpm build` must succeed with no new warnings
- **Component tests**: `SectionHeader.spec.ts` must pass; add StatCard spec if time permits

## 9. Files Touched (Complete)

```
app/ui/package.json                          # Add @element-plus/icons-vue
app/ui/src/main.ts                           # Global import ElementPlus
app/ui/src/styles/theme.css                  # CSS variable mapping
app/ui/src/components/shared/StatCard.vue    # el-statistic + el-card
app/ui/src/components/shared/SectionHeader.vue # el-divider
app/ui/src/components/shared/AnalysisLoading.vue # el-skeleton
app/ui/src/components/shared/ReanalyzeButton.vue # el-button
app/ui/src/components/layout/Sidebar.vue     # el-menu
app/ui/src/components/layout/TopNav.vue      # el-menu horizontal
app/ui/src/components/business/SearchBar.vue # el-input
app/ui/src/components/business/SortTabs.vue  # el-segmented
app/ui/src/components/business/FilterDropdown.vue # el-select
app/ui/src/components/business/VideoCard.vue # el-card
app/ui/src/components/business/WeekCard.vue  # el-card
app/ui/src/components/business/CreatorCard.vue # el-card
app/ui/src/components/analysis/SubNavTabs.vue # el-tabs
app/ui/src/components/analysis/CreatorTable.vue # el-progress, el-tag
app/ui/src/components/analysis/CategoryPanel.vue # el-card
app/ui/src/components/analysis/ForecastCards.vue # el-statistic, el-icon
app/ui/src/components/analysis/FeatureImportance.vue # el-progress
app/ui/src/components/analysis/ClusterCards.vue # el-tag
app/ui/src/pages/HomePage.vue                # States: el-skeleton
app/ui/src/pages/AdminPage.vue               # Buttons: el-button
app/ui/src/pages/browse/VideoLibraryPage.vue # States + el-button
app/ui/src/pages/browse/WeeksPage.vue        # States + el-button
app/ui/src/pages/browse/CreatorsPage.vue     # States + el-button
app/ui/src/pages/browse/VideoDetailPage.vue  # States + el-button
app/ui/src/pages/browse/WeekDetailPage.vue   # States + el-button
app/ui/src/pages/browse/CreatorDetailPage.vue # States + el-button
app/ui/src/pages/browse/CategoriesPage.vue   # States + el-button
app/ui/src/pages/analysis/StatsPage.vue      # States + el-button
app/ui/src/pages/analysis/ClusterPage.vue    # States + el-button
app/ui/src/pages/analysis/PredictPage.vue    # States + el-button
app/ui/src/pages/analysis/KeywordsPage.vue   # States + el-button
app/ui/src/pages/analysis/ModelComparisonPage.vue # States + el-button
```
