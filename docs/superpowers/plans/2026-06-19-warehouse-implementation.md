# Warehouse Layered Design Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full DWD/DWS/ADS data warehouse pipeline — pure Python functions in `src/bilianalysis/warehouse/` that consume `etl/transform.py` output and produce 8 Parquet tables.

**Architecture:** Three-layer Kimball-style pipeline: `transform_week()` records → `build_dwd()` merges into one wide fact table → `build_dws()` aggregates by creator/category/week → `build_ads()` projects and sorts for frontend pages. All functions are pure, no database access. Each layer reads only the previous layer's output. Full rebuild on every run.

**Tech Stack:** Python 3.13, pandas 3.0, pyarrow 24.0, pydantic 2.13, pytest

**Note:** The design spec references `pl.DataFrame` (Polars), but the project uses pandas (already a dependency). All DataFrames use `pd.DataFrame`.

---

### Task 1: WarehouseReport model and package init

**Files:**
- Create: `src/bilianalysis/warehouse/__init__.py`
- Create: `src/bilianalysis/warehouse/report.py`
- Create: `tests/test_warehouse.py`

- [ ] **Step 1: Write WarehouseReport model and init**

```python
# src/bilianalysis/warehouse/__init__.py
"""Data warehouse layered builder — DWD / DWS / ADS.

Pure computation. No database access.
"""
from .builder import build_warehouse
from .report import WarehouseReport

__all__ = ["build_warehouse", "WarehouseReport"]
```

```python
# src/bilianalysis/warehouse/report.py
"""WarehouseReport model for build_warehouse() output."""
from pydantic import BaseModel


class SkippedWeek(BaseModel):
    week_number: int
    error: str


class WarehouseReport(BaseModel):
    weeks_processed: int = 0
    weeks_skipped: int = 0
    skipped_details: list[SkippedWeek] = []
    tables_written: list[str] = []
    duration_seconds: float = 0.0
```

- [ ] **Step 2: Write tests for WarehouseReport**

```python
# tests/test_warehouse.py
"""Tests for data warehouse layered builder."""
from bilianalysis.warehouse import WarehouseReport
from bilianalysis.warehouse.report import SkippedWeek


def test_warehouse_report_empty():
    report = WarehouseReport()
    assert report.weeks_processed == 0
    assert report.weeks_skipped == 0
    assert report.skipped_details == []
    assert report.tables_written == []
    assert report.duration_seconds == 0.0


def test_warehouse_report_with_data():
    report = WarehouseReport(
        weeks_processed=4,
        weeks_skipped=1,
        skipped_details=[SkippedWeek(week_number=3, error="JSON decode error")],
        tables_written=["dwd_fact_video.parquet"],
        duration_seconds=1.5,
    )
    assert report.weeks_processed == 4
    assert len(report.skipped_details) == 1
    assert report.skipped_details[0].week_number == 3
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_warehouse.py -v`
Expected: 2 PASS

- [ ] **Step 4: Commit**

```bash
git add src/bilianalysis/warehouse/ tests/test_warehouse.py
git commit -m "feat: add WarehouseReport model and warehouse package init

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: DWD layer — build_dwd()

**Files:**
- Create: `src/bilianalysis/warehouse/dwd.py`
- Modify: `tests/test_warehouse.py` (append tests)

- [ ] **Step 1: Write failing tests for build_dwd**

Append to `tests/test_warehouse.py`:

```python
import json
from pathlib import Path

import pandas as pd
from bilianalysis.etl.transform import transform_week
from bilianalysis.warehouse.dwd import build_dwd

RAW_DIR = Path("data/raw")


def _load_records(week_number: int) -> dict:
    raw = json.loads((RAW_DIR / f"week_{week_number:03d}.json").read_text(encoding="utf-8"))
    return transform_week(raw)


def test_build_dwd_expected_columns():
    """DWD table has all 20 expected columns."""
    records_list = [_load_records(1)]
    dwd = build_dwd(records_list)

    expected = {
        "weekly_number", "aid", "bvid", "title", "duration", "pubdate",
        "up_mid", "up_name",
        "category_tid", "category_name",
        "view", "like_cnt", "coin", "favorite", "share", "reply", "danmaku",
        "like_rate", "coin_rate", "favorite_rate",
    }
    assert set(dwd.columns) == expected
    assert len(dwd) > 0


def test_build_dwd_grain_unique():
    """Each row is uniquely identified by (weekly_number, aid)."""
    records_list = [_load_records(1)]
    dwd = build_dwd(records_list)

    dupes = dwd.duplicated(subset=["weekly_number", "aid"]).sum()
    assert dupes == 0


def test_build_dwd_derive_rates():
    """Derived rates = metric / view, zero-safe. All between 0 and 1."""
    records_list = [_load_records(1)]
    dwd = build_dwd(records_list)

    assert dwd["like_rate"].notna().all()
    assert dwd["coin_rate"].notna().all()
    assert dwd["favorite_rate"].notna().all()
    assert (dwd["like_rate"] <= 1.0).all()
    assert (dwd["coin_rate"] <= 1.0).all()


