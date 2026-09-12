"""Application-level encryption for tenant secrets."""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class EncryptionError(RuntimeError):
    """Raised when application secret encryption is unavailable or invalid."""


def _fernet() -> Fernet:
    key = settings.data_protection_key

    if not key:
        raise EncryptionError(
            "DATA_PROTECTION_KEY must be configured before encrypting secrets."
        )

    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise EncryptionError("DATA_PROTECTION_KEY is not a valid Fernet key.") from exc


def encrypt_secret(value: str) -> bytes:
    """Encrypt a secret before persistence."""
    return _fernet().encrypt(value.encode("utf-8"))


def decrypt_secret(value: bytes) -> str:
    """Decrypt a persisted secret."""
    try:
        return _fernet().decrypt(value).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise EncryptionError("Unable to decrypt stored secret.") from exc