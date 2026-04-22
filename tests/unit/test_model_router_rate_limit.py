import asyncio

from application.agent_mvp.model_router import ModelRouter
from domain.exceptions import RateLimitError


class _AlwaysRateLimitClient:
    def __init__(self, retry_after: int):
        self.retry_after = retry_after

    async def generate(self, *_args, **_kwargs):
        raise RateLimitError("Kimi", retry_after=self.retry_after)


def test_model_router_exposes_rate_limit_metadata_on_terminate():
    router = ModelRouter(
        preferred_client=_AlwaysRateLimitClient(retry_after=3),
        fallback_client=_AlwaysRateLimitClient(retry_after=5),
    )
    result = asyncio.run(router.generate("test prompt"))
    assert result["ok"] is False
    assert result["error_type"] == "rate_limit"
    assert result["retry_after"] == 5
    assert result["preferred_error_meta"]["error_type"] == "rate_limit"
