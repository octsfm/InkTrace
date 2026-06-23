from __future__ import annotations

from pathlib import Path

import chromadb

from domain.repositories.ai.vector_store_repository import VectorStorePort


class ChromaVectorStore(VectorStorePort):
    def __init__(self, *, persist_directory: str, collection_name: str = "inktrace_vectors") -> None:
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=persist_directory)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_vector(self, *, vector_id: str, embedding: list[float], metadata: dict[str, object]) -> str:
        payload = dict(metadata or {})
        document = str(payload.get("text_excerpt", "") or "")
        self._collection.upsert(
            ids=[vector_id],
            embeddings=[list(embedding or [])],
            metadatas=[payload],
            documents=[document],
        )
        return vector_id

    def upsert_vectors(self, *, vectors: list[dict[str, object]]) -> list[str]:
        ids = [str(item["vector_id"]) for item in vectors]
        embeddings = [list(item.get("embedding", []) or []) for item in vectors]
        metadatas = [dict(item.get("metadata", {}) or {}) for item in vectors]
        documents = [str(metadata.get("text_excerpt", "") or "") for metadata in metadatas]
        if ids:
            self._collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
        return ids

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
        result = self._collection.query(
            query_embeddings=[list(query_embedding or [])],
            n_results=max(int(top_k or 5), 1),
            where={"work_id": work_id},
            include=["metadatas", "documents", "distances"],
        )
        excluded = set(exclude_chapter_ids or [])
        normalized: list[dict[str, object]] = []
        ids = list(result.get("ids", [[]])[0] or [])
        metadatas = list(result.get("metadatas", [[]])[0] or [])
        documents = list(result.get("documents", [[]])[0] or [])
        distances = list(result.get("distances", [[]])[0] or [])
        for vector_id, metadata, document, distance in zip(ids, metadatas, documents, distances, strict=False):
            meta = dict(metadata or {})
            if excluded and str(meta.get("chapter_id", "") or "") in excluded:
                continue
            status = str(meta.get("status", "") or "active")
            if status in {"deleted", "invalid", "failed", "skipped", "building"}:
                continue
            if status == "stale" and not allow_stale:
                continue
            if status not in {"active", "stale"}:
                continue
            score = max(0.0, round(1.0 - float(distance or 0.0), 6))
            if score < score_threshold:
                continue
            normalized.append(
                {
                    "vector_id": str(vector_id),
                    "score": score,
                    "text_excerpt": str(meta.get("text_excerpt", "") or document or ""),
                    "metadata": meta,
                }
            )
        return normalized

    def delete_vector(self, *, vector_id: str) -> None:
        self._collection.delete(ids=[vector_id])

    def mark_vector_deleted(self, *, vector_id: str) -> None:
        payload = self.get_vector_status(vector_id=vector_id)
        if payload is None:
            return
        metadata = dict(payload.get("metadata", {}) or {})
        metadata["status"] = "deleted"
        self._collection.upsert(
            ids=[vector_id],
            embeddings=[list(payload.get("embedding", []) or [])],
            metadatas=[metadata],
            documents=[str(metadata.get("text_excerpt", "") or payload.get("document", "") or "")],
        )

    def delete_by_chapter(self, *, work_id: str, chapter_id: str) -> int:
        ids = self._list_ids_by_chapter(work_id=work_id, chapter_id=chapter_id)
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)

    def mark_by_chapter_stale(self, *, work_id: str, chapter_id: str) -> int:
        items = self._get_items_by_chapter(work_id=work_id, chapter_id=chapter_id)
        count = 0
        for item in items:
            metadata = dict(item["metadata"])
            metadata["status"] = "stale"
            self._collection.upsert(
                ids=[item["vector_id"]],
                embeddings=[item["embedding"]],
                metadatas=[metadata],
                documents=[str(metadata.get("text_excerpt", "") or item["document"] or "")],
            )
            count += 1
        return count

    def get_vector_status(self, *, vector_id: str) -> dict[str, object] | None:
        result = self._collection.get(ids=[vector_id], include=["metadatas", "documents", "embeddings"])
        ids = list(result.get("ids", []) or [])
        if not ids:
            return None
        metadata = dict((result.get("metadatas", []) or [{}])[0] or {})
        document = str((result.get("documents", []) or [""])[0] or "")
        embeddings_raw = result.get("embeddings")
        if embeddings_raw is None or len(embeddings_raw) == 0:
            embedding = []
        else:
            embedding = list(embeddings_raw[0])
        return {
            "vector_id": ids[0],
            "metadata": metadata,
            "document": document,
            "embedding": embedding,
            "status": str(metadata.get("status", "") or ""),
        }

    def _list_ids_by_chapter(self, *, work_id: str, chapter_id: str) -> list[str]:
        result = self._collection.get(where={"$and": [{"work_id": work_id}, {"chapter_id": chapter_id}]})
        return [str(item) for item in list(result.get("ids", []) or [])]

    def _get_items_by_chapter(self, *, work_id: str, chapter_id: str) -> list[dict[str, object]]:
        result = self._collection.get(
            where={"$and": [{"work_id": work_id}, {"chapter_id": chapter_id}]},
            include=["metadatas", "documents", "embeddings"],
        )
        items: list[dict[str, object]] = []
        ids = list(result.get("ids") or [])
        metadatas = list(result.get("metadatas") or [])
        documents = list(result.get("documents") or [])
        embeddings_raw = result.get("embeddings")
        embeddings = list(embeddings_raw) if embeddings_raw is not None else []
        for vector_id, metadata, document, embedding in zip(ids, metadatas, documents, embeddings, strict=False):
            items.append(
                {
                    "vector_id": str(vector_id),
                    "metadata": dict(metadata or {}),
                    "document": str(document or ""),
                    "embedding": list(embedding) if embedding is not None else [],
                }
            )
        return items
