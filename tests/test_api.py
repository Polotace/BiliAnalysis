"""Integration tests for BiliAnalysis API."""
import pytest
from fastapi.testclient import TestClient

from bilianalysis.config.model import AppConfig
from api import create_app


@pytest.fixture
def client():
    config = AppConfig()
    app = create_app(config)
    return TestClient(app)


@pytest.fixture
def auth_client():
    """A TestClient with admin_api_key configured and X-API-Key header set."""
    config = AppConfig()
    app = create_app(config)
    client = TestClient(app)
    client.headers["X-API-Key"] = app.state.api_settings.admin_api_key
    return client


class TestHealthAndConfig:
    def test_config_get(self, client):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "crawler" in data
        assert "analysis" in data
        assert "data" in data
        assert "scheduler" in data

    def test_config_put_valid(self, auth_client):
        resp = auth_client.put("/api/config", json={
            "section": "crawler",
            "values": {"request_delay": 5.0},
            "persist": False,
        })
        assert resp.status_code == 200
        assert resp.json()["persisted"] is False

    def test_config_put_invalid_section(self, auth_client):
        resp = auth_client.put("/api/config", json={
            "section": "nonexistent",
            "values": {},
            "persist": False,
        })
        assert resp.status_code == 400

    def test_config_put_invalid_field(self, auth_client):
        resp = auth_client.put("/api/config", json={
            "section": "crawler",
            "values": {"nonexistent_field": 123},
            "persist": False,
        })
        assert resp.status_code == 400


class TestCrawlerRoutes:
    def test_get_crawler_status(self, client):
        resp = client.get("/api/crawler")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_weeks" in data
        assert "is_running" in data


class TestAnalysisRoutes:
    def test_get_analysis_overview(self, client):
        resp = client.get("/api/analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert "last_clean" in data

    def test_get_analysis_routes_exist(self, client):
        for path in ["/api/analysis/stats", "/api/analysis/clusters",
                      "/api/analysis/predictions"]:
            try:
                resp = client.get(path)
                # 500 (no data files) is acceptable — route is registered
                assert resp.status_code != 404, f"{path} returned 404"
            except FileNotFoundError:
                # Route exists but engine failed because data/processed/
                # is empty; the testclient re-raises the 500 exception.
                pass


class TestTasksRoutes:
    def test_list_tasks_empty(self, client):
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pipelines"] == []

    def test_list_tasks_with_pipelines(self):
        from bilianalysis.config.model import SchedulerConfig, PipelineConfig
        config = AppConfig()
        config.scheduler = SchedulerConfig(
            pipelines={
                "full": PipelineConfig(schedule="0 12 * * 6", steps=["crawl"]),
            }
        )
        app = create_app(config)
        client = TestClient(app)
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["pipelines"]) == 1
        assert data["pipelines"][0]["name"] == "full"


class TestTaskHistory:
    def test_history_nonexistent_pipeline(self, client):
        resp = client.get("/api/tasks/nonexistent/history")
        assert resp.status_code == 404


class TestErrorHandling:
    def test_404_on_unregistered_route(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404

    def test_app_error_response_format(self, auth_client):
        resp = auth_client.put("/api/config", json={
            "section": "nonexistent",
            "values": {},
        })
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data


class TestAdminAuth:
    def test_post_without_key_returns_401(self, client):
        """Any POST endpoint without X-API-Key returns 401."""
        resp = client.post("/api/tasks/nonexistent/run")
        assert resp.status_code == 401
        assert "Unauthorized" in resp.json()["detail"]

    def test_post_with_wrong_key_returns_401(self, auth_client):
        """Wrong key returns 401."""
        auth_client.headers["X-API-Key"] = "wrong-key-here"
        resp = auth_client.post("/api/tasks/nonexistent/run")
        assert resp.status_code == 401

    def test_get_endpoints_unaffected(self, client):
        """GET endpoints are not protected."""
        resp = client.get("/api/config")
        assert resp.status_code == 200
        resp = client.get("/api/crawler")
        assert resp.status_code == 200
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
