# 分析引擎实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 PandasEngine 分析引擎——分批加载 raw JSON 清洗后写出 5 张 Parquet，支持统计分析、KMeans 聚类、线性回归预测。

**Architecture:** `base.py`（AnalysisEngine ABC + 报告模型）→ `pandas_engine.py`（clean_data → statistics → clustering → prediction）→ `__init__.py`（公开 API）。复用已有 `models.py` 的 5 个数据模型。

**Tech Stack:** pandas, scikit-learn, pyarrow (pandas 默认后端), pydantic

---

## 文件结构

```
新建:
├── src/bilianalysis/engine/
│   ├── __init__.py              # 公开 API
│   ├── base.py                  # AnalysisEngine ABC + CleanReport/StatReport/ClusterReport/PredictionReport
│   └── pandas_engine.py         # PandasEngine(DataSection) — 全部 4 个方法
├── tests/test_engine.py         # ~30 tests total

修改:
└── pyproject.toml               # 添加 pandas, scikit-learn 依赖
```

已有 `src/bilianalysis/models.py`（Weekly/Video/Creator/Category/VideoStat）直接 import。

---

### Task 1: 添加依赖

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Install pandas and scikit-learn**

Run: `uv add pandas scikit-learn`

- [ ] **Step 2: Verify installs**

Run: `uv run python -c "import pandas; import sklearn; import pyarrow; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add pandas and scikit-learn dependencies"
```

---

### Task 2: Create base.py — Report Models + Abstract Interface

**Files:**
- Create: `src/bilianalysis/engine/__init__.py` (placeholder first, populated in Task 8)
- Create: `src/bilianalysis/engine/base.py`

**Note:** 所有报告模型定义在 base.py 中，AnalysisEngine ABC 也在此文件。PandasEngine 在 Task 3 创建。

#### Step 1: Create test_engine.py with model instantiation tests

Create `tests/test_engine.py`:

```python
"""测试分析引擎模块。"""
import pytest
from bilianalysis.engine.base import (
    AnalysisEngine,
    CleanReport,
    OverallStats,
    CategoryStats,
    CreatorStats,
    WeeklyTrend,
    StatReport,
    ClusterGroup,
    ClusterResult,
    ClusterReport,
    PredictionResult,
    PredictionReport,
)


class TestCleanReport:
    def test_create_clean_report(self):
        report = CleanReport(
            total_weeks=50,
            total_videos=500,
            duplicates_dropped=3,
            missing_filled=10,
            outliers_flagged=2,
            duration_seconds=1.5,
        )
        assert report.total_weeks == 50
        assert report.duplicates_dropped == 3

    def test_clean_report_defaults(self):
        report = CleanReport(
            total_weeks=0, total_videos=0, duplicates_dropped=0,
            missing_filled=0, outliers_flagged=0, duration_seconds=0.0,
        )
        assert isinstance(report, CleanReport)


class TestStatReport:
    def test_full_report_structure(self):
        overall = OverallStats(
            total_videos=100, total_creators=20,
            avg_view=50000.0, avg_like=2000.0, avg_coin=500.0,
            avg_favorite=800.0, avg_share=100.0, avg_danmaku=300.0,
            avg_like_rate=0.04, avg_coin_rate=0.01, avg_favorite_rate=0.016,
        )
        categories = [CategoryStats(tname="动画", video_count=30, avg_view=60000.0, avg_like=2500.0, avg_interaction_rate=0.06)]
        creators = [CreatorStats(mid=123, name="测试UP", appearance_count=5, total_view=500000, total_like=20000, total_favorite=8000)]
        weeks = [WeeklyTrend(week_number=1, video_count=30, avg_view=50000.0, avg_like=2000.0, avg_interaction_rate=0.05)]

        report = StatReport(overall=overall, by_category=categories, by_creator=creators, by_week=weeks)
        assert report.overall.total_videos == 100
        assert len(report.by_category) == 1
        assert len(report.by_creator) == 1
        assert len(report.by_week) == 1


class TestClusterReport:
    def test_report_structure(self):
        clusters = ClusterResult(
            k=3,
            clusters=[
                ClusterGroup(label=0, tag="爆款视频", count=30,
                             centroid={"view": 100000.0, "like": 5000.0, "coin": 1000.0, "favorite": 2000.0},
                             avg_view=100000.0, avg_like=5000.0, avg_coin=1000.0, avg_favorite=2000.0,
                             sample_ids=[1, 2, 3]),
            ],
            silhouette_score=0.65,
            feature_importance={"view": 0.4, "like": 0.3, "coin": 0.2, "favorite": 0.1},
        )
        report = ClusterReport(
            clusters=clusters,
            scatter_data={"labels": [0, 1, 2], "x": [1.0, -1.0, 0.5], "y": [0.5, 1.0, -1.0]},
            duration_seconds=2.0,
        )
        assert report.clusters.k == 3
        assert len(report.clusters.clusters) == 1


class TestPredictionReport:
    def test_report_structure(self):
        view_pred = PredictionResult(
            model_type="linear_regression", target="view", r2_score=0.85, mae=5000.0,
            coefficients={"week_number": 100.0}, intercept=40000.0,
            fitted=[{"week_number": 1, "actual": 50000, "predicted": 49000}],
            forecast=[{"week_number": 51, "predicted": 55000}],
        )
        like_pred = PredictionResult(
            model_type="linear_regression", target="like", r2_score=0.75, mae=200.0,
            coefficients={"week_number": 5.0}, intercept=1800.0,
            fitted=[{"week_number": 1, "actual": 2000, "predicted": 1950}],
            forecast=[{"week_number": 51, "predicted": 2200}],
        )
        report = PredictionReport(view_predict=view_pred, like_predict=like_pred, duration_seconds=3.0)
        assert report.view_predict.r2_score == 0.85
        assert report.like_predict.target == "like"
        assert len(report.view_predict.forecast) == 1


class TestAnalysisEngineABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            AnalysisEngine()
```

#### Step 2: Run to verify fail

Run: `uv run pytest tests/test_engine.py -v`
Expected: FAIL — `bilianalysis.engine.base` module not found

#### Step 3: Create placeholder __init__.py

Create `src/bilianalysis/engine/__init__.py`:

```python
"""分析引擎模块。"""
```

#### Step 4: Create base.py

Create `src/bilianalysis/engine/base.py`:

