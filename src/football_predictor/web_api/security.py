"""Authentication helpers for the read-only FootLumen API."""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from football_predictor.config.settings import get_settings


def _extract_bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    scheme, separator, token = authorization.partition(" ")
    if separator and scheme.lower() == "bearer" and token.strip():
        return token.strip()
    return None


def require_api_access(
    authorization: str | None = Header(default=None, alias="Authorization"),
    api_key: str | None = Header(default=None, alias="X-FootLumen-Api-Key"),
) -> None:
    """Require API enabled and, by default, a valid read-only token."""

    settings = get_settings()
    if not settings.footlumen_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "api_disabled", "message": "FootLumen API is disabled."},
        )
    if not settings.footlumen_api_read_only:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "read_only_required", "message": "FootLumen API must be read-only."},
        )
    if not settings.footlumen_api_require_token:
        return

    configured_token = settings.footlumen_api_token
    provided_token = api_key or _extract_bearer_token(authorization)
    if not configured_token or not provided_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "api_token_required", "message": "API token required."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not hmac.compare_digest(configured_token, provided_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_api_token", "message": "Invalid API token."},
            headers={"WWW-Authenticate": "Bearer"},
        )
