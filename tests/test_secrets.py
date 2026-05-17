from __future__ import annotations

from football_predictor.utils.secrets import hash_secret, mask_secret, safe_webhook_label


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
