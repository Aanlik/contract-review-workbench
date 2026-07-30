"""API key encryption at rest using Fernet symmetric encryption.

Keys are derived from a master key stored in the environment variable
CONTRACT_REVIEW_MASTER_KEY or auto-generated on first run and persisted
in the data directory.
"""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.fernet import Fernet


_MASTER_KEY_ENV = "CONTRACT_REVIEW_MASTER_KEY"
_KEY_FILE = Path("./data/.master_key")


def _get_or_create_master_key() -> bytes:
    env_key = os.environ.get(_MASTER_KEY_ENV)
    if env_key:
        return env_key.encode()
    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _KEY_FILE.exists():
        return _KEY_FILE.read_bytes().strip()
    key = Fernet.generate_key()
    _KEY_FILE.write_bytes(key + b"\n")
    os.chmod(_KEY_FILE, 0o600)
    return key


_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_get_or_create_master_key())
    return _fernet


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt an API key for storage."""
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    """Decrypt an API key for use."""
    if not ciphertext:
        return ciphertext
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except Exception:
        # If decryption fails, assume it's stored in plaintext (migration path)
        return ciphertext
