import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bilianalysis.crawler import list_series, get_weekly_videos, BASE_URL
from bilianalysis.crawler.signer import WbiSigner
from bilianalysis.utils.fetch import HttpError


SERIES_LIST_RESPONSE = {
    "code": 0,
    "message": "0",
    "data": {
        "list": [
            {"number": 1, "subject": "第一期", "name": "每周必看 01"},
            {"number": 2, "subject": "第二期", "name": "每周必看 02"},
            {"number": 3, "subject": "第三期", "name": "每周必看 03"},
        ]
    }
}

SERIES_ONE_RESPONSE = {
    "code": 0,
    "message": "0",
    "data": {
        "config": {"number": 1, "subject": "测试期", "name": "每周必看 01"},
        "list": [
            {"aid": 123, "title": "测试视频", "owner": {"mid": 1, "name": "UP主"},
             "stat": {"view": 1000, "like": 50}}
        ]
    }
}


@pytest.fixture
def signer():
    """创建一个测试用 WbiSigner（固定 mixin_key）。"""
    return WbiSigner("test_key_32_bytes_0123456789")


class TestListSeries:
    @pytest.mark.asyncio
    async def test_returns_series_list(self, signer):
        with patch("bilianalysis.crawler.api.get", AsyncMock(return_value=SERIES_LIST_RESPONSE)):
            result = await list_series(MagicMock(), signer)
        assert len(result) == 3
        assert result[0]["number"] == 1
        assert result[-1]["number"] == 3

    @pytest.mark.asyncio
    async def test_calls_correct_url(self, signer):
        mock_get = AsyncMock(return_value=SERIES_LIST_RESPONSE)
        with patch("bilianalysis.crawler.api.get", mock_get):
            await list_series(MagicMock(), signer)
        mock_get.assert_called_once()
        call_args = mock_get.call_args[0]
        url = call_args[1]
        assert url.startswith(f"{BASE_URL}/list?")
        assert "web_location=333.934" in url
        assert "w_rid=" in url
        assert "wts=" in url


class TestGetWeeklyVideos:
    @pytest.mark.asyncio
    async def test_returns_data_dict(self, signer):
        with patch("bilianalysis.crawler.api.get", AsyncMock(return_value=SERIES_ONE_RESPONSE)):
            result = await get_weekly_videos(MagicMock(), 1, signer)
        assert result["config"]["number"] == 1
        assert len(result["list"]) == 1
        assert result["list"][0]["title"] == "测试视频"

    @pytest.mark.asyncio
    async def test_url_includes_number(self, signer):
        mock_get = AsyncMock(return_value=SERIES_ONE_RESPONSE)
        with patch("bilianalysis.crawler.api.get", mock_get):
            await get_weekly_videos(MagicMock(), 42, signer)
        call_args = mock_get.call_args[0]
        url = call_args[1]
        assert "number=42" in url
        assert url.startswith(f"{BASE_URL}/one?")

    @pytest.mark.asyncio
    async def test_propagates_http_error(self, signer):
        err = HttpError(502, "bad gateway")
        mock_get = AsyncMock(side_effect=err)
        with patch("bilianalysis.crawler.api.get", mock_get):
            with pytest.raises(HttpError) as exc_info:
                await get_weekly_videos(MagicMock(), 1, signer)
            assert exc_info.value.status == 502
