import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domain.exceptions import RateLimitError
from infrastructure.llm.kimi_client import KimiClient


def _mock_response(status_code: int, *, headers=None, payload=None):
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {}
    response.json.return_value = payload or {"choices": [{"message": {"content": "ok"}}]}
    response.raise_for_status.return_value = None
    return response


def test_kimi_client_retries_on_429_with_retry_after():
    client = KimiClient(api_key="test-key", max_retries=2)
    client._client.post = AsyncMock(
        side_effect=[
            _mock_response(429, headers={"retry-after": "1"}),
            _mock_response(200, payload={"choices": [{"message": {"content": "recovered"}}]}),
        ]
    )
    with patch("infrastructure.llm.kimi_client.asyncio.sleep", new=AsyncMock()) as mocked_sleep:
        result = asyncio.run(client.generate("test prompt"))
    assert result == "recovered"
    assert client._client.post.call_count == 2
    mocked_sleep.assert_awaited_once_with(1)


def test_kimi_client_429_invalid_retry_after_does_not_raise_secondary_error():
    client = KimiClient(api_key="test-key", max_retries=2)
    client._client.post = AsyncMock(
        side_effect=[
            _mock_response(429, headers={"retry-after": "2s"}),
            _mock_response(429, headers={"retry-after": "abc"}),
        ]
    )
    with patch("infrastructure.llm.kimi_client.asyncio.sleep", new=AsyncMock()) as mocked_sleep:
        with pytest.raises(RateLimitError):
            asyncio.run(client.generate("test prompt"))
    assert client._client.post.call_count == 2
    assert mocked_sleep.await_count == 1
