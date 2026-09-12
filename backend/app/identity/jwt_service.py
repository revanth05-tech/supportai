"""JWT access-token creation and strict validation."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from jwt import InvalidTokenError

from app.core.config import settings


class InvalidAccessTokenError(ValueError):
    pass


def _secret() -> str:
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY must be configured before issuing or validating access tokens.")
    return settings.jwt_secret_key


def create_access_token(*, user_id: str, email: str, tenant_id: str, is_demo: bool = False) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "email": email,
        "tenantId": tenant_id,
        "jti": str(uuid4()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if is_demo:
        payload["is_demo"] = True
    return jwt.encode(payload, _secret(), algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, object]:
    try:
        payload = jwt.decode(
            token,
            _secret(),
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            leeway=30,
            options={"require": ["sub", "email", "tenantId", "jti", "exp", "iss", "aud"]},
        )
    except InvalidTokenError as exc:
        raise InvalidAccessTokenError("Invalid or expired access token.") from exc
    return payload


def is_demo_claim(payload: dict[str, object]) -> bool:
    """Future routes can use this without creating a demo account today."""
    return payload.get("is_demo") is True
