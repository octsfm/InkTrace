from __future__ import annotations

from abc import ABC, abstractmethod


class VectorStorePort(ABC):
    @abstractmethod
    def upsert_vector(self, *, vector_id: str, embedding: list[float], metadata: dict[str, object]) -> str:
        raise NotImplementedError

    @abstractmethod
    def upsert_vectors(self, *, vectors: list[dict[str, object]]) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def search_similar(
        self,
        *,
        query_embedding: list[float],
        work_id: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
        exclude_chapter_ids: list[str] | None = None,
        allow_stale: bool = False,
    ) -> list[dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def delete_vector(self, *, vector_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def mark_vector_deleted(self, *, vector_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_by_chapter(self, *, work_id: str, chapter_id: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def mark_by_chapter_stale(self, *, work_id: str, chapter_id: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_vector_status(self, *, vector_id: str) -> dict[str, object] | None:
        raise NotImplementedError
