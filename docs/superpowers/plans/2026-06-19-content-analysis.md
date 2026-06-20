# Content Analysis (关键词 + 词云) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a content insight pipeline: jieba TF-IDF keyword extraction from 13,983 video titles, aggregated by week/category/global, surfaced via a new `/analysis/keywords` API endpoint and an ECharts wordCloud page.

**Architecture:** Python `nlp/` module (pure, no DB) reads `Video.parquet`, runs jieba, outputs `keywords_report.json`. Scheduler task `keywords` wraps it. FastAPI endpoint reads the JSON cache. Vue3 page with ECharts wordCloud renders three views: global cloud, weekly selector, category selector.

**Tech Stack:** jieba (Chinese NLP), echarts-wordcloud (ECharts 5 extension), existing Pandas/Parquet infra.

---

## File Structure

```
src/bilianalysis/nlp/
├── __init__.py                  # CREATE: re-export
├── keywords.py                  # CREATE: extract + aggregate
├── stopwords.txt                # CREATE: Chinese stopwords list

src/bilianalysis/scheduler/builtins/
└── keywords_task.py             # CREATE: @register("keywords")

app/api/router/
└── analysis.py                  # MODIFY: add GET /analysis/keywords

app/ui/src/
├── types/api.ts                 # MODIFY: add KeywordsReport types
├── composables/useApi.ts        # MODIFY: add fetchKeywords + useKeywords
├── router/index.ts              # MODIFY: add /analysis/keywords route
├── components/charts/
│   └── KeywordCloud.vue         # CREATE: ECharts wordCloud wrapper
├── pages/analysis/
│   └── KeywordsPage.vue         # CREATE: content insight page
└── components/analysis/
    └── SubNavTabs.vue            # MODIFY: add 内容洞察 tab

tests/
└── test_nlp.py                  # CREATE: keyword extraction tests
```

---

### Task 1: Install Dependencies

**Files:**
- Modify: `pyproject.toml`
- Modify: `app/ui/package.json`

- [ ] **Step 1: Install jieba (Python)**

```bash
cd D:/Desktop/BiliAnalysis && uv add jieba 2>&1
```

Expected: `jieba` added to pyproject.toml.

- [ ] **Step 2: Install echarts-wordcloud (Frontend)**

```bash
cd D:/Desktop/BiliAnalysis/app/ui && pnpm add echarts-wordcloud 2>&1
```

Expected: `echarts-wordcloud` added to package.json.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock app/ui/package.json app/ui/pnpm-lock.yaml
git commit -m "chore: add jieba and echarts-wordcloud dependencies"
```

---

### Task 2: Chinese Stopwords List

**Files:**
- Create: `src/bilianalysis/nlp/stopwords.txt`

- [ ] **Step 1: Create stopwords.txt**

```
的
了
在
是
我
有
和
就
不
人
都
一
一个
上
也
很
到
说
要
去
你
会
着
没有
看
好
自己
这
他
她
它
们
那
些
什么
怎么
如何
为什么
因为
所以
但是
可以
这个
那个
已经
还是
或者
如果
虽然
然后
而且
不过
只是
当然
》
《
之
—
…
·
~
】

```
<!--  -->
```

(Full list available at deployment time; trim to ~100 common words.)

- [ ] **Step 2: Commit**

```bash
git add src/bilianalysis/nlp/stopwords.txt
git commit -m "feat: add Chinese stopwords list for keyword extraction"
```

---

### Task 3: NLP Keyword Extraction Module

**Files:**
- Create: `src/bilianalysis/nlp/__init__.py`
- Create: `src/bilianalysis/nlp/keywords.py`

- [ ] **Step 1: Create __init__.py**

```python
"""NLP module — jieba-based keyword extraction from video titles."""
from .keywords import (
    KeywordItem, WeeklyKeywords, CategoryKeywords, GlobalKeywords,
    KeywordsReport,
    extract_keywords, build_keywords_report,
)

__all__ = [
    "KeywordItem", "WeeklyKeywords", "CategoryKeywords", "GlobalKeywords",
    "KeywordsReport",
    "extract_keywords", "build_keywords_report",
]
```

