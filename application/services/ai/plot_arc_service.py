from __future__ import annotations


class PlotArcQueryService:
    def __init__(self, *, plot_arc_repository, chapter_service) -> None:
        self._plot_arc_repository = plot_arc_repository
        self._chapter_service = chapter_service

    def list_plot_arcs(self, work_id: str) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        master = self._plot_arc_repository.get_master_arc(work_id)
        if master is not None:
            items.append(self._serialize_arc("master_arc", master.master_arc_id, master))
        for item in self._plot_arc_repository.list_volume_arcs(work_id):
            items.append(self._serialize_arc("volume_arc", item.volume_arc_id, item))
        for item in self._plot_arc_repository.list_sequence_arcs(work_id):
            items.append(self._serialize_arc("sequence_arc", item.sequence_arc_id, item))
        return items

    def get_plot_arc(self, *, work_id: str, arc_id: str) -> dict[str, object]:
        for item in self.list_plot_arcs(work_id):
            if item["arc_id"] == arc_id:
                return item
        raise ValueError("plot_arc_not_found")

    def get_plot_arc_status(self, *, work_id: str, chapter_id: str = "") -> dict[str, object]:
        chapter_no = 0
        if chapter_id:
            chapters = self._chapter_service.list_chapters(work_id)
            chapter = next((item for item in chapters if item.id.value == chapter_id), None)
            if chapter is not None:
                chapter_no = int(getattr(chapter, "order_index", 0) or 0)
        master = self._plot_arc_repository.get_master_arc(work_id)
        volume = self._plot_arc_repository.get_active_volume_arc(work_id, chapter_no=chapter_no)
        sequence = self._plot_arc_repository.get_active_sequence_arc(work_id, chapter_no=chapter_no)
        return {
            "master_arc": self._status_payload(master),
            "volume_arc": self._status_payload(volume),
            "sequence_arc": self._status_payload(sequence),
        }

    @staticmethod
    def _serialize_arc(arc_type: str, arc_id: str, item) -> dict[str, object]:  # noqa: ANN001
        return {
            "arc_type": arc_type,
            "arc_id": arc_id,
            "status": item.status.value,
            "quality_level": item.quality_level.value,
            "stale_status": item.stale_status,
            "warning_codes": list(item.warning_codes),
            "data": item.model_dump(mode="json"),
        }

    @staticmethod
    def _status_payload(item) -> dict[str, object]:
        if item is None:
            return {"status": "empty", "quality_level": "placeholder", "warning_codes": []}
        return {
            "status": item.status.value,
            "quality_level": item.quality_level.value,
            "warning_codes": list(item.warning_codes),
            "stale_status": item.stale_status,
        }
