from __future__ import annotations

from threading import Event, Lock, Thread

from domain.entities.ai.models import WritingTask
from infrastructure.database.repositories.ai.file_direction_plan_store import FileDirectionPlanStore


class _LoadCoordinator:
    def __init__(self) -> None:
        self._lock = Lock()
        self.load_count = 0
        self.first_loaded = Event()
        self.second_loaded = Event()
        self.release_first = Event()

    def after_load(self) -> None:
        with self._lock:
            self.load_count += 1
            call_no = self.load_count
        if call_no == 1:
            self.first_loaded.set()
            self.release_first.wait(timeout=2)
        elif call_no == 2:
            self.second_loaded.set()
            self.release_first.set()


class _CoordinatedDirectionPlanStore(FileDirectionPlanStore):
    def __init__(self, file_path, coordinator: _LoadCoordinator) -> None:
        super().__init__(file_path)
        self._coordinator = coordinator

    def _load_payload(self):
        payload = super()._load_payload()
        self._coordinator.after_load()
        return payload


def test_writing_task_saves_share_one_process_lock_across_store_instances(tmp_path) -> None:
    path = tmp_path / "direction-plan.json"
    coordinator = _LoadCoordinator()
    first_store = _CoordinatedDirectionPlanStore(path, coordinator)
    second_store = _CoordinatedDirectionPlanStore(path, coordinator)
    failures: list[Exception] = []

    def save(store: FileDirectionPlanStore, task_id: str) -> None:
        try:
            store.save_writing_task(WritingTask(writing_task_id=task_id, work_id="work-1"))
        except Exception as exc:  # pragma: no cover - asserted below
            failures.append(exc)

    first = Thread(target=save, args=(first_store, "wt-1"))
    second = Thread(target=save, args=(second_store, "wt-2"))
    first.start()
    assert coordinator.first_loaded.wait(timeout=1)
    second.start()
    if not coordinator.second_loaded.wait(timeout=0.2):
        coordinator.release_first.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert failures == []
    stored_ids = {
        task.writing_task_id
        for task in FileDirectionPlanStore(path).list_writing_tasks("work-1")
    }
    assert stored_ids == {"wt-1", "wt-2"}
