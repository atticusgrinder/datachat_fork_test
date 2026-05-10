"""Encryption helpers for warehouse credentials."""

import base64
import json
from hashlib import sha256

from cryptography.fernet import Fernet

from app.core.config import ENCRYPTION_KEY


def _get_encryption_key() -> bytes:
    key_bytes = sha256(ENCRYPTION_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key_bytes)


_cipher = Fernet(_get_encryption_key())


def encrypt_credentials(data: dict) -> str:
    """Encrypt warehouse credentials dictionary."""
    return _cipher.encrypt(json.dumps(data).encode()).decode()


def decrypt_credentials(encrypted: str) -> dict:
    """Decrypt warehouse credentials dictionary."""
    return json.loads(_cipher.decrypt(encrypted.encode()).decode())
