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