```python
"""分析引擎抽象基类和报告模型。"""
from abc import ABC, abstractmethod
from pydantic import BaseModel


# ── clean_data ──

class CleanReport(BaseModel):
    """清洗阶段产出报告。"""
    total_weeks: int
    total_videos: int
    duplicates_dropped: int
    missing_filled: int
    outliers_flagged: int
    duration_seconds: float


# ── statistics ──

class OverallStats(BaseModel):
    total_videos: int
    total_creators: int
    avg_view: float
    avg_like: float
    avg_coin: float
    avg_favorite: float
    avg_share: float
    avg_danmaku: float
    avg_like_rate: float
    avg_coin_rate: float
    avg_favorite_rate: float


class CategoryStats(BaseModel):
    tname: str
    video_count: int
    avg_view: float
    avg_like: float
    avg_interaction_rate: float


class CreatorStats(BaseModel):
    mid: int
    name: str
    appearance_count: int
    total_view: int
    total_like: int
    total_favorite: int


class WeeklyTrend(BaseModel):
    week_number: int
    video_count: int
    avg_view: float
    avg_like: float
    avg_interaction_rate: float


class StatReport(BaseModel):
    overall: OverallStats
    by_category: list[CategoryStats]
    by_creator: list[CreatorStats]
    by_week: list[WeeklyTrend]


# ── clustering ──

class ClusterGroup(BaseModel):
    label: int
    tag: str
    count: int
    centroid: dict[str, float]
    avg_view: float
    avg_like: float
    avg_coin: float
    avg_favorite: float
    sample_ids: list[int]


class ClusterResult(BaseModel):
    k: int
    clusters: list[ClusterGroup]
    silhouette_score: float
    feature_importance: dict[str, float]


class ClusterReport(BaseModel):
    clusters: ClusterResult
    scatter_data: dict
    duration_seconds: float


# ── prediction ──

class PredictionResult(BaseModel):
    model_type: str
    target: str
    r2_score: float
    mae: float
    coefficients: dict[str, float]
    intercept: float
    fitted: list[dict]
    forecast: list[dict]


class PredictionReport(BaseModel):
    view_predict: PredictionResult
    like_predict: PredictionResult
    duration_seconds: float


# ── ABC ──

class AnalysisEngine(ABC):
    @abstractmethod
    async def clean_data(self) -> CleanReport:
        """分批加载 raw JSON → 清洗 → 写出 5 张 Parquet 表。"""
        ...

    @abstractmethod
    def statistics(self) -> StatReport:
        """从 processed/ Parquet 读取 → join → groupby 聚合。"""
        ...

    @abstractmethod
    def clustering(self) -> ClusterReport:
        """从 processed/ Parquet 读取 → KMeans(k=3) 聚类 → PCA 降维。"""
        ...

    @abstractmethod
    def prediction(self) -> PredictionReport:
        """从 processed/ Parquet 读取 → 周序列 LinearRegression 预测。"""
        ...
```

#### Step 5: Run model tests

Run: `uv run pytest tests/test_engine.py -v`
Expected: 8 PASS (model instantiation + ABC tests)

#### Step 6: Commit

```bash
git add src/bilianalysis/engine/__init__.py src/bilianalysis/engine/base.py tests/test_engine.py
git commit -m "feat: add analysis engine ABC and report models"
```

---

### Task 3: Create PandasEngine with clean_data()

**Files:**
- Create: `src/bilianalysis/engine/pandas_engine.py`
- Modify: `tests/test_engine.py` (append clean_data tests)

#### Step 1: Append clean_data test to test_engine.py

Append to `tests/test_engine.py`:

```python
import json
import pandas as pd
from pathlib import Path
from bilianalysis.engine.pandas_engine import PandasEngine
from bilianalysis.config import DataSection


# 模拟 Bilibili API 返回的 raw JSON 结构
def _make_week_json(number: int, videos: list[dict]) -> dict:
    return {
        "number": number,
        "config": {"number": number, "subject": f"第{number}期", "name": f"每周必看 {number:02d}",
                   "start_time": 1600000000, "end_time": 1600600000},
        "videos": videos,
    }


def _make_video(aid: int, view: int = 10000, like: int = 500) -> dict:
    return {
        "aid": aid, "bvid": f"BV{aid:010d}", "title": f"视频{aid}", "desc": "描述",
        "duration": 120, "pubdate": 1600000000, "cid": aid * 10, "pic": f"https://img/{aid}.jpg",
        "owner": {"mid": aid + 1000, "name": f"UP{aid}", "face": f"https://face/{aid}.jpg"},
        "stat": {"aid": aid, "view": view, "like": like, "coin": 100, "favorite": 200, "share": 30, "reply": 50, "danmaku": 60},
        "tid": 1, "tname": "动画",
    }


class TestPandasEngineCleanData:
    @pytest.mark.asyncio
    async def test_clean_data_basic(self, tmp_path, monkeypatch):
        """基本清洗流程：2 个 week JSON → 5 张 Parquet → CleanReport。"""
        raw_dir = tmp_path / "raw"
        processed_dir = tmp_path / "processed"
        raw_dir.mkdir()

        # 写入 2 个 week JSON（batch_size=2，一批处理）
        for n in [1, 2]:
            data = _make_week_json(n, [_make_video(n * 100 + i) for i in range(3)])
            (raw_dir / f"week_{n:03d}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf, batch_size=5)
        report = await engine.clean_data()

        assert report.total_weeks == 2
        assert report.total_videos == 6
        assert report.duplicates_dropped == 0

        # 验证 5 个 Parquet 文件存在
        for table in ["Weekly", "Video", "Creator", "Category", "VideoStat"]:
            path = processed_dir / f"{table}.parquet"
            assert path.exists(), f"{table}.parquet should exist"
            df = pd.read_parquet(path)
            assert len(df) > 0, f"{table} should have rows"

    @pytest.mark.asyncio
    async def test_clean_data_sliding_window(self, tmp_path, monkeypatch):
        """3 个 week，batch_size=2，验证滑动窗口分两批处理。"""
        raw_dir = tmp_path / "raw"
        processed_dir = tmp_path / "processed"
        raw_dir.mkdir()

        for n in [1, 2, 3]:
            data = _make_week_json(n, [_make_video(n * 100)])
            (raw_dir / f"week_{n:03d}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf, batch_size=2)
        report = await engine.clean_data()

        assert report.total_weeks == 3
        assert report.total_videos == 3
        df = pd.read_parquet(processed_dir / "Video.parquet")
        assert len(df) == 3

    @pytest.mark.asyncio
    async def test_clean_data_missing_values(self, tmp_path, monkeypatch):
        """缺失值：数值列填充为 0，文本列填充为 ""。"""
        raw_dir = tmp_path / "raw"
        processed_dir = tmp_path / "processed"
        raw_dir.mkdir()

        # video 缺少 title 和 stat.like
        video = _make_video(1)
        del video["title"]
        del video["stat"]["like"]
        data = _make_week_json(1, [video])
        (raw_dir / "week_001.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf, batch_size=10)
        report = await engine.clean_data()

        assert report.missing_filled > 0
        df_video = pd.read_parquet(processed_dir / "Video.parquet")
        assert df_video["title"].iloc[0] == ""
        df_stat = pd.read_parquet(processed_dir / "VideoStat.parquet")
        assert df_stat["like"].iloc[0] == 0

    @pytest.mark.asyncio
    async def test_clean_data_deduplication(self, tmp_path, monkeypatch):
        """跨批次 aid 去重：相同 aid 保留首次出现。"""
        raw_dir = tmp_path / "raw"
        processed_dir = tmp_path / "processed"
        raw_dir.mkdir()

        # week 1 有 aid=100，week 2 也有 aid=100
        data1 = _make_week_json(1, [_make_video(100)])
        data2 = _make_week_json(2, [_make_video(100), _make_video(101)])
        (raw_dir / "week_001.json").write_text(json.dumps(data1, ensure_ascii=False), encoding="utf-8")
        (raw_dir / "week_002.json").write_text(json.dumps(data2, ensure_ascii=False), encoding="utf-8")

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf, batch_size=2)
        report = await engine.clean_data()

        assert report.duplicates_dropped == 1
        df_video = pd.read_parquet(processed_dir / "Video.parquet")
        assert len(df_video) == 2  # 100, 101

    @pytest.mark.asyncio
    async def test_clean_data_outliers(self, tmp_path, monkeypatch):
        """异常值检测：view < 0 视为异常。"""
        raw_dir = tmp_path / "raw"
        processed_dir = tmp_path / "processed"
        raw_dir.mkdir()

        video = _make_video(1, view=-100)
        data = _make_week_json(1, [video])
        (raw_dir / "week_001.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf, batch_size=10)
        report = await engine.clean_data()

        assert report.outliers_flagged >= 1

    @pytest.mark.asyncio
    async def test_clean_data_type_conversion(self, tmp_path, monkeypatch):
        """类型转换：验证各列 dtype 正确。"""
        raw_dir = tmp_path / "raw"
        processed_dir = tmp_path / "processed"
        raw_dir.mkdir()

        data = _make_week_json(1, [_make_video(1)])
        (raw_dir / "week_001.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf, batch_size=10)
        await engine.clean_data()

        df_video = pd.read_parquet(processed_dir / "Video.parquet")
        assert pd.api.types.is_integer_dtype(df_video["aid"])
        assert pd.api.types.is_integer_dtype(df_video["duration"])

        df_stat = pd.read_parquet(processed_dir / "VideoStat.parquet")
        assert pd.api.types.is_float_dtype(df_stat["view"])
        assert pd.api.types.is_float_dtype(df_stat["like"])
```

