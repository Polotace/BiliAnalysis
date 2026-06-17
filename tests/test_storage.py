import json
import pytest
from bilianalysis.crawler import (
    save_week, load_progress, save_progress, get_pending_weeks,
    ProgressFile,
)


SAMPLE_WEEK_DATA = {
    "number": 1,
    "config": {"subject": "测试", "name": "每周必看 01"},
    "videos": [{"aid": 123, "title": "测试视频"}]
}


class TestSaveWeek:
    @pytest.mark.asyncio
    async def test_saves_json_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)
        await save_week(1, SAMPLE_WEEK_DATA)

        filepath = tmp_path / "week_001.json"
        assert filepath.exists()
        data = json.loads(filepath.read_text(encoding="utf-8"))
        assert data["number"] == 1
        assert data["videos"][0]["title"] == "测试视频"

    @pytest.mark.asyncio
    async def test_creates_directory_if_missing(self, tmp_path, monkeypatch):
        data_dir = tmp_path / "raw"
        monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", data_dir)
        await save_week(5, SAMPLE_WEEK_DATA)

        assert (data_dir / "week_005.json").exists()

    @pytest.mark.asyncio
    async def test_pads_number_to_three_digits(self, tmp_path, monkeypatch):
        monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)
        await save_week(42, SAMPLE_WEEK_DATA)

        assert (tmp_path / "week_042.json").exists()
        assert not (tmp_path / "week_42.json").exists()


class TestProgress:
    @pytest.mark.asyncio
    async def test_load_progress_returns_default_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)
        progress = await load_progress()
        assert progress == ProgressFile()

    @pytest.mark.asyncio
    async def test_save_and_load_progress(self, tmp_path, monkeypatch):
        monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)
        state = ProgressFile(
            crawled=[1, 2, 3],
            failed={15: "timeout"},
        )
        await save_progress(state)
        loaded = await load_progress()
        assert loaded.crawled == [1, 2, 3]
        assert loaded.failed == {15: "timeout"}


class TestGetPendingWeeks:
    @pytest.mark.asyncio
    async def test_all_pending_when_no_progress(self, tmp_path, monkeypatch):
        monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)
        retry, pending = await get_pending_weeks(5)
        assert pending == [1, 2, 3, 4, 5]
        assert retry == []

    @pytest.mark.asyncio
    async def test_excludes_crawled(self, tmp_path, monkeypatch):
        monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)
        await save_progress(ProgressFile(crawled=[1, 2]))
        retry, pending = await get_pending_weeks(5)
        assert pending == [3, 4, 5]
        assert retry == []

    @pytest.mark.asyncio
    async def test_returns_failed_as_retry(self, tmp_path, monkeypatch):
        monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)
        await save_progress(ProgressFile(crawled=[1, 2], failed={3: "timeout"}))
        retry, pending = await get_pending_weeks(5)
        assert pending == [4, 5]
        assert retry == [3]

    @pytest.mark.asyncio
    async def test_excludes_beyond_latest(self, tmp_path, monkeypatch):
        monkeypatch.setattr("bilianalysis.crawler.storage.DATA_DIR", tmp_path)
        retry, pending = await get_pending_weeks(3)
        assert pending == [1, 2, 3]
