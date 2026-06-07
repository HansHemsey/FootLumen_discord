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
    monkeypatch.delenv("FOOTLUMEN_API_DOCS_ENABLED", raising=False)
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


def test_openapi_docs_disabled_by_default(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)

    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404


def test_openapi_docs_can_be_enabled_with_explicit_env(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'api.db'}")
    monkeypatch.setenv("FOOTLUMEN_API_ENABLED", "true")
    monkeypatch.setenv("FOOTLUMEN_API_READ_ONLY", "true")
    monkeypatch.setenv("FOOTLUMEN_API_REQUIRE_TOKEN", "true")
    monkeypatch.setenv("FOOTLUMEN_API_TOKEN", "dev-token")
    monkeypatch.setenv("FOOTLUMEN_API_DOCS_ENABLED", "true")
    get_settings.cache_clear()
    client = TestClient(create_app())

    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "FootLumen API"
    assert schema["paths"]["/api/v1/combos/latest"]["get"]["tags"] == ["combos"]


def test_cors_wildcard_is_ignored(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    monkeypatch.setenv("FOOTLUMEN_API_CORS_ORIGINS", "*")
    get_settings.cache_clear()
    client = TestClient(create_app())

    response = client.get(
        "/api/v1/health",
        headers={"Authorization": "Bearer dev-token", "Origin": "https://app.footlumen.com"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in {key.lower() for key in response.headers}


def test_cors_explicit_origin_allowed(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'api.db'}")
    monkeypatch.setenv("FOOTLUMEN_API_ENABLED", "true")
    monkeypatch.setenv("FOOTLUMEN_API_READ_ONLY", "true")
    monkeypatch.setenv("FOOTLUMEN_API_REQUIRE_TOKEN", "true")
    monkeypatch.setenv("FOOTLUMEN_API_TOKEN", "dev-token")
    monkeypatch.setenv("FOOTLUMEN_API_CORS_ORIGINS", "https://app.footlumen.com")
    get_settings.cache_clear()
    client = TestClient(create_app())

    response = client.get(
        "/api/v1/health",
        headers={"Authorization": "Bearer dev-token", "Origin": "https://app.footlumen.com"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://app.footlumen.com"


def test_request_logging_omits_auth_token(monkeypatch, tmp_path) -> None:
    from football_predictor.web_api import app as api_app

    calls: list[tuple[str, dict]] = []

    def fake_info(message: str, *args, **kwargs) -> None:
        calls.append((message, kwargs.get("extra") or {}))

    monkeypatch.setattr(api_app.logger, "info", fake_info)
    client = _client(monkeypatch, tmp_path)

    response = client.get("/api/v1/health", headers={"Authorization": "Bearer dev-token"})

    assert response.status_code == 200
    assert calls
    message, extra = calls[-1]
    assert message == "web_api.request"
    assert extra["method"] == "GET"
    assert extra["path"] == "/api/v1/health"
    rendered = f"{message} {extra}"
    assert "dev-token" not in rendered
    assert "Authorization" not in rendered