- [ ] **Step 2: Create keywords.py**

```python
"""jieba TF-IDF keyword extraction from video titles."""
import json
import re
from pathlib import Path

import jieba.analyse
import pandas as pd
from pydantic import BaseModel


# ── Models ──

class KeywordItem(BaseModel):
    word: str
    weight: float


class WeeklyKeywords(BaseModel):
    week_number: int
    keywords: list[KeywordItem]  # TOP 10


class CategoryKeywords(BaseModel):
    tname: str
    keywords: list[KeywordItem]  # TOP 10


class GlobalKeywords(BaseModel):
    keywords: list[KeywordItem]  # TOP 50


class KeywordsReport(BaseModel):
    global_: GlobalKeywords
    by_week: list[WeeklyKeywords]
    by_category: list[CategoryKeywords]


# ── Stopwords ──

def _load_stopwords() -> set[str]:
    path = Path(__file__).parent / "stopwords.txt"
    if path.exists():
        return set(path.read_text(encoding="utf-8").splitlines())
    return set()


STOPWORDS = _load_stopwords()

# Add common single-char and noise words
STOPWORDS.update({
    " ", "", "\n", "\r", "\t",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "①", "②", "③", "④", "⑤",
    "第", "期", "万", "亿", "个", "次", "元", "年", "月", "日",
})

# Custom dictionary additions for Bilibili domain
for w in ["鬼畜", "混剪", "VLOG", "vlog", "MAD", "MMD", "AMV",
          "翻唱", "手书", "宅舞", "国创", "新番", "测评", "开箱"]:
    jieba.add_word(w)


# ── Extraction ──

def clean_title(title: str) -> str:
    """Remove punctuation, brackets, and normalize whitespace."""
    if not isinstance(title, str):
        return ""
    # Remove brackets and their content
    t = re.sub(r'[【\[（(].*?[】\]）)]', '', title)
    # Remove common video metadata
    t = re.sub(r'(https?://\S+)', '', t)
    # Keep Chinese chars, letters, digits
    t = re.sub(r'[^一-鿿\w]', ' ', t)
    return t.strip()


def extract_keywords(
    texts: list[str],
    topk: int = 20,
) -> list[KeywordItem]:
    """Extract TF-IDF keywords from a list of texts.

    Args:
        texts: List of cleaned title strings.
        topk: Number of keywords to return.

    Returns:
        Sorted list of KeywordItem (descending by weight).
    """
    if not texts:
        return []
    combined = " ".join(texts)
    tags = jieba.analyse.extract_tags(combined, topK=topk, withWeight=True)
    stopwords = STOPWORDS
    items = []
    for word, weight in tags:
        if word not in stopwords and len(word) >= 2:
            items.append(KeywordItem(word=word, weight=round(float(weight), 4)))
    return items


# ── Report Builder ──

def build_keywords_report(processed_dir: str | Path) -> KeywordsReport:
    """Build full keywords report from Video + Category Parquet files.

    Reads Video.parquet (title column) and Category.parquet (tname for
    grouping). Runs TF-IDF per week, per category, and globally.
    """
    pp = Path(processed_dir)
    video_df = pd.read_parquet(pp / "Video.parquet")
    category_df = pd.read_parquet(pp / "Category.parquet")

    # Merge category names
    df = video_df.join(category_df[["tname"]], how="left")

    # Clean titles
    df["clean_title"] = df["title"].apply(clean_title)

    # ── Global ──
    global_items = extract_keywords(df["clean_title"].dropna().tolist(), topk=50)

    # ── By Week ──
    # week_number is in VideoStat or we need to merge from the raw weekly data.
    # Since Video.parquet doesn't have week_number directly, we read from
    # the weekly_video mapping if available, or skip this dimension.
    by_week: list[WeeklyKeywords] = []
    try:
        wv = pd.read_parquet(pp / "WeeklyVideo.parquet")
        # Actually Video.parquet doesn't have week_number. Use WeeklyVideo.parquet
        # from warehouse to map aid → week_number
    except Exception:
        pass

    # Fallback: group by week_number from raw data (we already read it in clean_data)
    # We'll use the processed Parquet which may not have week_number.
    # For now, read from Warehouse ADS which has week_number.
    try:
        dwd = pd.read_parquet(pp / "dwd_fact_video.parquet")
        week_groups = dwd.groupby("weekly_number")["title"]
        for wn, titles in week_groups:
            cleaned = titles.dropna().apply(clean_title).tolist()
            items = extract_keywords(cleaned, topk=10)
            by_week.append(WeeklyKeywords(week_number=int(wn), keywords=items))
        by_week.sort(key=lambda x: x.week_number)
    except Exception:
        # Fallback: read directly by building aid→week map from raw
        pass

    # ── By Category ──
    by_category: list[CategoryKeywords] = []
    for tname, group in df.groupby("tname"):
        if pd.isna(tname) or not tname:
            continue
        cleaned = group["clean_title"].dropna().tolist()
        items = extract_keywords(cleaned, topk=10)
        by_category.append(CategoryKeywords(tname=str(tname), keywords=items))
    by_category.sort(key=lambda x: -len(x.keywords))

    return KeywordsReport(
        global_=GlobalKeywords(keywords=global_items),
        by_week=by_week,
        by_category=by_category,
    )
```