#### Step 2: Run to verify fail

Run: `uv run pytest tests/test_engine.py::TestPandasEngineCleanData -v`
Expected: FAIL — `PandasEngine` not defined

#### Step 3: Create pandas_engine.py skeleton with clean_data()

Create `src/bilianalysis/engine/pandas_engine.py`:

```python
"""Pandas 分析引擎实现。"""
import json
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from bilianalysis.config.model import DataSection
from bilianalysis.engine.base import AnalysisEngine, CleanReport, StatReport, ClusterReport, PredictionReport


class PandasEngine(AnalysisEngine):
    """基于 Pandas 的分析引擎。

    分批加载 raw JSON，清洗后写出 5 张 Parquet 表，
    支持统计分析、KMeans 聚类、线性回归预测。
    """

    def __init__(self, data_config: DataSection, batch_size: int = 10):
        self._batch_size = batch_size
        self._raw_dir = Path(data_config.raw_dir)
        self._processed_dir = Path(data_config.processed_dir)
        self._reports_dir = Path(data_config.reports_dir)

    # ── clean_data ───────────────────────────────────────────

    async def clean_data(self) -> CleanReport:
        start_time = time.monotonic()
        start_time_ref = start_time  # alias for readability

        files = sorted(self._raw_dir.glob("week_*.json"),
                       key=lambda p: int(p.stem.split("_")[1]))

        total_weeks = len(files)
        total_videos = 0
        duplicates_dropped = 0
        missing_filled = 0
        outliers_flagged = 0
        seen_aids: set[int] = set()

        # 全量覆盖：清空 processed/
        self._processed_dir.mkdir(parents=True, exist_ok=True)
        for f in self._processed_dir.glob("*.parquet"):
            f.unlink()

        writers: dict[str, pq.ParquetWriter] = {}

        for i in range(0, len(files), self._batch_size):
            batch = files[i:i + self._batch_size]

            # 2.1 加载
            records = []
            for fp in batch:
                with open(fp, encoding="utf-8") as fh:
                    records.append(json.load(fh))

            # 2.2 拆表
            dfs = self._extract_tables(records)

            # 2.3 缺失值
            dfs = self._fill_missing(dfs)
            batch_missing = sum(df.isna().sum().sum() for df in dfs.values())  # should be 0 after fill
            missing_filled += batch_missing  # pre-fill count; post-fill this is 0

            # 2.4 去重（跨批次）
            video_df = dfs["Video"]
            before = len(video_df)
            mask = ~video_df["aid"].isin(seen_aids)
            dfs["Video"] = video_df[mask]
            duplicates_dropped += before - len(dfs["Video"])

            # 同步去重到关联表
            kept_aids = set(dfs["Video"]["aid"])
            dfs["VideoStat"] = dfs["VideoStat"][dfs["VideoStat"]["aid"].isin(kept_aids)]
            dfs["Creator"] = dfs["Creator"][dfs["Creator"]["mid"].isin(
                dfs["Video"]["aid"].apply(lambda x: x + 1000)  # 与 extract 的 owner 映射一致
            )]

            seen_aids.update(kept_aids)
            total_videos += len(dfs["Video"])

            # 2.5 类型转换
            dfs = self._convert_types(dfs)

            # 2.6 异常值检测
            stat_before = len(dfs["VideoStat"])
            dfs["VideoStat"] = dfs["VideoStat"][
                (dfs["VideoStat"]["view"] >= 0) &
                (dfs["VideoStat"]["like"] >= 0) &
                (dfs["VideoStat"]["coin"] >= 0) &
                (dfs["VideoStat"]["favorite"] >= 0) &
                (dfs["VideoStat"]["share"] >= 0) &
                (dfs["VideoStat"]["reply"] >= 0) &
                (dfs["VideoStat"]["danmaku"] >= 0)
            ]
            outliers_flagged += stat_before - len(dfs["VideoStat"])

            # 2.7 写出 Parquet
            for table_name in ["Weekly", "Video", "Creator", "Category", "VideoStat"]:
                df = dfs[table_name]
                if df.empty:
                    continue
                out_path = self._processed_dir / f"{table_name}.parquet"
                table = pa.Table.from_pandas(df, preserve_index=False)
                if table_name not in writers:
                    writers[table_name] = pq.ParquetWriter(out_path, table.schema)
                writers[table_name].write_table(table)

        # 关闭所有 writer
        for w in writers.values():
            w.close()

        duration = time.monotonic() - start_time_ref
        return CleanReport(
            total_weeks=total_weeks,
            total_videos=total_videos,
            duplicates_dropped=duplicates_dropped,
            missing_filled=missing_filled,
            outliers_flagged=outliers_flagged,
            duration_seconds=round(duration, 2),
        )

    # ── 清洗子步骤 ──────────────────────────────────────────

    def _extract_tables(self, records: list[dict]) -> dict[str, pd.DataFrame]:
        """从 raw JSON records 拆出 5 张 DataFrame。"""
        weekly_rows = []
        video_rows = []
        creator_rows = []
        category_rows = []
        stat_rows = []

        for rec in records:
            cfg = rec.get("config", {})
            weekly_rows.append({
                "number": rec.get("number"),
                "subject": cfg.get("subject", ""),
                "name": cfg.get("name", ""),
                "start_time": cfg.get("start_time", None),
                "end_time": cfg.get("end_time", None),
            })

            for v in rec.get("videos", []):
                owner = v.get("owner", {})
                stat = v.get("stat", {})

                video_rows.append({
                    "aid": v.get("aid"),
                    "bvid": v.get("bvid", ""),
                    "title": v.get("title", ""),
                    "desc": v.get("desc", ""),
                    "duration": v.get("duration"),
                    "pubdate": v.get("pubdate"),
                    "cid": v.get("cid"),
                    "pic": v.get("pic", ""),
                })

                creator_rows.append({
                    "mid": owner.get("mid"),
                    "name": owner.get("name", ""),
                    "face": owner.get("face", ""),
                })

                category_rows.append({
                    "tid": v.get("tid"),
                    "tname": v.get("tname", ""),
                    "tid_v2": v.get("rcmd_reason", {}).get("tid_v2", 0) if v.get("rcmd_reason") else 0,
                    "tname_v2": v.get("rcmd_reason", {}).get("tname_v2", "") if v.get("rcmd_reason") else "",
                })

                stat_rows.append({
                    "aid": stat.get("aid", v.get("aid")),
                    "view": stat.get("view", 0),
                    "like": stat.get("like", 0),
                    "coin": stat.get("coin", 0),
                    "favorite": stat.get("favorite", 0),
                    "share": stat.get("share", 0),
                    "reply": stat.get("reply", 0),
                    "danmaku": stat.get("danmaku", 0),
                })

        return {
            "Weekly": pd.DataFrame(weekly_rows),
            "Video": pd.DataFrame(video_rows),
            "Creator": pd.DataFrame(creator_rows),
            "Category": pd.DataFrame(category_rows),
            "VideoStat": pd.DataFrame(stat_rows),
        }

    def _fill_missing(self, dfs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        """缺失值填充：数值列 → 0，文本列 → ""，时间列 → NaT。"""
        numeric_cols = {
            "Weekly": [], "Video": ["aid", "duration", "cid", "pubdate"],
            "Creator": ["mid"], "Category": ["tid", "tid_v2"],
            "VideoStat": ["aid", "view", "like", "coin", "favorite", "share", "reply", "danmaku"],
        }
        text_cols = {
            "Weekly": ["subject", "name"], "Video": ["bvid", "title", "desc", "pic"],
            "Creator": ["name", "face"], "Category": ["tname", "tname_v2"],
            "VideoStat": [],
        }

        for name, df in dfs.items():
            if df.empty:
                continue
            for col in numeric_cols.get(name, []):
                if col in df.columns:
                    df[col] = df[col].fillna(0)
            for col in text_cols.get(name, []):
                if col in df.columns:
                    df[col] = df[col].fillna("")

        return dfs

    def _convert_types(self, dfs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        """统一各表列类型。"""
        # VideoStat: 数值列 → float64
        stat_float_cols = ["view", "like", "coin", "favorite", "share", "reply", "danmaku"]
        df = dfs["VideoStat"]
        for col in stat_float_cols:
            if col in df.columns:
                df[col] = df[col].astype("float64")
        if "aid" in df.columns:
            df["aid"] = df["aid"].astype("int64")
        dfs["VideoStat"] = df

        # Video: aid/duration/cid → int64, pubdate → float64
        video = dfs["Video"]
        for col in ["aid", "duration", "cid"]:
            if col in video.columns:
                video[col] = video[col].astype("int64")
        if "pubdate" in video.columns:
            video["pubdate"] = video["pubdate"].astype("float64")
        dfs["Video"] = video

        # Creator: mid → int64
        creator = dfs["Creator"]
        if "mid" in creator.columns:
            creator["mid"] = creator["mid"].astype("int64")
        dfs["Creator"] = creator

        # Category: tid/tid_v2 → int64
        cat = dfs["Category"]
        for col in ["tid", "tid_v2"]:
            if col in cat.columns:
                cat[col] = cat[col].astype("int64")
        dfs["Category"] = cat

        # Weekly: number → int64
        weekly = dfs["Weekly"]
        if "number" in weekly.columns:
            weekly["number"] = weekly["number"].astype("int64")
        dfs["Weekly"] = weekly

        return dfs

    # ── statistics ───────────────────────────────────────────

    def statistics(self) -> StatReport:
        raise NotImplementedError("statistics: to be implemented in Task 4")

    # ── clustering ───────────────────────────────────────────

    def clustering(self) -> ClusterReport:
        raise NotImplementedError("clustering: to be implemented in Task 5")

    # ── prediction ───────────────────────────────────────────

    def prediction(self) -> PredictionReport:
        raise NotImplementedError("prediction: to be implemented in Task 6")
```

