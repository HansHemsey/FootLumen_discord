"""Discord-specific exceptions with secret-safe context."""

from __future__ import annotations

from dataclasses import dataclass

from football_predictor.utils.exceptions import DiscordWebhookError as BaseDiscordWebhookError


class DiscordRoutingError(BaseDiscordWebhookError):
    """Discord route resolution failed."""


@dataclass
class DiscordWebhookError(BaseDiscordWebhookError):
    """Discord webhook HTTP failure without exposing the webhook URL."""

    message: str
    status_code: int | None = None
    webhook_hash: str | None = None
    response_text: str | None = None

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code is not None:
            parts.append(f"status_code={self.status_code}")
        if self.webhook_hash:
            parts.append(f"webhook_hash={self.webhook_hash}")
        if self.response_text:
            parts.append(f"response_text={self.response_text[:200]}")
        return " ".join(parts)
