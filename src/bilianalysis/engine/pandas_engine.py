"""Pandas 分析引擎实现。"""
import json
import time
from pathlib import Path
from datetime import datetime

import pandas as pd


from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error, silhouette_score
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import numpy as np

from bilianalysis.config.model import DataSection
from bilianalysis.engine.base import (
    AnalysisEngine, CleanReport, StatReport, ClusterReport, PredictionReport,
    OverallStats, CategoryStats, CreatorStats, WeeklyTrend,
    ClusterGroup, ClusterResult, PredictionResult,
)


class PandasEngine(AnalysisEngine):
    """基于 Pandas 的分析引擎。

    全量加载 raw JSON，清洗后写出 5 张 Parquet 表，
    支持统计分析、KMeans 聚类、线性回归预测。
    """

    def __init__(self, data_config: DataSection):
        self._raw_dir = Path(data_config.raw_dir)
        self._processed_dir = Path(data_config.processed_dir)
        self._reports_dir = Path(data_config.reports_dir)

    # ── clean_data ───────────────────────────────────────────

    async def clean_data(self) -> CleanReport:
        start_time = time.monotonic()

        # 1. 全量加载所有 week JSON
        files = sorted(self._raw_dir.glob("week_*.json"),
                       key=lambda p: int(p.stem.split("_")[1]))
        records = []
        for fp in files:
            with open(fp, encoding="utf-8") as fh:
                records.append(json.load(fh))

        # 2. 拆表
        dfs = self._extract_tables(records)

        # 3. 缺失值
        na_before = sum(df.isna().sum().sum() for df in dfs.values())
        dfs = self._fill_missing(dfs)
        missing_filled = na_before

        # 4. 去重（按 aid，保留首次出现）
        video_df = dfs["Video"]
        before = len(video_df)
        if not video_df.empty:
            keep_mask = ~video_df["aid"].duplicated(keep="first")
            video_df = video_df[keep_mask].reset_index(drop=True)
            duplicates_dropped = before - len(video_df)
            dfs["Video"] = video_df
            # 同步关联表
            dfs["VideoStat"] = dfs["VideoStat"].loc[keep_mask.values].reset_index(drop=True) if not dfs["VideoStat"].empty else dfs["VideoStat"]
            dfs["Creator"] = dfs["Creator"].loc[keep_mask.values].reset_index(drop=True) if not dfs["Creator"].empty else dfs["Creator"]
            dfs["Category"] = dfs["Category"].loc[keep_mask.values].reset_index(drop=True) if not dfs["Category"].empty else dfs["Category"]
        else:
            duplicates_dropped = 0

        # 5. 类型转换
        dfs = self._convert_types(dfs)

        # 6. 异常值检测
        stat_df = dfs["VideoStat"]
        outliers_flagged = 0
        if not stat_df.empty:
            stat_before = len(stat_df)
            valid = (
                (stat_df["view"] >= 0) & (stat_df["like"] >= 0) &
                (stat_df["coin"] >= 0) & (stat_df["favorite"] >= 0) &
                (stat_df["share"] >= 0) & (stat_df["reply"] >= 0) &
                (stat_df["danmaku"] >= 0)
            )
            dfs["VideoStat"] = stat_df[valid].reset_index(drop=True)
            if not valid.all():
                dfs["Video"] = dfs["Video"].loc[valid.values].reset_index(drop=True)
                dfs["Creator"] = dfs["Creator"].loc[valid.values].reset_index(drop=True)
                dfs["Category"] = dfs["Category"].loc[valid.values].reset_index(drop=True)
            outliers_flagged = stat_before - len(dfs["VideoStat"])

        # 7. 写出 Parquet
        self._processed_dir.mkdir(parents=True, exist_ok=True)
        for f in self._processed_dir.glob("*.parquet"):
            f.unlink()
        for table_name, df in dfs.items():
            if not df.empty:
                df.to_parquet(self._processed_dir / f"{table_name}.parquet", index=False)

        total_videos = len(dfs["Video"])
        total_weeks = len(files)
        duration = time.monotonic() - start_time
        return CleanReport(
            total_weeks=total_weeks, total_videos=total_videos,
            duplicates_dropped=duplicates_dropped, missing_filled=missing_filled,
            outliers_flagged=outliers_flagged, duration_seconds=round(duration, 2),
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
            "Weekly": ["start_time", "end_time"], "Video": ["aid", "duration", "cid", "pubdate"],
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
        week_map = []
        for _, row in df.iterrows():
            pd_date = row["pubdate"]
            matched = None
            for _, wrow in weekly.iterrows():
                st = wrow.get("start_time", 0) or 0
                et = wrow.get("end_time", 0) or 0
                if st <= pd_date <= et:
                    matched = wrow["number"]
                    break
            week_map.append(matched if matched is not None else 1)
        df["week_number"] = week_map

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
        """从 processed/ Stat 读取 → StandardScaler → KMeans(k=3) → PCA(2D) → ClusterReport。"""
        start_time = time.monotonic()
        stat = pd.read_parquet(self._processed_dir / "VideoStat.parquet")

        # 特征选取
        features = ["view", "like", "coin", "favorite"]
        X = stat[features].copy()

        # 样本不足以聚类时返回空报告
        if len(X) < 3:
            duration = time.monotonic() - start_time
            return ClusterReport(
                clusters=ClusterResult(k=3, clusters=[], silhouette_score=0.0, feature_importance={}),
                scatter_data={"labels": [], "x": [], "y": []},
                duration_seconds=round(duration, 2),
            )

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
        stat["interaction"] = stat["like"] + stat["coin"] + stat["favorite"]
        stat["interaction_rate"] = stat["interaction"] / stat["view"].replace(0, 1)
        stat["label"] = labels

        # 先计算每个 cluster 的 avg_view，用于按播放量排名打标签
        label_view_rank = {}
        for label_idx in range(3):
            mask = stat["label"] == label_idx
            label_view_rank[label_idx] = float(stat.loc[mask, "view"].mean())

        # 按 avg_view 降序排名：最高 → "爆款视频"，其次 → "普通热门"，最低 → "潜力视频"
        sorted_labels = sorted(label_view_rank, key=label_view_rank.get, reverse=True)
        tag_map = {sorted_labels[0]: "爆款视频", sorted_labels[1]: "普通热门", sorted_labels[2]: "潜力视频"}

        clusters = []
        for label_idx in range(3):
            mask = stat["label"] == label_idx
            cluster_data = stat[mask]
            cluster_X = X[mask]
            centroid = {f: round(float(cluster_X[f].mean()), 2) for f in features}

            avg_view = float(cluster_data["view"].mean())
            avg_like = float(cluster_data["like"].mean())
            avg_coin = float(cluster_data["coin"].mean())
            avg_favorite = float(cluster_data["favorite"].mean())

            tag = tag_map[label_idx]
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

    # ── prediction ───────────────────────────────────────────

    def prediction(self) -> PredictionReport:
        """从 processed/ Parquet → 周聚合序列 → LinearRegression → PredictionReport。"""
        start_time = time.monotonic()
        video = pd.read_parquet(self._processed_dir / "Video.parquet")
        stat = pd.read_parquet(self._processed_dir / "VideoStat.parquet")
        weekly = pd.read_parquet(self._processed_dir / "Weekly.parquet")

        # 1. Merge Video + VideoStat on aid
        merged = video.merge(stat, on="aid", how="inner")

        # 2. 匹配每期视频所属周次（pubdate ∈ [start_time, end_time]）
        week_map = []
        for _, row in merged.iterrows():
            pd_date = row["pubdate"]
            matched = None
            for _, wrow in weekly.iterrows():
                st = wrow.get("start_time", 0) or 0
                et = wrow.get("end_time", 0) or 0
                if st <= pd_date <= et:
                    matched = wrow["number"]
                    break
            week_map.append(matched if matched is not None else 1)
        merged["week_number"] = week_map

        # 3. Aggregate by week
        weekly_agg = merged.groupby("week_number").agg(
            avg_view=("view", "mean"),
            avg_like=("like", "mean"),
            avg_coin=("coin", "mean"),
            avg_favorite=("favorite", "mean"),
            video_count=("aid", "count"),
        ).reset_index().sort_values("week_number")

        def _predict(target: str) -> PredictionResult:
            df = weekly_agg[weekly_agg["week_number"] > 0].copy()
            if len(df) < 3:
                return PredictionResult(
                    model_type="linear_regression", target=target, r2_score=0.0, mae=0.0,
                    coefficients={}, intercept=0.0, fitted=[], forecast=[],
                )

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

            last_week = int(df["week_number"].max())
            avg_vc = int(df["video_count"].mean())
            future_X = np.array([[last_week + i, avg_vc] for i in range(1, 5)])
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
