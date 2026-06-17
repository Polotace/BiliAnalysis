"""测试分析引擎模块。"""
import pytest
from bilianalysis.engine.base import (
    AnalysisEngine,
    CleanReport,
    OverallStats,
    CategoryStats,
    CreatorStats,
    WeeklyTrend,
    StatReport,
    ClusterGroup,
    ClusterResult,
    ClusterReport,
    PredictionResult,
    PredictionReport,
)


class TestCleanReport:
    def test_create_clean_report(self):
        report = CleanReport(
            total_weeks=50,
            total_videos=500,
            duplicates_dropped=3,
            missing_filled=10,
            outliers_flagged=2,
            duration_seconds=1.5,
        )
        assert report.total_weeks == 50
        assert report.duplicates_dropped == 3

    def test_clean_report_defaults(self):
        report = CleanReport(
            total_weeks=0, total_videos=0, duplicates_dropped=0,
            missing_filled=0, outliers_flagged=0, duration_seconds=0.0,
        )
        assert isinstance(report, CleanReport)


class TestStatReport:
    def test_full_report_structure(self):
        overall = OverallStats(
            total_videos=100, total_creators=20,
            avg_view=50000.0, avg_like=2000.0, avg_coin=500.0,
            avg_favorite=800.0, avg_share=100.0, avg_danmaku=300.0,
            avg_like_rate=0.04, avg_coin_rate=0.01, avg_favorite_rate=0.016,
        )
        categories = [CategoryStats(tname="动画", video_count=30, avg_view=60000.0, avg_like=2500.0, avg_interaction_rate=0.06)]
        creators = [CreatorStats(mid=123, name="测试UP", appearance_count=5, total_view=500000, total_like=20000, total_favorite=8000)]
        weeks = [WeeklyTrend(week_number=1, video_count=30, avg_view=50000.0, avg_like=2000.0, avg_interaction_rate=0.05)]

        report = StatReport(overall=overall, by_category=categories, by_creator=creators, by_week=weeks)
        assert report.overall.total_videos == 100
        assert len(report.by_category) == 1
        assert len(report.by_creator) == 1
        assert len(report.by_week) == 1


class TestClusterReport:
    def test_report_structure(self):
        clusters = ClusterResult(
            k=3,
            clusters=[
                ClusterGroup(label=0, tag="爆款视频", count=30,
                             centroid={"view": 100000.0, "like": 5000.0, "coin": 1000.0, "favorite": 2000.0},
                             avg_view=100000.0, avg_like=5000.0, avg_coin=1000.0, avg_favorite=2000.0,
                             sample_ids=[1, 2, 3]),
            ],
            silhouette_score=0.65,
            feature_importance={"view": 0.4, "like": 0.3, "coin": 0.2, "favorite": 0.1},
        )
        report = ClusterReport(
            clusters=clusters,
            scatter_data={"labels": [0, 1, 2], "x": [1.0, -1.0, 0.5], "y": [0.5, 1.0, -1.0]},
            duration_seconds=2.0,
        )
        assert report.clusters.k == 3
        assert len(report.clusters.clusters) == 1


class TestPredictionReport:
    def test_report_structure(self):
        view_pred = PredictionResult(
            model_type="linear_regression", target="view", r2_score=0.85, mae=5000.0,
            coefficients={"week_number": 100.0}, intercept=40000.0,
            fitted=[{"week_number": 1, "actual": 50000, "predicted": 49000}],
            forecast=[{"week_number": 51, "predicted": 55000}],
        )
        like_pred = PredictionResult(
            model_type="linear_regression", target="like", r2_score=0.75, mae=200.0,
            coefficients={"week_number": 5.0}, intercept=1800.0,
            fitted=[{"week_number": 1, "actual": 2000, "predicted": 1950}],
            forecast=[{"week_number": 51, "predicted": 2200}],
        )
        report = PredictionReport(view_predict=view_pred, like_predict=like_pred, duration_seconds=3.0)
        assert report.view_predict.r2_score == 0.85
        assert report.like_predict.target == "like"
        assert len(report.view_predict.forecast) == 1


class TestAnalysisEngineABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            AnalysisEngine()


import json
import pandas as pd
from pathlib import Path
from bilianalysis.engine.pandas_engine import PandasEngine
from bilianalysis.config import DataSection


# 模拟 Bilibili API 返回的 raw JSON 结构
def _make_week_json(number: int, videos: list[dict]) -> dict:
    return {
        "number": number,
        "config": {"number": number, "subject": f"第{number}期", "name": f"每周必看 {number:02d}",
                   "start_time": 1600000000, "end_time": 1600600000},
        "videos": videos,
    }


