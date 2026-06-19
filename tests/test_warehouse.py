"""Tests for data warehouse layered builder."""
import json
import tempfile
from pathlib import Path

import pandas as pd
from bilianalysis.etl.transform import transform_week
from bilianalysis.warehouse import WarehouseReport
from bilianalysis.warehouse.dwd import build_dwd
from bilianalysis.warehouse.report import SkippedWeek
from bilianalysis.warehouse.builder import build_warehouse

RAW_DIR = Path("data/raw")


def _load_records(week_number: int) -> dict:
    raw = json.loads((RAW_DIR / f"week_{week_number:03d}.json").read_text(encoding="utf-8"))
    return transform_week(raw)


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


# ---------------------------------------------------------------------------
# DWS layer tests
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# ADS layer tests
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Builder orchestration tests
# ---------------------------------------------------------------------------


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
