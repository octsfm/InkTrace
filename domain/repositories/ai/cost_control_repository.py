from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal


class CostControlRepository(ABC):
    @abstractmethod
    def get_summary(self, work_id: str, month: str) -> dict[str, object]: ...

    @abstractmethod
    def list_details(self, work_id: str, month: str, limit: int, offset: int) -> dict[str, object]: ...

    @abstractmethod
    def get_budget(self, work_id: str, budget_type: str) -> dict[str, object] | None: ...

    @abstractmethod
    def save_budget(self, *, work_id: str, budget_type: str, enabled: bool, limit: Decimal, currency: str, alert_threshold: Decimal, expected_revision: int | None, user_id: str, idempotency_key: str, inherit_global: bool = False) -> dict[str, object]: ...

    @abstractmethod
    def list_prices(self, work_id: str, provider_name: str = "", model_name: str = "") -> list[dict[str, object]]: ...

    @abstractmethod
    def save_price(self, *, work_id: str, provider_name: str, model_name: str, enabled: bool, input_price: Decimal, output_price: Decimal, currency: str, expected_revision: int | None, user_id: str, idempotency_key: str, inherit_global: bool = False) -> dict[str, object]: ...

    @abstractmethod
    def resolve_price(self, work_id: str, provider_name: str, model_name: str) -> dict[str, object] | None: ...

    @abstractmethod
    def get_trend(self, work_id: str, date_from: str, date_to: str) -> list[dict[str, object]]: ...

    @abstractmethod
    def get_task_cost(self, work_id: str, scope_type: str, scope_id: str) -> dict[str, object]: ...

    @abstractmethod
    def reconcile_usage(self, work_id: str) -> dict[str, object]: ...

    @abstractmethod
    def get_auto_queue_budget(self, work_id: str) -> dict[str, object] | None: ...

    @abstractmethod
    def save_auto_queue_budget(self, *, work_id: str, enabled: bool, limit_tokens: int, expected_revision: int | None, user_id: str, idempotency_key: str) -> dict[str, object]: ...
