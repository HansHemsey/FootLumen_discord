"""Discord webhook sender."""

from __future__ import annotations

from typing import Any

import httpx

from football_predictor.discord.exceptions import DiscordWebhookError
from football_predictor.security.sanitize import (
    contains_sensitive_data,
    sanitize_text,
    sanitize_value,
)
from football_predictor.utils.secrets import hash_secret

NO_MENTIONS: dict[str, list[str]] = {"parse": []}


class DiscordWebhookClient:
    def __init__(
        self,
        webhook_url: str,
        timeout: float = 10.0,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.webhook_url = webhook_url
        self.timeout = timeout
        self._client = client

    @property
    def webhook_hash(self) -> str | None:
        return hash_secret(self.webhook_url)

    def send_markdown(self, markdown: str, *, wait: bool = False) -> dict[str, object]:
        return self.send_message(markdown, wait=wait)

    def send_message(
        self,
        content: str,
        *,
        username: str | None = None,
        avatar_url: str | None = None,
        wait: bool = False,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "content": content,
            "allowed_mentions": NO_MENTIONS,
        }
        if username:
            payload["username"] = username
        if avatar_url:
            payload["avatar_url"] = avatar_url
        return self.send_payload(payload, wait=wait)

    def send_payload(
        self,
        payload: dict[str, object],
        *,
        wait: bool = False,
    ) -> dict[str, object]:
        payload.setdefault("allowed_mentions", NO_MENTIONS)
        if contains_sensitive_data(payload):
            raise DiscordWebhookError(
                "Discord webhook payload blocked by secret sanitizer",
                webhook_hash=self.webhook_hash,
            )
        params = {"wait": "true"} if wait else None
        if self._client is not None:
            response = self._client.post(self.webhook_url, json=payload, params=params)
        else:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.webhook_url, json=payload, params=params)
        return self._handle_response(response)

    def delete_message(self, message_id: str) -> dict[str, object]:
        """Delete a message created by this webhook."""
        delete_url = f"{self.webhook_url.rstrip('/')}/messages/{message_id}"
        if self._client is not None:
            response = self._client.delete(delete_url)
        else:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.delete(delete_url)
        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> dict[str, object]:
        if response.status_code in {200, 204}:
            return _response_payload(response)
        raise DiscordWebhookError(
            "Discord webhook failed",
            status_code=response.status_code,
            webhook_hash=self.webhook_hash,
            response_text=_safe_response_text(response),
        )


def _response_payload(response: httpx.Response) -> dict[str, object]:
    if not response.content:
        return {"status_code": response.status_code}
    try:
        data: Any = response.json()
    except ValueError:
        return {"status_code": response.status_code, "body": sanitize_text(response.text[:200])}
    if isinstance(data, dict):
        return sanitize_value(data)
    return {"status_code": response.status_code, "body": sanitize_value(data)}


def _safe_response_text(response: httpx.Response) -> str:
    text = response.text[:200]
    return sanitize_text(text.replace("\n", " ").replace("\r", " "))
