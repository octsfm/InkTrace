from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingModelInfo:
    provider_name: str
    model_name: str
    model_version: str
    vector_dimension: int


class EmbeddingProviderPort(ABC):
    @abstractmethod
    def embed_text(self, *, text: str, request_id: str = "", trace_id: str = "") -> list[float]:
        raise NotImplementedError

    @abstractmethod
    def embed_batch(self, *, texts: list[str], request_id: str = "", trace_id: str = "") -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def get_embedding_model_info(self) -> EmbeddingModelInfo:
        raise NotImplementedError