- [ ] **Step 3: Run quick verification**

```bash
cd D:/Desktop/BiliAnalysis && uv run python -c "
from bilianalysis.nlp import build_keywords_report
r = build_keywords_report('data/processed')
print(f'Global keywords: {len(r.global_.keywords)}')
print(f'By week: {len(r.by_week)} weeks')
print(f'By category: {len(r.by_category)} categories')
print('Top 5 global:', [(k.word, k.weight) for k in r.global_.keywords[:5]])
" 2>&1
```

Expected: Global keywords >= 0, by_week and by_category non-empty.

- [ ] **Step 4: Commit**

```bash
git add src/bilianalysis/nlp/__init__.py src/bilianalysis/nlp/keywords.py
git commit -m "feat: add NLP keyword extraction module (jieba TF-IDF)"
```

---

### Task 4: Keywords Scheduler Task

**Files:**
- Create: `src/bilianalysis/scheduler/builtins/keywords_task.py`

- [ ] **Step 1: Create keywords_task.py**

Following the existing pattern (stats_task.py, cluster_task.py):

```python
"""关键词提取 Task。"""
import json
import time
from pathlib import Path

from bilianalysis.scheduler.task import Task, TaskResult, TaskContext
from bilianalysis.scheduler.registry import register
from bilianalysis.nlp import build_keywords_report


@register("keywords")
class KeywordsTask(Task):
    name = "keywords"

    async def run(self, ctx: TaskContext) -> TaskResult:
        start = time.monotonic()
        try:
            report = build_keywords_report(ctx.config.data.processed_dir)
            # Write to reports dir
            rd = Path(ctx.config.data.reports_dir)
            rd.mkdir(parents=True, exist_ok=True)
            (rd / "keywords_report.json").write_text(
                report.model_dump_json(indent=2), encoding="utf-8")
            return TaskResult(
                task_name="keywords", status="success",
                duration_seconds=round(time.monotonic() - start, 2),
                output={
                    "global_keywords": len(report.global_.keywords),
                    "weeks_with_keywords": len(report.by_week),
                    "categories_with_keywords": len(report.by_category),
                },
            )
        except Exception as exc:
            return TaskResult(
                task_name="keywords", status="failed",
                duration_seconds=round(time.monotonic() - start, 2),
                error=str(exc),
            )
```

- [ ] **Step 2: Register the task import**

