from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from application.services.v1.service_factory import build_writing_asset_service
from application.services.v1.writing_asset_service import WritingAssetService
from domain.entities.ai.models import (
    CitationBatch,
    CitationLink,
    CitationSourceType,
    CitationVerificationStatus,
)
from domain.repositories.ai.candidate_draft_repository import CandidateDraftRepository
from domain.repositories.ai.citation_link_repository import CitationLinkRepository


class CitationLinkService:
    def __init__(
        self,
        *,
        citation_repository: CitationLinkRepository,
        candidate_draft_repository: CandidateDraftRepository,
        work_service,
        chapter_service,
        writing_asset_service: WritingAssetService | None = None,
        story_state_repository=None,
        vector_recall_service=None,
        vector_similarity_threshold: float = 0.7,
    ) -> None:
        self._citation_repository = citation_repository
        self._candidate_draft_repository = candidate_draft_repository
        self._work_service = work_service
        self._chapter_service = chapter_service
        self._writing_asset_service = writing_asset_service or build_writing_asset_service()
        self._story_state_repository = story_state_repository
        self._vector_recall_service = vector_recall_service
        self._vector_similarity_threshold = float(vector_similarity_threshold)

    def process_candidate_citations(
        self,
        *,
        candidate_version_id: str,
        raw_citations: list[dict[str, object]],
    ) -> CitationBatch:
        version = self._candidate_draft_repository.get_version(candidate_version_id)
        draft = self._candidate_draft_repository.get(version.candidate_draft_id)
        citations = [
            self._validate_single(
                self._map_raw_to_citation(
                    raw=raw,
                    candidate_version_id=candidate_version_id,
                    candidate_draft_id=draft.candidate_draft_id,
                    work_id=draft.work_id,
                )
            )
            for raw in list(raw_citations or [])
        ]
        self._citation_repository.save_batch(citations)
        draft.metadata.update(
            {
                "citation_status": "ready" if citations else "none",
                "citation_count": len(citations),
                "citation_verified_count": sum(1 for item in citations if item.verification_status == CitationVerificationStatus.VERIFIED),
                "citation_updated_at": self._now(),
            }
        )
        self._candidate_draft_repository.save(draft)
        return self._build_batch(candidate_version_id, draft.candidate_draft_id, citations)

    def get_by_candidate_version(self, candidate_version_id: str) -> CitationBatch:
        version = self._candidate_draft_repository.get_version(candidate_version_id)
        citations = self._citation_repository.get_by_candidate_version(candidate_version_id)
        return self._build_batch(candidate_version_id, version.candidate_draft_id, citations)

    def get_by_candidate_draft(self, candidate_draft_id: str) -> list[CitationBatch]:
        versions = self._candidate_draft_repository.list_versions(candidate_draft_id)
        batches: list[CitationBatch] = []
        for version in versions:
            citations = self._citation_repository.get_by_candidate_version(version.candidate_version_id)
            batches.append(self._build_batch(version.candidate_version_id, candidate_draft_id, citations))
        return batches

    def get_by_source(self, source_type: str, source_id: str) -> list[CitationLink]:
        return self._citation_repository.get_by_source(source_type, source_id)

    def get_source_detail(self, source_type: str, source_id: str) -> dict[str, object]:
        resolution = self._resolve_source(CitationSourceType(source_type), source_id)
        return {
            "source_type": source_type,
            "source_id": source_id,
            "source_name_snapshot": resolution["name"],
            "source_full_summary": resolution["summary"],
            "is_active": resolution["is_active"],
        }

    def get_citation_source_detail(self, citation_id: str) -> dict[str, object]:
        citation = self._citation_repository.get_by_id(citation_id)
        if citation is None:
            raise ValueError("citation_not_found")
        payload = self.get_source_detail(citation.source_type.value, citation.source_id)
        payload["citation_id"] = citation.citation_id
        payload["source_name_snapshot"] = citation.source_name_snapshot or payload["source_name_snapshot"]
        return payload

    def _map_raw_to_citation(
        self,
        *,
        raw: dict[str, object],
        candidate_version_id: str,
        candidate_draft_id: str,
        work_id: str,
    ) -> CitationLink:
        source_type = CitationSourceType(str(raw.get("source_type") or "chapter"))
        resolved_source_id = str(raw.get("source_id_hint") or "").strip()
        return CitationLink(
            citation_id=f"cite_{uuid.uuid4().hex[:12]}",
            candidate_version_id=candidate_version_id,
            candidate_draft_id=candidate_draft_id,
            work_id=work_id,
            source_type=source_type,
            source_id=resolved_source_id,
            source_hash=str(raw.get("source_hash") or "").strip(),
            source_name_snapshot=str(raw.get("source_name") or "").strip(),
            source_span=str(raw.get("source_span") or "").strip(),
            context_in_draft=str(raw.get("context_in_draft") or "").strip()[:80],
            verification_status=CitationVerificationStatus.UNKNOWN_SOURCE,
            verification_detail="pending_verification",
            confidence=float(raw.get("confidence") or 0.0),
            created_at=self._now(),
        )

    def _validate_single(self, citation: CitationLink) -> CitationLink:
        try:
            resolution = self._resolve_source(
                citation.source_type,
                citation.source_id,
                citation.source_name_snapshot,
                citation.work_id,
            )
        except ValueError:
            return citation.model_copy(
                update={
                    "verification_status": CitationVerificationStatus.UNKNOWN_SOURCE,
                    "verification_detail": "source_not_found",
                    "verified_at": self._now(),
                }
            )
        base_citation = citation.model_copy(
            update={
                "source_id": str(resolution["source_id"]),
                "source_hash": str(citation.source_hash or ""),
                "source_name_snapshot": str(resolution["name"]),
                "source_excerpt": str(resolution["summary"])[:120],
                "verified_at": self._now(),
            }
        )
        self._validate_source_hash(base_citation, str(resolution.get("hash_source_text") or ""))
        if citation.source_type in {CitationSourceType.CHAPTER, CitationSourceType.EVENT}:
            verified = self._verify_with_vector_recall(base_citation)
            if verified is not None:
                return verified
        if citation.source_type in {
            CitationSourceType.CHARACTER,
            CitationSourceType.FORESHADOW,
            CitationSourceType.SETTING,
            CitationSourceType.LOCATION,
        }:
            return base_citation.model_copy(
                update={
                    "verification_status": CitationVerificationStatus.LOW_CONFIDENCE,
                    "verification_detail": "existence_only",
                }
            )
        return base_citation.model_copy(
            update={
                "verification_status": CitationVerificationStatus.LOW_CONFIDENCE,
                "verification_detail": "vector_unavailable",
            }
        )

    def _resolve_source(
        self,
        source_type: CitationSourceType,
        source_id: str,
        source_name: str = "",
        work_id: str = "",
    ) -> dict[str, object]:
        if source_type == CitationSourceType.CHAPTER:
            return self._resolve_chapter(source_id=source_id, source_name=source_name)
        if source_type == CitationSourceType.CHARACTER:
            return self._resolve_character(source_id=source_id, source_name=source_name)
        if source_type == CitationSourceType.FORESHADOW:
            return self._resolve_foreshadow(source_id=source_id, source_name=source_name)
        if source_type == CitationSourceType.EVENT:
            return self._resolve_event(source_id=source_id, source_name=source_name)
        if source_type == CitationSourceType.SETTING:
            return self._resolve_setting(source_id=source_id, source_name=source_name, work_id=work_id)
        if source_type == CitationSourceType.LOCATION:
            return self._resolve_location(source_id=source_id, source_name=source_name, work_id=work_id)
        raise ValueError("citation_source_unsupported")

    def _resolve_chapter(self, *, source_id: str, source_name: str) -> dict[str, object]:
        for work in self._work_service.list_works():
            for chapter in self._chapter_service.list_chapters(work.id):
                if source_id and chapter.id.value == source_id:
                    return {
                        "source_id": chapter.id.value,
                        "name": chapter.title,
                        "summary": chapter.content[:120],
                        "hash_source_text": chapter.content,
                        "is_active": True,
                    }
                if source_name and chapter.title == source_name:
                    return {
                        "source_id": chapter.id.value,
                        "name": chapter.title,
                        "summary": chapter.content[:120],
                        "hash_source_text": chapter.content,
                        "is_active": True,
                    }
        raise ValueError("chapter_not_found")

    def _resolve_character(self, *, source_id: str, source_name: str) -> dict[str, object]:
        for work in self._work_service.list_works():
            for item in self._writing_asset_service.list_characters(work.id):
                if source_id and item.id == source_id:
                    return {
                        "source_id": item.id,
                        "name": item.name,
                        "summary": item.description[:120],
                        "hash_source_text": item.description,
                        "is_active": True,
                    }
                if source_name and item.name == source_name:
                    return {
                        "source_id": item.id,
                        "name": item.name,
                        "summary": item.description[:120],
                        "hash_source_text": item.description,
                        "is_active": True,
                    }
        raise ValueError("character_not_found")

    def _resolve_foreshadow(self, *, source_id: str, source_name: str) -> dict[str, object]:
        for work in self._work_service.list_works():
            for item in self._writing_asset_service.list_foreshadows(work.id, status=None):
                if source_id and item.id == source_id:
                    return {
                        "source_id": item.id,
                        "name": item.title,
                        "summary": item.description[:120],
                        "hash_source_text": item.description,
                        "is_active": True,
                    }
                if source_name and item.title == source_name:
                    return {
                        "source_id": item.id,
                        "name": item.title,
                        "summary": item.description[:120],
                        "hash_source_text": item.description,
                        "is_active": True,
                    }
        raise ValueError("foreshadow_not_found")

    def _resolve_event(self, *, source_id: str, source_name: str) -> dict[str, object]:
        for work in self._work_service.list_works():
            for item in self._writing_asset_service.list_timeline_events(work.id):
                if source_id and item.id == source_id:
                    return {
                        "source_id": item.id,
                        "name": item.title,
                        "summary": item.description[:120],
                        "hash_source_text": item.description,
                        "is_active": True,
                    }
                if source_name and item.title == source_name:
                    return {
                        "source_id": item.id,
                        "name": item.title,
                        "summary": item.description[:120],
                        "hash_source_text": item.description,
                        "is_active": True,
                    }
        raise ValueError("timeline_event_not_found")

    def _resolve_setting(self, *, source_id: str, source_name: str, work_id: str = "") -> dict[str, object]:
        for story_state in self._iter_story_states(work_id):
            for note in list(story_state.continuity_notes or []):
                clean = str(note or "").strip()
                if not clean:
                    continue
                if source_id and clean == source_id:
                    return {
                        "source_id": clean,
                        "name": clean,
                        "summary": clean[:120],
                        "hash_source_text": clean,
                        "is_active": True,
                    }
                if source_name and clean == source_name:
                    return {
                        "source_id": clean,
                        "name": clean,
                        "summary": clean[:120],
                        "hash_source_text": clean,
                        "is_active": True,
                    }
        raise ValueError("setting_not_found")

    def _resolve_location(self, *, source_id: str, source_name: str, work_id: str = "") -> dict[str, object]:
        for story_state in self._iter_story_states(work_id):
            for location in list(story_state.active_locations or []):
                clean = str(location or "").strip()
                if not clean:
                    continue
                if source_id and clean == source_id:
                    return {
                        "source_id": clean,
                        "name": clean,
                        "summary": clean[:120],
                        "hash_source_text": clean,
                        "is_active": True,
                    }
                if source_name and clean == source_name:
                    return {
                        "source_id": clean,
                        "name": clean,
                        "summary": clean[:120],
                        "hash_source_text": clean,
                        "is_active": True,
                    }
        raise ValueError("location_not_found")

    def _build_batch(self, candidate_version_id: str, candidate_draft_id: str, citations: list[CitationLink]) -> CitationBatch:
        return CitationBatch(
            batch_id=f"cb_{uuid.uuid4().hex[:12]}",
            candidate_version_id=candidate_version_id,
            candidate_draft_id=candidate_draft_id,
            total_count=len(citations),
            verified_count=sum(1 for item in citations if item.verification_status == CitationVerificationStatus.VERIFIED),
            unknown_count=sum(1 for item in citations if item.verification_status == CitationVerificationStatus.UNKNOWN_SOURCE),
            citations=citations,
        )

    def _verify_with_vector_recall(self, citation: CitationLink) -> CitationLink | None:
        if self._vector_recall_service is None:
            return None
        try:
            results = self._vector_recall_service.recall(
                {
                    "query_text": citation.context_in_draft or citation.source_name_snapshot,
                    "source_type": citation.source_type.value,
                    "source_id": citation.source_id,
                }
            )
        except Exception:  # noqa: BLE001
            return citation.model_copy(
                update={
                    "verification_status": CitationVerificationStatus.LOW_CONFIDENCE,
                    "verification_detail": "vector_unavailable",
                }
            )
        first = next((item for item in list(results or []) if isinstance(item, dict)), None)
        if first is None:
            return citation.model_copy(
                update={
                    "verification_status": CitationVerificationStatus.LOW_CONFIDENCE,
                    "verification_detail": "vector_no_match",
                }
            )
        score = float(first.get("score") or 0.0)
        matched_source_id = str(first.get("source_id") or "")
        excerpt = str(first.get("content_text") or citation.source_excerpt or "")[:120]
        if matched_source_id == citation.source_id and score >= self._vector_similarity_threshold:
            return citation.model_copy(
                update={
                    "source_excerpt": excerpt,
                    "verification_status": CitationVerificationStatus.VERIFIED,
                    "verification_detail": f"vector_matched:{score:.2f}",
                }
            )
        return citation.model_copy(
            update={
                "source_excerpt": excerpt,
                "verification_status": CitationVerificationStatus.LOW_CONFIDENCE,
                "verification_detail": f"vector_score_low:{score:.2f}",
            }
        )

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _validate_source_hash(self, citation: CitationLink, source_text: str) -> None:
        normalized_hash = str(citation.source_hash or "").strip()
        if not normalized_hash:
            return
        actual_hash = self._sha256_text(source_text)
        if normalized_hash != actual_hash:
            raise ValueError("P2_CITATION_SOURCE_HASH_MISMATCH")

    def _sha256_text(self, value: str) -> str:
        return f"sha256:{hashlib.sha256(str(value or '').encode('utf-8')).hexdigest()}"

    def _iter_story_states(self, work_id: str = "") -> list[object]:
        if self._story_state_repository is None:
            return []
        if work_id:
            story_state = self._story_state_repository.get_latest_analysis_baseline_by_work(work_id)
            return [story_state] if story_state is not None else []
        states: list[object] = []
        for work in self._work_service.list_works():
            story_state = self._story_state_repository.get_latest_analysis_baseline_by_work(work.id)
            if story_state is not None:
                states.append(story_state)
        return states
