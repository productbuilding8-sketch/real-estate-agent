"""Symmetric encryption helpers for storing integration credentials at rest."""

from __future__ import annotations

import base64
import hashlib
from typing import Any


def _fernet(secret_key: str) -> Any:
    from cryptography.fernet import Fernet

    key = base64.urlsafe_b64encode(hashlib.sha256(secret_key.encode()).digest())
    return Fernet(key)


def encrypt(plaintext: str, secret_key: str) -> str:
    """Encrypt *plaintext* and return a URL-safe base64 token."""
    result: str = _fernet(secret_key).encrypt(plaintext.encode()).decode()
    return result


def decrypt(token: str, secret_key: str) -> str:
    """Decrypt a token produced by :func:`encrypt`."""
    result: str = _fernet(secret_key).decrypt(token.encode()).decode()
    return result