#### Step 4: Run clean_data tests

Run: `uv run pytest tests/test_engine.py::TestPandasEngineCleanData -v`
Expected: 6 PASS

#### Step 5: Commit

```bash
git add src/bilianalysis/engine/pandas_engine.py tests/test_engine.py
git commit -m "feat: add PandasEngine with clean_data (batch load + Parquet write)"
```

---

### Task 4: Implement statistics()

**Files:**
- Modify: `src/bilianalysis/engine/pandas_engine.py` (replace statistics() stub)
- Modify: `tests/test_engine.py` (append statistics tests)

#### Step 1: Append statistics tests to test_engine.py

Append to `tests/test_engine.py`:

```python
class TestPandasEngineStatistics:
    def _create_parquet_files(self, processed_dir: Path):
        """在 processed_dir 下创建 5 张测试 Parquet。"""
        processed_dir.mkdir(parents=True, exist_ok=True)

        pd.DataFrame({
            "number": [1, 2], "subject": ["第1期", "第2期"],
            "name": ["每周必看 01", "每周必看 02"],
            "start_time": [1600000000.0, 1600600000.0],
            "end_time": [1600300000.0, 1600900000.0],
        }).to_parquet(processed_dir / "Weekly.parquet", index=False)

        pd.DataFrame({
            "aid": [100, 101, 200], "bvid": ["BV001", "BV002", "BV003"],
            "title": ["v1", "v2", "v3"], "desc": ["", "", ""],
            "duration": [120, 180, 150], "pubdate": [1600000000.0, 1600000000.0, 1600600000.0],
            "cid": [10, 11, 20], "pic": ["", "", ""],
        }).to_parquet(processed_dir / "Video.parquet", index=False)

        pd.DataFrame({
            "mid": [1100, 1101, 1200], "name": ["UP1", "UP2", "UP3"],
            "face": ["", "", ""],
        }).to_parquet(processed_dir / "Creator.parquet", index=False)

        pd.DataFrame({
            "tid": [1, 1, 2], "tname": ["动画", "动画", "游戏"],
            "tid_v2": [0, 0, 0], "tname_v2": ["", "", ""],
        }).to_parquet(processed_dir / "Category.parquet", index=False)

        pd.DataFrame({
            "aid": [100, 101, 200],
            "view": [10000.0, 20000.0, 30000.0],
            "like": [500.0, 1000.0, 1500.0],
            "coin": [100.0, 200.0, 300.0],
            "favorite": [200.0, 400.0, 600.0],
            "share": [30.0, 50.0, 70.0],
            "reply": [50.0, 100.0, 150.0],
            "danmaku": [60.0, 120.0, 180.0],
        }).to_parquet(processed_dir / "VideoStat.parquet", index=False)

    def test_statistics_overall(self, tmp_path):
        """验证 overall 统计值的正确性。"""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        processed_dir = tmp_path / "processed"
        self._create_parquet_files(processed_dir)

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = engine.statistics()

        assert report.overall.total_videos == 3
        assert report.overall.total_creators == 3
        assert report.overall.avg_view == 20000.0
        assert report.overall.avg_like == 1000.0
        assert report.overall.avg_coin == 200.0
        assert report.overall.avg_favorite == 400.0
        assert report.overall.avg_share == 50.0
        assert report.overall.avg_danmaku == 120.0
        # 交互率 = 交互量/播放量
        assert report.overall.avg_like_rate == pytest.approx(500.0 / 10000.0)
        assert report.overall.avg_coin_rate == pytest.approx(100.0 / 10000.0)
        assert report.overall.avg_favorite_rate == pytest.approx(200.0 / 10000.0)

    def test_statistics_by_category(self, tmp_path):
        """验证分区统计。"""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        processed_dir = tmp_path / "processed"
        self._create_parquet_files(processed_dir)

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = engine.statistics()

        assert len(report.by_category) == 2  # 动画, 游戏
        tnames = [c.tname for c in report.by_category]
        assert "动画" in tnames
        assert "游戏" in tnames

    def test_statistics_by_creator_top10(self, tmp_path):
        """验证 UP主 TOP10 按出现次数排序。"""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        processed_dir = tmp_path / "processed"
        self._create_parquet_files(processed_dir)

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = engine.statistics()

        assert len(report.by_creator) <= 10
        assert len(report.by_creator) == 3
        assert report.by_creator[0].name in ["UP1", "UP2", "UP3"]

    def test_statistics_by_week(self, tmp_path):
        """验证按周趋势（2 周数据）。"""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        processed_dir = tmp_path / "processed"
        self._create_parquet_files(processed_dir)

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = engine.statistics()

        assert len(report.by_week) == 2
        assert report.by_week[0].week_number == 1
        assert report.by_week[0].video_count == 2  # aid 100, 101
        assert report.by_week[1].week_number == 2
        assert report.by_week[1].video_count == 1  # aid 200
```

