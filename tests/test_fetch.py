import pytest
from unittest.mock import AsyncMock, MagicMock
import aiohttp
from bilianalysis.utils.fetch import HttpError, create_session, get, post, DEFAULT_TIMEOUT


class TestHttpError:
    def test_http_error_has_status_and_message(self):
        err = HttpError(404, "Not Found")
        assert err.status == 404
        assert err.message == "Not Found"
        assert str(err) == "[404] Not Found"

    def test_http_error_default_message(self):
        err = HttpError(500)
        assert err.status == 500
        assert "500" in str(err)


class TestCreateSession:
    @pytest.mark.asyncio
    async def test_returns_client_session(self):
        async with create_session() as session:
            assert isinstance(session, aiohttp.ClientSession)

    @pytest.mark.asyncio
    async def test_uses_default_timeout(self):
        async with create_session() as session:
            assert session.timeout == DEFAULT_TIMEOUT

    @pytest.mark.asyncio
    async def test_custom_timeout(self):
        custom = aiohttp.ClientTimeout(total=5, connect=1)
        async with create_session(timeout=custom) as session:
            assert session.timeout == custom


class TestGet:
    @pytest.mark.asyncio
    async def test_get_json_success(self):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.content_type = "application/json"
        mock_resp.json = AsyncMock(return_value={"code": 0, "data": [1, 2, 3]})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        result = await get(mock_session, "https://example.com/api")
        assert result == {"code": 0, "data": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_get_text_response(self):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.content_type = "text/html"
        mock_resp.text = AsyncMock(return_value="<html>ok</html>")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        result = await get(mock_session, "https://example.com")
        assert result == "<html>ok</html>"

    @pytest.mark.asyncio
    async def test_get_non_200_raises_http_error(self):
        mock_resp = AsyncMock()
        mock_resp.status = 404
        mock_resp.text = AsyncMock(return_value="not found")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        with pytest.raises(HttpError) as exc_info:
            await get(mock_session, "https://example.com/missing")
        assert exc_info.value.status == 404

    @pytest.mark.asyncio
    async def test_get_passes_headers_to_session(self):
        """Verify custom headers are passed to session.get"""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.content_type = "application/json"
        mock_resp.json = AsyncMock(return_value={"ok": True})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        custom_headers = {"X-Custom": "value", "Authorization": "Bearer token"}
        result = await get(mock_session, "https://example.com/api", headers=custom_headers)

        mock_session.get.assert_called_once()
        call_kwargs = mock_session.get.call_args
        # Verify URL is in positional args
        assert call_kwargs[0][0] == "https://example.com/api"
        # Verify headers were passed
        assert "headers" in call_kwargs[1]
        assert call_kwargs[1]["headers"]["X-Custom"] == "value"

    @pytest.mark.asyncio
    async def test_get_network_error_raises_http_error(self):
        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=aiohttp.ClientError("connection refused"))

        with pytest.raises(HttpError) as exc_info:
            await get(mock_session, "https://example.com")
        assert exc_info.value.status == 0
        assert "connection refused" in exc_info.value.message


class TestPost:
    @pytest.mark.asyncio
    async def test_post_json_success(self):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.content_type = "application/json"
        mock_resp.json = AsyncMock(return_value={"result": "ok"})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)

        result = await post(mock_session, "https://example.com/api", json={"key": "val"})
        assert result == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_post_with_data_param(self):
        """Verify data parameter is passed to session.post"""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.content_type = "application/json"
        mock_resp.json = AsyncMock(return_value={"result": "ok"})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)

        result = await post(mock_session, "https://example.com/api", data={"key": "val"})

        mock_session.post.assert_called_once()
        call_kwargs = mock_session.post.call_args
        assert call_kwargs[0][0] == "https://example.com/api"
        assert call_kwargs[1]["data"] == {"key": "val"}

    @pytest.mark.asyncio
    async def test_post_text_response(self):
        """Verify non-JSON POST response returns text"""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.content_type = "text/plain"
        mock_resp.text = AsyncMock(return_value="created")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)

        result = await post(mock_session, "https://example.com/api")
        assert result == "created"

    @pytest.mark.asyncio
    async def test_post_non_200_raises_http_error(self):
        mock_resp = AsyncMock()
        mock_resp.status = 500
        mock_resp.text = AsyncMock(return_value="server error")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)

        with pytest.raises(HttpError) as exc_info:
            await post(mock_session, "https://example.com/api")
        assert exc_info.value.status == 500
