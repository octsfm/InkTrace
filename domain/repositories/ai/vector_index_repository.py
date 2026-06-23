from __future__ import annotations

from abc import ABC, abstractmethod


class VectorIndexRepositoryPort(ABC):
    @abstractmethod
    def save_chunk(self, chunk: dict[str, object]) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def save_embedding_metadata(self, metadata: dict[str, object]) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def get_embedding_metadata_by_chapter(self, work_id: str, chapter_id: str) -> list[dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def get_chunks_by_work(self, work_id: str) -> list[dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def get_chunks_by_chapter(self, work_id: str, chapter_id: str) -> list[dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def mark_chunks_stale_by_chapter(self, work_id: str, chapter_id: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def mark_chunks_deleted_by_chapter(self, work_id: str, chapter_id: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def mark_embeddings_stale_by_chapter(self, work_id: str, chapter_id: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def mark_embeddings_deleted_by_chapter(self, work_id: str, chapter_id: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_index_status_by_work(self, work_id: str) -> dict[str, object] | None:
        raise NotImplementedError

    @abstractmethod
    def update_index_status(self, work_id: str, status: dict[str, object]) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def list_stale_chunks(self, work_id: str = "") -> list[dict[str, object]]:
        raise NotImplementedError
