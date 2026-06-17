"""Pandas 分析引擎实现。"""
import json
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from bilianalysis.config.model import DataSection
from bilianalysis.engine.base import (
    AnalysisEngine, CleanReport, StatReport, ClusterReport, PredictionReport,
    OverallStats, CategoryStats, CreatorStats, WeeklyTrend,
)


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

            # 2.3 缺失值: count before fill for report
            na_before = sum(df.isna().sum().sum() for df in dfs.values())
            dfs = self._fill_missing(dfs)
            missing_filled += na_before

            # 2.4 去重（批次内 + 跨批次）
            video_df = dfs["Video"]
            before = len(video_df)
            if not video_df.empty:
                # 批次内去重：保留每个 aid 首次出现
                in_batch_mask = ~video_df["aid"].duplicated(keep='first')
                # 跨批次去重：排除已在 seen_aids 中的 aid
                cross_batch_mask = ~video_df["aid"].isin(seen_aids)
                # 合并两个条件
                keep_mask = in_batch_mask & cross_batch_mask

                dfs["Video"] = video_df[keep_mask].reset_index(drop=True)
                duplicates_dropped += before - len(dfs["Video"])

                # 同步去重到关联表（按行位置对应）
                kept_mask = keep_mask.values
            else:
                kept_mask = None
                duplicates_dropped += before

            if kept_mask is not None:
                dfs["VideoStat"] = dfs["VideoStat"].loc[kept_mask].reset_index(drop=True) if not dfs["VideoStat"].empty else dfs["VideoStat"]
                dfs["Creator"] = dfs["Creator"].loc[kept_mask].reset_index(drop=True) if not dfs["Creator"].empty else dfs["Creator"]
                dfs["Category"] = dfs["Category"].loc[kept_mask].reset_index(drop=True) if not dfs["Category"].empty else dfs["Category"]

            if not dfs["Video"].empty:
                seen_aids.update(dfs["Video"]["aid"].tolist())
            total_videos += len(dfs["Video"])

            # 2.5 类型转换
            dfs = self._convert_types(dfs)

            # 2.6 异常值检测
            stat_df = dfs["VideoStat"]
            if not stat_df.empty:
                stat_before = len(stat_df)
                valid = (
                    (stat_df["view"] >= 0) &
                    (stat_df["like"] >= 0) &
                    (stat_df["coin"] >= 0) &
                    (stat_df["favorite"] >= 0) &
                    (stat_df["share"] >= 0) &
                    (stat_df["reply"] >= 0) &
                    (stat_df["danmaku"] >= 0)
                )
                dfs["VideoStat"] = stat_df[valid].reset_index(drop=True)
                # 同步过滤关联表（按行位置）
                if not valid.all():
                    dfs["Video"] = dfs["Video"].loc[valid.values].reset_index(drop=True)
                    dfs["Creator"] = dfs["Creator"].loc[valid.values].reset_index(drop=True)
                    dfs["Category"] = dfs["Category"].loc[valid.values].reset_index(drop=True)
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

        duration = time.monotonic() - start_time
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
                "subject": cfg.get("subject"),
                "name": cfg.get("name"),
                "start_time": cfg.get("start_time"),
                "end_time": cfg.get("end_time"),
            })

            for v in rec.get("videos", []):
                owner = v.get("owner", {})
                stat = v.get("stat", {})

                video_rows.append({
                    "aid": v.get("aid"),
                    "bvid": v.get("bvid"),
                    "title": v.get("title"),
                    "desc": v.get("desc"),
                    "duration": v.get("duration"),
                    "pubdate": v.get("pubdate"),
                    "cid": v.get("cid"),
                    "pic": v.get("pic"),
                })

                creator_rows.append({
                    "mid": owner.get("mid"),
                    "name": owner.get("name"),
                    "face": owner.get("face"),
                })

                rcmd = v.get("rcmd_reason")
                category_rows.append({
                    "tid": v.get("tid"),
                    "tname": v.get("tname"),
                    "tid_v2": rcmd.get("tid_v2") if rcmd else None,
                    "tname_v2": rcmd.get("tname_v2") if rcmd else None,
                })

                stat_rows.append({
                    "aid": stat.get("aid", v.get("aid")),
                    "view": stat.get("view"),
                    "like": stat.get("like"),
                    "coin": stat.get("coin"),
                    "favorite": stat.get("favorite"),
                    "share": stat.get("share"),
                    "reply": stat.get("reply"),
                    "danmaku": stat.get("danmaku"),
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
        """从 processed/ Parquet 读取 → join → groupby 聚合 → StatReport。"""
        # 1. 读取 5 张 Parquet 表
        weekly = pd.read_parquet(self._processed_dir / "Weekly.parquet")
        video = pd.read_parquet(self._processed_dir / "Video.parquet")
        video_stat = pd.read_parquet(self._processed_dir / "VideoStat.parquet")
        creator = pd.read_parquet(self._processed_dir / "Creator.parquet")
        category = pd.read_parquet(self._processed_dir / "Category.parquet")

        # 2. Merge Video + VideoStat on aid
        df = video.merge(video_stat, on="aid", how="inner")

        # 3. 按行位置分配 Creator 和 Category 信息
        #    clean_data 保证 Creator/Category 与 Video 行顺序一致
        df["creator_mid"] = creator["mid"].values
        df["creator_name"] = creator["name"].values
        df["tname"] = category["tname"].values

        # 4. 匹配每期视频所属周次（pubdate ∈ [start_time, end_time]）
        #    使用 cross join + 过滤实现向量化匹配
        df = df.assign(_key=1).merge(weekly.assign(_key=1), on="_key").drop(columns="_key")
        df = df[(df["start_time"] <= df["pubdate"]) & (df["pubdate"] <= df["end_time"])]
        week_number_map = df[["number"]].rename(columns={"number": "week_number"})
        # 将 week_number 关联回原 df（按索引）
        df["week_number"] = week_number_map["week_number"].values

        # 5. 计算交互率（view=0 替换为 1 避免除零）
        view_safe = df["view"].replace(0, 1.0)
        df["like_rate"] = df["like"] / view_safe
        df["coin_rate"] = df["coin"] / view_safe
        df["favorite_rate"] = df["favorite"] / view_safe

        # 6. OverallStats
        overall = OverallStats(
            total_videos=len(df),
            total_creators=int(df["creator_mid"].nunique()),
            avg_view=float(df["view"].mean()),
            avg_like=float(df["like"].mean()),
            avg_coin=float(df["coin"].mean()),
            avg_favorite=float(df["favorite"].mean()),
            avg_share=float(df["share"].mean()),
            avg_danmaku=float(df["danmaku"].mean()),
            avg_like_rate=float(df["like_rate"].mean()),
            avg_coin_rate=float(df["coin_rate"].mean()),
            avg_favorite_rate=float(df["favorite_rate"].mean()),
        )

        # 7. by_category
        cat_agg = df.groupby("tname").agg(
            video_count=("aid", "count"),
            avg_view=("view", "mean"),
            avg_like=("like", "mean"),
            avg_interaction_rate=("like_rate", "mean"),
        ).reset_index()
        by_category = [
            CategoryStats(
                tname=row["tname"],
                video_count=int(row["video_count"]),
                avg_view=float(row["avg_view"]),
                avg_like=float(row["avg_like"]),
                avg_interaction_rate=float(row["avg_interaction_rate"]),
            )
            for _, row in cat_agg.iterrows()
        ]

        # 8. by_creator (TOP10，按出现次数降序)
        creator_agg = df.groupby(["creator_mid", "creator_name"]).agg(
            appearance_count=("aid", "count"),
            total_view=("view", "sum"),
            total_like=("like", "sum"),
            total_favorite=("favorite", "sum"),
        ).reset_index().sort_values("appearance_count", ascending=False).head(10)
        by_creator = [
            CreatorStats(
                mid=int(row["creator_mid"]),
                name=row["creator_name"],
                appearance_count=int(row["appearance_count"]),
                total_view=int(row["total_view"]),
                total_like=int(row["total_like"]),
                total_favorite=int(row["total_favorite"]),
            )
            for _, row in creator_agg.iterrows()
        ]

        # 9. by_week（按周次排序）
        week_agg = df.groupby("week_number").agg(
            video_count=("aid", "count"),
            avg_view=("view", "mean"),
            avg_like=("like", "mean"),
            avg_interaction_rate=("like_rate", "mean"),
        ).reset_index().sort_values("week_number")
        by_week = [
            WeeklyTrend(
                week_number=int(row["week_number"]),
                video_count=int(row["video_count"]),
                avg_view=float(row["avg_view"]),
                avg_like=float(row["avg_like"]),
                avg_interaction_rate=float(row["avg_interaction_rate"]),
            )
            for _, row in week_agg.iterrows()
        ]

        return StatReport(
            overall=overall,
            by_category=by_category,
            by_creator=by_creator,
            by_week=by_week,
        )

    # ── clustering ───────────────────────────────────────────

    def clustering(self) -> ClusterReport:
        raise NotImplementedError("clustering: to be implemented in Task 5")

    # ── prediction ───────────────────────────────────────────

    def prediction(self) -> PredictionReport:
        raise NotImplementedError("prediction: to be implemented in Task 6")
