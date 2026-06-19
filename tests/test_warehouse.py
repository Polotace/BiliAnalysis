"""Tests for data warehouse layered builder."""
import json
from pathlib import Path

import pandas as pd
from bilianalysis.etl.transform import transform_week
from bilianalysis.warehouse import WarehouseReport
from bilianalysis.warehouse.dwd import build_dwd
from bilianalysis.warehouse.report import SkippedWeek

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
