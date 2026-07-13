from __future__ import annotations

from abc import ABC, abstractmethod


class FeaturePreferenceRepository(ABC):
    @abstractmethod
    def load(self) -> dict[str, bool]:
        raise NotImplementedError

    @abstractmethod
    def save_preference(
        self,
        *,
        feature_key: str,
        enabled: bool,
        idempotency_key: str,
    ) -> dict[str, bool]:
        raise NotImplementedError
