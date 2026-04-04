"""
encryption.py — Audit Log Encryption Utility

Secures the audit JSON blobs using Fernet symmetric encryption before
they are uploaded to the public IPFS network.

Usage:
    from utils.encryption import encrypt_data, decrypt_data
    
    encrypted_str = encrypt_data({"my": "data"})
    original_dict = decrypt_data(encrypted_str)
"""

import json
import os
import logging
from typing import Any
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

def _get_cipher() -> Fernet:
    """Initialize the encryption cipher from the environment key."""
    key = os.environ.get("ENCRYPTION_KEY", "")
    
    if not key or key == "paste_your_encryption_key_here":
        # Fallback for development if no key is set yet
        logger.warning("No ENCRYPTION_KEY found in environment! Using an insecure temporary key across restarts. Please fix this in .env!")
        key = Fernet.generate_key().decode()
        os.environ["ENCRYPTION_KEY"] = key # store it temporarily for this runtime

    try:
        return Fernet(key.encode())
    except ValueError as e:
        raise ValueError("Invalid ENCRYPTION_KEY format. Must be a valid 32-byte url-safe base64 string.") from e

def encrypt_data(data: dict[str, Any]) -> str:
    """
    Encrypts a dictionary into a secure string.
    """
    cipher = _get_cipher()
    
    # 1. Convert dict to JSON string
    json_str = json.dumps(data)
    
    # 2. Convert string to bytes
    byte_data = json_str.encode("utf-8")
    
    # 3. Encrypt the bytes
    encrypted_bytes = cipher.encrypt(byte_data)
    
    # 4. Return as string
    return encrypted_bytes.decode("utf-8")

def decrypt_data(encrypted_str: str) -> dict[str, Any]:
    """
    Decrypts a secure string back into the original dictionary.
    """
    cipher = _get_cipher()
    
    encrypted_bytes = encrypted_str.encode("utf-8")
    decrypted_bytes = cipher.decrypt(encrypted_bytes)
    
    json_str = decrypted_bytes.decode("utf-8")
    return json.loads(json_str)
