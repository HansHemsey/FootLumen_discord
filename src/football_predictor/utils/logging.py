"""Secret-safe logging helpers."""

from __future__ import annotations

import logging as stdlib_logging
import re
import sys
from collections.abc import Mapping
from typing import Any

SENSITIVE_KEY_PARTS = (
    "authorization",
    "key",
    "secret",
    "token",
    "webhook",
    "x-apisports-key",
)
REDACTED_VALUE = "<redacted>"
DEFAULT_LOG_FORMAT = "%(levelname)s %(name)s - %(message)s"
SECRET_TEXT_PATTERNS = (
    re.compile(r"https://discord(?:app)?\.com/api/webhooks/[^\s'\"<>]+", re.IGNORECASE),
    re.compile(r"(?i)(Bearer)\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)((?:api[_-]?key|token|secret|webhook)[=:]\s*)[^\s,;]+"),
)


def configure_logging(level: int | str = stdlib_logging.INFO) -> stdlib_logging.Logger:
    """Configure the standard project logger for readable console output."""
    logger = stdlib_logging.getLogger("football_predictor")
    if not logger.handlers:
        handler = stdlib_logging.StreamHandler(sys.stderr)
        handler.setFormatter(stdlib_logging.Formatter(DEFAULT_LOG_FORMAT))
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = True
    return logger


def get_logger(name: str | None = None) -> stdlib_logging.Logger:
    """Return a project logger."""
    configure_logging()
    if name is None or name == "football_predictor":
        return stdlib_logging.getLogger("football_predictor")
    if name.startswith("football_predictor"):
        return stdlib_logging.getLogger(name)
    return stdlib_logging.getLogger(f"football_predictor.{name}")


def is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("_", "-")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def sanitize_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of mapping values with secret-looking keys redacted."""
    sanitized: dict[str, Any] = {}
    for key, value in values.items():
        if is_sensitive_key(str(key)):
            sanitized[str(key)] = REDACTED_VALUE
        else:
            sanitized[str(key)] = sanitize_value(value)
    return sanitized


def sanitize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return sanitize_mapping(value)
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_value(item) for item in value)
    if isinstance(value, str):
        return sanitize_text(value)
    return value


def sanitize_text(value: str) -> str:
    """Mask secret-looking fragments inside free-form text."""
    sanitized = value
    for pattern in SECRET_TEXT_PATTERNS:
        if pattern.pattern.startswith("(?i)((?:api"):
            sanitized = pattern.sub(r"\1<redacted>", sanitized)
        elif pattern.pattern.startswith("(?i)(Bearer"):
            sanitized = pattern.sub(r"\1 <redacted>", sanitized)
        else:
            sanitized = pattern.sub("<redacted>", sanitized)
    return sanitized


def log_event(
    logger: stdlib_logging.Logger,
    level: int | str,
    event: str,
    **context: Any,
) -> None:
    """Log a compact key-value event with recursively sanitized context."""
    numeric_level = stdlib_logging.getLevelName(level.upper()) if isinstance(level, str) else level
    if not isinstance(numeric_level, int):
        numeric_level = stdlib_logging.INFO
    sanitized = sanitize_mapping(context)
    parts = [f"event={sanitize_text(event)}"]
    for key in sorted(sanitized):
        parts.append(f"{key}={_format_log_value(sanitized[key])}")
    logger.log(numeric_level, " ".join(parts))


def _format_log_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    text = sanitize_text(str(value))
    if any(char.isspace() for char in text):
        return repr(text)
    return text