def _make_video(aid: int, view: int = 10000, like: int = 500) -> dict:
    return {
        "aid": aid, "bvid": f"BV{aid:010d}", "title": f"视频{aid}", "desc": "描述",
        "duration": 120, "pubdate": 1600000000, "cid": aid * 10, "pic": f"https://img/{aid}.jpg",
        "owner": {"mid": aid + 1000, "name": f"UP{aid}", "face": f"https://face/{aid}.jpg"},
        "stat": {"aid": aid, "view": view, "like": like, "coin": 100, "favorite": 200, "share": 30, "reply": 50, "danmaku": 60},
        "tid": 1, "tname": "动画",
    }


class TestPandasEngineCleanData:
    @pytest.mark.asyncio
    async def test_clean_data_basic(self, tmp_path, monkeypatch):
        """基本清洗流程：2 个 week JSON → 5 张 Parquet → CleanReport。"""
        raw_dir = tmp_path / "raw"
        processed_dir = tmp_path / "processed"
        raw_dir.mkdir()

        # 写入 2 个 week JSON（batch_size=5，一批处理）
        for n in [1, 2]:
            data = _make_week_json(n, [_make_video(n * 100 + i) for i in range(3)])
            (raw_dir / f"week_{n:03d}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf, batch_size=5)
        report = await engine.clean_data()

        assert report.total_weeks == 2
        assert report.total_videos == 6
        assert report.duplicates_dropped == 0

        # 验证 5 个 Parquet 文件存在
        for table in ["Weekly", "Video", "Creator", "Category", "VideoStat"]:
            path = processed_dir / f"{table}.parquet"
            assert path.exists(), f"{table}.parquet should exist"
            df = pd.read_parquet(path)
            assert len(df) > 0, f"{table} should have rows"

    @pytest.mark.asyncio
    async def test_clean_data_sliding_window(self, tmp_path, monkeypatch):
        """3 个 week，batch_size=2，验证滑动窗口分两批处理。"""
        raw_dir = tmp_path / "raw"
        processed_dir = tmp_path / "processed"
        raw_dir.mkdir()

        for n in [1, 2, 3]:
            data = _make_week_json(n, [_make_video(n * 100)])
            (raw_dir / f"week_{n:03d}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf, batch_size=2)
        report = await engine.clean_data()

        assert report.total_weeks == 3
        assert report.total_videos == 3
        df = pd.read_parquet(processed_dir / "Video.parquet")
        assert len(df) == 3

    @pytest.mark.asyncio
    async def test_clean_data_missing_values(self, tmp_path, monkeypatch):
        """缺失值：数值列填充为 0，文本列填充为 ""。"""
        raw_dir = tmp_path / "raw"
        processed_dir = tmp_path / "processed"
        raw_dir.mkdir()

        # video 缺少 title 和 stat.like
        video = _make_video(1)
        del video["title"]
        del video["stat"]["like"]
        data = _make_week_json(1, [video])
        (raw_dir / "week_001.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf, batch_size=10)
        report = await engine.clean_data()

        assert report.missing_filled > 0
        df_video = pd.read_parquet(processed_dir / "Video.parquet")
        assert df_video["title"].iloc[0] == ""
        df_stat = pd.read_parquet(processed_dir / "VideoStat.parquet")
        assert df_stat["like"].iloc[0] == 0

    @pytest.mark.asyncio
    async def test_clean_data_deduplication(self, tmp_path, monkeypatch):
        """跨批次 aid 去重：相同 aid 保留首次出现。"""
        raw_dir = tmp_path / "raw"
        processed_dir = tmp_path / "processed"
        raw_dir.mkdir()

        # week 1 有 aid=100，week 2 也有 aid=100
        data1 = _make_week_json(1, [_make_video(100)])
        data2 = _make_week_json(2, [_make_video(100), _make_video(101)])
        (raw_dir / "week_001.json").write_text(json.dumps(data1, ensure_ascii=False), encoding="utf-8")
        (raw_dir / "week_002.json").write_text(json.dumps(data2, ensure_ascii=False), encoding="utf-8")

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf, batch_size=2)
        report = await engine.clean_data()

        assert report.duplicates_dropped == 1
        df_video = pd.read_parquet(processed_dir / "Video.parquet")
        assert len(df_video) == 2  # 100, 101

    @pytest.mark.asyncio
    async def test_clean_data_outliers(self, tmp_path, monkeypatch):
        """异常值检测：view < 0 视为异常。"""
        raw_dir = tmp_path / "raw"
        processed_dir = tmp_path / "processed"
        raw_dir.mkdir()

        video = _make_video(1, view=-100)
        data = _make_week_json(1, [video])
        (raw_dir / "week_001.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf, batch_size=10)
        report = await engine.clean_data()

        assert report.outliers_flagged >= 1

    @pytest.mark.asyncio
    async def test_clean_data_type_conversion(self, tmp_path, monkeypatch):
        """类型转换：验证各列 dtype 正确。"""
        raw_dir = tmp_path / "raw"
        processed_dir = tmp_path / "processed"
        raw_dir.mkdir()

        data = _make_week_json(1, [_make_video(1)])
        (raw_dir / "week_001.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf, batch_size=10)
        await engine.clean_data()

        df_video = pd.read_parquet(processed_dir / "Video.parquet")
        assert pd.api.types.is_integer_dtype(df_video["aid"])
        assert pd.api.types.is_integer_dtype(df_video["duration"])

        df_stat = pd.read_parquet(processed_dir / "VideoStat.parquet")
        assert pd.api.types.is_float_dtype(df_stat["view"])
        assert pd.api.types.is_float_dtype(df_stat["like"])


class TestPandasEngineStatistics:
    def _create_parquet_files(self, processed_dir: Path):
        """在 processed_dir 下创建 5 张测试 Parquet。"""
        processed_dir.mkdir(parents=True, exist_ok=True)

        pd.DataFrame({
            "number": [1, 2], "subject": ["第1期", "第2期"],
            "name": ["每周必看 01", "每周必看 02"],
            "start_time": [1600000000.0, 1600600000.0],
            "end_time": [1600300000.0, 1600900000.0],
        }).to_parquet(processed_dir / "Weekly.parquet", index=False)

        pd.DataFrame({
            "aid": [100, 101, 200], "bvid": ["BV001", "BV002", "BV003"],
            "title": ["v1", "v2", "v3"], "desc": ["", "", ""],
            "duration": [120, 180, 150], "pubdate": [1600000000.0, 1600000000.0, 1600600000.0],
            "cid": [10, 11, 20], "pic": ["", "", ""],
        }).to_parquet(processed_dir / "Video.parquet", index=False)

        pd.DataFrame({
            "mid": [1100, 1101, 1200], "name": ["UP1", "UP2", "UP3"],
            "face": ["", "", ""],
        }).to_parquet(processed_dir / "Creator.parquet", index=False)

        pd.DataFrame({
            "tid": [1, 1, 2], "tname": ["动画", "动画", "游戏"],
            "tid_v2": [0, 0, 0], "tname_v2": ["", "", ""],
        }).to_parquet(processed_dir / "Category.parquet", index=False)

        pd.DataFrame({
            "aid": [100, 101, 200],
            "view": [10000.0, 20000.0, 30000.0],
            "like": [500.0, 1000.0, 1500.0],
            "coin": [100.0, 200.0, 300.0],
            "favorite": [200.0, 400.0, 600.0],
            "share": [30.0, 50.0, 70.0],
            "reply": [50.0, 100.0, 150.0],
            "danmaku": [60.0, 120.0, 180.0],
        }).to_parquet(processed_dir / "VideoStat.parquet", index=False)

    def test_statistics_overall(self, tmp_path):
        """验证 overall 统计值的正确性。"""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        processed_dir = tmp_path / "processed"
        self._create_parquet_files(processed_dir)

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = engine.statistics()

        assert report.overall.total_videos == 3
        assert report.overall.total_creators == 3
        assert report.overall.avg_view == 20000.0
        assert report.overall.avg_like == 1000.0
        assert report.overall.avg_coin == 200.0
        assert report.overall.avg_favorite == 400.0
        assert report.overall.avg_share == 50.0
        assert report.overall.avg_danmaku == 120.0

    def test_statistics_by_category(self, tmp_path):
        """验证分区统计。"""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        processed_dir = tmp_path / "processed"
        self._create_parquet_files(processed_dir)

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = engine.statistics()

        assert len(report.by_category) == 2  # 动画, 游戏
        tnames = [c.tname for c in report.by_category]
        assert "动画" in tnames
        assert "游戏" in tnames

    def test_statistics_by_creator_top10(self, tmp_path):
        """验证 UP主 TOP10 按出现次数排序。"""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        processed_dir = tmp_path / "processed"
        self._create_parquet_files(processed_dir)

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = engine.statistics()

        assert len(report.by_creator) <= 10
        assert len(report.by_creator) == 3

    def test_statistics_by_week(self, tmp_path):
        """验证按周趋势（2 周数据）。"""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        processed_dir = tmp_path / "processed"
        self._create_parquet_files(processed_dir)

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = engine.statistics()

        assert len(report.by_week) == 2
        assert report.by_week[0].week_number == 1
        assert report.by_week[0].video_count == 2  # aid 100, 101 (pubdate in week 1 range)
        assert report.by_week[1].week_number == 2
        assert report.by_week[1].video_count == 1  # aid 200 (pubdate in week 2 range)


class TestPandasEngineClustering:
    def _create_clustering_data(self, processed_dir: Path):
        """创建适合聚类的测试数据（3 种视频类型模拟）。"""
        processed_dir.mkdir(parents=True, exist_ok=True)

        # 3 类视频: 爆款(高播放高互动), 普通(中), 潜力(低播放高互动率)
        vids = []
        cats = []
        for i in range(30):
            vids.append({
                "aid": i + 1, "bvid": f"BV{i}", "title": f"v{i}", "desc": "",
                "duration": 120, "pubdate": 1600000000.0, "cid": i * 10, "pic": "",
            })
            cats.append({"tid": 1, "tname": "动画", "tid_v2": 0, "tname_v2": ""})

        pd.DataFrame(vids).to_parquet(processed_dir / "Video.parquet", index=False)
        pd.DataFrame(cats).to_parquet(processed_dir / "Category.parquet", index=False)

        pd.DataFrame({
            "mid": list(range(1001, 1031)), "name": [f"UP{i}" for i in range(1, 31)],
            "face": [""] * 30,
        }).to_parquet(processed_dir / "Creator.parquet", index=False)

        # 生成 3 聚类: 0-9 爆款(高播放高互动率), 10-19 普通(中), 20-29 潜力(低播放)
        import numpy as np
        np.random.seed(42)
        aids = list(range(1, 31))
        views, likes, coins, favorites = [], [], [], []
        for i in range(30):
            if i < 10:
                views.append(np.random.randint(80000, 120000))
                likes.append(np.random.randint(20000, 30000))
                coins.append(np.random.randint(5000, 8000))
                favorites.append(np.random.randint(8000, 12000))
            elif i < 20:
                views.append(np.random.randint(40000, 70000))
                likes.append(np.random.randint(1500, 3000))
                coins.append(np.random.randint(400, 700))
                favorites.append(np.random.randint(800, 1500))
            else:
                views.append(np.random.randint(8000, 25000))
                likes.append(np.random.randint(200, 500))
                coins.append(np.random.randint(50, 100))
                favorites.append(np.random.randint(100, 200))

        pd.DataFrame({
            "aid": aids, "view": [float(v) for v in views],
            "like": [float(l) for l in likes],
            "coin": [float(c) for c in coins],
            "favorite": [float(f) for f in favorites],
            "share": [10.0] * 30, "reply": [20.0] * 30, "danmaku": [30.0] * 30,
        }).to_parquet(processed_dir / "VideoStat.parquet", index=False)

        pd.DataFrame({
            "number": [1], "subject": ["第1期"], "name": ["每周必看 01"],
            "start_time": [1600000000.0], "end_time": [1600600000.0],
        }).to_parquet(processed_dir / "Weekly.parquet", index=False)

    def test_clustering_structure(self, tmp_path):
        """验证聚类报告基本结构。"""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        processed_dir = tmp_path / "processed"
        self._create_clustering_data(processed_dir)

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = engine.clustering()

        assert report.clusters.k == 3
        assert len(report.clusters.clusters) == 3
        assert report.clusters.silhouette_score > 0
        assert "view" in report.clusters.feature_importance
        assert "like" in report.clusters.feature_importance

    def test_clustering_scatter_data(self, tmp_path):
        """验证散点图数据格式正确。"""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        processed_dir = tmp_path / "processed"
        self._create_clustering_data(processed_dir)

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = engine.clustering()

        scatter = report.scatter_data
        assert "labels" in scatter
        assert "x" in scatter
        assert "y" in scatter
        assert len(scatter["labels"]) == 30
        assert len(scatter["x"]) == 30
        assert len(scatter["y"]) == 30

    def test_clustering_tags_present(self, tmp_path):
        """验证三个聚类都有标签。"""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        processed_dir = tmp_path / "processed"
        self._create_clustering_data(processed_dir)

        data_conf = DataSection(raw_dir=str(raw_dir), processed_dir=str(processed_dir))
        engine = PandasEngine(data_conf)
        report = engine.clustering()

        tags = {c.tag for c in report.clusters.clusters}
        assert "爆款视频" in tags
        assert "普通热门" in tags
        assert "潜力视频" in tags
