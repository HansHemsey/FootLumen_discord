from __future__ import annotations

import httpx
import pytest

from football_predictor.discord.exceptions import DiscordWebhookError
from football_predictor.discord.webhook import DiscordWebhookClient


def test_webhook_client_posts_without_mentions() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read().decode()
        return httpx.Response(204)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        response = DiscordWebhookClient(
            "https://example.invalid/webhook",
            client=client,
        ).send_message("```md\nsynthetic\n```")

    assert response == {"status_code": 204}
    assert '"allowed_mentions":{"parse":[]}' in str(captured["body"]).replace(" ", "")
    assert "wait=true" not in captured.get("query", "")


def test_webhook_client_wait_and_delete_message() -> None:
    requests: list[tuple[str, str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path, request.url.query.decode()))
        if request.method == "POST":
            return httpx.Response(200, json={"id": "discord-message-1"})
        return httpx.Response(204)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        webhook = DiscordWebhookClient("https://example.invalid/webhook", client=client)
        response = webhook.send_markdown("```md\nsynthetic\n```", wait=True)
        deleted = webhook.delete_message("discord-message-1")

    assert response["id"] == "discord-message-1"
    assert deleted["status_code"] == 204
    assert requests == [
        ("POST", "/webhook", "wait=true"),
        ("DELETE", "/webhook/messages/discord-message-1", ""),
    ]


@pytest.mark.parametrize("status_code", [200, 204])
def test_webhook_client_success_codes(status_code: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"ok": True} if status_code == 200 else None)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        response = DiscordWebhookClient(
            "https://example.invalid/webhook",
            client=client,
        ).send_payload({"content": "synthetic"})

    if status_code == 200:
        assert response == {"ok": True}
    else:
        assert response["status_code"] == status_code


@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 429, 500])
def test_webhook_client_errors_mask_url(status_code: int) -> None:
    url = "https://example.invalid/synthetic-webhook-secret"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"message": f"error {status_code}"})

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(DiscordWebhookError) as exc_info,
    ):
        DiscordWebhookClient(url, client=client).send_message("message")

    assert exc_info.value.status_code == status_code
    assert url not in str(exc_info.value)
    assert "synthetic-webhook-secret" not in str(exc_info.value)
    assert "hash=" in str(exc_info.value)


def test_webhook_payload_does_not_include_bot_token() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read().decode()
        captured["authorization"] = request.headers.get("Authorization", "")
        return httpx.Response(204)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        DiscordWebhookClient("https://example.invalid/webhook", client=client).send_payload(
            {"content": "synthetic-token should not appear in headers"}
        )

    assert captured["authorization"] == ""
    assert "Bot " not in captured["body"]


def test_webhook_client_blocks_secret_payload_before_post() -> None:
    calls = 0
    webhook = "https://discord.com/api/" + "webhooks/123456789012345678/" + ("a" * 48)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(DiscordWebhookError),
    ):
        DiscordWebhookClient("https://example.invalid/webhook", client=client).send_payload(
            {"content": "secret " + webhook}
        )

    assert calls == 0
