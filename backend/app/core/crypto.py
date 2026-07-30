"""API key encryption at rest using Fernet symmetric encryption.

Keys are derived from a master key stored in the environment variable
CONTRACT_REVIEW_MASTER_KEY or auto-generated on first run and persisted
in the data directory.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet


_MASTER_KEY_ENV = "CONTRACT_REVIEW_MASTER_KEY"


def _get_key_file() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path.cwd()
    key_dir = base / "data"
    key_dir.mkdir(parents=True, exist_ok=True)
    return key_dir / ".master_key"


_KEY_FILE: Path | None = None


def _get_or_create_master_key() -> bytes:
    global _KEY_FILE
    if _KEY_FILE is None:
        _KEY_FILE = _get_key_file()

    env_key = os.environ.get(_MASTER_KEY_ENV)
    if env_key:
        return env_key.encode()

    if _KEY_FILE.exists():
        return _KEY_FILE.read_bytes().strip()

    key = Fernet.generate_key()
    _KEY_FILE.write_bytes(key + b"\n")
    try:
        os.chmod(_KEY_FILE, 0o600)
    except OSError:
        pass  # Windows doesn't support chmod the same way
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