```bash
# It's auto-registered via @register decorator.
# Just need to make sure builtins/__init__.py imports it.
```

Check `src/bilianalysis/scheduler/builtins/__init__.py` — it likely already imports all task modules.

- [ ] **Step 3: Verify task registration**

```bash
cd D:/Desktop/BiliAnalysis && uv run python -c "
import bilianalysis.scheduler.builtins
from bilianalysis.scheduler.registry import get_task
t = get_task('keywords')
print(t.name)
" 2>&1
```

Expected: `keywords`

- [ ] **Step 4: Commit**

```bash
git add src/bilianalysis/scheduler/builtins/keywords_task.py
git commit -m "feat: add keywords scheduler task"
```

---

### Task 5: API Endpoint — GET /api/analysis/keywords

**Files:**
- Modify: `app/api/router/analysis.py`

- [ ] **Step 1: Add KeywordsReport import and endpoint**

Add to `analysis.py` (append before the last line):

```python
from bilianalysis.nlp import KeywordsReport as NLPKeywordsReport


@router.get("/analysis/keywords")
async def get_keywords(config: Annotated[AppConfig, Depends(get_config)]):
    """Get keyword analysis report from cache, or 503 if not generated."""
    cached = _read_json(_reports_dir(config) / "keywords_report.json")
    if cached:
        return cached
    _check_data_ready(config)
    raise HTTPException(
        status_code=503,
        detail="关键词报告尚未生成，请先触发 analysis 流水线",
    )
```

- [ ] **Step 2: Verify endpoint**

```bash
# Start backend, then:
curl -s http://localhost:8080/api/analysis/keywords 2>&1 | head -c 100
```

Expected: 200 with JSON or 503 with message.

- [ ] **Step 3: Commit**

```bash
git add app/api/router/analysis.py
git commit -m "feat: add GET /api/analysis/keywords endpoint"
```

---

### Task 6: Frontend Types + Alova Functions

**Files:**
- Modify: `app/ui/src/types/api.ts`
- Modify: `app/ui/src/composables/useApi.ts`

- [ ] **Step 1: Add types to api.ts**

```typescript
// ── Keywords ──

export interface KeywordItem {
  word: string
  weight: number
}

export interface WeeklyKeywords {
  week_number: number
  keywords: KeywordItem[]
}

export interface CategoryKeywords {
  tname: string
  keywords: KeywordItem[]
}

export interface GlobalKeywords {
  keywords: KeywordItem[]
}

export interface KeywordsReport {
  global_: GlobalKeywords
  by_week: WeeklyKeywords[]
  by_category: CategoryKeywords[]
}
```

- [ ] **Step 2: Add Alova function to useApi.ts**

```typescript
import type { ..., KeywordsReport } from '@/types/api'

// In the request functions section:
export function fetchKeywords() {
  return alova.Get<KeywordsReport>('/analysis/keywords')
}

// In the composables section:
export function useKeywords() {
  return useRequest(fetchKeywords, { immediate: false })
}
```

- [ ] **Step 3: Type check**

```bash
cd app/ui && pnpm exec vue-tsc -b --noEmit 2>&1
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add app/ui/src/types/api.ts app/ui/src/composables/useApi.ts
git commit -m "feat: add Keywords types and Alova request function"
```

---

### Task 7: ECharts WordCloud Chart Component

**Files:**
- Create: `app/ui/src/components/charts/KeywordCloud.vue`

- [ ] **Step 1: Create KeywordCloud.vue**

