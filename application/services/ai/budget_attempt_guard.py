from __future__ import annotations


class BudgetAttemptBlocked(RuntimeError):
    def __init__(self, error_code: str) -> None:
        self.error_code = error_code
        super().__init__(error_code)


class BudgetProviderAttemptGuard:
    """Fail-safe adapter between the generic router and cost budget service."""

    _ERRORS = {
        "budget_exceeded": "P2_BUDGET_EXCEEDED",
        "budget_usage_unknown": "P2_BUDGET_USAGE_UNKNOWN",
        "budget_price_unknown": "P2_BUDGET_PRICE_UNKNOWN",
        "budget_currency_mismatch": "P2_BUDGET_CURRENCY_MISMATCH",
        "budget_check_failed": "P2_BUDGET_CHECK_FAILED",
    }

    def __init__(self, cost_control_service) -> None:
        self._service = cost_control_service

    def before_attempt(self, request, selection) -> None:
        work_id = str(getattr(request, "work_id", "") or "")
        if not work_id:
            return
        try:
            result = self._service.check_before_attempt(work_id, selection.provider_name, selection.model_name, request)
        except Exception as exc:
            raise BudgetAttemptBlocked("P2_BUDGET_CHECK_FAILED") from exc
        if not bool(result.get("allowed", False)):
            raise BudgetAttemptBlocked(self._ERRORS.get(str(result.get("reason_code") or ""), "P2_BUDGET_CHECK_FAILED"))

    def price_snapshot(self,request,selection) -> dict[str,object]:
        return self._service.price_snapshot(str(getattr(request,"work_id","") or ""),selection.provider_name,selection.model_name)

    def after_logged_attempt(self,request,selection) -> dict[str,object]:
        work_id=str(getattr(request,"work_id","") or "")
        return self._service.check_after_attempt(work_id,request) if work_id else {"allowed":True,"control":"allow","reason_code":"no_enabled_budget"}
