"""Internal staff publication helpers for predictions skipped from public channels."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from football_predictor.db import models
from football_predictor.discord.formatter import DISCORD_LIMIT, truncate_discord_message
from football_predictor.discord.service import DiscordDeliveryService, DiscordSendResult

STAFF_PREDICTIONS_CHANNEL_KEY = "predictions_staff"
STAFF_PREDICTION_SKIPPED_MESSAGE_TYPE = "prediction_skipped"
STAFF_OU_PREDICTION_SKIPPED_MESSAGE_TYPE = "ou_prediction_skipped"

logger = logging.getLogger(__name__)


def send_skipped_prediction_to_staff(
    delivery: DiscordDeliveryService | None,
    markdown: str,
    *,
    fixture: models.Fixture,
    model_family: str,
    confidence_label: str | None,
    confidence_score: float | None,
    reason: str,
    prediction_time: datetime | None,
    automation_window: str,
    message_type: str = STAFF_PREDICTION_SKIPPED_MESSAGE_TYPE,
    model_prediction_id: int | None = None,
    payload_metadata: dict[str, Any] | None = None,
    force: bool = False,
) -> DiscordSendResult | None:
    """Send a non-public prediction to the global staff channel.

    Staff sends are best-effort: a missing staff route must not accidentally
    publish to the public channel or fail the prediction pipeline.
    """
    if delivery is None:
        logger.warning(
            "Staff skipped prediction not sent: missing Discord delivery fixture_id=%s",
            fixture.fixture_id,
        )
        return None
    metadata = {
        "model_family": model_family,
        "fixture_id": fixture.fixture_id,
        "league_id": fixture.league_id,
        "season": fixture.season,
        "confidence_label": confidence_label,
        "confidence_score": confidence_score,
        "skip_reason": reason,
        "automation_window": automation_window,
        "prediction_time": prediction_time.isoformat() if prediction_time else None,
        **(payload_metadata or {}),
    }
    try:
        return delivery.send_markdown(
            _staff_markdown(markdown, reason=reason),
            competition_key=None,
            league_id=None,
            season=None,
            channel_key=STAFF_PREDICTIONS_CHANNEL_KEY,
            message_type=message_type,
            fixture_id=fixture.fixture_id,
            model_prediction_id=model_prediction_id,
            dry_run=False,
            print_only=False,
            force=force,
            payload_metadata=metadata,
        )
    except Exception as exc:
        logger.warning(
            "Staff skipped prediction send failed: fixture_id=%s model_family=%s reason=%s",
            fixture.fixture_id,
            model_family,
            exc,
        )
        return None


def _staff_markdown(markdown: str, *, reason: str) -> str:
    header = (
        "**INTERNE STAFF - NON PUBLIE PUBLIC**\n"
        f"Raison: `{reason}`\n\n"
    )
    remaining = max(100, DISCORD_LIMIT - len(header))
    return header + truncate_discord_message(markdown, max_chars=remaining)
