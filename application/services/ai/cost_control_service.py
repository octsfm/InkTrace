from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from domain.repositories.ai.cost_control_repository import CostControlRepository
from domain.services.ai.budget_guard import BudgetContext, BudgetGuard


class CostControlError(RuntimeError):
    def __init__(self, error_code: str) -> None:
        self.error_code = error_code
        super().__init__(error_code)


class CostControlService:
    def __init__(self, repository: CostControlRepository) -> None:
        self._repository = repository
        self._guard = BudgetGuard()

    def summary(self, work_id: str, month: str) -> dict[str, object]:
        return self._repository.get_summary(work_id, self._month(month))

    def details(self, work_id: str, month: str, limit: int, offset: int) -> dict[str, object]:
        return self._repository.list_details(work_id, self._month(month), limit, offset)

    def trend(self, work_id: str, date_from: str, date_to: str) -> dict[str, object]:
        try: return {"granularity":"day","items":self._repository.get_trend(work_id,date_from,date_to)}
        except ValueError as exc: raise CostControlError("P2_COST_QUERY_INVALID") from exc

    def task_cost(self, work_id: str, *, job_id: str = "", session_id: str = "", run_id: str = "") -> dict[str, object]:
        scopes=[("job_id",job_id),("session_id",session_id),("run_id",run_id)]; selected=[item for item in scopes if item[1]]
        if len(selected)!=1: raise CostControlError("P2_COST_SCOPE_INVALID")
        return self._repository.get_task_cost(work_id,*selected[0])

    def reconcile_usage(self, work_id: str) -> dict[str, object]: return self._repository.reconcile_usage(work_id)

    def budgets(self, work_id: str) -> dict[str, object]:
        policies = [self._repository.get_budget(work_id, kind) for kind in ("monthly", "initialization")]
        policies.append(self._repository.get_auto_queue_budget(work_id))
        return {"policies": [item for item in policies if item is not None]}

    def save_budget(self, *, work_id: str, budget_type: str, enabled: bool, limit: str, currency: str, alert_threshold: str, expected_revision: int | None, user_id: str, idempotency_key: str, inherit_global: bool = False) -> dict[str, object]:
        if budget_type not in {"monthly", "initialization", "auto_queue"}:
            raise CostControlError("P2_BUDGET_VALIDATION_FAILED")
        try:
            value = Decimal(limit); threshold = Decimal(alert_threshold)
        except InvalidOperation as exc:
            raise CostControlError("P2_BUDGET_VALIDATION_FAILED") from exc
        if value < 0 or threshold <= 0 or threshold > 1:
            raise CostControlError("P2_BUDGET_VALIDATION_FAILED")
        if budget_type == "monthly" and enabled and not currency.strip():
            raise CostControlError("P2_BUDGET_VALIDATION_FAILED")
        if budget_type == "auto_queue":
            return self._repository.save_auto_queue_budget(work_id=work_id,enabled=enabled,limit_tokens=int(value),expected_revision=expected_revision,user_id=user_id,idempotency_key=idempotency_key)
        return self._repository.save_budget(
            work_id=work_id, budget_type=budget_type, enabled=enabled, limit=value,
            currency=currency.strip().upper() if budget_type == "monthly" else "",
            alert_threshold=threshold, expected_revision=expected_revision,user_id=user_id,idempotency_key=idempotency_key,inherit_global=bool(inherit_global and work_id),
        )

    def check(self, work_id: str) -> dict[str, object]:
        month = datetime.now(UTC).strftime("%Y-%m")
        summary = self.summary(work_id, month)
        budget = self._repository.get_budget(work_id, "monthly")
        if budget is None:
            result = self._guard.evaluate(BudgetContext(limit=None, used=Decimal("0"), enabled=False))
        else:
            used = Decimal("0") if int(summary.get("call_count", 0)) == 0 else Decimal(summary["estimated_cost"]) if summary["estimated_cost"] is not None else None
            result = self._guard.evaluate(BudgetContext(limit=Decimal(str(budget["limit"])), used=used, enabled=bool(budget["enabled"])))
        return {"allowed": result.allowed, "determination": result.determination, "control": result.control, "reason_code": result.reason_code, "usage_ratio": str(result.usage_ratio) if result.usage_ratio is not None else None, "remaining": str(result.remaining) if result.remaining is not None else None}

    def prices(self, work_id: str, provider_name: str = "", model_name: str = "") -> dict[str, object]:
        return {"policies": self._repository.list_prices(work_id, provider_name, model_name)}

    def price_snapshot(self,work_id: str,provider_name: str,model_name: str) -> dict[str,object]:
        price=self._repository.resolve_price(work_id,provider_name,model_name)
        if price is None: return {}
        return {"currency":price["currency"],"input_price_per_1k":str(Decimal(str(price["input_price_per_1m"]))/Decimal("1000")),"output_price_per_1k":str(Decimal(str(price["output_price_per_1m"]))/Decimal("1000")),"pricing_source":"manual_exact","policy_revision":price["revision"]}

    def save_price(self, *, work_id: str, provider_name: str, model_name: str, enabled: bool, input_price: str, output_price: str, currency: str, expected_revision: int | None, user_id: str, idempotency_key: str, inherit_global: bool = False) -> dict[str, object]:
        if not provider_name.strip() or not model_name.strip() or not currency.strip(): raise CostControlError("P2_PRICE_VALIDATION_FAILED")
        try: input_value = Decimal(input_price); output_value = Decimal(output_price)
        except InvalidOperation as exc: raise CostControlError("P2_PRICE_VALIDATION_FAILED") from exc
        if input_value < 0 or output_value < 0: raise CostControlError("P2_PRICE_VALIDATION_FAILED")
        return self._repository.save_price(work_id=work_id, provider_name=provider_name.strip(), model_name=model_name.strip(), enabled=enabled, input_price=input_value, output_price=output_value, currency=currency.strip().upper(), expected_revision=expected_revision,user_id=user_id,idempotency_key=idempotency_key,inherit_global=bool(inherit_global and work_id))

    def check_before_attempt(self, work_id: str, provider_name: str, model_name: str, request) -> dict[str, object]:
        input_tokens = max(sum(len(str(item.get("content", ""))) for item in request.messages) // 4, 1)
        output_tokens = int(request.max_tokens or 0)
        if output_tokens <= 0:
            return {"allowed": False, "determination": "indeterminate", "control": "block", "reason_code": "budget_price_unknown", "results": []}
        projected_tokens = Decimal(input_tokens + output_tokens)
        results: list[dict[str, object]] = []
        monthly = self._repository.get_budget(work_id, "monthly")
        if monthly and monthly["enabled"]:
            summary = self.summary(work_id, datetime.now(UTC).strftime("%Y-%m"))
            used = Decimal("0") if int(summary.get("call_count", 0)) == 0 else Decimal(summary["estimated_cost"]) if summary["estimated_cost"] is not None else None
            price = self._repository.resolve_price(work_id, provider_name, model_name)
            if price is None:
                projected_cost = None
            elif str(price["currency"]) != str(monthly["currency"]):
                results.append({"budget_type": "monthly", "allowed": False, "determination": "indeterminate", "control": "block", "reason_code": "budget_currency_mismatch"})
                projected_cost = None
            else:
                projected_cost = (Decimal(input_tokens) * Decimal(str(price["input_price_per_1m"])) + Decimal(output_tokens) * Decimal(str(price["output_price_per_1m"]))) / Decimal("1000000")
            if not results or results[-1].get("budget_type") != "monthly":
                decision = self._guard.evaluate(BudgetContext(limit=Decimal(str(monthly["limit"])), used=used, projected=projected_cost, enabled=True, alert_threshold=Decimal(str(monthly["alert_threshold"]))))
                results.append(self._result_dict("monthly", decision))
        if request.operation_type == "initialization" and request.job_id:
            policy = self._repository.get_budget(work_id, "initialization")
            if policy and policy["enabled"]:
                usage = self._repository.get_task_cost(work_id, "job_id", request.job_id)
                used_tokens = None if usage["usage_completeness"] == "unknown" else Decimal(str(usage["total_tokens"]))
                decision = self._guard.evaluate(BudgetContext(limit=Decimal(str(policy["limit"])), used=used_tokens, projected=projected_tokens, enabled=True, alert_threshold=Decimal(str(policy["alert_threshold"]))))
                results.append(self._result_dict("initialization", decision))
        if request.run_id:
            policy = self._repository.get_auto_queue_budget(work_id)
            if policy and policy["enabled"]:
                usage = self._repository.get_task_cost(work_id, "run_id", request.run_id)
                used_tokens = None if usage["usage_completeness"] == "unknown" else Decimal(str(usage["total_tokens"]))
                decision = self._guard.evaluate(BudgetContext(limit=Decimal(str(policy["limit"])), used=used_tokens, projected=projected_tokens, enabled=True, alert_threshold=Decimal(str(policy["alert_threshold"]))))
                results.append(self._result_dict("auto_queue", decision))
        if not results:
            return {"allowed": True, "determination": "determined", "control": "allow", "reason_code": "no_enabled_budget", "results": []}
        blocked = next((item for item in results if not item["allowed"]), None)
        warning = next((item for item in results if item["control"] == "warn"), None)
        return {**(blocked or warning or results[0]), "results": results}

    def check_after_attempt(self,work_id: str,request) -> dict[str,object]:
        results=[]
        monthly=self._repository.get_budget(work_id,"monthly")
        if monthly and monthly["enabled"]:
            summary=self.summary(work_id,datetime.now(UTC).strftime("%Y-%m"))
            used=Decimal(summary["estimated_cost"]) if summary["estimated_cost"] is not None else None
            decision=self._guard.evaluate(BudgetContext(limit=Decimal(str(monthly["limit"])),used=used,projected=Decimal("0"),enabled=True,alert_threshold=Decimal(str(monthly["alert_threshold"]))))
            results.append(self._result_dict("monthly",decision))
        if request.operation_type=="initialization" and request.job_id:
            policy=self._repository.get_budget(work_id,"initialization")
            if policy and policy["enabled"]:
                usage=self._repository.get_task_cost(work_id,"job_id",request.job_id)
                used=None if usage["usage_completeness"]=="unknown" else Decimal(str(usage["total_tokens"]))
                decision=self._guard.evaluate(BudgetContext(limit=Decimal(str(policy["limit"])),used=used,projected=Decimal("0"),enabled=True,alert_threshold=Decimal(str(policy["alert_threshold"]))))
                results.append(self._result_dict("initialization",decision))
        if request.run_id:
            policy=self._repository.get_auto_queue_budget(work_id)
            if policy and policy["enabled"]:
                usage=self._repository.get_task_cost(work_id,"run_id",request.run_id)
                used=None if usage["usage_completeness"]=="unknown" else Decimal(str(usage["total_tokens"]))
                decision=self._guard.evaluate(BudgetContext(limit=Decimal(str(policy["limit"])),used=used,projected=Decimal("0"),enabled=True,alert_threshold=Decimal(str(policy["alert_threshold"]))))
                results.append(self._result_dict("auto_queue",decision))
        blocked=next((item for item in results if not item["allowed"]),None); return {**(blocked or {"allowed":True,"determination":"determined","control":"allow","reason_code":"budget_normal"}),"results":results}

    @staticmethod
    def _result_dict(budget_type: str,result) -> dict[str,object]: return {"budget_type":budget_type,"allowed":result.allowed,"determination":result.determination,"control":result.control,"reason_code":result.reason_code}

    @staticmethod
    def _month(value: str) -> str:
        text = value.strip() or datetime.now(UTC).strftime("%Y-%m")
        try: datetime.strptime(text, "%Y-%m")
        except ValueError as exc: raise CostControlError("P2_COST_QUERY_INVALID") from exc
        return text
