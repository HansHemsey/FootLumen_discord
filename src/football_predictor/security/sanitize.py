"""Central secret sanitizer for logs, snapshots and persisted payloads."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

REDACTED_VALUE = "<redacted>"

SENSITIVE_KEY_PARTS = (
    "authorization",
    "api-key",
    "apikey",
    "bearer",
    "password",
    "secret",
    "token",
    "webhook",
    "x-apisports-key",
)

DISCORD_WEBHOOK_RE = re.compile(
    r"https://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/[^\s'\"<>]+",
    re.IGNORECASE,
)
BEARER_TOKEN_RE = re.compile(r"(?i)\b(Bearer)\s+[A-Za-z0-9._~+/=-]{12,}")
SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"""(?ix)
    \b(
        [A-Z0-9_]*(?:API[_-]?KEY|KEY|TOKEN|SECRET|PASSWORD|WEBHOOK)[A-Z0-9_]*
        | x-apisports-key
    )
    \s*[:=]\s*
    ["']?
    ([^"'\s,;{}]+)
    """
)
LONG_SUSPICIOUS_RE = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_.~+/=-]{40,}(?![A-Za-z0-9_-])")


@dataclass(frozen=True)
class SensitiveFinding:
    kind: str
    path: str
    preview: str

    def as_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "path": self.path, "preview": self.preview}


def is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("_", "-")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def sanitize_text(value: str) -> str:
    """Mask secret-looking fragments inside free-form text."""
    sanitized = DISCORD_WEBHOOK_RE.sub(REDACTED_VALUE, value)
    sanitized = BEARER_TOKEN_RE.sub(r"\1 " + REDACTED_VALUE, sanitized)
    sanitized = SENSITIVE_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}={REDACTED_VALUE}",
        sanitized,
    )
    return LONG_SUSPICIOUS_RE.sub(_mask_suspicious_match, sanitized)


def sanitize_value(value: Any) -> Any:
    """Recursively sanitize JSON-like values while preserving shape."""
    if isinstance(value, Mapping):
        return sanitize_mapping(value)
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_value(item) for item in value)
    if isinstance(value, str):
        return sanitize_text(value)
    return value


def sanitize_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of mapping values with sensitive keys and values redacted."""
    sanitized: dict[str, Any] = {}
    for key, value in values.items():
        key_text = str(key)
        if is_sensitive_key(key_text):
            sanitized[key_text] = REDACTED_VALUE
        else:
            sanitized[key_text] = sanitize_value(value)
    return sanitized


def contains_sensitive_data(value: Any) -> bool:
    return bool(find_sensitive_data(value))


def assert_no_sensitive_data(value: Any, *, context: str = "payload") -> None:
    findings = find_sensitive_data(value, path=context)
    if findings:
        kinds = ", ".join(sorted({finding.kind for finding in findings}))
        raise ValueError(f"Sensitive data detected in {context}: {kinds}")


def find_sensitive_data(value: Any, *, path: str = "$") -> list[SensitiveFinding]:
    findings: list[SensitiveFinding] = []
    _collect_findings(value, path, findings)
    return findings


def _collect_findings(value: Any, path: str, findings: list[SensitiveFinding]) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            if is_sensitive_key(key_text) and _has_non_empty_secret_value(item):
                findings.append(
                    SensitiveFinding(
                        kind="sensitive_key",
                        path=child_path,
                        preview=_preview(item),
                    )
                )
            _collect_findings(item, child_path, findings)
        return

    if isinstance(value, str):
        findings.extend(_text_findings(value, path))
        return

    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        for index, item in enumerate(value):
            _collect_findings(item, f"{path}[{index}]", findings)


def _text_findings(value: str, path: str) -> list[SensitiveFinding]:
    findings: list[SensitiveFinding] = []
    for match in DISCORD_WEBHOOK_RE.finditer(value):
        findings.append(_finding("discord_webhook_url", path, match.group(0)))
    for match in BEARER_TOKEN_RE.finditer(value):
        findings.append(_finding("bearer_token", path, match.group(0)))
    for match in SENSITIVE_ASSIGNMENT_RE.finditer(value):
        assigned_value = match.group(2)
        if _has_non_empty_secret_value(assigned_value):
            findings.append(_finding("sensitive_assignment", path, match.group(0)))
    for match in LONG_SUSPICIOUS_RE.finditer(value):
        candidate = match.group(0)
        if _looks_like_long_secret(candidate):
            findings.append(_finding("long_suspicious_token", path, candidate))
    return findings


def _finding(kind: str, path: str, value: str) -> SensitiveFinding:
    return SensitiveFinding(kind=kind, path=path, preview=sanitize_text(value)[:160])


def _has_non_empty_secret_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        stripped = value.strip().strip("\"'")
        return bool(stripped) and stripped not in {
            REDACTED_VALUE,
            "REPLACE_WITH_WEBHOOK_URL",
            "REPLACE_WITH_TOKEN",
            "REPLACE_WITH_API_KEY",
            "YOUR_API_KEY",
            "CHANGEME",
            "changeme",
        }
    return True


def _mask_suspicious_match(match: re.Match[str]) -> str:
    candidate = match.group(0)
    return REDACTED_VALUE if _looks_like_long_secret(candidate) else candidate


def _looks_like_long_secret(candidate: str) -> bool:
    if len(candidate) < 40:
        return False
    has_lower = any(char.islower() for char in candidate)
    has_upper = any(char.isupper() for char in candidate)
    has_digit = any(char.isdigit() for char in candidate)
    has_symbol = any(char in "._~+/=-" for char in candidate)
    classes = sum((has_lower, has_upper, has_digit, has_symbol))
    if classes >= 3:
        return True
    if len(candidate) >= 48 and classes >= 2:
        return _shannon_entropy(candidate) >= 3.2
    return False


def _shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = {char: value.count(char) for char in set(value)}
    return -sum((count / len(value)) * math.log2(count / len(value)) for count in counts.values())


def _preview(value: Any) -> str:
    return sanitize_text(str(value))[:160]