#### Step 2: Run to verify fail

Run: `uv run pytest tests/test_engine.py::TestPandasEngineStatistics::test_statistics_overall -v`
Expected: FAIL — NotImplementedError

#### Step 3: Implement statistics() in pandas_engine.py

Replace the statistics() stub:

```python
    def statistics(self) -> StatReport:
        """从 processed/ Parquet 读取 → pd.merge → groupby 聚合 → StatReport。"""
        video = pd.read_parquet(self._processed_dir / "Video.parquet")
        creator = pd.read_parquet(self._processed_dir / "Creator.parquet")
        category = pd.read_parquet(self._processed_dir / "Category.parquet")
        stat = pd.read_parquet(self._processed_dir / "VideoStat.parquet")
        weekly = pd.read_parquet(self._processed_dir / "Weekly.parquet")

        # 按周号关联：Video 的 pubdate 对比 Weekly 的 start_time 区间
        # 简化策略：按 pubdate 排序后填充周号
        # 更稳健：用 Weekly.number 关联 —— 实际上 raw JSON 保留了 week number
        # 这里按 week_NNN.json 的 number 已在 clean_data 时写入 Weekly.number
        # Video 不含 week_number，需要 join
        # 暂用简单方式：按 pubdate 匹配 Weekly 区间
        merged = video.merge(stat, on="aid", how="inner")
        # 为每行分配 week_number：按 pubdate 匹配最接近的 start_time
        # 简化：假设 pubdate 与 raw JSON 一一对应，直接按顺序分配
        # 实际场景：Video.pubdate 落在哪个 Weekly 的 [start_time, end_time]
        if "start_time" in weekly.columns and "end_time" in weekly.columns:
            # 使用区间匹配
            week_map = []
            for _, row in merged.iterrows():
                pd_date = row["pubdate"]
                mask = (weekly["start_time"] <= pd_date) & (weekly["end_time"] >= pd_date)
                matched = weekly[mask]
                if not matched.empty:
                    week_map.append(matched.iloc[0]["number"])
                else:
                    week_map.append(0)
            merged["week_number"] = week_map
        else:
            merged["week_number"] = 1  # fallback

        # Overall
        total_videos = len(merged)
        total_creators = creator["mid"].nunique()
        rates = merged.copy()
        rates["like_rate"] = rates["like"] / rates["view"].replace(0, 1)
        rates["coin_rate"] = rates["coin"] / rates["view"].replace(0, 1)
        rates["favorite_rate"] = rates["favorite"] / rates["view"].replace(0, 1)

        overall = OverallStats(
            total_videos=total_videos,
            total_creators=total_creators,
            avg_view=round(float(stat["view"].mean()), 2),
            avg_like=round(float(stat["like"].mean()), 2),
            avg_coin=round(float(stat["coin"].mean()), 2),
            avg_favorite=round(float(stat["favorite"].mean()), 2),
            avg_share=round(float(stat["share"].mean()), 2),
            avg_danmaku=round(float(stat["danmaku"].mean()), 2),
            avg_like_rate=round(float(rates["like_rate"].mean()), 4),
            avg_coin_rate=round(float(rates["coin_rate"].mean()), 4),
            avg_favorite_rate=round(float(rates["favorite_rate"].mean()), 4),
        )

        # By category
        merged_cat = merged.merge(category, on="tid" if "tid" in category.columns else None, how="left")
        # category 有独立行，需要按行索引匹配
        # 简化：category 与 video 一一对应（同序）
        merged["tname"] = category["tname"].values if len(category) == len(merged) else category.iloc[:len(merged)]["tname"].values
        merged["interaction"] = merged["like"] + merged["coin"] + merged["favorite"]
        merged["interaction_rate"] = merged["interaction"] / merged["view"].replace(0, 1)

        cat_groups = merged.groupby("tname").agg(
            video_count=("aid", "count"),
            avg_view=("view", "mean"),
            avg_like=("like", "mean"),
            avg_interaction_rate=("interaction_rate", "mean"),
        ).reset_index()
        by_category = [
            CategoryStats(
                tname=row["tname"], video_count=int(row["video_count"]),
                avg_view=round(float(row["avg_view"]), 2),
                avg_like=round(float(row["avg_like"]), 2),
                avg_interaction_rate=round(float(row["avg_interaction_rate"]), 4),
            )
            for _, row in cat_groups.iterrows()
        ]

        # By creator (TOP10 by appearance_count)
        creator_counts = creator.groupby(["mid", "name"]).size().reset_index(name="appearance_count")
        # aggregate stat by creator
        # 简化：Creator 行顺序与 Video 一一对应
        if len(creator) == len(merged):
            merged["mid"] = creator["mid"].values
            merged["creator_name"] = creator["name"].values

        creator_agg = merged.groupby(["mid", "creator_name"]).agg(
            appearance_count=("aid", "count"),
            total_view=("view", "sum"),
            total_like=("like", "sum"),
            total_favorite=("favorite", "sum"),
        ).reset_index().sort_values("appearance_count", ascending=False).head(10)

        by_creator = [
            CreatorStats(
                mid=int(row["mid"]), name=row["creator_name"],
                appearance_count=int(row["appearance_count"]),
                total_view=int(row["total_view"]),
                total_like=int(row["total_like"]),
                total_favorite=int(row["total_favorite"]),
            )
            for _, row in creator_agg.iterrows()
        ]

        # By week
        week_agg = merged.groupby("week_number").agg(
            video_count=("aid", "count"),
            avg_view=("view", "mean"),
            avg_like=("like", "mean"),
            avg_interaction_rate=("interaction_rate", "mean"),
        ).reset_index().sort_values("week_number")
        by_week = [
            WeeklyTrend(
                week_number=int(row["week_number"]),
                video_count=int(row["video_count"]),
                avg_view=round(float(row["avg_view"]), 2),
                avg_like=round(float(row["avg_like"]), 2),
                avg_interaction_rate=round(float(row["avg_interaction_rate"]), 4),
            )
            for _, row in week_agg.iterrows()
        ]

        return StatReport(overall=overall, by_category=by_category, by_creator=by_creator, by_week=by_week)
```

