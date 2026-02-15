"""
Encryption utilities for securing sensitive configuration data.
Uses Fernet symmetric encryption from the cryptography library.
All sensitive settings (API keys, passwords, tokens) are encrypted
at rest in the database ConfigStore.
"""

import os
import base64
import hashlib
import json
from cryptography.fernet import Fernet, InvalidToken


def _get_encryption_key():
    """
    Derive a Fernet key from the ENCRYPTION_KEY environment variable.
    Falls back to SECRET_KEY if ENCRYPTION_KEY is not set.
    """
    raw_key = os.environ.get("ENCRYPTION_KEY") or os.environ.get(
        "SECRET_KEY", "change_secret_key"
    )
    # Derive a 32-byte key using SHA-256, then base64 encode for Fernet
    derived = hashlib.sha256(raw_key.encode()).digest()
    return base64.urlsafe_b64encode(derived)


def encrypt_value(plaintext):
    """Encrypt a string value. Returns base64-encoded ciphertext."""
    if not plaintext:
        return plaintext
    key = _get_encryption_key()
    f = Fernet(key)
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext):
    """Decrypt a base64-encoded ciphertext. Returns plaintext string."""
    if not ciphertext:
        return ciphertext
    key = _get_encryption_key()
    f = Fernet(key)
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        # If decryption fails, return the original value
        # (may be stored unencrypted from before encryption was enabled)
        return ciphertext


def encrypt_dict(data):
    """Encrypt all string values in a dictionary."""
    encrypted = {}
    for k, v in data.items():
        if isinstance(v, str) and v:
            encrypted[k] = encrypt_value(v)
        else:
            encrypted[k] = v
    return encrypted


def decrypt_dict(data):
    """Decrypt all string values in a dictionary."""
    decrypted = {}
    for k, v in data.items():
        if isinstance(v, str) and v:
            decrypted[k] = decrypt_value(v)
        else:
            decrypted[k] = v
    return decrypted


def encrypt_json(data):
    """Encrypt a JSON-serializable object as a single encrypted blob."""
    if not data:
        return data
    plaintext = json.dumps(data)
    return encrypt_value(plaintext)


def decrypt_json(ciphertext):
    """Decrypt a single encrypted blob back to a JSON object."""
    if not ciphertext:
        return ciphertext
    plaintext = decrypt_value(ciphertext)
    try:
        return json.loads(plaintext)
    except (json.JSONDecodeError, TypeError):
        return plaintext
