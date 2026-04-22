import pytest

from domain.exceptions import TokenLimitError
from infrastructure.llm.kimi_client import KimiClient


def test_token_limit_error_fields():
    error = TokenLimitError(
        "Kimi",
        current_tokens=9000,
        max_tokens=7600,
        stage="global_analysis",
        model_name="moonshot-v1-8k",
        request_id="req-test-1",
    )
    assert error.provider == "Kimi"
    assert error.current_tokens == 9000
    assert error.max_tokens == 7600
    assert error.stage == "global_analysis"
    assert error.model_name == "moonshot-v1-8k"
    assert error.request_id == "req-test-1"
    assert "9000" in str(error)
    assert "7600" in str(error)


def test_kimi_preflight_budget_block():
    client = KimiClient(api_key="test", model="moonshot-v1-8k")
    huge_text = "超长文本" * 6000
    with pytest.raises(TokenLimitError) as err:
        client.validate_request_budget(
            messages=[{"role": "user", "content": huge_text}],
            max_tokens=2000,
            stage="global_analysis",
            request_id="req-preflight",
        )
    assert err.value.stage == "global_analysis"
    assert err.value.model_name == "moonshot-v1-8k"
    assert err.value.request_id == "req-preflight"
