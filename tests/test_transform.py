"""Unit tests for etl/transform.py — pure functions, no DB needed."""
import json
from datetime import datetime, timezone
from pathlib import Path

from bilianalysis.etl.transform import transform_week

RAW_DIR = Path("data/raw")


def test_transform_week_produces_six_groups():
    """transform_week returns all 6 expected keys with correct types."""
    raw = json.loads((RAW_DIR / "week_001.json").read_text(encoding="utf-8"))
    result = transform_week(raw)

    assert set(result.keys()) == {
        "weekly", "creators", "categories",
        "videos", "video_stats", "weekly_videos",
    }
    # weekly is a single-element list
    assert len(result["weekly"]) == 1
    assert result["weekly"][0]["number"] == 1
    assert result["weekly"][0]["subject"] == "神仙爱情"
    assert result["weekly"][0]["label"] == "第1期(0329更新)"

    # at least one video
    assert len(result["videos"]) > 0

    # creator, video_stats, weekly_videos have same length as videos
    n = len(result["videos"])
    assert len(result["video_stats"]) == n
    assert len(result["weekly_videos"]) == n


def test_transform_week_dedup_creators():
    """Creators are deduped by mid within a single week."""
    raw = json.loads((RAW_DIR / "week_001.json").read_text(encoding="utf-8"))
    result = transform_week(raw)

    mids = [c["mid"] for c in result["creators"]]
    assert len(mids) == len(set(mids))  # no duplicates

    # week_001 has at least creator mid=546195 (老番茄)
    assert 546195 in mids


def test_transform_week_dedup_categories():
    """Categories are deduped by tid within a single week."""
    raw = json.loads((RAW_DIR / "week_001.json").read_text(encoding="utf-8"))
    result = transform_week(raw)

    tids = [c["tid"] for c in result["categories"]]
    assert len(tids) == len(set(tids))


def test_transform_week_unix_timestamps_become_datetime():
    """UNIX int timestamps are converted to timezone-aware datetime objects."""
    raw = json.loads((RAW_DIR / "week_001.json").read_text(encoding="utf-8"))
    result = transform_week(raw)

    w = result["weekly"][0]
    assert isinstance(w["start_time"], datetime)
    assert isinstance(w["end_time"], datetime)
    assert w["start_time"].tzinfo is not None

    v = result["videos"][0]
    assert isinstance(v["pubdate"], datetime)
    assert v["pubdate"].tzinfo is not None


def test_transform_week_field_mapping():
    """Spot-check that key fields map from raw JSON correctly."""
    raw = json.loads((RAW_DIR / "week_001.json").read_text(encoding="utf-8"))
    result = transform_week(raw)

    # First video: aid=46900196
    v = next(x for x in result["videos"] if x["aid"] == 46900196)
    assert v["bvid"] == "BV14b411J7ML"
    assert v["video_url"] == "https://b23.tv/BV14b411J7ML"
    assert v["copyright"] == 1
    assert v["creator_mid"] == 326257138
    assert v["category_tid"] == 250

    # Its stat
    vs = next(x for x in result["video_stats"] if x["aid"] == 46900196)
    assert vs["view"] == 5391512
    assert vs["like_cnt"] == 509422
    assert vs["coin"] == 553737
    assert vs["danmaku"] == 70080


def test_transform_week_empty_videos():
    """Week with no videos should return empty lists except weekly."""
    raw = {"number": 999, "config": {}, "videos": []}
    result = transform_week(raw)

    assert len(result["weekly"]) == 1
    assert result["videos"] == []
    assert result["creators"] == []
    assert result["categories"] == []
    assert result["video_stats"] == []
    assert result["weekly_videos"] == []


def test_transform_week_missing_optional_fields():
    """Videos with missing optional fields should get None values."""
    raw = {
        "number": 999,
        "config": {},
        "videos": [{
            "aid": 1,
            "stat": {},
            "owner": {},
        }]
    }
    result = transform_week(raw)

    v = result["videos"][0]
    assert v["bvid"] is None
    assert v["video_url"] is None
    assert v["copyright"] is None
