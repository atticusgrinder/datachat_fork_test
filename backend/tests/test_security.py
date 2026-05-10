"""Tests for core/security.py — Fernet encryption helpers."""

import json

import pytest


class TestEncryptDecrypt:
    def test_roundtrip(self):
        from app.core.security import encrypt_credentials, decrypt_credentials

        data = {"host": "localhost", "port": 5432, "password": "s3cret"}
        encrypted = encrypt_credentials(data)
        assert isinstance(encrypted, str)
        assert encrypted != json.dumps(data)
        decrypted = decrypt_credentials(encrypted)
        assert decrypted == data

    def test_different_data_different_ciphertext(self):
        from app.core.security import encrypt_credentials

        e1 = encrypt_credentials({"key": "val1"})
        e2 = encrypt_credentials({"key": "val2"})
        assert e1 != e2

    def test_tampered_ciphertext_raises(self):
        from app.core.security import encrypt_credentials, decrypt_credentials

        encrypted = encrypt_credentials({"a": "b"})
        tampered = encrypted[:-5] + "XXXXX"
        with pytest.raises(Exception):
            decrypt_credentials(tampered)

    def test_invalid_ciphertext_raises(self):
        from app.core.security import decrypt_credentials

        with pytest.raises(Exception):
            decrypt_credentials("not-valid-ciphertext")

    def test_empty_dict(self):
        from app.core.security import encrypt_credentials, decrypt_credentials

        encrypted = encrypt_credentials({})
        assert decrypt_credentials(encrypted) == {}

    def test_nested_data(self):
        from app.core.security import encrypt_credentials, decrypt_credentials

        data = {
            "credentials_json": '{"type": "service_account", "project_id": "proj"}',
            "project_id": "proj",
        }
        encrypted = encrypt_credentials(data)
        decrypted = decrypt_credentials(encrypted)
        assert decrypted == data

    def test_encryption_key_derivation(self):
        from app.core.security import _get_encryption_key

        key = _get_encryption_key()
        assert isinstance(key, bytes)
        assert len(key) == 44  # base64-encoded 32-byte key