```vue
<script setup lang="ts">
import { computed, ref, type Ref } from 'vue'
import { useChart } from '@/composables/useChart'
import type { KeywordItem } from '@/types/api'
import type { EChartsOption } from 'echarts'
import 'echarts-wordcloud'

const props = defineProps<{ keywords: KeywordItem[] }>()

const chartRef: Ref<HTMLElement | null> = ref(null)

const option = computed<EChartsOption>(() => {
  const data = props.keywords.map(k => ({
    name: k.word,
    value: Math.round(k.weight * 10000),
  }))

  if (data.length === 0) {
    return {
      title: { text: '暂无数据', left: 'center', top: 'center',
               textStyle: { color: '#9CA3AF', fontSize: 14 } },
    }
  }

  return {
    tooltip: {
      show: true,
      formatter: (params: any) => `${params.name}: ${params.value}`,
    },
    series: [{
      type: 'wordCloud' as any,
      shape: 'circle',
      left: 'center',
      top: 'center',
      width: '90%',
      height: '90%',
      sizeRange: [14, 48],
      rotationRange: [-45, 45],
      rotationStep: 15,
      gridSize: 8,
      drawOutOfBound: false,
      layoutAnimation: true,
      textStyle: {
        fontFamily: 'Inter, "HarmonyOS Sans SC", "PingFang SC", sans-serif',
        fontWeight: 'normal',
        color: () => {
          const colors = ['#00AEEC', '#22C55E', '#F59E0B', '#8B5CF6',
                          '#EF4444', '#10B981', '#EC4899', '#6366F1']
          return colors[Math.floor(Math.random() * colors.length)]
        },
      },
      emphasisStyle: {
        fontWeight: 'bold',
        color: '#00AEEC',
      },
      data,
    }],
  }
})

useChart(chartRef, option)
</script>

<template>
  <div ref="chartRef" class="w-full h-[400px]" />
</template>
```

- [ ] **Step 2: Register wordCloud chart type in useChart.ts**

```typescript
// In useChart.ts, add:
import 'echarts-wordcloud'
```

Actually, the import in the component itself should work since echarts-wordcloud registers itself. But to ensure tree-shaking compatibility, add it in useChart.ts instead.

```typescript
// At the top of useChart.ts, after the existing imports:
import 'echarts-wordcloud'
```

- [ ] **Step 3: Type check**

```bash
cd app/ui && pnpm exec vue-tsc -b --noEmit 2>&1
```

Expected: No errors (may have `as any` for wordCloud type).

- [ ] **Step 4: Commit**

```bash
git add app/ui/src/components/charts/KeywordCloud.vue app/ui/src/composables/useChart.ts
git commit -m "feat: add ECharts wordCloud chart component"
```

---

### Task 8: KeywordsPage + Route + SubNavTabs

**Files:**
- Create: `app/ui/src/pages/analysis/KeywordsPage.vue`
- Modify: `app/ui/src/router/index.ts`
- Modify: `app/ui/src/components/analysis/SubNavTabs.vue`

- [ ] **Step 1: Create KeywordsPage.vue**

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useKeywords } from '@/composables/useApi'
import PageShell from '@/components/layout/PageShell.vue'
import SectionHeader from '@/components/shared/SectionHeader.vue'
import SubNavTabs from '@/components/analysis/SubNavTabs.vue'
import KeywordCloud from '@/components/charts/KeywordCloud.vue'

const { data, loading, error, send } = useKeywords()

onMounted(() => send())

const selectedWeek = ref<number | null>(null)
const selectedCategory = ref<string | null>(null)
</script>

