from __future__ import annotations

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict

from presentation.api import dependencies
from presentation.api.routers.v2.ai.response_utils import error_response, success_response


router = APIRouter(prefix="/api/v2/ai", tags=["v2-ai-cost-control"])


class BudgetUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    work_id: str = ""
    budget_type: str
    enabled: bool
    limit: str
    currency: str = ""
    alert_threshold: str = "0.8"
    expected_revision: int | None = None
    caller_type: str = "user_action"
    user_action: bool = False
    user_id: str = ""
    idempotency_key: str = ""
    confirm_budget_change: bool = False
    confirm_disable: bool = False
    inherit_global: bool = False


class PriceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    work_id: str = ""
    provider_name: str
    model_name: str
    enabled: bool = True
    input_price_per_1m: str
    output_price_per_1m: str
    currency: str
    expected_revision: int | None = None
    caller_type: str = "user_action"
    user_action: bool = False
    user_id: str = ""
    idempotency_key: str = ""
    confirm_price_change: bool = False
    confirm_manual_price_source: bool = False
    inherit_global: bool = False


class ReconcileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    work_id: str
    caller_type: str = "user_action"
    user_action: bool = False
    user_id: str = ""
    idempotency_key: str = ""


@router.get("/cost-dashboard/summary")
def summary(request: Request, work_id: str, month: str = ""):
    try: data = dependencies.get_cost_control_service().summary(work_id, month)
    except Exception as exc: return _cost_error(request, exc)
    return success_response(request, data=data)


@router.get("/cost-dashboard/details")
def details(request: Request, work_id: str, month: str = "", limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    try: data = dependencies.get_cost_control_service().details(work_id, month, limit, offset)
    except Exception as exc: return _cost_error(request, exc)
    return success_response(request, data=data)


@router.get("/cost-dashboard/trend")
def trend(request: Request, work_id: str, from_: str = Query(alias="from"), to: str = Query(), granularity: str = "day"):
    if granularity != "day": return error_response(request,error_code="P2_COST_QUERY_INVALID",status_code=422)
    try: data=dependencies.get_cost_control_service().trend(work_id,from_,to)
    except Exception as exc: return _cost_error(request,exc)
    return success_response(request,data=data)


@router.get("/cost-dashboard/task-cost")
def task_cost(request: Request, work_id: str, job_id: str = "", session_id: str = "", run_id: str = ""):
    try: data=dependencies.get_cost_control_service().task_cost(work_id,job_id=job_id,session_id=session_id,run_id=run_id)
    except Exception as exc: return _cost_error(request,exc)
    return success_response(request,data=data)


@router.get("/cost-budget")
def budgets(request: Request, work_id: str = ""):
    return success_response(request, data=dependencies.get_cost_control_service().budgets(work_id))


@router.get("/cost-budget/check")
def check_budget(request: Request, work_id: str):
    return success_response(request, data=dependencies.get_cost_control_service().check(work_id))


@router.put("/cost-budget")
def save_budget(payload: BudgetUpdateRequest, request: Request):
    if payload.caller_type != "user_action" or not payload.user_action or not payload.user_id.strip():
        return error_response(request, error_code="P2_CALLER_FORBIDDEN", status_code=403)
    if not payload.idempotency_key.strip():
        return error_response(request, error_code="P2_IDEMPOTENCY_REQUIRED", status_code=400)
    if not payload.confirm_budget_change:
        return error_response(request, error_code="P2_BUDGET_CONFIRMATION_REQUIRED", status_code=400)
    if not payload.enabled and not payload.confirm_disable:
        return error_response(request, error_code="P2_BUDGET_DISABLE_CONFIRMATION_REQUIRED", status_code=400)
    try:
        data = dependencies.get_cost_control_service().save_budget(
            work_id=payload.work_id, budget_type=payload.budget_type, enabled=payload.enabled,
            limit=payload.limit, currency=payload.currency, alert_threshold=payload.alert_threshold,
            expected_revision=payload.expected_revision,
            user_id=payload.user_id,idempotency_key=payload.idempotency_key,
            inherit_global=payload.inherit_global,
        )
    except Exception as exc:
        return _cost_error(request, exc)
    return success_response(request, data={"policy": data, "message": "预算已更新。请回到刚才的 AI 功能，由你确认后继续。"})


@router.get("/cost-prices")
def prices(request: Request, work_id: str = "", provider_name: str = "", model_name: str = ""):
    return success_response(request, data=dependencies.get_cost_control_service().prices(work_id, provider_name, model_name))


@router.put("/cost-prices")
def save_price(payload: PriceUpdateRequest, request: Request):
    if payload.caller_type != "user_action" or not payload.user_action or not payload.user_id.strip(): return error_response(request, error_code="P2_CALLER_FORBIDDEN", status_code=403)
    if not payload.idempotency_key.strip(): return error_response(request, error_code="P2_IDEMPOTENCY_REQUIRED", status_code=400)
    if not payload.confirm_price_change: return error_response(request, error_code="P2_PRICE_CONFIRMATION_REQUIRED", status_code=400)
    if not payload.confirm_manual_price_source: return error_response(request, error_code="P2_PRICE_SOURCE_CONFIRMATION_REQUIRED", status_code=400)
    try:
        policy = dependencies.get_cost_control_service().save_price(work_id=payload.work_id, provider_name=payload.provider_name, model_name=payload.model_name, enabled=payload.enabled, input_price=payload.input_price_per_1m, output_price=payload.output_price_per_1m, currency=payload.currency, expected_revision=payload.expected_revision,user_id=payload.user_id,idempotency_key=payload.idempotency_key,inherit_global=payload.inherit_global)
    except Exception as exc: return _cost_error(request, exc)
    return success_response(request, data={"policy": policy, "message": "费用信息已保存，只用于之后的 AI 使用。"})


@router.post("/cost-budget/reconcile-usage")
def reconcile_usage(payload: ReconcileRequest, request: Request):
    if payload.caller_type!="user_action" or not payload.user_action or not payload.user_id.strip(): return error_response(request,error_code="P2_CALLER_FORBIDDEN",status_code=403)
    if not payload.idempotency_key.strip(): return error_response(request,error_code="P2_IDEMPOTENCY_REQUIRED",status_code=400)
    try: data=dependencies.get_cost_control_service().reconcile_usage(payload.work_id)
    except Exception as exc: return _cost_error(request,exc)
    return success_response(request,data=data)


def _cost_error(request: Request, exc: Exception):
    code = getattr(exc, "error_code", str(exc) or "P2_BUDGET_CHECK_FAILED")
    status = 409 if code in {"P2_BUDGET_CONFLICT", "P2_BUDGET_EXCEEDED", "P2_BUDGET_USAGE_UNKNOWN"} else 422 if "VALIDATION" in code or "QUERY_INVALID" in code else 503
    return error_response(request, error_code=code, status_code=status)
