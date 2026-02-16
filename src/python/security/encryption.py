"""
Encryption utilities for data at rest.

Provides symmetric encryption for caching FHIR data, tokens, and other
sensitive values that need to be stored temporarily. Uses Fernet
(AES-128-CBC with HMAC-SHA256) from the cryptography library, with a
pure-Python HMAC fallback for environments without cryptography installed.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any

from src.python.utils.config import settings
from src.python.utils.logging import get_logger

logger = get_logger(__name__)


class EncryptionManager:
    """
    Manages encryption/decryption for sensitive data at rest.

    Attempts to use Fernet (cryptography library) for strong encryption.
    Falls back to HMAC-based obfuscation if cryptography is not installed.
    """

    def __init__(self, key_path: str | None = None):
        """
        Initialize the encryption manager.

        Args:
            key_path: Path to encryption key file (defaults to settings)
        """
        self._key_path = Path(key_path or settings.encryption_key_path)
        self._fernet = None
        self._raw_key: bytes = b""
        self._method = "hmac_obfuscate"

        self._initialize_key()

        logger.info(
            "encryption_manager_initialized",
            method=self._method,
        )

    def _initialize_key(self) -> None:
        """Load or generate the encryption key."""
        if self._key_path.exists():
            self._raw_key = self._key_path.read_bytes().strip()
        else:
            self._raw_key = self._generate_key()
            self._key_path.parent.mkdir(parents=True, exist_ok=True)
            self._key_path.write_bytes(self._raw_key)
            logger.info("encryption_key_generated", path=str(self._key_path))

        # Try to use Fernet if cryptography is installed
        try:
            from cryptography.fernet import Fernet

            # Ensure key is valid Fernet key (32 bytes, base64-encoded)
            if len(self._raw_key) == 44:
                self._fernet = Fernet(self._raw_key)
                self._method = "fernet"
            else:
                # Derive a Fernet-compatible key
                derived = base64.urlsafe_b64encode(
                    hashlib.sha256(self._raw_key).digest()
                )
                self._fernet = Fernet(derived)
                self._method = "fernet"
        except ImportError:
            logger.warning(
                "cryptography_not_installed",
                fallback="hmac_obfuscate",
            )

    @staticmethod
    def _generate_key() -> bytes:
        """Generate a new encryption key."""
        try:
            from cryptography.fernet import Fernet

            return Fernet.generate_key()
        except ImportError:
            return base64.urlsafe_b64encode(os.urandom(32))

    @property
    def method(self) -> str:
        """Current encryption method."""
        return self._method

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded ciphertext
        """
        data = plaintext.encode("utf-8")

        if self._fernet is not None:
            return self._fernet.encrypt(data).decode("utf-8")

        # Fallback: XOR with HMAC-derived keystream
        return self._hmac_obfuscate(data)

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a ciphertext string.

        Args:
            ciphertext: Base64-encoded ciphertext from encrypt()

        Returns:
            Original plaintext string
        """
        if self._fernet is not None:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

        return self._hmac_deobfuscate(ciphertext)

    def encrypt_dict(self, data: dict[str, Any]) -> str:
        """Encrypt a dictionary as JSON."""
        return self.encrypt(json.dumps(data))

    def decrypt_dict(self, ciphertext: str) -> dict[str, Any]:
        """Decrypt a dictionary from encrypted JSON."""
        return json.loads(self.decrypt(ciphertext))

    def _hmac_obfuscate(self, data: bytes) -> str:
        """HMAC-based obfuscation fallback (not cryptographically secure encryption)."""
        nonce = os.urandom(16)
        keystream = self._derive_keystream(nonce, len(data))
        obfuscated = bytes(a ^ b for a, b in zip(data, keystream))
        payload = nonce + obfuscated
        return base64.urlsafe_b64encode(payload).decode("utf-8")

    def _hmac_deobfuscate(self, encoded: str) -> str:
        """Reverse HMAC-based obfuscation."""
        payload = base64.urlsafe_b64decode(encoded.encode("utf-8"))
        nonce = payload[:16]
        obfuscated = payload[16:]
        keystream = self._derive_keystream(nonce, len(obfuscated))
        plaintext = bytes(a ^ b for a, b in zip(obfuscated, keystream))
        return plaintext.decode("utf-8")

    def _derive_keystream(self, nonce: bytes, length: int) -> bytes:
        """Derive a keystream using HMAC-SHA256 in counter mode."""
        keystream = b""
        counter = 0
        while len(keystream) < length:
            block = hmac.new(
                self._raw_key,
                nonce + counter.to_bytes(4, "big"),
                hashlib.sha256,
            ).digest()
            keystream += block
            counter += 1
        return keystream[:length]