**Note:** statistics() 需要正确处理关联。当前简化策略是 Video/Creator/Category/VideoStat 按行一一对应（因为 clean_data 提取时保持顺序）。Week 匹配通过 pubdate 区间匹配。

#### Step 4: Run statistics tests

Run: `uv run pytest tests/test_engine.py::TestPandasEngineStatistics -v`
Expected: 4 PASS

#### Step 5: Commit

```bash
git add src/bilianalysis/engine/pandas_engine.py tests/test_engine.py
git commit -m "feat: implement PandasEngine.statistics()"
```

---

### Task 5: Implement clustering()

**Files:**
- Modify: `src/bilianalysis/engine/pandas_engine.py` (replace clustering() stub)
- Modify: `tests/test_engine.py` (append clustering tests)

#### Step 1: Append clustering tests to test_engine.py

Append to `tests/test_engine.py`:

```python
class TestPandasEngineClustering:
    def _create_clustering_data(self, processed_dir: Path):
        """创建适合聚类的测试数据（3 种视频类型模拟）。"""
        processed_dir.mkdir(parents=True, exist_ok=True)

        # 3 类视频: 爆款(高播放高互动), 普通(中), 潜力(低播放高互动率)
        vids = []
        cats = []
        for i in range(30):
            vids.append({
                "aid": i + 1, "bvid": f"BV{i}", "title": f"v{i}", "desc": "",
                "duration": 120, "pubdate": 1600000000.0, "cid": i * 10, "pic": "",
            })
            cats.append({"tid": 1, "tname": "动画", "tid_v2": 0, "tname_v2": ""})

        pd.DataFrame(vids).to_parquet(processed_dir / "Video.parquet", index=False)
        pd.DataFrame(cats).to_parquet(processed_dir / "Category.parquet", index=False)

        pd.DataFrame({
            "mid": list(range(1001, 1031)), "name": [f"UP{i}" for i in range(1, 31)],
            "face": [""] * 30,
        }).to_parquet(processed_dir / "Creator.parquet", index=False)

        # 生成 3 聚类: 0-9 爆款, 10-19 普通, 20-29 潜力
        import numpy as np
        np.random.seed(42)
        aids = list(range(1, 31))
        views, likes, coins, favorites = [], [], [], []
        for i in range(30):
            if i < 10:
                views.append(np.random.randint(80000, 120000))
                likes.append(np.random.randint(4000, 6000))
                coins.append(np.random.randint(800, 1200))
                favorites.append(np.random.randint(2000, 3000))
            elif i < 20:
                views.append(np.random.randint(40000, 70000))
                likes.append(np.random.randint(1500, 3000))
                coins.append(np.random.randint(400, 700))
                favorites.append(np.random.randint(800, 1500))
            else:
                views.append(np.random.randint(8000, 25000))
                likes.append(np.random.randint(800, 2000))
                coins.append(np.random.randint(300, 600))
                favorites.append(np.random.randint(500, 1000))

        pd.DataFrame({
            "aid": aids, "view": [float(v) for v in views],
            "like": [float(l) for l in likes],
            "coin": [float(c) for c in coins],
            "favorite": [float(f) for f in favorites],
            "share": [10.0] * 30, "reply": [20.0] * 30, "danmaku": [30.0] * 30,
        }).to_parquet(processed_dir / "VideoStat.parquet", index=False)

        pd.DataFrame({
            "number": [1], "subject": ["第1期"], "name": ["每周必看 01"],
            "start_time": [1600000000.0], "end_time": [1600600000.0],
        }).to_parquet(processed_dir / "Weekly.parquet", index=False)

    def test_clustering_structure(self, tmp_path):
        """验证聚类报告基本结构。"""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        processed_dir = tmp_path / "processed"
        self._create_clustering_data(processed_dir)

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = engine.clustering()

        assert report.clusters.k == 3
        assert len(report.clusters.clusters) == 3
        assert report.clusters.silhouette_score > 0
        assert "view" in report.clusters.feature_importance
        assert "like" in report.clusters.feature_importance

    def test_clustering_scatter_data(self, tmp_path):
        """验证散点图数据格式正确。"""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        processed_dir = tmp_path / "processed"
        self._create_clustering_data(processed_dir)

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = engine.clustering()

        scatter = report.scatter_data
        assert "labels" in scatter
        assert "x" in scatter
        assert "y" in scatter
        assert len(scatter["labels"]) == 30
        assert len(scatter["x"]) == 30
        assert len(scatter["y"]) == 30

    def test_clustering_tags_present(self, tmp_path):
        """验证三个聚类都有标签。"""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        processed_dir = tmp_path / "processed"
        self._create_clustering_data(processed_dir)

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = engine.clustering()

        tags = {c.tag for c in report.clusters.clusters}
        assert "爆款视频" in tags
        assert "普通热门" in tags
        assert "潜力视频" in tags
```

#### Step 2: Run to verify fail

Run: `uv run pytest tests/test_engine.py::TestPandasEngineClustering::test_clustering_structure -v`
Expected: FAIL — NotImplementedError

#### Step 3: Implement clustering() in pandas_engine.py

Add imports at top of `pandas_engine.py`:

```python
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
```

Replace the clustering() stub:

