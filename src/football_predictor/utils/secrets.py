"""Secret-safe formatting helpers."""

from __future__ import annotations

import hashlib
import re

SECRET_REDACTION = "<redacted>"
_DISCORD_WEBHOOK_RE = re.compile(
    r"https://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/[^\s'\"<>`]+",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"\b(Bearer)\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"\b((?:api[_-]?football[_-]?key|api[_-]?key|token|secret|webhook|authorization)"
    r"\s*[:=]\s*)['\"]?[^'\"\s,;<>]+",
    re.IGNORECASE,
)
_DISCORD_TOKEN_RE = re.compile(
    r"\b[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{20,}\b"
)


def secret_configured(value: str | None) -> bool:
    return bool(value and value.strip())


def secret_fingerprint(value: str | None) -> str | None:
    """Return a short non-reversible fingerprint for logs."""
    if not value or not value.strip():
        return None
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()[:8]


def hash_secret(value: str | None) -> str | None:
    """Public alias for short non-reversible secret hashes."""
    return secret_fingerprint(value)


def describe_secret(name: str, value: str | None) -> str:
    configured = secret_configured(value)
    fingerprint = secret_fingerprint(value)
    if configured and fingerprint:
        return f"{name} configured: yes, hash={fingerprint}"
    return f"{name} configured: no"


def mask_secret(value: str | None) -> str:
    if not secret_configured(value):
        return ""
    fingerprint = secret_fingerprint(value)
    return f"<secret:{fingerprint}>"


def sanitize_secret_text(value: str, *, replacement: str = SECRET_REDACTION) -> str:
    """Mask secret-looking fragments inside free-form text."""
    sanitized = _DISCORD_WEBHOOK_RE.sub(replacement, value)
    sanitized = _BEARER_RE.sub(lambda match: f"{match.group(1)} {replacement}", sanitized)
    sanitized = _SECRET_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}{replacement}",
        sanitized,
    )
    return _DISCORD_TOKEN_RE.sub(replacement, sanitized)


def safe_webhook_label(webhook_url: str | None) -> str:
    """Return a traceable webhook label without exposing the URL."""
    fingerprint = secret_fingerprint(webhook_url)
    return f"webhook_hash={fingerprint}" if fingerprint else "webhook_hash=none"
