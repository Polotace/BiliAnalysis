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
