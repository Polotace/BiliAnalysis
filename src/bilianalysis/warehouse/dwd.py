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