def test_build_dwd_view_zero_is_safe():
    """Rows with view=0 produce rate=0.0, not NaN or exception."""
    records = {
        "weekly": [{"number": 999, "subject": "", "name": ""}],
        "creators": [{"mid": 1, "name": "Test", "face": ""}],
        "categories": [{"tid": 1, "tname": "Test", "tid_v2": None, "tname_v2": None}],
        "videos": [{"aid": 1, "bvid": "BV0000", "title": "Test", "description": "",
                     "duration": 0, "pubdate": None, "cid": None, "video_url": None,
                     "cover_url": None, "creator_mid": 1, "category_tid": 1}],
        "video_stats": [{"aid": 1, "view": 0, "like_cnt": 0, "coin": 0, "favorite": 0,
                          "share": 0, "reply": 0, "danmaku": 0}],
        "weekly_videos": [{"weekly_number": 999, "aid": 1}],
    }
    dwd = build_dwd([records])

    assert dwd.loc[0, "like_rate"] == 0.0
    assert dwd.loc[0, "coin_rate"] == 0.0
    assert dwd.loc[0, "favorite_rate"] == 0.0


def test_build_dwd_multi_week_merge():
    """Multiple weeks merge into a single DWD table."""
    records_list = [_load_records(1), _load_records(2)]
    dwd = build_dwd(records_list)

    weeks = dwd["weekly_number"].unique()
    assert 1 in weeks
    assert 2 in weeks


def test_build_dwd_type1_creator_name():
    """Creator name is taken from the last occurrence (Type 1)."""
    week1 = {
        "weekly": [{"number": 998, "subject": "", "name": ""}],
        "creators": [{"mid": 1, "name": "OldName", "face": ""}],
        "categories": [{"tid": 1, "tname": "Test", "tid_v2": None, "tname_v2": None}],
        "videos": [{"aid": 1, "bvid": "BV0000", "title": "Test", "description": "",
                     "duration": 0, "pubdate": None, "cid": None, "video_url": None,
                     "cover_url": None, "creator_mid": 1, "category_tid": 1}],
        "video_stats": [{"aid": 1, "view": 100, "like_cnt": 10, "coin": 2, "favorite": 5,
                          "share": 0, "reply": 0, "danmaku": 0}],
        "weekly_videos": [{"weekly_number": 998, "aid": 1}],
    }
    week2 = {
        "weekly": [{"number": 999, "subject": "", "name": ""}],
        "creators": [{"mid": 1, "name": "NewName", "face": ""}],
        "categories": [{"tid": 1, "tname": "Test", "tid_v2": None, "tname_v2": None}],
        "videos": [{"aid": 2, "bvid": "BV0001", "title": "Test2", "description": "",
                     "duration": 0, "pubdate": None, "cid": None, "video_url": None,
                     "cover_url": None, "creator_mid": 1, "category_tid": 1}],
        "video_stats": [{"aid": 2, "view": 200, "like_cnt": 20, "coin": 4, "favorite": 10,
                          "share": 0, "reply": 0, "danmaku": 0}],
        "weekly_videos": [{"weekly_number": 999, "aid": 2}],
    }
    dwd = build_dwd([week1, week2])

    names = dwd["up_name"].unique()
    assert len(names) == 1
    assert names[0] == "NewName"
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `uv run pytest tests/test_warehouse.py -v -k "dwd"`
Expected: FAIL — ImportError: cannot import build_dwd

- [ ] **Step 3: Implement build_dwd**

