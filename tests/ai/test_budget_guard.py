from decimal import Decimal

from domain.services.ai.budget_guard import BudgetContext, BudgetGuard


def test_budget_guard_allows_and_warns_before_limit():
    result = BudgetGuard().evaluate(BudgetContext(limit=Decimal("10"), used=Decimal("8"), projected=Decimal("1"), alert_threshold=Decimal("0.8")))
    assert result.allowed is True
    assert result.control == "warn"
    assert result.usage_ratio == Decimal("0.9")


def test_budget_guard_blocks_at_limit_and_unknown_is_not_ready():
    exceeded = BudgetGuard().evaluate(BudgetContext(limit=Decimal("10"), used=Decimal("9"), projected=Decimal("2")))
    unknown = BudgetGuard().evaluate(BudgetContext(limit=Decimal("10"), used=None, projected=Decimal("1")))
    assert exceeded.allowed is False
    assert exceeded.reason_code == "budget_exceeded"
    assert unknown.allowed is False
    assert unknown.determination == "indeterminate"
    assert unknown.reason_code == "budget_usage_unknown"