<template>
  <PageShell>
    <SubNavTabs />

    <div v-if="loading" class="space-y-8">
      <div class="h-[400px] bg-card rounded-[12px] animate-pulse" />
      <div class="h-[400px] bg-card rounded-[12px] animate-pulse" />
    </div>

    <div v-else-if="error" class="py-24 text-center">
      <p class="text-lg font-semibold text-text mb-2">加载失败，请重试</p>
      <p class="text-sm text-text-secondary mb-6">{{ (error as Error).message }}</p>
      <button @click="send()" class="px-6 py-2 bg-blue text-white rounded-[12px] font-medium hover:opacity-90">重试</button>
    </div>

    <template v-else-if="data">
      <!-- Global Keywords -->
      <section class="py-8">
        <SectionHeader title="全局热词" :description="`TOP ${data.global_.keywords.length} 关键词`" />
        <div class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
          <KeywordCloud :keywords="data.global_.keywords" />
        </div>
      </section>

      <!-- Weekly Keywords -->
      <section class="py-8">
        <SectionHeader title="每周热词" description="按周报期数查看关键词" />
        <div class="flex gap-2 flex-wrap mb-4">
          <button
            v-for="wk in data.by_week"
            :key="wk.week_number"
            @click="selectedWeek = wk.week_number"
            class="px-3 py-1.5 border rounded-[20px] text-xs font-medium transition-colors cursor-pointer"
            :class="selectedWeek === wk.week_number
              ? 'bg-blue text-white border-blue'
              : 'bg-card text-text-secondary border-border hover:border-blue hover:text-blue'"
          >
            第{{ wk.week_number }}期
          </button>
        </div>
        <div v-if="selectedWeek" class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
          <KeywordCloud
            :keywords="data.by_week.find(w => w.week_number === selectedWeek)?.keywords ?? []"
          />
        </div>
        <div v-else class="text-text-secondary text-sm">请选择一期周报</div>
      </section>

      <!-- Category Keywords -->
      <section class="py-8">
        <SectionHeader title="分区热词" description="按内容分区查看关键词" />
        <div class="flex gap-2 flex-wrap mb-4">
          <button
            v-for="cat in data.by_category"
            :key="cat.tname"
            @click="selectedCategory = cat.tname"
            class="px-3 py-1.5 border rounded-[20px] text-xs font-medium transition-colors cursor-pointer"
            :class="selectedCategory === cat.tname
              ? 'bg-blue text-white border-blue'
              : 'bg-card text-text-secondary border-border hover:border-blue hover:text-blue'"
          >
            {{ cat.tname }}
          </button>
        </div>
        <div v-if="selectedCategory" class="bg-card rounded-[12px] p-6 shadow-[var(--shadow-default)]">
          <KeywordCloud
            :keywords="data.by_category.find(c => c.tname === selectedCategory)?.keywords ?? []"
          />
        </div>
        <div v-else class="text-text-secondary text-sm">请选择一个分区</div>
      </section>
    </template>

    <div v-else class="py-12 text-center">
      <p class="text-text-secondary">暂无数据，请先触发一次分析流水线</p>
    </div>
  </PageShell>
</template>
```

- [ ] **Step 2: Add route**

```typescript
// In router/index.ts, after the predict route:
{
  path: '/analysis/keywords',
  name: 'keywords',
  component: () => import('@/pages/analysis/KeywordsPage.vue'),
},
```

- [ ] **Step 3: Add tab to SubNavTabs**

```typescript
// In SubNavTabs.vue, add to TABS array:
const TABS = [
  { key: 'stats', label: '统计概览', path: '/analysis/stats' },
  { key: 'clusters', label: '聚类分析', path: '/analysis/clusters' },
  { key: 'predict', label: '预测分析', path: '/analysis/predictions' },
  { key: 'keywords', label: '内容洞察', path: '/analysis/keywords' },
] as const
```

And update activeKey:
```typescript
const activeKey = computed(() => {
  if (route.path.includes('keywords')) return 'keywords'
  if (route.path.includes('clusters')) return 'clusters'
  if (route.path.includes('predict')) return 'predict'
  return 'stats'
})
```

- [ ] **Step 4: Type check + tests**

```bash
cd app/ui && pnpm exec vue-tsc -b --noEmit 2>&1 && pnpm exec vitest run 2>&1 | tail -3
```

Expected: Type check passes. Tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/ui/src/pages/analysis/KeywordsPage.vue \
        app/ui/src/router/index.ts \
        app/ui/src/components/analysis/SubNavTabs.vue
git commit -m "feat: add KeywordsPage + route + SubNavTabs tab"
```

---

### Task 9: Add keywords to config.yaml pipeline

**Files:**
- Modify: `config.example.yaml`

- [ ] **Step 1: Add keywords step**

