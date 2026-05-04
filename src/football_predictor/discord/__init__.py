"""Discord formatting, routing and webhook clients."""

from football_predictor.discord.formatter import format_prediction_markdown
from football_predictor.discord.match_formatters import (
    format_match_analysis_message,
    format_match_result_message,
)
from football_predictor.discord.router import (
    DiscordChannelRouter,
    DiscordRoute,
    resolve_discord_route,
)
from football_predictor.discord.service import DiscordDeliveryService, DiscordSendResult
from football_predictor.discord.webhook import DiscordWebhookClient
from football_predictor.discord.weekly_score import (
    format_weekly_score_messages,
    publish_weekly_prediction_score,
)

__all__ = [
    "DiscordDeliveryService",
    "DiscordChannelRouter",
    "DiscordRoute",
    "DiscordSendResult",
    "DiscordWebhookClient",
    "format_match_analysis_message",
    "format_match_result_message",
    "format_prediction_markdown",
    "format_weekly_score_messages",
    "publish_weekly_prediction_score",
    "resolve_discord_route",
]
