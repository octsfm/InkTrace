from __future__ import annotations

import base64
import hashlib
import json
import time
from pathlib import Path


class EncryptedTemporarySensitiveTextStore:
    def __init__(self, root: Path | str, *, secret: str, ttl_seconds: int = 1800) -> None:
        if not secret:
            raise ValueError("temporary_sensitive_store_secret_missing")
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._key = hashlib.sha256(secret.encode("utf-8")).digest()
        self._ttl_seconds = ttl_seconds
        self.cleanup_expired()

    def put(self, reference_session_id: str, texts: list[str]) -> None:
        raw = json.dumps(texts, ensure_ascii=False).encode("utf-8")
        encrypted = bytes(value ^ self._key[index % len(self._key)] for index, value in enumerate(raw))
        payload = {
            "expires_at": int(time.time()) + self._ttl_seconds,
            "ciphertext": base64.b64encode(encrypted).decode("ascii"),
        }
        self._path(reference_session_id).write_text(json.dumps(payload), encoding="utf-8")

    def get(self, reference_session_id: str) -> list[str]:
        path = self._path(reference_session_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if int(payload["expires_at"]) <= int(time.time()):
            self.delete(reference_session_id)
            raise ValueError("temporary_sensitive_text_expired")
        encrypted = base64.b64decode(payload["ciphertext"])
        raw = bytes(value ^ self._key[index % len(self._key)] for index, value in enumerate(encrypted))
        return list(json.loads(raw.decode("utf-8")))

    def delete(self, reference_session_id: str) -> None:
        self._path(reference_session_id).unlink(missing_ok=True)

    def exists(self, reference_session_id: str) -> bool:
        return self._path(reference_session_id).exists()

    def cleanup_expired(self) -> int:
        removed = 0
        now = int(time.time())
        for path in self._root.glob("*.secret"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if int(payload.get("expires_at", 0)) <= now:
                    path.unlink(missing_ok=True)
                    removed += 1
            except Exception:
                path.unlink(missing_ok=True)
                removed += 1
        return removed

    def _path(self, reference_session_id: str) -> Path:
        safe_id = hashlib.sha256(reference_session_id.encode("utf-8")).hexdigest()
        return self._root / f"{safe_id}.secret"