```python
# src/bilianalysis/warehouse/dwd.py
"""DWD layer: build dwd_fact_video wide table from transform records."""
import pandas as pd


def build_dwd(records_list: list[dict]) -> pd.DataFrame:
    """Merge multiple weeks of transform_week() records into a single DWD wide table.

    Grain: (weekly_number, aid) — one row per video per week.

    Args:
        records_list: List of dicts returned by transform_week(), one per week.

    Returns:
        DataFrame with 20 columns. Sorted by (weekly_number, aid).
    """
    all_videos = []
    all_stats = []
    all_weekly_videos = []
    all_creators = {}    # mid → most recent name (Type 1)
    all_categories = {}  # tid → most recent name

    for records in records_list:
        for c in records.get("creators", []):
            all_creators[c["mid"]] = c["name"]
        for cat in records.get("categories", []):
            all_categories[cat["tid"]] = cat["tname"]

        all_videos.extend(records.get("videos", []))
        all_stats.extend(records.get("video_stats", []))
        all_weekly_videos.extend(records.get("weekly_videos", []))

    videos_df = pd.DataFrame(all_videos)
    stats_df = pd.DataFrame(all_stats)
    wv_df = pd.DataFrame(all_weekly_videos)

    if videos_df.empty:
        return pd.DataFrame(columns=[
            "weekly_number", "aid", "bvid", "title", "duration", "pubdate",
            "up_mid", "up_name", "category_tid", "category_name",
            "view", "like_cnt", "coin", "favorite", "share", "reply", "danmaku",
            "like_rate", "coin_rate", "favorite_rate",
        ])

    # Merge: videos ← weekly_videos ← video_stats
    dwd = videos_df.merge(wv_df, on="aid", how="left")
    dwd = dwd.merge(stats_df, on="aid", how="left")

    # Type 1 dimension lookups
    dwd["up_name"] = dwd["creator_mid"].map(all_creators)
    dwd["category_name"] = dwd["category_tid"].map(all_categories)

    # Derive rates (zero-safe: view=0 → rate=0.0)
    view = dwd["view"].fillna(0).astype("int64")
    dwd["like_rate"] = (dwd["like_cnt"] / view).where(view > 0, 0.0).astype("float64")
    dwd["coin_rate"] = (dwd["coin"] / view).where(view > 0, 0.0).astype("float64")
    dwd["favorite_rate"] = (dwd["favorite"] / view).where(view > 0, 0.0).astype("float64")

    # Select columns and rename
    result = dwd[[
        "weekly_number", "aid", "bvid", "title", "duration", "pubdate",
        "creator_mid", "up_name", "category_tid", "category_name",
        "view", "like_cnt", "coin", "favorite", "share", "reply", "danmaku",
        "like_rate", "coin_rate", "favorite_rate",
    ]].rename(columns={"creator_mid": "up_mid"})

    # Fill missing numerics
    int_cols = ["view", "like_cnt", "coin", "favorite", "share", "reply", "danmaku"]
    for col in int_cols:
        result[col] = result[col].fillna(0).astype("int64")

    result["weekly_number"] = result["weekly_number"].astype("int32")
    result["aid"] = result["aid"].astype("int64")
    result["up_mid"] = result["up_mid"].fillna(0).astype("int64")
    result["category_tid"] = result["category_tid"].fillna(0).astype("int32")
    result["duration"] = result["duration"].fillna(0).astype("int32")

    return result.sort_values(["weekly_number", "aid"]).reset_index(drop=True)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_warehouse.py -v -k "dwd"`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add src/bilianalysis/warehouse/dwd.py tests/test_warehouse.py
git commit -m "feat: add build_dwd() — transform records to wide fact table

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: DWS layer — build_dws()

**Files:**
- Create: `src/bilianalysis/warehouse/dws.py`
- Modify: `tests/test_warehouse.py` (append tests)

- [ ] **Step 1: Write failing tests for build_dws**

Append to `tests/test_warehouse.py`:

```python
from bilianalysis.warehouse.dws import build_dws


def test_build_dws_returns_three_tables():
    """build_dws returns a dict with exactly 3 DataFrames."""
    records_list = [_load_records(1)]
    dwd = build_dwd(records_list)
    dws = build_dws(dwd)

    assert set(dws.keys()) == {"dws_creator", "dws_category", "dws_weekly"}
    assert all(isinstance(df, pd.DataFrame) for df in dws.values())


def test_dws_creator_columns_and_grain():
    """dws_creator has expected columns, one row per up_mid."""
    records_list = [_load_records(1)]
    dwd = build_dwd(records_list)
    dws = build_dws(dwd)

    df = dws["dws_creator"]
    expected = {
        "up_mid", "up_name", "total_views", "total_likes",
        "total_coins", "total_favorites",
        "avg_view", "avg_like_rate", "avg_coin_rate",
        "video_count", "unique_video_count",
        "week_first", "week_last", "active_span",
    }
    assert set(df.columns) == expected
    assert df["up_mid"].is_unique


def test_dws_creator_aggregations():
    """Verify aggregation values for a known creator."""
    records_list = [_load_records(1), _load_records(2)]
    dwd = build_dwd(records_list)
    dws = build_dws(dwd)

    df = dws["dws_creator"]
    assert (df["unique_video_count"] <= df["video_count"]).all()
    assert (df["active_span"] >= 1).all()


def test_dws_category_columns_and_grain():
    """dws_category has expected columns, one row per category_tid."""
    records_list = [_load_records(1), _load_records(2)]
    dwd = build_dwd(records_list)
    dws = build_dws(dwd)

    df = dws["dws_category"]
    expected = {
        "category_tid", "category_name", "total_views",
        "avg_view_per_video", "avg_like_rate",
        "video_count", "unique_creator_count",
    }
    assert set(df.columns) == expected
    assert df["category_tid"].is_unique


def test_dws_weekly_columns_and_grain():
    """dws_weekly has expected columns, one row per weekly_number."""
    records_list = [_load_records(1), _load_records(2)]
    dwd = build_dwd(records_list)
    dws = build_dws(dwd)

    df = dws["dws_weekly"]
    expected = {
        "weekly_number", "total_views", "avg_view_per_video",
        "video_count", "creator_count", "category_count",
        "total_likes", "total_coins", "total_favorites",
    }
    assert set(df.columns) == expected
    assert df["weekly_number"].is_unique
    assert len(df) >= 2


def test_dws_empty_dwd():
    """build_dws on empty DWD returns empty tables with correct columns."""
    empty_dwd = pd.DataFrame(columns=[
        "weekly_number", "aid", "bvid", "title", "duration", "pubdate",
        "up_mid", "up_name", "category_tid", "category_name",
        "view", "like_cnt", "coin", "favorite", "share", "reply", "danmaku",
        "like_rate", "coin_rate", "favorite_rate",
    ])
    dws = build_dws(empty_dwd)

    assert len(dws["dws_creator"]) == 0
    assert len(dws["dws_category"]) == 0
    assert len(dws["dws_weekly"]) == 0
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `uv run pytest tests/test_warehouse.py -v -k "dws"`
Expected: FAIL — ImportError: cannot import build_dws

- [ ] **Step 3: Implement build_dws**

```python
# src/bilianalysis/warehouse/dws.py
"""DWS layer: build three summary tables from DWD wide table."""
import pandas as pd