```yaml
    analysis:
      schedule: ""                 # 空字符串 = 仅手动触发
      steps: [clean_data, statistics, clustering, prediction, keywords]
      step_failure: stop
```

- [ ] **Step 2: Commit**

```bash
git add config.example.yaml
git commit -m "chore: add keywords step to analysis pipeline"
```

---

### Task 10: Unit Tests

**Files:**
- Create: `tests/test_nlp.py`

- [ ] **Step 1: Write tests**

```python
import pytest
from bilianalysis.nlp import (
    KeywordItem, extract_keywords, clean_title,
)


class TestCleanTitle:
    def test_removes_brackets(self):
        assert clean_title("【MAD】混剪作品") == "混剪作品"

    def test_removes_urls(self):
        assert clean_title("看这个 https://b23.tv/xxx 视频") == "看这个  视频"

    def test_handles_none(self):
        assert clean_title(None) == ""

    def test_handles_empty(self):
        assert clean_title("") == ""


class TestExtractKeywords:
    def test_returns_keyword_items(self):
        result = extract_keywords(["鬼畜视频", "鬼畜大作", "搞笑视频"], topk=5)
        assert len(result) > 0
        assert all(isinstance(k, KeywordItem) for k in result)
        assert all(k.weight > 0 for k in result)

    def test_empty_input(self):
        assert extract_keywords([]) == []

    def test_topk_respected(self):
        result = extract_keywords(
            ["人工智能改变生活", "机器学习入门", "深度学习框架对比",
             "AI时代来临", "数据科学导论", "神经网络详解",
             "自然语言处理"], topk=3)
        assert len(result) <= 3

    def test_single_char_filtered(self):
        result = extract_keywords(["这是一段测试的文本"], topk=10)
        # "的" should be filtered as stopword
        words = {k.word for k in result}
        assert "的" not in words
```

- [ ] **Step 2: Run tests**

```bash
cd D:/Desktop/BiliAnalysis && uv run pytest tests/test_nlp.py -v 2>&1
```

Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_nlp.py
git commit -m "test: add NLP keyword extraction unit tests"
```

---

### Task 11: Run Analysis Pipeline + End-to-End Verification

**Files:** None (verification only)

- [ ] **Step 1: Run analysis pipeline to generate keywords report**

```bash
cd D:/Desktop/BiliAnalysis && uv run bilianalysis schedule run -p analysis 2>&1
```

Expected: Pipeline completes, keywords step succeeds.

- [ ] **Step 2: Verify report file exists**

```bash
ls -la data/reports/keywords_report.json 2>&1
```

- [ ] **Step 3: Validate JSON content**

```bash
cd D:/Desktop/BiliAnalysis && uv run python -c "
import json
with open('data/reports/keywords_report.json') as f:
    r = json.load(f)
print('Global keywords:', len(r['global_']['keywords']))
print('Weeks:', len(r['by_week']))
print('Categories:', len(r['by_category']))
print('Top 5:', [k['word'] for k in r['global_']['keywords'][:5]])
" 2>&1
```

Expected: Reasonable keywords output.

- [ ] **Step 4: Test API endpoint**

```bash
curl -s http://localhost:8080/api/analysis/keywords | head -c 200
```

Expected: 200 with JSON.

- [ ] **Step 5: Full test suite**

```bash
cd D:/Desktop/BiliAnalysis && uv run pytest tests/ -q 2>&1
```

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "chore: end-to-end verification complete"
```

---

## Parallel Execution Guide

Tasks that can run in parallel:

```
Task 1 (deps) → Task 2 (stopwords)
                    ↓
Task 3 (nlp module) → Task 4 (scheduler task)
                    ↓
Task 5 (API endpoint)
                    ↓
Task 6 (frontend types) → Task 7 (wordCloud chart) → Task 8 (KeywordsPage)
                                                              ↓
Task 9 (config) → Task 10 (tests) → Task 11 (verification)
```
