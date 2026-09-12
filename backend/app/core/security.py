"""Non-authentication security primitives for later identity and widget work."""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password with Argon2id; plaintext is never persisted."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Safely verify an Argon2id password hash."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def hash_token(token: str) -> str:
    """Return a stable SHA-256 digest suitable for opaque-token storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_opaque_token() -> str:
    """Create a cryptographically random URL-safe opaque token."""
    return secrets.token_urlsafe(32)
