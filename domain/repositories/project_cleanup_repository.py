from abc import ABC, abstractmethod


class IProjectCleanupRepository(ABC):
    @abstractmethod
    def cleanup_project_payloads(self, project_id: str, novel_id: str) -> None:
        """Delete project/novel related derived payloads in batch."""
        pass