def build_dws(dwd_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build three DWS summary tables from DWD wide table.

    Args:
        dwd_df: DWD wide table from build_dwd().

    Returns:
        {"dws_creator": df, "dws_category": df, "dws_weekly": df}
    """
    if dwd_df.empty:
        return _empty_dws()

    # dws_creator: aggregate by up_mid
    dws_creator = (
        dwd_df.groupby("up_mid", as_index=False)
        .agg(
            up_name=("up_name", "last"),
            total_views=("view", "sum"),
            total_likes=("like_cnt", "sum"),
            total_coins=("coin", "sum"),
            total_favorites=("favorite", "sum"),
            avg_view=("view", "mean"),
            avg_like_rate=("like_rate", "mean"),
            avg_coin_rate=("coin_rate", "mean"),
            video_count=("aid", "count"),
            unique_video_count=("aid", "nunique"),
            week_first=("weekly_number", "min"),
            week_last=("weekly_number", "max"),
        )
    )
    dws_creator["active_span"] = (
        dws_creator["week_last"] - dws_creator["week_first"] + 1
    )
    dws_creator["avg_view"] = dws_creator["avg_view"].round(2)
    dws_creator["avg_like_rate"] = dws_creator["avg_like_rate"].round(6)
    dws_creator["avg_coin_rate"] = dws_creator["avg_coin_rate"].round(6)
    for col in ["total_views", "total_likes", "total_coins", "total_favorites"]:
        dws_creator[col] = dws_creator[col].astype("int64")
    for col in ["video_count", "unique_video_count", "week_first", "week_last", "active_span"]:
        dws_creator[col] = dws_creator[col].astype("int32")

    # dws_category: aggregate by category_tid
    dws_category = (
        dwd_df.groupby("category_tid", as_index=False)
        .agg(
            category_name=("category_name", "last"),
            total_views=("view", "sum"),
            avg_view_per_video=("view", "mean"),
            avg_like_rate=("like_rate", "mean"),
            video_count=("aid", "count"),
            unique_creator_count=("up_mid", "nunique"),
        )
    )
    dws_category["avg_view_per_video"] = dws_category["avg_view_per_video"].round(2)
    dws_category["avg_like_rate"] = dws_category["avg_like_rate"].round(6)
    dws_category["total_views"] = dws_category["total_views"].astype("int64")
    dws_category["video_count"] = dws_category["video_count"].astype("int32")
    dws_category["unique_creator_count"] = dws_category["unique_creator_count"].astype("int32")

    # dws_weekly: aggregate by weekly_number
    dws_weekly = (
        dwd_df.groupby("weekly_number", as_index=False)
        .agg(
            total_views=("view", "sum"),
            avg_view_per_video=("view", "mean"),
            video_count=("aid", "count"),
            creator_count=("up_mid", "nunique"),
            category_count=("category_tid", "nunique"),
            total_likes=("like_cnt", "sum"),
            total_coins=("coin", "sum"),
            total_favorites=("favorite", "sum"),
        )
    )
    dws_weekly["avg_view_per_video"] = dws_weekly["avg_view_per_video"].round(2)
    for col in ["total_views", "total_likes", "total_coins", "total_favorites"]:
        dws_weekly[col] = dws_weekly[col].astype("int64")
    for col in ["video_count", "creator_count", "category_count", "weekly_number"]:
        dws_weekly[col] = dws_weekly[col].astype("int32")

    return {
        "dws_creator": dws_creator,
        "dws_category": dws_category,
        "dws_weekly": dws_weekly,
    }


def _empty_dws() -> dict[str, pd.DataFrame]:
    """Return empty DWS tables with correct column schemas."""
    return {
        "dws_creator": pd.DataFrame(columns=[
            "up_mid", "up_name", "total_views", "total_likes",
            "total_coins", "total_favorites", "avg_view",
            "avg_like_rate", "avg_coin_rate", "video_count",
            "unique_video_count", "week_first", "week_last", "active_span",
        ]),
        "dws_category": pd.DataFrame(columns=[
            "category_tid", "category_name", "total_views",
            "avg_view_per_video", "avg_like_rate",
            "video_count", "unique_creator_count",
        ]),
        "dws_weekly": pd.DataFrame(columns=[
            "weekly_number", "total_views", "avg_view_per_video",
            "video_count", "creator_count", "category_count",
            "total_likes", "total_coins", "total_favorites",
        ]),
    }
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_warehouse.py -v -k "dws"`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add src/bilianalysis/warehouse/dws.py tests/test_warehouse.py
git commit -m "feat: add build_dws() — DWD to three summary tables

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: ADS layer — build_ads()

**Files:**
- Create: `src/bilianalysis/warehouse/ads.py`
- Modify: `tests/test_warehouse.py` (append tests)

- [ ] **Step 1: Write failing tests for build_ads**

Append to `tests/test_warehouse.py`:

```python
from bilianalysis.warehouse.ads import build_ads


def test_build_ads_returns_four_tables():
    """build_ads returns a dict with exactly 4 DataFrames."""
    records_list = [_load_records(1), _load_records(2)]
    dwd = build_dwd(records_list)
    dws = build_dws(dwd)
    ads = build_ads(dws, dwd)

    assert set(ads.keys()) == {
        "ads_hot_videos", "ads_top_creators",
        "ads_category_trend", "ads_weekly_kpi",
    }
    assert all(isinstance(df, pd.DataFrame) for df in ads.values())


def test_ads_hot_videos_deduped():
    """ads_hot_videos has one row per unique video, no weekly_number."""
    records_list = [_load_records(1), _load_records(2)]
    dwd = build_dwd(records_list)
    dws = build_dws(dwd)
    ads = build_ads(dws, dwd)

    df = ads["ads_hot_videos"]
    assert df["aid"].is_unique
    assert "weekly_number" not in df.columns
    expected_cols = {"aid", "bvid", "title", "up_mid", "up_name",
                     "category_name", "view", "like_cnt", "coin",
                     "favorite", "like_rate", "coin_rate", "pubdate"}
    assert set(df.columns) == expected_cols


def test_ads_hot_videos_sorted_by_view():
    """ads_hot_videos is sorted by view descending."""
    records_list = [_load_records(1), _load_records(2)]
    dwd = build_dwd(records_list)
    dws = build_dws(dwd)
    ads = build_ads(dws, dwd)

    df = ads["ads_hot_videos"]
    views = df["view"].tolist()
    assert views == sorted(views, reverse=True)


def test_ads_top_creators_sorted():
    """ads_top_creators is sorted by total_views descending."""
    records_list = [_load_records(1), _load_records(2)]
    dwd = build_dwd(records_list)
    dws = build_dws(dwd)
    ads = build_ads(dws, dwd)

    df = ads["ads_top_creators"]
    views = df["total_views"].tolist()
    assert views == sorted(views, reverse=True)


def test_ads_category_trend_columns():
    """ads_category_trend has cross-product (category, week) grain."""
    records_list = [_load_records(1), _load_records(2)]
    dwd = build_dwd(records_list)
    dws = build_dws(dwd)
    ads = build_ads(dws, dwd)

    df = ads["ads_category_trend"]
    expected = {"weekly_number", "category_name", "video_count", "total_views", "avg_like_rate"}
    assert set(df.columns) == expected


def test_ads_weekly_kpi_columns():
    """ads_weekly_kpi has one row per week with KPI columns."""
    records_list = [_load_records(1), _load_records(2)]
    dwd = build_dwd(records_list)
    dws = build_dws(dwd)
    ads = build_ads(dws, dwd)

    df = ads["ads_weekly_kpi"]
    expected = {
        "weekly_number", "total_views", "avg_view_per_video",
        "video_count", "creator_count", "category_count",
        "avg_like_rate", "avg_coin_rate",
    }
    assert set(df.columns) == expected
    assert len(df) >= 2


def test_ads_empty_input():
    """build_ads on empty DWD/DWS returns empty tables with correct columns."""
    empty_dwd = pd.DataFrame(columns=[
        "weekly_number", "aid", "bvid", "title", "duration", "pubdate",
        "up_mid", "up_name", "category_tid", "category_name",
        "view", "like_cnt", "coin", "favorite", "share", "reply", "danmaku",
        "like_rate", "coin_rate", "favorite_rate",
    ])
    empty_dws = {
        "dws_creator": pd.DataFrame(),
        "dws_category": pd.DataFrame(),
        "dws_weekly": pd.DataFrame(),
    }
    ads = build_ads(empty_dws, empty_dwd)

    assert len(ads["ads_hot_videos"]) == 0
    assert len(ads["ads_top_creators"]) == 0
    assert len(ads["ads_category_trend"]) == 0
    assert len(ads["ads_weekly_kpi"]) == 0
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `uv run pytest tests/test_warehouse.py -v -k "ads"`
Expected: FAIL — ImportError: cannot import build_ads

- [ ] **Step 3: Implement build_ads**

```python
# src/bilianalysis/warehouse/ads.py
"""ADS layer: build four application-facing tables from DWS + DWD."""
import pandas as pd


def build_ads(
    dws_dict: dict[str, pd.DataFrame], dwd_df: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    """Build four ADS tables for frontend pages.

    Args:
        dws_dict: Output of build_dws() — {"dws_creator", "dws_category", "dws_weekly"}
        dwd_df: DWD wide table from build_dwd()

    Returns:
        {"ads_hot_videos", "ads_top_creators", "ads_category_trend", "ads_weekly_kpi"}
    """
    ads_hot_videos = _build_hot_videos(dwd_df)
    ads_top_creators = _build_top_creators(dws_dict.get("dws_creator", pd.DataFrame()))
    ads_category_trend = _build_category_trend(dwd_df)
    # Note: dws_weekly lacks rate columns; compute them from DWD
    ads_weekly_kpi = _build_weekly_kpi(
        dws_dict.get("dws_weekly", pd.DataFrame()), dwd_df
    )
    return {
        "ads_hot_videos": ads_hot_videos,
        "ads_top_creators": ads_top_creators,
        "ads_category_trend": ads_category_trend,
        "ads_weekly_kpi": ads_weekly_kpi,
    }


def _build_hot_videos(dwd_df: pd.DataFrame) -> pd.DataFrame:
    if dwd_df.empty:
        return pd.DataFrame(columns=[
            "aid", "bvid", "title", "up_mid", "up_name", "category_name",
            "view", "like_cnt", "coin", "favorite", "like_rate", "coin_rate", "pubdate",
        ])
    deduped = dwd_df.drop_duplicates(subset=["aid"], keep="last")
    result = deduped[[
        "aid", "bvid", "title", "up_mid", "up_name", "category_name",
        "view", "like_cnt", "coin", "favorite", "like_rate", "coin_rate", "pubdate",
    ]].copy()
    return result.sort_values("view", ascending=False).reset_index(drop=True)


def _build_top_creators(dws_creator: pd.DataFrame) -> pd.DataFrame:
    if dws_creator.empty:
        return pd.DataFrame(columns=[
            "up_mid", "up_name", "total_views", "avg_like_rate", "avg_coin_rate",
            "video_count", "unique_video_count", "active_span",
        ])
    result = dws_creator[[
        "up_mid", "up_name", "total_views", "avg_like_rate", "avg_coin_rate",
        "video_count", "unique_video_count", "active_span",
    ]].copy()
    return result.sort_values("total_views", ascending=False).reset_index(drop=True)


def _build_category_trend(dwd_df: pd.DataFrame) -> pd.DataFrame:
    if dwd_df.empty:
        return pd.DataFrame(columns=[
            "weekly_number", "category_name", "video_count", "total_views", "avg_like_rate",
        ])
    result = (
        dwd_df.groupby(["category_name", "weekly_number"], as_index=False)
        .agg(
            video_count=("aid", "count"),
            total_views=("view", "sum"),
            avg_like_rate=("like_rate", "mean"),
        )
    )
    result["avg_like_rate"] = result["avg_like_rate"].round(6)
    result["total_views"] = result["total_views"].astype("int64")
    result["video_count"] = result["video_count"].astype("int32")
    result["weekly_number"] = result["weekly_number"].astype("int32")
    return result.sort_values(["weekly_number", "category_name"]).reset_index(drop=True)


def _build_weekly_kpi(
    dws_weekly: pd.DataFrame, dwd_df: pd.DataFrame
) -> pd.DataFrame:
    if dws_weekly.empty:
        return pd.DataFrame(columns=[
            "weekly_number", "total_views", "avg_view_per_video",
            "video_count", "creator_count", "category_count",
            "avg_like_rate", "avg_coin_rate",
        ])
    # Compute weekly avg rates from DWD (dws_weekly doesn't have rate columns)
    weekly_rates = (
        dwd_df.groupby("weekly_number", as_index=False)
        .agg(
            avg_like_rate=("like_rate", "mean"),
            avg_coin_rate=("coin_rate", "mean"),
        )
    )
    weekly_rates["avg_like_rate"] = weekly_rates["avg_like_rate"].round(6)
    weekly_rates["avg_coin_rate"] = weekly_rates["avg_coin_rate"].round(6)
    weekly_rates["weekly_number"] = weekly_rates["weekly_number"].astype("int32")

    result = dws_weekly[[
        "weekly_number", "total_views", "avg_view_per_video",
        "video_count", "creator_count", "category_count",
    ]].merge(weekly_rates, on="weekly_number", how="left")
    result["avg_like_rate"] = result["avg_like_rate"].fillna(0.0)
    result["avg_coin_rate"] = result["avg_coin_rate"].fillna(0.0)
    return result.sort_values("weekly_number").reset_index(drop=True)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_warehouse.py -v -k "ads"`
Expected: 7 PASS

- [ ] **Step 5: Commit**

```bash
git add src/bilianalysis/warehouse/ads.py tests/test_warehouse.py
git commit -m "feat: add build_ads() — four application-facing tables from DWS+DWD

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Builder orchestration — build_warehouse()

**Files:**
- Create: `src/bilianalysis/warehouse/builder.py`
- Modify: `src/bilianalysis/warehouse/__init__.py` (already imports from .builder)
- Modify: `tests/test_warehouse.py` (append tests)

- [ ] **Step 1: Write failing tests for build_warehouse**

Append to `tests/test_warehouse.py`:

```python
import tempfile
from pathlib import Path

from bilianalysis.warehouse.builder import build_warehouse
from bilianalysis.warehouse import WarehouseReport


def test_build_warehouse_end_to_end():
    """Full pipeline with real data: 4 weeks → 8 parquet files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        warehouse_dir = Path(tmpdir) / "warehouse"
        report = build_warehouse(RAW_DIR, warehouse_dir)

        assert isinstance(report, WarehouseReport)
        assert report.weeks_processed >= 4
        assert report.weeks_skipped == 0
        assert len(report.tables_written) == 8
        assert report.duration_seconds > 0

        for table_name in report.tables_written:
            assert (warehouse_dir / table_name).exists()

        dwd = pd.read_parquet(warehouse_dir / "dwd_fact_video.parquet")
        assert len(dwd) > 0
        assert "weekly_number" in dwd.columns


def test_build_warehouse_empty_dir():
    """Empty raw_dir → report with 0 processed, no files written."""
    with tempfile.TemporaryDirectory() as tmpdir:
        raw_dir = Path(tmpdir) / "empty_raw"
        raw_dir.mkdir()
        warehouse_dir = Path(tmpdir) / "warehouse"

        report = build_warehouse(raw_dir, warehouse_dir)

        assert report.weeks_processed == 0
        assert report.weeks_skipped == 0
        assert report.tables_written == []
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `uv run pytest tests/test_warehouse.py -v -k "builder"`
Expected: FAIL — ImportError: cannot import build_warehouse

- [ ] **Step 3: Implement build_warehouse**

```python
# src/bilianalysis/warehouse/builder.py
"""Orchestration: scan raw JSON → transform → DWD → DWS → ADS → write Parquet."""
import json
import time
from pathlib import Path

from bilianalysis.etl.transform import transform_week
from bilianalysis.warehouse.dwd import build_dwd
from bilianalysis.warehouse.dws import build_dws
from bilianalysis.warehouse.ads import build_ads
from bilianalysis.warehouse.report import WarehouseReport, SkippedWeek


def build_warehouse(raw_dir: Path, warehouse_dir: Path) -> WarehouseReport:
    """Full rebuild of the data warehouse from raw JSON files.

    Args:
        raw_dir: Directory containing week_*.json files.
        warehouse_dir: Directory to write Parquet files to.

    Returns:
        WarehouseReport with processing statistics.
    """
    start = time.monotonic()
    warehouse_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(raw_dir.glob("week_*.json"))
    if not json_files:
        return WarehouseReport(duration_seconds=round(time.monotonic() - start, 2))

    all_records = []
    skipped = []
    for json_path in json_files:
        try:
            week_number = int(json_path.stem.split("_")[1])
            raw = json.loads(json_path.read_text(encoding="utf-8"))
            records = transform_week(raw)
            all_records.append(records)
        except Exception as exc:
            skipped.append(SkippedWeek(
                week_number=week_number if "week_number" in dir() else -1,
                error=str(exc),
            ))

    if not all_records:
        return WarehouseReport(
            weeks_skipped=len(skipped),
            skipped_details=skipped,
            duration_seconds=round(time.monotonic() - start, 2),
        )

    dwd_df = build_dwd(all_records)
    tables_written = []
    _write_parquet(dwd_df, warehouse_dir / "dwd_fact_video.parquet")
    tables_written.append("dwd_fact_video.parquet")

    dws_dict = build_dws(dwd_df)
    for name in ["dws_creator", "dws_category", "dws_weekly"]:
        _write_parquet(dws_dict[name], warehouse_dir / f"{name}.parquet")
        tables_written.append(f"{name}.parquet")

    ads_dict = build_ads(dws_dict, dwd_df)
    for name in ["ads_hot_videos", "ads_top_creators", "ads_category_trend", "ads_weekly_kpi"]:
        _write_parquet(ads_dict[name], warehouse_dir / f"{name}.parquet")
        tables_written.append(f"{name}.parquet")

    return WarehouseReport(
        weeks_processed=len(all_records),
        weeks_skipped=len(skipped),
        skipped_details=skipped,
        tables_written=tables_written,
        duration_seconds=round(time.monotonic() - start, 2),
    )


def _write_parquet(df, path: Path) -> None:
    """Write DataFrame to Parquet with atomic tmp→rename."""
    tmp_path = path.with_suffix(".tmp.parquet")
    df.to_parquet(tmp_path, index=False)
    tmp_path.rename(path)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_warehouse.py -v -k "builder"`
Expected: 2 PASS

- [ ] **Step 5: Run all warehouse tests together**

Run: `uv run pytest tests/test_warehouse.py -v`
Expected: 23 PASS (2 report + 6 dwd + 6 dws + 7 ads + 2 builder)

- [ ] **Step 6: Commit**

```bash
git add src/bilianalysis/warehouse/builder.py tests/test_warehouse.py
git commit -m "feat: add build_warehouse() — full pipeline orchestration

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Scheduler integration — WarehouseTask

**Files:**
- Create: `src/bilianalysis/scheduler/builtins/warehouse_task.py`
- Modify: `src/bilianalysis/scheduler/builtins/__init__.py`
- Modify: `tests/test_scheduler.py` (append test)

- [ ] **Step 1: Write the WarehouseTask**

```python
# src/bilianalysis/scheduler/builtins/warehouse_task.py
"""数据仓库构建 Task。"""
import time
from pathlib import Path

from bilianalysis.scheduler.task import Task, TaskContext, TaskResult
from bilianalysis.scheduler.registry import register


@register("build_warehouse")
class WarehouseTask(Task):
    name = "build_warehouse"

    async def run(self, ctx: TaskContext) -> TaskResult:
        start = time.monotonic()
        try:
            from bilianalysis.warehouse import build_warehouse

            raw_dir = Path(ctx.config.data.raw_dir)
            warehouse_dir = Path(ctx.config.data.processed_dir).parent / "warehouse"
            report = build_warehouse(raw_dir, warehouse_dir)

            return TaskResult(
                task_name="build_warehouse", status="success",
                duration_seconds=round(time.monotonic() - start, 2),
                output={
                    "weeks_processed": report.weeks_processed,
                    "weeks_skipped": report.weeks_skipped,
                    "tables_written": report.tables_written,
                },
            )
        except Exception as exc:
            return TaskResult(
                task_name="build_warehouse", status="failed",
                duration_seconds=round(time.monotonic() - start, 2),
                error=str(exc),
            )
```

```python
# in src/bilianalysis/scheduler/builtins/__init__.py — add:
from .warehouse_task import WarehouseTask  # noqa: F401
```

- [ ] **Step 2: Write scheduler test**

Append to `tests/test_scheduler.py`:

```python
def test_build_warehouse_task_registered():
    """build_warehouse task is registered and importable."""
    from bilianalysis.scheduler.registry import get_task
    task = get_task("build_warehouse")
    assert task is not None
    assert task.name == "build_warehouse"
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_scheduler.py::test_build_warehouse_task_registered -v`
Expected: PASS

Run: `uv run pytest tests/ -v`
Expected: all existing tests + new warehouse tests pass

- [ ] **Step 4: Commit**

```bash
git add src/bilianalysis/scheduler/builtins/warehouse_task.py \
        src/bilianalysis/scheduler/builtins/__init__.py \
        tests/test_scheduler.py
git commit -m "feat: add build_warehouse scheduler task

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Final integration test

**Files:**
- Verify `.gitignore` coverage (no changes expected)

- [ ] **Step 1: Verify .gitignore covers warehouse output**

Run: `grep "data/" .gitignore`
Expected: `data/` entry exists → `data/warehouse/` already covered.

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests pass including the 23 new warehouse tests

- [ ] **Step 3: Dry-run with real data**

Run: `uv run python -c "from pathlib import Path; from bilianalysis.warehouse import build_warehouse; r = build_warehouse(Path('data/raw'), Path('data/warehouse')); print(r.model_dump_json(indent=2))"`
Expected: Prints WarehouseReport JSON with weeks_processed >= 4, 8 tables_written

- [ ] **Step 4: Verify Parquet output**

Run: `uv run python -c "import pandas as pd; dwd = pd.read_parquet('data/warehouse/dwd_fact_video.parquet'); print(f'DWD: {len(dwd)} rows, {len(dwd.columns)} cols'); print(dwd.columns.tolist())"`
Expected: DWD has >0 rows and 20 columns

- [ ] **Step 5: Commit**

```bash
git commit -m "chore: verify warehouse pipeline end-to-end with real data

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```
