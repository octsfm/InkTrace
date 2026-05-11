from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.ai.models import AISettings


class AISettingsRepository(ABC):
    @abstractmethod
    def load(self) -> AISettings:
        raise NotImplementedError

    @abstractmethod
    def save(self, settings: AISettings) -> AISettings:
        raise NotImplementedError
