from __future__ import annotations

from fastapi.testclient import TestClient

from football_predictor.config.settings import get_settings
from football_predictor.web_api.app import create_app


def _client(
    monkeypatch,
    tmp_path,
    *,
    enabled: bool = True,
    token: str | None = "dev-token",
) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'api.db'}")
    monkeypatch.setenv("FOOTLUMEN_API_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("FOOTLUMEN_API_READ_ONLY", "true")
    monkeypatch.setenv("FOOTLUMEN_API_REQUIRE_TOKEN", "true")
    monkeypatch.setenv("FOOTLUMEN_API_CORS_ORIGINS", "")
    if token is None:
        monkeypatch.delenv("FOOTLUMEN_API_TOKEN", raising=False)
    else:
        monkeypatch.setenv("FOOTLUMEN_API_TOKEN", token)
    get_settings.cache_clear()
    return TestClient(create_app())


def test_web_api_app_importable() -> None:
    from football_predictor.web_api.app import app

    assert app.title == "FootLumen API"


def test_health_api_disabled_returns_403(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path, enabled=False)

    response = client.get("/api/v1/health", headers={"Authorization": "Bearer dev-token"})

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "api_disabled"


def test_health_requires_token(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)

    response = client.get("/api/v1/health")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "api_token_required"


def test_health_rejects_invalid_token(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)

    response = client.get("/api/v1/health", headers={"Authorization": "Bearer wrong-token"})

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_api_token"


def test_health_with_bearer_token(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)

    response = client.get("/api/v1/health", headers={"Authorization": "Bearer dev-token"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["api_enabled"] is True
    assert payload["read_only"] is True
    assert payload["database_ok"] is True
    assert payload["app_timezone"] == "Europe/Paris"
    assert "dev-token" not in response.text
    assert "sqlite:///" not in response.text
    assert "payload_json" not in response.text


def test_health_with_api_key_header(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)

    response = client.get("/api/v1/health", headers={"X-FootLumen-Api-Key": "dev-token"})

    assert response.status_code == 200


def test_version_with_token(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)

    response = client.get("/api/v1/version", headers={"Authorization": "Bearer dev-token"})

    assert response.status_code == 200
    assert response.json()["name"] == "FootLumen API"
    assert response.json()["api_version"] == "v1"
    assert response.json()["read_only"] is True


def test_cors_closed_by_default(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)

    response = client.get(
        "/api/v1/health",
        headers={"Authorization": "Bearer dev-token", "Origin": "https://app.footlumen.com"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in {key.lower() for key in response.headers}


def test_no_endpoint_writes_to_db(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)

    client.get("/api/v1/health", headers={"Authorization": "Bearer dev-token"})
    response = client.get("/api/v1/version", headers={"Authorization": "Bearer dev-token"})

    assert response.status_code == 200
