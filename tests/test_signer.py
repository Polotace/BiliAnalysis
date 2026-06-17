"""测试 WBI 签名模块。"""
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from bilianalysis.crawler.signer import (
    fetch_mixin_key, WbiSigner, WEB_LOCATION, MIXIN_TABLE, NAV_URL,
)


NAV_RESPONSE = {
    "code": 0,
    "data": {
        "wbi_img": {
            "img_url": "https://i0.hdslb.com/bfs/wbi/7cd084941338484aae1ad9425b840f84.png",
            "sub_url": "https://i0.hdslb.com/bfs/wbi/4932caff0ff746eab6f01bf08b70ac45.png",
        }
    }
}


class TestFetchMixinKey:
    @pytest.mark.asyncio
    async def test_returns_mixin_key_from_valid_response(self):
        mock_get = AsyncMock(return_value=NAV_RESPONSE)
        with patch("bilianalysis.crawler.signer.get", mock_get):
            result = await fetch_mixin_key(MagicMock())

        assert isinstance(result, str)
        assert len(result) == 32
        call_args = mock_get.call_args[0]
        assert call_args[1] == NAV_URL

    @pytest.mark.asyncio
    async def test_mixin_key_derivation(self):
        """手动验证 mixin_key 推导逻辑。"""
        resp = {"data": {"wbi_img": {
            "img_url": "https://i0.hdslb.com/bfs/wbi/7cd084941338484aae1ad9425b840f84.png",
            "sub_url": "https://i0.hdslb.com/bfs/wbi/4932caff0ff746eab6f01bf08b70ac45.png",
        }}}
        mock_get = AsyncMock(return_value=resp)
        with patch("bilianalysis.crawler.signer.get", mock_get):
            result = await fetch_mixin_key(MagicMock())

        # Manual computation
        img_key = "7cd084941338484aae1ad9425b840f84"
        sub_key = "4932caff0ff746eab6f01bf08b70ac45"
        raw = img_key + sub_key
        expected = "".join(raw[i] for i in MIXIN_TABLE[:32])
        assert result == expected


class TestWbiSigner:
    def test_sign_adds_required_params(self):
        signer = WbiSigner("a" * 32)
        result = signer.sign({})
        assert "wts" in result
        assert "web_location" in result
        assert "w_rid" in result
        assert result["web_location"] == WEB_LOCATION
        assert len(result["w_rid"]) == 32  # MD5 hex

    def test_sign_preserves_input_params(self):
        signer = WbiSigner("b" * 32)
        result = signer.sign({"number": "123"})
        assert result.get("number") == "123"

    def test_sign_deterministic_with_fixed_time(self, monkeypatch):
        """固定时间戳时，签名是确定性的。"""
        import bilianalysis.crawler.signer as mod
        monkeypatch.setattr(mod.time, "time", lambda: 1781522463)
        signer = WbiSigner("test_key_32_bytes_123456789")
        result = signer.sign({"number": "377"})

        assert result["wts"] == "1781522463"
        # sorted: number=377, web_location=333.934, wts=1781522463
        qs = "number=377&web_location=333.934&wts=1781522463"
        expected_wrid = hashlib.md5((qs + "test_key_32_bytes_123456789").encode()).hexdigest()
        assert result["w_rid"] == expected_wrid

    def test_sign_params_alphabetically_ordered(self, monkeypatch):
        """验证参数按 key 字母序排列。"""
        import bilianalysis.crawler.signer as mod
        monkeypatch.setattr(mod.time, "time", lambda: 1781522463)
        signer = WbiSigner("x" * 32)

        # 传入非字母序的参数，内部应重新排序
        result = signer.sign({"z_param": "1", "a_param": "2"})
        # w_rid 的计算应该基于排序后的 query string
        qs = "a_param=2&web_location=333.934&wts=1781522463&z_param=1"
        expected = hashlib.md5((qs + "x" * 32).encode()).hexdigest()
        assert result["w_rid"] == expected
