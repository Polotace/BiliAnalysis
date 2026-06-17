import pytest
from unittest.mock import AsyncMock, patch
from bilianalysis.crawler import CrawlReport, CrawlRunner as run
from bilianalysis.config import CrawlerSection
from bilianalysis.crawler import ProgressFile
from bilianalysis.utils.fetch import HttpError
from bilianalysis.crawler.signer import WbiSigner


SERIES_LIST = [
    {"number": 1, "subject": "第一期"},
    {"number": 2, "subject": "第二期"},
    {"number": 3, "subject": "第三期"},
]

WEEKLY_DATA = {
    "config": {"number": 1, "subject": "第一期"},
    "list": [{"aid": 123, "title": "test"}]
}


class TestCrawlerSection:
    def test_defaults(self):
        config = CrawlerSection()
        assert config.mode == "sequential"
        assert config.concurrency == 3
        assert config.request_delay == 2.5
        assert config.max_retries == 3
        assert config.retry_delay == 1.0

    def test_override(self):
        config = CrawlerSection(mode="concurrent", concurrency=5)
        assert config.mode == "concurrent"
        assert config.concurrency == 5


class TestCrawlReport:
    def test_create_report(self):
        report = CrawlReport(
            total=10,
            crawled=5,
            skipped=2,
            failed=3,
            failed_weeks={1: "timeout", 2: "404", 3: "500"},
            duration_seconds=12.5
        )
        assert report.total == 10
        assert report.failed == 3
        assert len(report.failed_weeks) == 3


class TestRun:
    @pytest.fixture
    def signer(self):
        return WbiSigner("test_key_32_bytes_0123456789")

    @pytest.mark.asyncio
    async def test_full_crawl_success(self, tmp_path, monkeypatch, signer):
        """集成测试：模拟完整爬取流程"""
        monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)

        mock_list_series = AsyncMock(return_value=SERIES_LIST)
        mock_get_weekly = AsyncMock(return_value=WEEKLY_DATA)
        mock_fetch_key = AsyncMock(return_value="test_key_32_bytes_0123456789")

        with patch("bilianalysis.crawler.pipeline.fetch_mixin_key", mock_fetch_key):
            with patch("bilianalysis.crawler.pipeline.list_series", mock_list_series):
                with patch("bilianalysis.crawler.pipeline.get_weekly_videos", mock_get_weekly):
                    config = CrawlerSection(mode="sequential", request_delay=0, retry_delay=0)
                    report = await run(config)

        assert report.total == 3
        assert report.crawled == 3
        assert report.skipped == 0
        assert report.failed == 0
        assert report.duration_seconds > 0

    @pytest.mark.asyncio
    async def test_skips_already_crawled(self, tmp_path, monkeypatch, signer):
        """已爬取的期号被跳过"""
        from bilianalysis.crawler import save_progress
        monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)
        await save_progress(ProgressFile(crawled=[1, 2]))

        mock_list_series = AsyncMock(return_value=SERIES_LIST)
        mock_get_weekly = AsyncMock(return_value=WEEKLY_DATA)
        mock_fetch_key = AsyncMock(return_value="test_key_32_bytes_0123456789")

        with patch("bilianalysis.crawler.pipeline.fetch_mixin_key", mock_fetch_key):
            with patch("bilianalysis.crawler.pipeline.list_series", mock_list_series):
                with patch("bilianalysis.crawler.pipeline.get_weekly_videos", mock_get_weekly):
                    config = CrawlerSection(mode="sequential", request_delay=0, retry_delay=0)
                    report = await run(config)

        assert report.skipped == 2
        assert report.crawled == 1  # only week 3
        assert mock_get_weekly.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_failed_then_skips(self, tmp_path, monkeypatch, signer):
        """失败期号重试一次，仍失败则保留"""
        from bilianalysis.crawler import save_progress, load_progress
        monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)
        await save_progress(ProgressFile(crawled=[1], failed={2: "prev timeout"}))

        async def mock_get_weekly(session, number, signer=None):
            if number == 2:
                raise HttpError(502, "bad gateway")
            return WEEKLY_DATA

        mock_fetch_key = AsyncMock(return_value="test_key_32_bytes_0123456789")

        with patch("bilianalysis.crawler.pipeline.fetch_mixin_key", mock_fetch_key):
            with patch("bilianalysis.crawler.pipeline.list_series", AsyncMock(return_value=SERIES_LIST)):
                with patch("bilianalysis.crawler.pipeline.get_weekly_videos", mock_get_weekly):
                    config = CrawlerSection(mode="sequential", request_delay=0, retry_delay=0)
                    report = await run(config)

        assert report.crawled == 1  # only week 3
        assert report.skipped == 1  # week 1 already done
        assert report.failed == 1   # week 2 failed again
        assert 2 in report.failed_weeks

        progress = await load_progress()
        assert 2 in progress.failed   # still in failed
        assert 3 in progress.crawled

    @pytest.mark.asyncio
    async def test_failed_retry_recovered(self, tmp_path, monkeypatch, signer):
        """失败期号重试成功，从 failed 移除"""
        from bilianalysis.crawler import save_progress, load_progress
        monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)
        await save_progress(ProgressFile(crawled=[1], failed={2: "prev timeout"}))

        async def mock_get_weekly(session, number, signer=None):
            return WEEKLY_DATA

        mock_fetch_key = AsyncMock(return_value="test_key_32_bytes_0123456789")

        with patch("bilianalysis.crawler.pipeline.fetch_mixin_key", mock_fetch_key):
            with patch("bilianalysis.crawler.pipeline.list_series", AsyncMock(return_value=SERIES_LIST)):
                with patch("bilianalysis.crawler.pipeline.get_weekly_videos", mock_get_weekly):
                    config = CrawlerSection(mode="sequential", request_delay=0, retry_delay=0)
                    report = await run(config)

        progress = await load_progress()
        assert 2 not in progress.failed
        assert 2 in progress.crawled

    @pytest.mark.asyncio
    async def test_concurrent_mode(self, tmp_path, monkeypatch, signer):
        """并发模式正常完成"""
        from bilianalysis.crawler import save_progress
        monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)
        await save_progress(ProgressFile())

        mock_fetch_key = AsyncMock(return_value="test_key_32_bytes_0123456789")

        with patch("bilianalysis.crawler.pipeline.fetch_mixin_key", mock_fetch_key):
            with patch("bilianalysis.crawler.pipeline.list_series", AsyncMock(return_value=SERIES_LIST)):
                with patch("bilianalysis.crawler.pipeline.get_weekly_videos", AsyncMock(return_value=WEEKLY_DATA)):
                    config = CrawlerSection(mode="concurrent", concurrency=3, retry_delay=0)
                    report = await run(config)

        assert report.crawled == 3
