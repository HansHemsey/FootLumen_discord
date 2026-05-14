from __future__ import annotations

import subprocess
from pathlib import Path

from football_predictor.utils.secrets import (
    hash_secret,
    mask_secret,
    safe_webhook_label,
    sanitize_secret_text,
)


def test_mask_secret_never_contains_original_value() -> None:
    secret = "synthetic-secret-value"

    masked = mask_secret(secret)

    assert masked.startswith("<secret:")
    assert secret not in masked


def test_hash_secret_is_stable_and_non_reversible() -> None:
    secret = "synthetic-secret-value"

    first = hash_secret(secret)
    second = hash_secret(secret)

    assert first == second
    assert first is not None
    assert len(first) == 8
    assert secret not in first


def test_empty_secret_helpers_do_not_create_fake_values() -> None:
    assert mask_secret(None) == ""
    assert hash_secret(None) is None
    assert safe_webhook_label(None) == "webhook_hash=none"


def test_sanitize_secret_text_masks_common_secret_shapes() -> None:
    webhook = "https://discord.com/api/webhooks/123456/synthetic-secret"
    token = "Bearer " + "synthetic-token-value"
    api_key = "api_key=synthetic-api-key-value"
    bot_token = "ABCDEFGHIJKLMNOPQRSTUVWX.abcdef.ABCDEFGHIJKLMNOPQRST"

    sanitized = sanitize_secret_text(f"{webhook} {token} {api_key} {bot_token}")

    assert webhook not in sanitized
    assert "synthetic-token-value" not in sanitized
    assert "synthetic-api-key-value" not in sanitized
    assert bot_token not in sanitized
    assert sanitized.count("<redacted>") >= 4


def test_gitignore_covers_local_secret_files(repo_root: Path) -> None:
    paths = [
        ".env.local",
        ".env.production",
        "config/foo.local.yaml",
        "private.pem",
        "service.credentials.json",
    ]

    result = subprocess.run(
        ["git", "check-ignore", "--stdin"],
        input="\n".join(paths) + "\n",
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert set(result.stdout.splitlines()) == set(paths)
