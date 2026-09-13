"""Secure opaque token generation and hashing."""

import hashlib
import secrets


def generate_opaque_token() -> str:
    """Generate a cryptographically secure opaque session token."""
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    """Return a SHA-256 hash suitable for database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()