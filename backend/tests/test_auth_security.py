from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.common.tenant_context import (
    TenantAccessViolationError,
    TenantContextMissingError,
    get_current_tenant_id,
    reset_current_tenant_id,
    set_authenticated_identity,
    set_current_tenant_id,
    system_access,
)
from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.tenant_isolation import (
    enforce_tenant_scope,
    stamp_and_validate_tenant_rows,
)
from app.identity.jwt_service import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
)
from app.identity.service import hash_refresh_token
from app.knowledge.models import KnowledgeItem
from app.main import app
from app.tenancy.models import Tenant


@pytest.fixture(autouse=True)
def jwt_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        settings,
        "jwt_secret_key",
        "test-secret-that-is-not-for-production",
    )
    monkeypatch.setattr(settings, "jwt_issuer", "test-issuer")
    monkeypatch.setattr(settings, "jwt_audience", "test-audience")


def test_argon2_password_hashing() -> None:
    password_hash = hash_password("password1")

    assert password_hash.startswith("$argon2id$")
    assert verify_password("password1", password_hash)
    assert not verify_password("incorrect", password_hash)


def test_jwt_claims_and_invalid_or_expired_tokens() -> None:
    tenant_id = str(uuid4())

    token = create_access_token(
        user_id="user-1",
        email="person@example.com",
        tenant_id=tenant_id,
    )

    claims = decode_access_token(token)

    assert {"sub", "email", "tenantId", "jti"} <= set(claims)
    assert claims["tenantId"] == tenant_id

    expired = jwt.encode(
        {
            "sub": "user-1",
            "email": "person@example.com",
            "tenantId": tenant_id,
            "jti": "x",
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(expired)

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token + "tampered")


def test_refresh_hash_does_not_store_raw_token() -> None:
    raw = "raw-refresh-token"

    assert hash_refresh_token(raw) != raw
    assert len(hash_refresh_token(raw)) == 64


def test_tenant_context_is_request_local_and_system_access_is_explicit() -> None:
    tenant_id = uuid4()

    token = set_authenticated_identity("user-1", tenant_id)

    try:
        assert get_current_tenant_id() == tenant_id

        with system_access():
            assert get_current_tenant_id() is None

        assert get_current_tenant_id() == tenant_id

    finally:
        reset_current_tenant_id(token)

    assert get_current_tenant_id() is None


def test_new_rows_are_stamped_and_cross_tenant_writes_rejected() -> None:
    tenant_id = uuid4()
    row = KnowledgeItem(item_type="Faq", payload={})

    token = set_current_tenant_id(tenant_id)

    try:
        stamp_and_validate_tenant_rows(
            SimpleNamespace(new={row}, dirty=set()),
            None,
            None,
        )

        assert row.tenant_id == tenant_id

        other = KnowledgeItem(
            tenant_id=uuid4(),
            item_type="Faq",
            payload={},
        )

        with pytest.raises(TenantAccessViolationError):
            stamp_and_validate_tenant_rows(
                SimpleNamespace(new={other}, dirty=set()),
                None,
                None,
            )

    finally:
        reset_current_tenant_id(token)


def test_unscoped_tenant_query_is_rejected_and_scoped_query_gets_criteria() -> None:
    statement = select(KnowledgeItem)

    state = SimpleNamespace(
        is_select=True,
        is_update=False,
        is_delete=False,
        bind_mapper=KnowledgeItem.__mapper__,
        statement=statement,
    )

    with pytest.raises(TenantContextMissingError):
        enforce_tenant_scope(state)

    token = set_current_tenant_id(uuid4())

    try:
        scoped = SimpleNamespace(
            is_select=True,
            is_update=False,
            is_delete=False,
            bind_mapper=KnowledgeItem.__mapper__,
            statement=statement,
        )

        enforce_tenant_scope(scoped)

        assert len(scoped.statement._with_options) == 8

    finally:
        reset_current_tenant_id(token)


def _collect_paths(routes) -> set[str]:
    paths: set[str] = set()

    for route in routes:
        if hasattr(route, "path"):
            paths.add(route.path)

        original_router = getattr(route, "original_router", None)

        if original_router is not None:
            paths.update(_collect_paths(original_router.routes))

    return paths


def test_auth_routes_are_registered_and_me_requires_bearer_token() -> None:
    paths = _collect_paths(app.routes)

    assert {
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/refresh",
        "/api/auth/logout",
        "/api/auth/me",
    } <= paths

    response = TestClient(app).get("/api/auth/me")

    assert response.status_code == 401
    
def test_agent_and_llm_routes_are_registered_and_protected() -> None:
    paths = _collect_paths(app.routes)

    assert {
        "/api/agent",
        "/api/agent/rotate-site-key",
        "/api/agent/llm",
    } <= paths

    client = TestClient(app)

    assert client.get("/api/agent").status_code == 401
    assert client.get("/api/agent/llm").status_code == 401

    assert client.put(
        "/api/agent/llm",
        json={
            "provider": "OpenRouter",
            "api_key": "test-secret",
        },
    ).status_code == 401

    assert client.delete("/api/agent/llm").status_code == 401