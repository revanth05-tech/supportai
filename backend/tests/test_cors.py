"""Regression tests for the credentialed local dashboard CORS policy."""

from fastapi.testclient import TestClient

from app.main import app


def test_credentialed_local_cors_preflight_and_error_response() -> None:
    client = TestClient(app)
    origin = "http://localhost:3000"

    preflight = client.options(
        "/api/auth/register",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == origin
    assert preflight.headers["access-control-allow-credentials"] == "true"

    # Validation errors must carry CORS headers too, otherwise the browser
    # reports a misleading generic "Failed to fetch" message.
    response = client.post(
        "/api/auth/register",
        headers={"Origin": origin},
        json={},
    )

    assert response.status_code == 422
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"


def test_local_loopback_cors_origin_is_explicitly_supported() -> None:
    response = TestClient(app).options(
        "/api/auth/register",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
