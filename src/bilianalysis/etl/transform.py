"""Pure data transformation: raw JSON dict → typed record dicts.

This module is the sole accessor of data/raw/. It MUST NOT import
sqlalchemy, asyncpg, or any other database driver.
"""
import json
from datetime import datetime, timezone
from pathlib import Path


def _ts_to_datetime(ts: int | float) -> datetime:
    """Convert a UNIX timestamp to a timezone-aware datetime."""
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def transform_week(raw: dict) -> dict[str, list[dict]]:
    """Convert a single week's raw JSON dict into 6 groups of plain dict records.

    Pure function — no file I/O, no DB imports.

    Returns:
        {
            "weekly":       [dict],   # 1-element list
            "creators":     [dict],   # deduped by mid within this week
            "categories":   [dict],   # deduped by tid within this week
            "videos":       [dict],
            "video_stats":  [dict],
            "weekly_videos": [dict],
        }
    """
    number = raw["number"]
    cfg = raw.get("config", {})
    videos = raw.get("videos", [])

    # Weekly
    weekly = [{
        "number": number,
        "subject": cfg.get("subject"),
        "name": cfg.get("name"),
        "label": cfg.get("label"),
        "cover": cfg.get("cover"),
        "start_time": _ts_to_datetime(cfg["stime"]) if "stime" in cfg else None,
        "end_time": _ts_to_datetime(cfg["etime"]) if "etime" in cfg else None,
    }]

    creators = []
    categories = []
    video_list = []
    video_stats = []
    weekly_videos = []

    seen_mids: set[int] = set()
    seen_tids: set[int] = set()

    for v in videos:
        owner = v.get("owner", {})
        stat = v.get("stat", {})

        mid = owner.get("mid")
        tid = v.get("tid")

        # Creator (dedup by mid)
        if mid is not None and mid not in seen_mids:
            seen_mids.add(mid)
            creators.append({
                "mid": mid,
                "name": owner.get("name"),
                "face": owner.get("face"),
            })

        # Category (dedup by tid)
        if tid is not None and tid not in seen_tids:
            seen_tids.add(tid)
            categories.append({
                "tid": tid,
                "tname": v.get("tname"),
                "tid_v2": v.get("tidv2"),
                "tname_v2": v.get("tnamev2"),
                "pid_v2": v.get("pid_v2"),
                "pid_name_v2": v.get("pid_name_v2"),
            })

        aid = v.get("aid")

        video_list.append({
            "aid": aid,
            "bvid": v.get("bvid"),
            "title": v.get("title"),
            "description": v.get("desc"),
            "duration": v.get("duration"),
            "pubdate": _ts_to_datetime(v["pubdate"]) if "pubdate" in v else None,
            "cid": v.get("cid"),
            "video_url": v.get("short_link_v2"),
            "cover_url": v.get("pic"),
            "copyright": v.get("copyright"),
            "creator_mid": mid,
            "category_tid": tid,
        })

        video_stats.append({
            "aid": stat.get("aid", aid),
            "view": stat.get("view"),
            "like_cnt": stat.get("like"),
            "coin": stat.get("coin"),
            "favorite": stat.get("favorite"),
            "share": stat.get("share"),
            "reply": stat.get("reply"),
            "danmaku": stat.get("danmaku"),
        })

        weekly_videos.append({
            "weekly_number": number,
            "aid": aid,
        })

    return {
        "weekly": weekly,
        "creators": creators,
        "categories": categories,
        "videos": video_list,
        "video_stats": video_stats,
        "weekly_videos": weekly_videos,
    }


def load_raw_weeks(raw_dir: str | Path) -> list[dict[str, list[dict]]]:
    """Read all week_*.json files from data/raw/, apply transform_week to each.

    Returns a list in week-number ascending order.

    This is the ONLY function in the codebase that reads from data/raw/.
    """
    raw_dir = Path(raw_dir)
    files = sorted(raw_dir.glob("week_*.json"),
                   key=lambda p: int(p.stem.split("_")[1]))
    results: list[dict[str, list[dict]]] = []
    for fp in files:
        raw = json.loads(fp.read_text(encoding="utf-8"))
        results.append(transform_week(raw))
    return results
