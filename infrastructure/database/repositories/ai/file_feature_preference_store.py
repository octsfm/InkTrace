from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

from domain.repositories.ai.feature_preference_repository import FeaturePreferenceRepository
from infrastructure.database.session import get_database_path


class FeaturePreferenceConflictError(RuntimeError):
    error_code = "idempotency_conflict"


class FileFeaturePreferenceStore(FeaturePreferenceRepository):
    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else get_database_path().with_name("feature_preferences.json")
        self._lock = threading.RLock()

    def _read_payload(self) -> dict[str, object]:
        if not self._file_path.exists():
            return {"preferences": {}, "receipts": {}}
        payload = json.loads(self._file_path.read_text(encoding="utf-8"))
        return {
            "preferences": dict(payload.get("preferences") or {}),
            "receipts": dict(payload.get("receipts") or {}),
        }

    def load(self) -> dict[str, bool]:
        with self._lock:
            payload = self._read_payload()
            return {str(key): bool(value) for key, value in dict(payload["preferences"]).items()}

    def save_preference(
        self,
        *,
        feature_key: str,
        enabled: bool,
        idempotency_key: str,
    ) -> dict[str, bool]:
        key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        fingerprint = f"{feature_key}:{int(enabled)}"
        with self._lock:
            payload = self._read_payload()
            receipts = dict(payload["receipts"])
            existing = receipts.get(key_hash)
            if existing is not None and existing != fingerprint:
                raise FeaturePreferenceConflictError("idempotency_conflict")
            preferences = {str(key): bool(value) for key, value in dict(payload["preferences"]).items()}
            if existing is None:
                preferences[feature_key] = enabled
                receipts[key_hash] = fingerprint
                self._file_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path = self._file_path.with_suffix(".tmp")
                temp_path.write_text(
                    json.dumps({"preferences": preferences, "receipts": receipts}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                temp_path.replace(self._file_path)
            return preferences
