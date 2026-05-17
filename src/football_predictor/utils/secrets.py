"""Secret-safe formatting helpers."""

from __future__ import annotations

import hashlib


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


def safe_webhook_label(webhook_url: str | None) -> str:
    """Return a traceable webhook label without exposing the URL."""
    fingerprint = secret_fingerprint(webhook_url)
    return f"webhook_hash={fingerprint}" if fingerprint else "webhook_hash=none"
