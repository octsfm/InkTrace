import pytest

from application.services.ai.budget_attempt_guard import BudgetAttemptBlocked, BudgetProviderAttemptGuard
from domain.entities.ai.models import LLMRequest, ModelSelection


class _CostService:
    def __init__(self, result): self.result = result
    def check_before_attempt(self, work_id, provider_name, model_name, request): return self.result


def test_budget_attempt_guard_blocks_unknown_and_does_not_call_any_provider():
    guard = BudgetProviderAttemptGuard(_CostService({"allowed": False, "reason_code": "budget_usage_unknown"}))
    with pytest.raises(BudgetAttemptBlocked) as error:
        guard.before_attempt(LLMRequest(model_role="writer", work_id="work-1"), ModelSelection(provider_name="p", model_name="m"))
    assert error.value.error_code == "P2_BUDGET_USAGE_UNKNOWN"


def test_budget_attempt_guard_does_not_apply_work_budget_to_diagnostic_scope():
    guard = BudgetProviderAttemptGuard(_CostService({"allowed": False, "reason_code": "budget_exceeded"}))
    guard.before_attempt(LLMRequest(model_role="writer"), ModelSelection(provider_name="p", model_name="m"))
