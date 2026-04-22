from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class IOutlineDocumentRepository(ABC):
    @abstractmethod
    def save_document(
        self,
        *,
        novel_id: str,
        raw_content: str,
        digest_json: Dict[str, Any],
        raw_hash: str,
        digest_version: str,
    ) -> None:
        pass

    @abstractmethod
    def find_by_novel_id(self, novel_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def delete_by_novel_id(self, novel_id: str) -> None:
        pass
