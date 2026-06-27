"""Pandas 分析引擎实现。"""
import json
import time
from pathlib import Path
from datetime import datetime

from bilianalysis.utils.async_utils import safe_run_async

import pandas as pd


from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error, silhouette_score
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.model_selection import KFold, cross_val_score
from sklearn.ensemble import AdaBoostRegressor, RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
import numpy as np

import jieba
import jieba.analyse

from bilianalysis.config.model import DataSection
from bilianalysis.engine.base import (
    AnalysisEngine, CleanReport, StatReport, ClusterReport, PredictionReport,
    OverallStats, CategoryStats, CreatorStats, WeeklyTrend,
    ClusterGroup, ClusterResult, PredictionResult,
    SingleModelResult, FeatureImportanceItem, ModelComparisonReport,
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

    # ── Lazy clean_data ──────────────────────────────────────

    def _ensure_processed(self) -> None:
        """Ensure processed Parquet data is readable; auto-trigger ``clean_data`` if not.

        Tries to read ``Weekly.parquet`` — when that fails with any exception,
        runs the full clean_data pipeline and then verifies the data became readable.

        Safe to call repeatedly: a successful read returns immediately.
        """
        weekly_path = self._processed_dir / "Weekly.parquet"
        try:
            pd.read_parquet(weekly_path)
            return
        except Exception:
            pass

        safe_run_async(self.clean_data())

        # Verify
        try:
            pd.read_parquet(weekly_path)
        except Exception as exc:
            raise RuntimeError(
                f"clean_data completed but {weekly_path} still unreadable"
            ) from exc

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
            videos = rec.get("videos", [])
            if not cfg and not videos:
                continue  # skip empty weeks
            weekly_rows.append({
                "number": rec.get("number"),
                "subject": cfg.get("subject"),
                "name": cfg.get("name"),
                "start_time": cfg.get("stime"),
                "end_time": cfg.get("etime"),
            })

            for v in videos:
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
                    "tid_v2": rcmd.get("tid_v2") if isinstance(rcmd, dict) else None,
                    "tname_v2": rcmd.get("tname_v2") if isinstance(rcmd, dict) else None,
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
        self._ensure_processed()
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
        self._ensure_processed()
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
        self._ensure_processed()
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

        from sklearn.model_selection import train_test_split

        def _predict(target: str) -> PredictionResult:
            df = weekly_agg[weekly_agg["week_number"] > 0].copy()
            if len(df) < 6:
                return PredictionResult(
                    model_type="linear_regression", target=target,
                    r2_score=0.0, mae=0.0, rmse=0.0,
                    train_size=0, test_size=0,
                    coefficients={}, intercept=0.0, fitted=[], forecast=[],
                )

            feature_cols = ["week_number", "video_count"]
            X = df[feature_cols].values
            y = df[f"avg_{target}"].values

            # Train/test split (80/20)
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42)
            n_train, n_test = len(X_train), len(X_test)

            model = LinearRegression()
            model.fit(X_train, y_train)

            # Train metrics
            y_train_pred = model.predict(X_train)
            r2 = round(float(r2_score(y_train, y_train_pred)), 4)
            mae = round(float(mean_absolute_error(y_train, y_train_pred)), 2)
            rmse = round(float(np.sqrt(np.mean((y_train - y_train_pred) ** 2))), 2)

            # Test metrics
            y_test_pred = model.predict(X_test)
            test_r2 = round(float(r2_score(y_test, y_test_pred)), 4)
            test_rmse = round(float(np.sqrt(np.mean((y_test - y_test_pred) ** 2))), 2)

            coef = {feature_cols[i]: round(float(model.coef_[i]), 4) for i in range(len(feature_cols))}
            intercept = round(float(model.intercept_), 2)

            # Fitted values (retrain on full data for forecast)
            model.fit(X, y)
            y_pred = model.predict(X)
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
                r2_score=r2, mae=mae, rmse=rmse,
                test_r2_score=test_r2, test_rmse=test_rmse,
                train_size=n_train, test_size=n_test,
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

    # ── keywords ────────────────────────────────────────────

    def keywords(self):
        """Extract keywords from local Video.parquet via jieba TF-IDF."""
        from bilianalysis.nlp.keywords import build_keywords_report
        return build_keywords_report(self._processed_dir)

    # ── model_comparison ───────────────────────────────────────

    def model_comparison(self) -> ModelComparisonReport:
        """加载 raw JSON → 特征工程 → 训练 5 个回归模型 (5-fold CV) → 模型对比报告。

        此为视频级预测 (log(view) ~ 127 features)，与 prediction() 的周级预测不同。
        """
        start_time = time.monotonic()

        # 1. 全量加载 raw JSON（需要 extended 字段：width/height/dynamic/rcmd_reason 等）
        files = sorted(self._raw_dir.glob("week_*.json"),
                       key=lambda p: int(p.stem.split("_")[1]))
        rows = []
        for fp in files:
            data = json.loads(fp.read_text(encoding="utf-8"))
            cfg = data.get("config", {})
            for v in data.get("videos", []):
                stat = v.get("stat", {}) or {}
                owner = v.get("owner", {}) or {}
                dim = v.get("dimension", {}) or {}
                rights = v.get("rights", {}) or {}
                rows.append({
                    "aid": v.get("aid"),
                    "view": stat.get("view"),
                    "like": stat.get("like"),
                    "coin": stat.get("coin"),
                    "favorite": stat.get("favorite"),
                    "share": stat.get("share"),
                    "danmaku": stat.get("danmaku"),
                    "reply": stat.get("reply"),
                    "tid": v.get("tid"),
                    "tidv2": v.get("tidv2"),
                    "tname": v.get("tname"),
                    "duration": v.get("duration"),
                    "pubdate": v.get("pubdate"),
                    "title": v.get("title", ""),
                    "desc": v.get("desc", ""),
                    "dynamic": v.get("dynamic", ""),
                    "rcmd_reason": v.get("rcmd_reason"),
                    "up_name": owner.get("name"),
                    "mid": owner.get("mid"),
                    "width": dim.get("width"),
                    "height": dim.get("height"),
                    "is_pay": int(bool((rights.get("pay") or 0))),
                    "week_stime": cfg.get("stime"),
                })
        df = pd.DataFrame(rows)

        # 2. 数据清洗
        df = df.dropna(subset=["view", "duration", "pubdate", "tid", "title", "up_name"])
        df = df[(df["view"] > 100) & (df["duration"] > 0)]
        v_q995 = df["view"].quantile(0.995)
        df = df[df["view"] <= v_q995]
        df = df.drop_duplicates(subset=["aid"], keep="last").reset_index(drop=True)

        # 3. 特征工程 (14 个派生特征)
        df["duration_log"] = np.log1p(df["duration"])
        df["view_log"] = np.log1p(df["view"])
        df["title_length"] = df["title"].str.len()
        df["desc_length"] = df["desc"].fillna("").str.len()
        df["has_dynamic"] = df["dynamic"].fillna("").astype(bool).astype(int)
        df["has_rcmd_reason"] = df["rcmd_reason"].fillna("").astype(bool).astype(int)
        df["rcmd_reason_length"] = df["rcmd_reason"].fillna("").str.len()
        df["publish_time"] = pd.to_datetime(df["pubdate"], unit="s")
        df["publish_hour"] = df["publish_time"].dt.hour
        df["publish_weekday"] = df["publish_time"].dt.weekday
        df["days_to_listing"] = (df["week_stime"] - df["pubdate"]) / 86400
        df["aspect_ratio"] = df["width"] / df["height"].replace(0, np.nan)
        df["is_verified"] = df["tidv2"].notna().astype(int)

        # 3.5 NLP 文本特征 — jieba TF-IDF 关键词二值编码
        # clean_title / jieba domain words / STOPWORDS 复用自 bilianalysis.nlp.keywords
        from bilianalysis.nlp.keywords import clean_title, STOPWORDS

        # 补充 ML 特征工程需要的常见虚词（NLP 模块的 STOPWORDS 偏通用）
        _ml_stopwords = STOPWORDS | set(
            "的 了 在 是 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 "
            "你 会 着 没有 看 好 自己 这 他 她 它 们 那 被 从 把 让 用 为 "
            "吗 呢 吧 啊 哦 呀 什么 怎么 如何 为什么 这个 那个 这些 那些 "
            "第 期 万 亿 个 次 元".split())

        def _extract_top_keywords(texts: list[str], topk: int = 30) -> list[str]:
            combined = " ".join(t for t in texts if t)
            if not combined.strip():
                return []
            tags = jieba.analyse.extract_tags(combined, topK=topk * 2, withWeight=True)
            return [w for w, _ in tags if w not in _ml_stopwords and len(w) >= 2][:topk]

        # 标题关键词
        title_series = df["title"].apply(clean_title)
        title_list = title_series.tolist()
        title_top_kw = _extract_top_keywords(title_list, topk=30)
        nlp_title_features = pd.DataFrame(index=df.index)
        for kw in title_top_kw:
            nlp_title_features[f"title_kw_{kw}"] = (
                title_series.str.contains(kw, na=False).astype(int))

        # 推荐理由关键词
        rcmd_series = df["rcmd_reason"].fillna("").apply(clean_title)
        rcmd_list = rcmd_series.tolist()
        rcmd_top_kw = _extract_top_keywords(rcmd_list, topk=15)
        nlp_rcmd_features = pd.DataFrame(index=df.index)
        for kw in rcmd_top_kw:
            nlp_rcmd_features[f"rcmd_kw_{kw}"] = (
                rcmd_series.str.contains(kw, na=False).astype(int))

        n_nlp = len(nlp_title_features.columns) + len(nlp_rcmd_features.columns)

        # 4. 构建特征矩阵 (元数据 + NLP)
        CATEGORICAL = ["tid", "publish_weekday"]
        NUMERICAL = [
            "duration_log", "title_length", "desc_length",
            "days_to_listing", "publish_hour",
            "has_dynamic", "has_rcmd_reason", "rcmd_reason_length",
            "aspect_ratio", "is_verified", "is_pay",
            "width", "height",
        ]
        feat_df = df[CATEGORICAL + NUMERICAL].copy()
        feat_df = pd.get_dummies(feat_df, columns=CATEGORICAL, drop_first=True)

        # 合并 NLP 关键词特征
        feat_df = feat_df.join(nlp_title_features)
        feat_df = feat_df.join(nlp_rcmd_features)

        feat_df = feat_df.replace([np.inf, -np.inf], np.nan).dropna()

        y = df.loc[feat_df.index, "view_log"].astype(float)
        X = feat_df.astype(float)

        n_samples = len(X)
        n_features = X.shape[1]

        # 5. 5-Fold CV 训练 6 个模型 + 贝叶斯优化
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        models_def: dict[str, object] = {
            "Linear Regression": LinearRegression(),
            "Decision Tree": DecisionTreeRegressor(max_depth=8, random_state=42),
            "Random Forest": RandomForestRegressor(
                n_estimators=200, max_depth=12, n_jobs=-1, random_state=42,
            ),
            "AdaBoost": AdaBoostRegressor(
                n_estimators=100, learning_rate=0.5, random_state=42,
            ),
        }
        # XGBoost 可选
        try:
            from xgboost import XGBRegressor
            models_def["XGBoost"] = XGBRegressor(
                n_estimators=300, max_depth=6, learning_rate=0.05,
                n_jobs=-1, random_state=42, tree_method="hist",
            )
        except ImportError:
            pass

        # LightGBM 可选
        try:
            from lightgbm import LGBMRegressor
            models_def["LightGBM"] = LGBMRegressor(
                n_estimators=300, max_depth=6, learning_rate=0.05,
                n_jobs=-1, random_state=42, verbose=-1,
            )
        except ImportError:
            pass

        model_results: list[SingleModelResult] = []
        best_model = ""
        best_r2 = -float("inf")
        best_predictor = None

        for name, model in models_def.items():
            t0 = time.monotonic()
            cv_mae = -cross_val_score(model, X, y, cv=kf,
                                       scoring="neg_mean_absolute_error", n_jobs=-1)
            cv_rmse = np.sqrt(-cross_val_score(model, X, y, cv=kf,
                                                scoring="neg_mean_squared_error", n_jobs=-1))
            cv_r2 = cross_val_score(model, X, y, cv=kf, scoring="r2", n_jobs=-1)
            model.fit(X, y)
            train_time = time.monotonic() - t0

            r2_mean = float(cv_r2.mean())
            model_results.append(SingleModelResult(
                model_name=name,
                r2_mean=round(r2_mean, 4),
                r2_std=round(float(cv_r2.std()), 4),
                mae_mean=round(float(cv_mae.mean()), 4),
                mae_std=round(float(cv_mae.std()), 4),
                rmse_mean=round(float(cv_rmse.mean()), 4),
                rmse_std=round(float(cv_rmse.std()), 4),
                train_time_seconds=round(train_time, 2),
            ))
            if r2_mean > best_r2:
                best_r2 = r2_mean
                best_model = name
                best_predictor = model

        # 5.5 贝叶斯优化 XGBoost 超参数
        bayesian_opt_result: dict | None = None
        try:
            from skopt import BayesSearchCV
            from xgboost import XGBRegressor as XGBR
            param_space: dict = {
                "max_depth": (3, 10),
                "learning_rate": (0.01, 0.3, "log-uniform"),
                "n_estimators": (100, 500),
                "subsample": (0.6, 1.0),
                "colsample_bytree": (0.6, 1.0),
                "min_child_weight": (1, 10),
            }
            bayes_opt = BayesSearchCV(
                XGBR(tree_method="hist", n_jobs=-1, random_state=42),
                param_space, cv=kf, scoring="r2", n_iter=30,
                random_state=42, n_jobs=-1,
            )
            t_bo = time.monotonic()
            bayes_opt.fit(X, y)
            bo_time = time.monotonic() - t_bo
            bo_xgb = bayes_opt.best_estimator_
            cv_mae_bo = -cross_val_score(bo_xgb, X, y, cv=kf,
                                          scoring="neg_mean_absolute_error", n_jobs=-1)
            cv_rmse_bo = np.sqrt(-cross_val_score(bo_xgb, X, y, cv=kf,
                                                   scoring="neg_mean_squared_error", n_jobs=-1))
            cv_r2_bo = cross_val_score(bo_xgb, X, y, cv=kf, scoring="r2", n_jobs=-1)

            bo_r2 = float(cv_r2_bo.mean())
            model_results.append(SingleModelResult(
                model_name="XGBoost (Bayesian)",
                r2_mean=round(bo_r2, 4),
                r2_std=round(float(cv_r2_bo.std()), 4),
                mae_mean=round(float(cv_mae_bo.mean()), 4),
                mae_std=round(float(cv_mae_bo.std()), 4),
                rmse_mean=round(float(cv_rmse_bo.mean()), 4),
                rmse_std=round(float(cv_rmse_bo.std()), 4),
                train_time_seconds=round(float(bo_time), 2),
            ))
            if bo_r2 > best_r2:
                best_r2 = bo_r2
                best_model = "XGBoost (Bayesian)"
                best_predictor = bo_xgb

            bayesian_opt_result = {
                "best_score": round(float(bayes_opt.best_score_), 4),
                "best_params": {str(k): v for k, v in bayes_opt.best_params_.items()},
            }
        except ImportError:
            pass

        # 6. 特征重要性 (Top 15，来自最优模型)
        importance_items: list[FeatureImportanceItem] = []
        if best_predictor is not None and hasattr(best_predictor, "feature_importances_"):
            imp_series = pd.Series(best_predictor.feature_importances_, index=X.columns)
            top15 = imp_series.nlargest(15)
            importance_items = [
                FeatureImportanceItem(feature=str(k), importance=round(float(v), 6))
                for k, v in top15.items()
            ]

        # 7. 预测 vs 实际数据 (所有样本，供前端散点图 + 残差直方图)
        y_pred = best_predictor.predict(X)
        predicted_vs_actual: list[dict] = [
            {
                "actual": round(float(y.iloc[i]), 4),
                "predicted": round(float(y_pred[i]), 4),
                "residual": round(float(y.iloc[i] - y_pred[i]), 4),
            }
            for i in range(len(y))
        ]

        duration = time.monotonic() - start_time
        return ModelComparisonReport(
            n_samples=n_samples, n_features=n_features,
            n_nlp_features=n_nlp,
            target="log(view)", models=model_results, best_model=best_model,
            feature_importance=importance_items,
            predicted_vs_actual=predicted_vs_actual,
            bayesian_opt=bayesian_opt_result,
            duration_seconds=round(duration, 2),
        )
