from __future__ import annotations

from types import SimpleNamespace

from presentation.api.routers.v2.ai.response_utils import error_response


def _request_stub():
    return SimpleNamespace(state=SimpleNamespace(request_id="req_test"), headers={})


def test_error_response_maps_safe_message_to_readable_text() -> None:
    request = _request_stub()

    caller_type_denied = error_response(request, error_code="caller_type_not_allowed", status_code=403)
    work_not_found = error_response(request, error_code="work_not_found", status_code=404)
    internal = error_response(request, error_code="RuntimeError", status_code=500, safe_message="internal_error")

    assert caller_type_denied.body.decode("utf-8").find("当前请求来源不被允许") != -1
    assert work_not_found.body.decode("utf-8").find("未找到对应作品") != -1
    assert internal.body.decode("utf-8").find("服务暂时不可用") != -1