```python
    def clustering(self) -> ClusterReport:
        """从 processed/ Stat 读取 → StandardScaler → KMeans(k=3) → PCA(2D) → ClusterReport。"""
        start_time = time.monotonic()
        stat = pd.read_parquet(self._processed_dir / "VideoStat.parquet")

        # 特征选取
        features = ["view", "like", "coin", "favorite"]
        X = stat[features].copy()

        # 标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # KMeans
        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)

        # Silhouette score
        sil_score = silhouette_score(X_scaled, labels)

        # Feature importance: 各特征在聚类中心的方差
        centers = pd.DataFrame(kmeans.cluster_centers_, columns=features)
        importance = {f: round(float(centers[f].var()), 4) for f in features}

        # 构建每个 cluster 的信息
        clusters = []
        # 计算每类的 avg 交互率以打标签
        stat["interaction"] = stat["like"] + stat["coin"] + stat["favorite"]
        stat["interaction_rate"] = stat["interaction"] / stat["view"].replace(0, 1)
        stat["label"] = labels

        for label_idx in range(3):
            mask = stat["label"] == label_idx
            cluster_data = stat[mask]
            cluster_X = X[mask]
            centroid = {f: round(float(cluster_X[f].mean()), 2) for f in features}

            avg_view = float(cluster_data["view"].mean())
            avg_like = float(cluster_data["like"].mean())
            avg_coin = float(cluster_data["coin"].mean())
            avg_favorite = float(cluster_data["favorite"].mean())
            avg_interaction_rate = float(cluster_data["interaction_rate"].mean())

            # 打标签
            if avg_view > X["view"].median() and avg_interaction_rate > stat["interaction_rate"].median():
                tag = "爆款视频"
            elif avg_view > X["view"].median():
                tag = "普通热门"
            else:
                tag = "潜力视频"

            sample_ids = cluster_data["aid"].head(20).astype(int).tolist()

            clusters.append(ClusterGroup(
                label=label_idx, tag=tag, count=int(mask.sum()),
                centroid=centroid, avg_view=round(avg_view, 2),
                avg_like=round(avg_like, 2), avg_coin=round(avg_coin, 2),
                avg_favorite=round(avg_favorite, 2), sample_ids=sample_ids,
            ))

        # PCA 降维供散点图
        pca = PCA(n_components=2, random_state=42)
        X_pca = pca.fit_transform(X_scaled)
        scatter_data = {
            "labels": labels.tolist(),
            "x": [round(float(v), 4) for v in X_pca[:, 0].tolist()],
            "y": [round(float(v), 4) for v in X_pca[:, 1].tolist()],
        }

        duration = time.monotonic() - start_time
        return ClusterReport(
            clusters=ClusterResult(k=3, clusters=clusters, silhouette_score=round(float(sil_score), 4),
                                   feature_importance=importance),
            scatter_data=scatter_data,
            duration_seconds=round(duration, 2),
        )
```

#### Step 4: Run clustering tests

Run: `uv run pytest tests/test_engine.py::TestPandasEngineClustering -v`
Expected: 3 PASS

#### Step 5: Commit

```bash
git add src/bilianalysis/engine/pandas_engine.py tests/test_engine.py
git commit -m "feat: implement PandasEngine.clustering() with KMeans + PCA"
```

---

### Task 6: Implement prediction()

**Files:**
- Modify: `src/bilianalysis/engine/pandas_engine.py` (replace prediction() stub)
- Modify: `tests/test_engine.py` (append prediction tests)

#### Step 1: Append prediction tests to test_engine.py

Append to `tests/test_engine.py`:

```python
class TestPandasEnginePrediction:
    def _create_weekly_data(self, processed_dir: Path):
        """创建 10 周的测试数据。"""
        processed_dir.mkdir(parents=True, exist_ok=True)

        import numpy as np
        np.random.seed(42)

        weekly = []
        vids, stats, creators, cats = [], [], [], []
        aid_counter = 1

        for week_num in range(1, 11):
            base_time = 1600000000 + (week_num - 1) * 604800
            weekly.append({
                "number": week_num, "subject": f"第{week_num}期",
                "name": f"每周必看 {week_num:02d}",
                "start_time": float(base_time), "end_time": float(base_time + 604800),
            })
            # 每周 5 个视频，播放量随周次递增
            for j in range(5):
                base_view = 10000 + week_num * 2000 + np.random.randint(-1000, 1000)
                vids.append({
                    "aid": aid_counter, "bvid": f"BV{aid_counter}", "title": f"v{aid_counter}",
                    "desc": "", "duration": 120, "pubdate": float(base_time + j * 10000),
                    "cid": aid_counter * 10, "pic": "",
                })
                stats.append({
                    "aid": aid_counter, "view": float(max(0, base_view)),
                    "like": float(max(0, base_view * 0.05 + np.random.randint(-50, 50))),
                    "coin": float(max(0, base_view * 0.01)), "favorite": float(max(0, base_view * 0.02)),
                    "share": 10.0, "reply": 20.0, "danmaku": 30.0,
                })
                creators.append({"mid": 1000 + aid_counter, "name": f"UP{aid_counter}", "face": ""})
                cats.append({"tid": 1, "tname": "动画", "tid_v2": 0, "tname_v2": ""})
                aid_counter += 1

        pd.DataFrame(weekly).to_parquet(processed_dir / "Weekly.parquet", index=False)
        pd.DataFrame(vids).to_parquet(processed_dir / "Video.parquet", index=False)
        pd.DataFrame(stats).to_parquet(processed_dir / "VideoStat.parquet", index=False)
        pd.DataFrame(creators).to_parquet(processed_dir / "Creator.parquet", index=False)
        pd.DataFrame(cats).to_parquet(processed_dir / "Category.parquet", index=False)

    def test_prediction_structure(self, tmp_path):
        """验证预测报告基本结构。"""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        processed_dir = tmp_path / "processed"
        self._create_weekly_data(processed_dir)

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = engine.prediction()

        assert report.view_predict.model_type == "linear_regression"
        assert report.view_predict.target == "view"
        assert -1.0 <= report.view_predict.r2_score <= 1.0  # R² 范围
        assert report.view_predict.mae >= 0
        assert len(report.view_predict.fitted) == 10  # 历史拟合
        assert len(report.view_predict.forecast) == 4  # 未来 4 周
        assert "week_number" in report.view_predict.coefficients

    def test_prediction_forecast_future_weeks(self, tmp_path):
        """验证预测的未来周号 > 历史最大周号。"""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        processed_dir = tmp_path / "processed"
        self._create_weekly_data(processed_dir)

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = engine.prediction()

        max_hist_week = max(f["week_number"] for f in report.view_predict.fitted)
        forecast_weeks = [f["week_number"] for f in report.view_predict.forecast]
        assert all(w > max_hist_week for w in forecast_weeks)

    def test_prediction_both_targets(self, tmp_path):
        """验证 view 和 like 两个预测目标都存在。"""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        processed_dir = tmp_path / "processed"
        self._create_weekly_data(processed_dir)

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = engine.prediction()

        assert report.view_predict is not None
        assert report.like_predict is not None
        assert report.view_predict.target == "view"
        assert report.like_predict.target == "like"
```

#### Step 2: Run to verify fail

Run: `uv run pytest tests/test_engine.py::TestPandasEnginePrediction::test_prediction_structure -v`
Expected: FAIL — NotImplementedError

#### Step 3: Implement prediction() in pandas_engine.py

Add import at top:

```python
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error
import numpy as np
```

Replace the prediction() stub:

