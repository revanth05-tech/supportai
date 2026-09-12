"""Non-authentication security primitives for later identity and widget work."""

import hashlib
import secrets


def hash_token(token: str) -> str:
    """Return a stable SHA-256 digest suitable for opaque-token storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_opaque_token() -> str:
    """Create a cryptographically random URL-safe opaque token."""
    return secrets.token_urlsafe(32)
