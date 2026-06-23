from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from application.services.v1.chapter_service import ChapterService
from domain.entities.ai.models import ChapterChunk, ChunkEmbedding, VectorIndexBuildResult
from domain.repositories.ai.vector_index_repository import VectorIndexRepositoryPort
from domain.repositories.ai.vector_store_repository import VectorStorePort
from domain.services.ai.embedding_provider import EmbeddingProviderPort


class VectorIndexService:
    def __init__(
        self,
        *,
        chapter_service: ChapterService,
        embedding_provider: EmbeddingProviderPort,
        vector_store: VectorStorePort,
        vector_index_repository: VectorIndexRepositoryPort,
        chunk_size: int = 1000,
        overlap_size: int = 150,
        min_chunk_size: int = 100,
    ) -> None:
        self._chapter_service = chapter_service
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._vector_index_repository = vector_index_repository
        self._chunk_size = max(int(chunk_size or 1000), 100)
        self._overlap_size = max(min(int(overlap_size or 150), self._chunk_size - 1), 0)
        self._min_chunk_size = max(int(min_chunk_size or 100), 1)

    def build_initial_index(self, work_id: str, should_continue=None) -> VectorIndexBuildResult:  # noqa: ANN001
        return self._index_chapters(
            work_id=work_id,
            chapters=self._published_chapters(work_id),
            should_continue=should_continue,
        )

    def mark_chapter_stale(self, work_id: str, chapter_id: str) -> int:
        stale_chunks = self._vector_index_repository.mark_chunks_stale_by_chapter(work_id, chapter_id)
        self._vector_index_repository.mark_embeddings_stale_by_chapter(work_id, chapter_id)
        self._vector_store.mark_by_chapter_stale(work_id=work_id, chapter_id=chapter_id)
        self._update_work_index_status(work_id, index_status="stale", stale_status="partial_stale")
        return stale_chunks

    def reindex_chapter(self, work_id: str, chapter_id: str, should_continue=None) -> VectorIndexBuildResult:  # noqa: ANN001
        chapter = self._published_chapter(work_id=work_id, chapter_id=chapter_id)
        if chapter is None:
            self._update_work_index_status(work_id, index_status="degraded", stale_status="partial_stale")
            return VectorIndexBuildResult(
                index_status="degraded",
                degraded_reason="target_chapter_not_confirmed",
                warning_count=1,
                warnings=["target_chapter_not_confirmed"],
            )
        prepared = self._prepare_pending_entries(work_id=work_id, chapters=[chapter], should_continue=should_continue)
        if prepared["failed_chunk_count"] > 0 and prepared["indexed_chunk_count"] <= 0:
            self._cleanup_pending_vectors(prepared["vector_ids"])
            return self._build_pending_result(prepared)
        self._switch_chapter_entries(work_id=work_id, chapter_id=chapter_id, pending_entries=prepared["entries"])
        self._update_work_index_status(work_id, index_status="ready", stale_status="fresh")
        return self._build_pending_result(prepared, index_status_override="ready")

    def reindex_work(self, work_id: str, should_continue=None) -> VectorIndexBuildResult:  # noqa: ANN001
        chapters = self._published_chapters(work_id)
        prepared = self._prepare_pending_entries(work_id=work_id, chapters=chapters, should_continue=should_continue)
        if prepared["failed_chunk_count"] > 0:
            self._cleanup_pending_vectors(prepared["vector_ids"])
            return self._build_pending_result(prepared)
        existing_chunks = self._vector_index_repository.get_chunks_by_work(work_id)
        for chapter_id in {item.chapter_id for item in existing_chunks if item.index_status != "deleted"}:
            self._vector_index_repository.mark_chunks_stale_by_chapter(work_id, chapter_id)
            self._vector_index_repository.mark_embeddings_stale_by_chapter(work_id, chapter_id)
            self._vector_store.mark_by_chapter_stale(work_id=work_id, chapter_id=chapter_id)
        for chapter in chapters:
            self._save_pending_entries(prepared["entries"], chapter_id=chapter.id.value)
        self._update_work_index_status(work_id, index_status="ready", stale_status="fresh")
        return self._build_pending_result(prepared, index_status_override="ready")

    def remove_chapter_from_index(self, work_id: str, chapter_id: str) -> int:
        deleted_chunks = self._vector_index_repository.mark_chunks_deleted_by_chapter(work_id, chapter_id)
        self._vector_index_repository.mark_embeddings_deleted_by_chapter(work_id, chapter_id)
        self._vector_store.delete_by_chapter(work_id=work_id, chapter_id=chapter_id)
        self._update_work_index_status(work_id, index_status="stale", stale_status="partial_stale")
        return deleted_chunks

    def _index_chapters(self, *, work_id: str, chapters: list[object], should_continue=None) -> VectorIndexBuildResult:  # noqa: ANN001
        warnings: list[str] = []
        indexed_chapter_ids: set[str] = set()
        indexed_chunk_count = 0
        failed_chunk_count = 0
        model_info = self._embedding_provider.get_embedding_model_info()

        if not chapters:
            self._update_work_index_status(work_id, index_status="degraded", stale_status="fresh")
            return VectorIndexBuildResult(
                index_status="degraded",
                degraded_reason="no_confirmed_chapters",
                warning_count=1,
                warnings=["no_confirmed_chapters"],
            )

        for chapter in chapters:
            chunks = self._split_chapter(str(chapter.content or ""))
            if not chunks:
                warnings.append("empty_chapter_skipped")
                continue
            if len(str(chapter.content or "").strip()) < self._min_chunk_size:
                warnings.append("small_chunk")
            for chunk_index, chunk_payload in enumerate(chunks):
                try:
                    if not self._should_continue(should_continue):
                        failed_chunk_count += 1
                        break
                    chunk = self._build_chunk(
                        work_id=work_id,
                        chapter_id=chapter.id.value,
                        chapter_order=chapter.order_index,
                        chunk_index=chunk_index,
                        text=str(chunk_payload["text"]),
                        start_offset=int(chunk_payload["start_offset"]),
                        end_offset=int(chunk_payload["end_offset"]),
                    )
                    embedding = self._embedding_provider.embed_text(text=chunk.text_excerpt)
                    if not self._should_continue(should_continue):
                        failed_chunk_count += 1
                        continue
                    vector_id = f"vec_{chunk.chunk_id}"
                    self._vector_store.upsert_vector(
                        vector_id=vector_id,
                        embedding=embedding,
                        metadata={
                            "work_id": work_id,
                            "chapter_id": chapter.id.value,
                            "chunk_id": chunk.chunk_id,
                            "status": "active",
                            "source": "confirmed_chapter",
                            "chapter_title": chapter.title,
                            "text_excerpt": chunk.text_excerpt,
                            "content_hash": chunk.content_hash,
                        },
                    )
                    if not self._should_continue(should_continue):
                        self._vector_store.delete_vector(vector_id=vector_id)
                        failed_chunk_count += 1
                        continue
                    self._vector_index_repository.save_chunk(chunk)
                    now = self._now()
                    self._vector_index_repository.save_embedding_metadata(
                        ChunkEmbedding(
                            embedding_id=f"embedding_{chunk.chunk_id}",
                            chunk_id=chunk.chunk_id,
                            work_id=work_id,
                            chapter_id=chapter.id.value,
                            embedding_model=model_info.model_name,
                            embedding_provider=model_info.provider_name,
                            embedding_version=model_info.model_version,
                            vector_id=vector_id,
                            content_hash=chunk.content_hash,
                            status="active",
                            created_at=now,
                            updated_at=now,
                        )
                    )
                    indexed_chapter_ids.add(chapter.id.value)
                    indexed_chunk_count += 1
                except Exception:
                    failed_chunk_count += 1

        index_status = self._result_index_status(indexed_chunk_count=indexed_chunk_count, failed_chunk_count=failed_chunk_count)
        degraded_reason = self._result_degraded_reason(
            index_status=index_status,
            indexed_chunk_count=indexed_chunk_count,
            failed_chunk_count=failed_chunk_count,
        )
        self._update_work_index_status(work_id, index_status=index_status, stale_status="fresh")
        normalized_warnings = list(dict.fromkeys(item for item in warnings if item))
        return VectorIndexBuildResult(
            index_status=index_status,
            indexed_chapter_count=len(indexed_chapter_ids),
            indexed_chunk_count=indexed_chunk_count,
            failed_chunk_count=failed_chunk_count,
            warning_count=len(normalized_warnings),
            degraded_reason=degraded_reason,
            warnings=normalized_warnings,
        )

    def _prepare_pending_entries(self, *, work_id: str, chapters: list[object], should_continue=None) -> dict[str, object]:  # noqa: ANN001
        warnings: list[str] = []
        indexed_chapter_ids: set[str] = set()
        indexed_chunk_count = 0
        failed_chunk_count = 0
        vector_ids: list[str] = []
        entries: list[dict[str, object]] = []
        model_info = self._embedding_provider.get_embedding_model_info()
        if not chapters:
            return {
                "entries": [],
                "vector_ids": [],
                "indexed_chapter_ids": set(),
                "indexed_chunk_count": 0,
                "failed_chunk_count": 0,
                "warnings": ["no_confirmed_chapters"],
                "degraded_reason": "no_confirmed_chapters",
            }
        for chapter in chapters:
            chunks = self._split_chapter(str(chapter.content or ""))
            if not chunks:
                warnings.append("empty_chapter_skipped")
                continue
            if len(str(chapter.content or "").strip()) < self._min_chunk_size:
                warnings.append("small_chunk")
            for chunk_index, chunk_payload in enumerate(chunks):
                try:
                    if not self._should_continue(should_continue):
                        failed_chunk_count += 1
                        break
                    chunk = self._build_chunk(
                        work_id=work_id,
                        chapter_id=chapter.id.value,
                        chapter_order=chapter.order_index,
                        chunk_index=chunk_index,
                        text=str(chunk_payload["text"]),
                        start_offset=int(chunk_payload["start_offset"]),
                        end_offset=int(chunk_payload["end_offset"]),
                    )
                    embedding = self._embedding_provider.embed_text(text=chunk.text_excerpt)
                    if not self._should_continue(should_continue):
                        failed_chunk_count += 1
                        continue
                    vector_id = f"vec_{chunk.chunk_id}"
                    vector_ids.append(vector_id)
                    self._vector_store.upsert_vector(
                        vector_id=vector_id,
                        embedding=embedding,
                        metadata={
                            "work_id": work_id,
                            "chapter_id": chapter.id.value,
                            "chunk_id": chunk.chunk_id,
                            "status": "building",
                            "source": "confirmed_chapter",
                            "chapter_title": chapter.title,
                            "text_excerpt": chunk.text_excerpt,
                            "content_hash": chunk.content_hash,
                        },
                    )
                    if not self._should_continue(should_continue):
                        self._vector_store.delete_vector(vector_id=vector_id)
                        failed_chunk_count += 1
                        continue
                    now = self._now()
                    entries.append(
                        {
                            "chapter_id": chapter.id.value,
                            "chunk": chunk.model_copy(update={"index_status": "active"}),
                            "embedding": ChunkEmbedding(
                                embedding_id=f"embedding_{chunk.chunk_id}",
                                chunk_id=chunk.chunk_id,
                                work_id=work_id,
                                chapter_id=chapter.id.value,
                                embedding_model=model_info.model_name,
                                embedding_provider=model_info.provider_name,
                                embedding_version=model_info.model_version,
                                vector_id=vector_id,
                                content_hash=chunk.content_hash,
                                status="active",
                                created_at=now,
                                updated_at=now,
                            ),
                        }
                    )
                    indexed_chapter_ids.add(chapter.id.value)
                    indexed_chunk_count += 1
                except Exception:
                    failed_chunk_count += 1
        index_status = self._result_index_status(indexed_chunk_count=indexed_chunk_count, failed_chunk_count=failed_chunk_count)
        return {
            "entries": entries,
            "vector_ids": vector_ids,
            "indexed_chapter_ids": indexed_chapter_ids,
            "indexed_chunk_count": indexed_chunk_count,
            "failed_chunk_count": failed_chunk_count,
            "warnings": list(dict.fromkeys(item for item in warnings if item)),
            "degraded_reason": self._result_degraded_reason(
                index_status=index_status,
                indexed_chunk_count=indexed_chunk_count,
                failed_chunk_count=failed_chunk_count,
            ),
        }

    def _switch_chapter_entries(self, *, work_id: str, chapter_id: str, pending_entries: list[dict[str, object]]) -> None:
        self._vector_index_repository.mark_chunks_stale_by_chapter(work_id, chapter_id)
        self._vector_index_repository.mark_embeddings_stale_by_chapter(work_id, chapter_id)
        self._vector_store.mark_by_chapter_stale(work_id=work_id, chapter_id=chapter_id)
        self._save_pending_entries(pending_entries, chapter_id=chapter_id)

    def _save_pending_entries(self, pending_entries: list[dict[str, object]], *, chapter_id: str) -> None:
        for item in pending_entries:
            if str(item["chapter_id"]) != chapter_id:
                continue
            chunk = item["chunk"]
            embedding = item["embedding"]
            self._vector_index_repository.save_chunk(chunk)
            self._vector_index_repository.save_embedding_metadata(embedding)
            self._promote_vector(embedding.vector_id)

    def _promote_vector(self, vector_id: str) -> None:
        payload = self._vector_store.get_vector_status(vector_id=vector_id)
        if payload is None:
            return
        metadata = dict(payload.get("metadata", {}) or {})
        metadata["status"] = "active"
        self._vector_store.upsert_vector(
            vector_id=vector_id,
            embedding=list(payload.get("embedding", []) or []),
            metadata=metadata,
        )

    def _cleanup_pending_vectors(self, vector_ids: list[str]) -> None:
        for vector_id in vector_ids:
            try:
                payload = self._vector_store.get_vector_status(vector_id=vector_id)
                if payload is None:
                    continue
                if str(payload.get("status", "") or "") == "building":
                    self._vector_store.delete_vector(vector_id=vector_id)
            except Exception:
                continue

    def _build_pending_result(self, prepared: dict[str, object], index_status_override: str = "") -> VectorIndexBuildResult:
        index_status = index_status_override or self._result_index_status(
            indexed_chunk_count=int(prepared["indexed_chunk_count"]),
            failed_chunk_count=int(prepared["failed_chunk_count"]),
        )
        return VectorIndexBuildResult(
            index_status=index_status,
            indexed_chapter_count=len(prepared["indexed_chapter_ids"]),
            indexed_chunk_count=int(prepared["indexed_chunk_count"]),
            failed_chunk_count=int(prepared["failed_chunk_count"]),
            warning_count=len(list(prepared["warnings"])),
            degraded_reason="" if index_status == "ready" else str(prepared["degraded_reason"] or ""),
            warnings=list(prepared["warnings"]),
        )

    def _should_continue(self, callback) -> bool:  # noqa: ANN001
        if callback is None:
            return True
        try:
            return bool(callback())
        except Exception:
            return False

    def _published_chapters(self, work_id: str) -> list[object]:
        return [chapter for chapter in self._chapter_service.list_chapters(work_id) if chapter.is_published]

    def _published_chapter(self, *, work_id: str, chapter_id: str) -> object | None:
        chapter = self._chapter_service.chapter_repo.find_by_id(chapter_id)
        if chapter is None:
            return None
        if chapter.work_id.value != work_id or not chapter.is_published:
            return None
        return chapter

    def _update_work_index_status(self, work_id: str, *, index_status: str, stale_status: str) -> None:
        active_chunk_count = sum(
            1 for item in self._vector_index_repository.get_chunks_by_work(work_id) if item.index_status == "active"
        )
        self._vector_index_repository.update_index_status(
            work_id,
            {
                "work_id": work_id,
                "index_status": index_status,
                "stale_status": stale_status,
                "chunk_count": active_chunk_count,
                "active_embedding_count": active_chunk_count,
                "updated_at": self._now(),
            },
        )

    def _result_index_status(self, *, indexed_chunk_count: int, failed_chunk_count: int) -> str:
        if indexed_chunk_count <= 0 and failed_chunk_count > 0:
            return "failed"
        if failed_chunk_count > 0:
            return "degraded"
        if indexed_chunk_count <= 0:
            return "degraded"
        return "ready"

    def _result_degraded_reason(self, *, index_status: str, indexed_chunk_count: int, failed_chunk_count: int) -> str:
        if index_status == "ready":
            return ""
        if indexed_chunk_count <= 0 and failed_chunk_count > 0:
            return "index_build_failed"
        if failed_chunk_count > 0:
            return "partial_index_failed"
        return "no_effective_chunks"

    def _split_chapter(self, content: str) -> list[dict[str, object]]:
        normalized = str(content or "").strip()
        if not normalized:
            return []
        if len(normalized) <= self._chunk_size:
            return [{"text": normalized, "start_offset": 0, "end_offset": len(normalized)}]
        items: list[dict[str, object]] = []
        start = 0
        while start < len(normalized):
            end = min(start + self._chunk_size, len(normalized))
            excerpt = normalized[start:end]
            if not excerpt:
                break
            items.append({"text": excerpt, "start_offset": start, "end_offset": end})
            if end >= len(normalized):
                break
            start = max(end - self._overlap_size, start + 1)
        return items

    def _build_chunk(
        self,
        *,
        work_id: str,
        chapter_id: str,
        chapter_order: int,
        chunk_index: int,
        text: str,
        start_offset: int,
        end_offset: int,
    ) -> ChapterChunk:
        now = self._now()
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return ChapterChunk(
            chunk_id=f"chunk_{uuid.uuid4().hex}",
            work_id=work_id,
            chapter_id=chapter_id,
            chapter_order=chapter_order,
            chunk_index=chunk_index,
            text_excerpt=text,
            content_hash=content_hash,
            token_count=max(len(text) // 2, 1),
            start_offset=start_offset,
            end_offset=end_offset,
            source="confirmed_chapter",
            index_status="active",
            stale_status="fresh",
            created_at=now,
            updated_at=now,
        )

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