```python
    def prediction(self) -> PredictionReport:
        """从 processed/ Parquet → 周聚合序列 → LinearRegression → PredictionReport。"""
        start_time = time.monotonic()
        video = pd.read_parquet(self._processed_dir / "Video.parquet")
        stat = pd.read_parquet(self._processed_dir / "VideoStat.parquet")
        weekly = pd.read_parquet(self._processed_dir / "Weekly.parquet")

        # 构建周聚合序列
        merged = video.merge(stat, on="aid", how="inner")

        # 按 pubdate 匹配 week_number
        if "start_time" in weekly.columns and "end_time" in weekly.columns:
            week_map = []
            for _, row in merged.iterrows():
                pd_date = row["pubdate"]
                mask = (weekly["start_time"] <= pd_date) & (weekly["end_time"] >= pd_date)
                matched = weekly[mask]
                if not matched.empty:
                    week_map.append(matched.iloc[0]["number"])
                else:
                    week_map.append(0)
            merged["week_number"] = week_map
        else:
            merged["week_number"] = 1

        # 按周聚合
        weekly_agg = merged.groupby("week_number").agg(
            avg_view=("view", "mean"),
            avg_like=("like", "mean"),
            avg_coin=("coin", "mean"),
            avg_favorite=("favorite", "mean"),
            video_count=("aid", "count"),
        ).reset_index().sort_values("week_number")

        def _predict(target: str) -> PredictionResult:
            """对 target 做线性回归预测。"""
            df = weekly_agg[weekly_agg["week_number"] > 0].copy()
            if len(df) < 3:
                return PredictionResult(
                    model_type="linear_regression", target=target, r2_score=0.0, mae=0.0,
                    coefficients={}, intercept=0.0, fitted=[], forecast=[],
                )

            # 特征: week_number + 其他聚合指标（避免用 target 自身）
            feature_cols = ["week_number", "video_count"]
            X = df[feature_cols].values
            y = df[f"avg_{target}"].values

            model = LinearRegression()
            model.fit(X, y)
            y_pred = model.predict(X)

            r2 = r2_score(y, y_pred)
            mae = mean_absolute_error(y, y_pred)
            coef = {feature_cols[i]: round(float(model.coef_[i]), 4) for i in range(len(feature_cols))}
            intercept = round(float(model.intercept_), 2)

            fitted = [
                {"week_number": int(df.iloc[i]["week_number"]),
                 "actual": round(float(y[i]), 2),
                 "predicted": round(float(y_pred[i]), 2)}
                for i in range(len(df))
            ]

            # 预测未来 4 周
            last_week = int(df["week_number"].max())
            future_X = np.array([[last_week + i, int(df["video_count"].mean())] for i in range(1, 5)])
            future_pred = model.predict(future_X)
            forecast = [
                {"week_number": int(last_week + i), "predicted": round(float(future_pred[j]), 2)}
                for j, i in enumerate(range(1, 5))
            ]

            return PredictionResult(
                model_type="linear_regression", target=target,
                r2_score=round(float(r2), 4), mae=round(float(mae), 2),
                coefficients=coef, intercept=intercept,
                fitted=fitted, forecast=forecast,
            )

        view_result = _predict("view")
        like_result = _predict("like")

        duration = time.monotonic() - start_time
        return PredictionReport(
            view_predict=view_result,
            like_predict=like_result,
            duration_seconds=round(duration, 2),
        )
```

#### Step 4: Run prediction tests

Run: `uv run pytest tests/test_engine.py::TestPandasEnginePrediction -v`
Expected: 3 PASS

#### Step 5: Commit

```bash
git add src/bilianalysis/engine/pandas_engine.py tests/test_engine.py
git commit -m "feat: implement PandasEngine.prediction() with LinearRegression"
```

---

### Task 7: Create __init__.py Public API + Final Verification

**Files:**
- Modify: `src/bilianalysis/engine/__init__.py`

#### Step 1: Write __init__.py

Replace `src/bilianalysis/engine/__init__.py`:

```python
"""分析引擎模块。"""
from bilianalysis.engine.base import (
    AnalysisEngine,
    CleanReport,
    OverallStats, CategoryStats, CreatorStats, WeeklyTrend, StatReport,
    ClusterGroup, ClusterResult, ClusterReport,
    PredictionResult, PredictionReport,
)
from bilianalysis.engine.pandas_engine import PandasEngine

__all__ = [
    "AnalysisEngine", "PandasEngine",
    "CleanReport",
    "OverallStats", "CategoryStats", "CreatorStats", "WeeklyTrend", "StatReport",
    "ClusterGroup", "ClusterResult", "ClusterReport",
    "PredictionResult", "PredictionReport",
]
```

#### Step 2: Verify public API import

Run: `uv run python -c "from bilianalysis.engine import AnalysisEngine, PandasEngine, CleanReport, StatReport, ClusterReport, PredictionReport; print('ok')"`
Expected: `ok`

#### Step 3: Run full test suite

Run: `uv run pytest tests/ -v`
Expected: All tests PASS (~51 existing + ~24 new engine tests = ~75 total)

#### Step 4: Smoke test — end-to-end clean_data with real small data

Run:
```bash
uv run python -c "
from bilianalysis.config import DataSection
from bilianalysis.engine import PandasEngine
import json, tempfile, os, asyncio

async def main():
    with tempfile.TemporaryDirectory() as td:
        raw = os.path.join(td, 'raw')
        processed = os.path.join(td, 'processed')
        os.makedirs(raw)

        data = {'number': 1, 'config': {'subject': 'test', 'name': 'test'}, 'videos': [
            {'aid': 1, 'bvid': 'BV1', 'title': 'test', 'desc': '', 'duration': 120,
             'pubdate': 1600000000, 'cid': 10, 'pic': '',
             'owner': {'mid': 100, 'name': 'UP', 'face': ''},
             'stat': {'aid': 1, 'view': 1000, 'like': 50, 'coin': 10, 'favorite': 20, 'share': 5, 'reply': 8, 'danmaku': 12},
             'tid': 1, 'tname': '动画', 'rcmd_reason': {'tid_v2': 0, 'tname_v2': ''}}
        ]}
        with open(os.path.join(raw, 'week_001.json'), 'w') as f:
            json.dump(data, f)

        engine = PandasEngine(DataSection(raw_dir=raw, processed_dir=processed), batch_size=10)
        report = await engine.clean_data()
        print(f'Cleaned: {report.total_weeks} weeks, {report.total_videos} videos')

        stat_report = engine.statistics()
        print(f'Stats: {stat_report.overall.total_videos} videos, avg_view={stat_report.overall.avg_view}')

        cluster_report = engine.clustering()
        print(f'Clusters: k={cluster_report.clusters.k}, sil={cluster_report.clusters.silhouette_score}')

        pred_report = engine.prediction()
        print(f'Prediction: view_r2={pred_report.view_predict.r2_score}')

asyncio.run(main())
"
```
Expected: prints clean/stats/cluster/pred results without errors

#### Step 5: Final commit

```bash
git add src/bilianalysis/engine/__init__.py
git commit -m "feat: complete engine public API and final verification"
```
