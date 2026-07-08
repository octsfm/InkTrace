from __future__ import annotations

import json
from pathlib import Path

from domain.entities.ai.models import MasterArc, SequenceArc, VolumeArc
from domain.repositories.ai.plot_arc_repository import PlotArcRepository
from infrastructure.database.session import get_database_path


class FilePlotArcStore(PlotArcRepository):
    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("plot_arcs.json")

    def save_master_arc(self, arc: MasterArc) -> MasterArc:
        arc = self._normalize_master_arc(arc)
        payload = self._load_payload()
        payload["master_arcs"][arc.work_id] = arc.model_dump(mode="json")
        self._save_payload(payload)
        return arc

    def get_master_arc(self, work_id: str) -> MasterArc | None:
        payload = self._load_payload()
        raw = payload["master_arcs"].get(work_id)
        return MasterArc.model_validate(raw) if raw else None

    def save_volume_arc(self, arc: VolumeArc) -> VolumeArc:
        arc = self._normalize_volume_arc(arc)
        payload = self._load_payload()
        payload["volume_arcs"][arc.volume_arc_id] = arc.model_dump(mode="json")
        self._save_payload(payload)
        return arc

    def get_active_volume_arc(self, work_id: str, chapter_no: int = 0) -> VolumeArc | None:
        items = self.list_volume_arcs(work_id)
        if not items:
            return None
        if chapter_no > 0:
            for item in items:
                start = int(item.chapter_range.get("from_chapter", 0) or 0)
                end = int(item.chapter_range.get("to_chapter_estimate", 0) or 0)
                if start <= chapter_no and (end == 0 or chapter_no <= end):
                    return item
        return items[-1]

    def list_volume_arcs(self, work_id: str) -> list[VolumeArc]:
        payload = self._load_payload()
        items = [
            VolumeArc.model_validate(item)
            for item in payload["volume_arcs"].values()
            if item.get("work_id") == work_id
        ]
        return sorted(items, key=lambda item: (item.volume_no, item.updated_at or item.created_at))

    def save_sequence_arc(self, arc: SequenceArc) -> SequenceArc:
        arc = self._normalize_sequence_arc(arc)
        payload = self._load_payload()
        payload["sequence_arcs"][arc.sequence_arc_id] = arc.model_dump(mode="json")
        self._save_payload(payload)
        return arc

    def get_active_sequence_arc(self, work_id: str, chapter_no: int = 0) -> SequenceArc | None:
        items = self.list_sequence_arcs(work_id)
        if not items:
            return None
        if chapter_no > 0:
            for item in items:
                start = int(item.chapter_range.get("from_chapter", 0) or 0)
                end = int(item.chapter_range.get("to_chapter_estimate", 0) or 0)
                if start <= chapter_no and (end == 0 or chapter_no <= end):
                    return item
        return items[-1]

    def list_sequence_arcs(self, work_id: str) -> list[SequenceArc]:
        payload = self._load_payload()
        items = [
            SequenceArc.model_validate(item)
            for item in payload["sequence_arcs"].values()
            if item.get("work_id") == work_id
        ]
        return sorted(items, key=lambda item: (item.seq_no, item.updated_at or item.created_at))

    def _load_payload(self) -> dict[str, dict[str, object]]:
        if not self._file_path.exists():
            return {
                "master_arcs": {},
                "volume_arcs": {},
                "sequence_arcs": {},
            }
        payload = json.loads(self._file_path.read_text(encoding="utf-8"))
        payload.setdefault("master_arcs", {})
        payload.setdefault("volume_arcs", {})
        payload.setdefault("sequence_arcs", {})
        return payload

    def _save_payload(self, payload: dict[str, dict[str, object]]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _normalize_master_arc(arc: MasterArc) -> MasterArc:
        return MasterArc.model_validate({
            key: value
            for key, value in arc.__dict__.items()
            if not key.startswith("_")
        })

    @staticmethod
    def _normalize_volume_arc(arc: VolumeArc) -> VolumeArc:
        return VolumeArc.model_validate({
            key: value
            for key, value in arc.__dict__.items()
            if not key.startswith("_")
        })

    @staticmethod
    def _normalize_sequence_arc(arc: SequenceArc) -> SequenceArc:
        return SequenceArc.model_validate({
            key: value
            for key, value in arc.__dict__.items()
            if not key.startswith("_")
        })
