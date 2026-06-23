from __future__ import annotations

import hashlib
import math

from domain.services.ai.embedding_provider import EmbeddingModelInfo, EmbeddingProviderPort


class LocalEmbeddingProvider(EmbeddingProviderPort):
    """Deterministic local embedding adapter for offline tests and dev runtime."""

    def __init__(self, *, vector_dimension: int = 16) -> None:
        self._vector_dimension = max(int(vector_dimension or 16), 4)

    def embed_text(self, *, text: str, request_id: str = "", trace_id: str = "") -> list[float]:
        _ = request_id, trace_id
        return self._embed(text)

    def embed_batch(self, *, texts: list[str], request_id: str = "", trace_id: str = "") -> list[list[float]]:
        _ = request_id, trace_id
        return [self._embed(text) for text in texts]

    def get_embedding_model_info(self) -> EmbeddingModelInfo:
        return EmbeddingModelInfo(
            provider_name="local",
            model_name="local-hash-embedding",
            model_version="v1",
            vector_dimension=self._vector_dimension,
        )

    def _embed(self, text: str) -> list[float]:
        normalized = "".join(str(text or "").strip().split())
        if not normalized:
            return [0.0] * self._vector_dimension
        vector = [0.0] * self._vector_dimension
        for index, char in enumerate(normalized):
            digest = hashlib.sha256(f"{index}:{char}".encode("utf-8")).digest()
            slot = digest[0] % self._vector_dimension
            weight = 1.0 + (digest[1] / 255.0)
            vector[slot] += weight
        norm = math.sqrt(sum(value * value for value in vector))
        if norm <= 0:
            return [0.0] * self._vector_dimension
        return [round(value / norm, 6) for value in vector]
