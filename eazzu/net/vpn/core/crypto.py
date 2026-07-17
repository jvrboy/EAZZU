"""
Cryptography helpers for UltraVPN
- WireGuard-style Curve25519 keypair generation
- Symmetric encryption of stored credentials (Fernet / AES-GCM)
- Secure random utilities
"""
import os
import base64
import hashlib
import secrets
from typing import Tuple

try:
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


def generate_wireguard_keypair() -> Tuple[str, str]:
    """
    Generate a WireGuard-compatible Curve25519 keypair.
    Returns (private_key_b64, public_key_b64).
    """
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography package is required. Install with: pip install cryptography")

    priv = X25519PrivateKey.generate()
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return (
        base64.b64encode(priv_bytes).decode("ascii"),
        base64.b64encode(pub_bytes).decode("ascii"),
    )


def generate_preshared_key() -> str:
    """Generate a 32-byte preshared key encoded in base64."""
    return base64.b64encode(secrets.token_bytes(32)).decode("ascii")


def derive_key_from_password(password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
    """
    Derive a Fernet-compatible key from a password using scrypt.
    Returns (key, salt).
    """
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography package required")
    if salt is None:
        salt = os.urandom(16)
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
    return key, salt


def encrypt_data(data: str, password: str) -> str:
    """Encrypt string with password, output: base64(salt)|base64(token)"""
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography package required")
    key, salt = derive_key_from_password(password)
    token = Fernet(key).encrypt(data.encode("utf-8"))
    return base64.b64encode(salt).decode() + "|" + token.decode()


def decrypt_data(payload: str, password: str) -> str:
    """Decrypt string previously produced by encrypt_data."""
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography package required")
    salt_b64, token = payload.split("|", 1)
    salt = base64.b64decode(salt_b64)
    key, _ = derive_key_from_password(password, salt)
    return Fernet(key).decrypt(token.encode()).decode("utf-8")


def hash_fingerprint(data: str) -> str:
    """Short fingerprint for a public key or config (first 16 hex chars of SHA-256)."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]
