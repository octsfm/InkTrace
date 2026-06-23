from __future__ import annotations

from application.services.v1.chapter_service import ChapterService
from domain.services.ai.embedding_provider import EmbeddingProviderPort
from domain.types import NovelId
from domain.value_objects.embedding import SearchResult
from domain.repositories.ai.vector_store_repository import VectorStorePort


class ContextVectorRecallService:
    """Minimal runtime adapter that returns recall excerpts for ContextPack."""

    def __init__(
        self,
        *,
        chapter_service: ChapterService,
        embedding_provider: EmbeddingProviderPort | None = None,
        vector_store: VectorStorePort | None = None,
        vector_repository=None,
    ) -> None:
        self._chapter_service = chapter_service
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._vector_repository = vector_repository

    def recall(self, query):  # noqa: ANN001
        work_id = str(getattr(query, "work_id", "") or "").strip()
        query_text = str(getattr(query, "query_text", "") or "").strip()
        top_k = max(int(getattr(query, "top_k", 3) or 3), 1)
        score_threshold = float(getattr(query, "score_threshold", 0.6) or 0.6)
        target_chapter_id = str(getattr(query, "target_chapter_id", "") or "").strip()
        if not work_id or not query_text:
            return []

        port_items = self._recall_from_formal_ports(query=query, work_id=work_id, query_text=query_text)
        if port_items:
            return port_items

        vector_items = self._recall_from_vector_repository(
            work_id=work_id,
            query_text=query_text,
            top_k=top_k,
            score_threshold=score_threshold,
        )
        if vector_items:
            return vector_items

        scored: list[tuple[float, dict[str, object]]] = []
        for chapter in self._chapter_service.list_chapters(work_id):
            chapter_id = getattr(getattr(chapter, "id", None), "value", "")
            content = str(getattr(chapter, "content", "") or "").strip()
            title = str(getattr(chapter, "title", "") or "").strip()
            if not chapter_id or not content:
                continue
            score = self._score(query_text=query_text, content_text=content)
            if score < score_threshold:
                continue
            excerpt = self._excerpt(content, query_text)
            scored.append(
                (
                    score,
                    {
                        "item_id": f"recall_{chapter_id}",
                        "source_id": chapter_id,
                        "content_text": f"召回片段[{title or chapter_id}]: {excerpt}",
                        "token_estimate": max(len(excerpt) // 2, 8),
                        "stale_status": "fresh",
                        "warning": "current_chapter_recall" if target_chapter_id and chapter_id == target_chapter_id else "",
                        "metadata": {
                            "score": round(score, 2),
                            "chapter_title": title,
                            "recall_backend": "local_fallback",
                        },
                    },
                )
            )
        scored.sort(key=lambda item: item[0], reverse=True)
        return [payload for _, payload in scored[:top_k]]

    def _recall_from_formal_ports(self, *, query, work_id: str, query_text: str) -> list[dict[str, object]]:  # noqa: ANN001
        if self._embedding_provider is None or self._vector_store is None:
            return []
        query_embedding = self._embedding_provider.embed_text(
            text=query_text,
            request_id=str(getattr(query, "request_id", "") or ""),
            trace_id=str(getattr(query, "trace_id", "") or ""),
        )
        raw_results = self._vector_store.search_similar(
            query_embedding=list(query_embedding or []),
            work_id=work_id,
            top_k=max(int(getattr(query, "top_k", 3) or 3), 1),
            score_threshold=float(getattr(query, "score_threshold", 0.6) or 0.6),
            exclude_chapter_ids=[],
            allow_stale=bool(getattr(query, "allow_stale", False)),
        )
        return self._normalize_vector_store_results(raw_results)

    def _recall_from_vector_repository(
        self,
        *,
        work_id: str,
        query_text: str,
        top_k: int,
        score_threshold: float,
    ) -> list[dict[str, object]]:
        if self._vector_repository is None:
            return []
        raw_results = self._vector_repository.search(
            query=query_text,
            novel_id=NovelId(work_id),
            source_type="confirmed_chapter",
            n_results=top_k,
        )
        return self._normalize_vector_results(raw_results, score_threshold=score_threshold)

    def _normalize_vector_results(
        self,
        results: list[SearchResult],
        *,
        score_threshold: float,
    ) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        for result in results or []:
            metadata = getattr(result, "metadata", None)
            source_type = str(getattr(metadata, "source_type", "") or "").strip()
            if source_type and source_type != "confirmed_chapter":
                continue
            score = float(getattr(result, "score", 0.0) or 0.0)
            if score < score_threshold:
                continue
            content = str(getattr(result, "content", "") or "").strip()
            if not content:
                continue
            normalized.append(
                {
                    "item_id": f"recall_{getattr(result, 'id', '') or len(normalized)}",
                    "source_id": str(getattr(metadata, "source_id", "") or ""),
                    "content_text": f"召回片段[{getattr(metadata, 'content_preview', '') or getattr(metadata, 'source_id', '')}]: {content[:120]}",
                    "token_estimate": max(len(content[:120]) // 2, 8),
                    "stale_status": "fresh",
                    "warning": "",
                    "metadata": {
                        "score": round(score, 2),
                        "vector_id": str(getattr(result, "id", "") or ""),
                        "chunk_index": int(getattr(metadata, "chunk_index", 0) or 0),
                        "content_preview": str(getattr(metadata, "content_preview", "") or ""),
                        "recall_backend": "vector_repository",
                    },
                }
            )
        return normalized

    def _normalize_vector_store_results(self, results: list[dict[str, object]]) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        for result in results or []:
            if not isinstance(result, dict):
                continue
            metadata = dict(result.get("metadata", {}) or {})
            if str(metadata.get("source", "") or "").strip() not in {"", "confirmed_chapter"}:
                continue
            text_excerpt = str(result.get("text_excerpt", "") or "").strip()
            if not text_excerpt:
                continue
            normalized.append(
                {
                    "item_id": f"recall_{str(result.get('vector_id', '') or len(normalized))}",
                    "source_id": str(metadata.get("chapter_id", "") or ""),
                    "content_text": f"召回片段[{metadata.get('chapter_title', '') or metadata.get('chapter_id', '')}]: {text_excerpt[:120]}",
                    "token_estimate": max(len(text_excerpt[:120]) // 2, 8),
                    "stale_status": "fresh",
                    "warning": "",
                    "metadata": {
                        "score": round(float(result.get("score", 0.0) or 0.0), 2),
                        "vector_id": str(result.get("vector_id", "") or ""),
                        "chunk_id": str(metadata.get("chunk_id", "") or ""),
                        "source": str(metadata.get("source", "") or "confirmed_chapter"),
                        "recall_backend": "vector_store_port",
                    },
                }
            )
        return normalized

    def _score(self, *, query_text: str, content_text: str) -> float:
        normalized_query = self._normalize(query_text)
        normalized_content = self._normalize(content_text)
        if not normalized_query or not normalized_content:
            return 0.0
        if normalized_query in normalized_content or normalized_content in normalized_query:
            return 0.98
        if self._has_fragment_match(normalized_query, normalized_content):
            return 0.9
        query_chars = {char for char in normalized_query if not char.isspace()}
        content_chars = {char for char in normalized_content if not char.isspace()}
        if not query_chars or not content_chars:
            return 0.0
        overlap = len(query_chars & content_chars) / max(len(query_chars), 1)
        if overlap <= 0:
            return 0.0
        return round(min(0.88, 0.45 + overlap * 0.55), 2)

    def _has_fragment_match(self, query_text: str, content_text: str) -> bool:
        if len(query_text) < 2:
            return False
        for size in range(min(6, len(query_text)), 1, -1):
            for index in range(0, len(query_text) - size + 1):
                fragment = query_text[index : index + size].strip()
                if fragment and fragment in content_text:
                    return True
        return False

    def _excerpt(self, content_text: str, query_text: str) -> str:
        content = str(content_text or "").strip()
        query = self._normalize(query_text)
        best_index = -1
        best_fragment = ""
        for size in range(min(6, len(query)), 1, -1):
            for index in range(0, len(query) - size + 1):
                fragment = query[index : index + size].strip()
                if fragment and fragment in self._normalize(content):
                    best_fragment = fragment
                    break
            if best_fragment:
                break
        if best_fragment:
            raw_index = content.find(best_fragment)
            best_index = raw_index
        if best_index < 0:
            return content[:120]
        start = max(best_index - 20, 0)
        end = min(best_index + 100, len(content))
        return content[start:end]

    def _normalize(self, value: str) -> str:
        return "".join(str(value or "").strip().split())
