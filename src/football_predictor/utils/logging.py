"""Secret-safe logging helpers."""

from __future__ import annotations

import logging as stdlib_logging
import sys
from typing import Any

from football_predictor.security.sanitize import (
    sanitize_mapping,
    sanitize_text,
)

DEFAULT_LOG_FORMAT = "%(levelname)s %(name)s - %(message)s"


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
