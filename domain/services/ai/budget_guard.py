from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BudgetContext:
    limit: Decimal | None
    used: Decimal | None
    projected: Decimal | None = Decimal("0")
    alert_threshold: Decimal = Decimal("0.8")
    enabled: bool = True


@dataclass(frozen=True)
class BudgetCheckResult:
    allowed: bool
    determination: str
    control: str
    reason_code: str
    usage_ratio: Decimal | None
    remaining: Decimal | None


class BudgetGuard:
    """Pure budget decision; it never changes jobs, drafts, or formal assets."""

    def evaluate(self, context: BudgetContext) -> BudgetCheckResult:
        if not context.enabled or context.limit is None:
            return BudgetCheckResult(True, "determined", "allow", "no_enabled_budget", None, None)
        if context.used is None:
            return BudgetCheckResult(False, "indeterminate", "block", "budget_usage_unknown", None, None)
        if context.projected is None:
            return BudgetCheckResult(False, "indeterminate", "block", "budget_price_unknown", None, None)
        if context.limit <= 0:
            return BudgetCheckResult(True, "determined", "allow", "no_enabled_budget", None, None)
        total = context.used + context.projected
        ratio = total / context.limit
        remaining = max(context.limit - context.used, Decimal("0"))
        if total > context.limit or (context.projected == 0 and context.used >= context.limit):
            return BudgetCheckResult(False, "determined", "block", "budget_exceeded", ratio, remaining)
        if ratio >= context.alert_threshold:
            return BudgetCheckResult(True, "determined", "warn", "budget_warning", ratio, remaining)
        return BudgetCheckResult(True, "determined", "allow", "budget_normal", ratio, remaining)
