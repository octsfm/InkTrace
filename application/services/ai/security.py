from __future__ import annotations

import base64
import hashlib
import hmac
import os


class SettingsCipher:
    def __init__(self, secret: str | None = None) -> None:
        raw_secret = secret or os.getenv("INKTRACE_AI_SETTINGS_SECRET", "inktrace-local-dev-secret")
        self._secret = raw_secret.encode("utf-8")

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        nonce = os.urandom(16)
        plaintext_bytes = plaintext.encode("utf-8")
        ciphertext = self._xor_with_keystream(plaintext_bytes, nonce)
        mac = hmac.new(self._secret, nonce + ciphertext, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(nonce + mac + ciphertext).decode("ascii")

    def decrypt(self, payload: str) -> str:
        if not payload:
            return ""
        raw = base64.urlsafe_b64decode(payload.encode("ascii"))
        nonce = raw[:16]
        mac = raw[16:48]
        ciphertext = raw[48:]
        expected = hmac.new(self._secret, nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected):
            raise ValueError("settings_cipher_invalid_payload")
        return self._xor_with_keystream(ciphertext, nonce).decode("utf-8")

    def _xor_with_keystream(self, data: bytes, nonce: bytes) -> bytes:
        keystream = bytearray()
        counter = 0
        while len(keystream) < len(data):
            block = hashlib.sha256(self._secret + nonce + counter.to_bytes(4, "big")).digest()
            keystream.extend(block)
            counter += 1
        return bytes(left ^ right for left, right in zip(data, keystream))
