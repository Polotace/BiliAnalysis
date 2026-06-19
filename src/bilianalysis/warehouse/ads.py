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
    # dws_weekly lacks rate columns; compute them from DWD
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
