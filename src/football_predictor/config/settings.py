"""Application settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from football_predictor.utils.secrets import describe_secret


class Settings(BaseSettings):
    """Runtime settings loaded from environment and optional `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_football_key: str | None = Field(
        default=None,
        validation_alias="API_FOOTBALL_KEY",
        repr=False,
    )
    api_football_base_url: str = Field(
        default="https://v3.football.api-sports.io",
        validation_alias="API_FOOTBALL_BASE_URL",
    )
    api_football_timeout_seconds: float = Field(
        default=20.0,
        validation_alias="API_FOOTBALL_TIMEOUT_SECONDS",
    )
    api_football_max_retries: int = Field(
        default=2,
        validation_alias="API_FOOTBALL_MAX_RETRIES",
    )
    api_football_raw_snapshot_dir: Path = Field(
        default=Path("data/raw/api_football"),
        validation_alias="API_FOOTBALL_RAW_SNAPSHOT_DIR",
    )
    database_url: str = Field(
        default="sqlite:///./data/football_predictor.db",
        validation_alias="DATABASE_URL",
    )
    discord_webhook_url: str | None = Field(
        default=None,
        validation_alias="DISCORD_WEBHOOK_URL",
        repr=False,
    )
    discord_channels_config_path: Path = Field(
        default=Path("config/discord_channels.yaml"),
        validation_alias="DISCORD_CHANNELS_CONFIG_PATH",
    )
    discord_webhooks_config_path: Path = Field(
        default=Path("config/discord_webhooks.local.yaml"),
        validation_alias="DISCORD_WEBHOOKS_CONFIG_PATH",
    )
    discord_bot_token: str | None = Field(
        default=None,
        validation_alias="DISCORD_BOT_TOKEN",
        repr=False,
    )
    discord_api_base_url: str = Field(
        default="https://discord.com/api/v10",
        validation_alias="DISCORD_API_BASE_URL",
    )
    discord_guild_id: str | None = Field(
        default=None,
        validation_alias="DISCORD_GUILD_ID",
        repr=False,
    )
    discord_provision_webhooks_enabled: bool = Field(
        default=False,
        validation_alias="DISCORD_PROVISION_WEBHOOKS_ENABLED",
    )
    discord_timeout_seconds: float = Field(
        default=10.0,
        validation_alias="DISCORD_TIMEOUT_SECONDS",
    )
    app_timezone: str = Field(default="Europe/Paris", validation_alias="APP_TIMEZONE")
    competitions_config_path: Path = Field(
        default=Path("config/competitions.example.yaml"),
        validation_alias="COMPETITIONS_CONFIG_PATH",
    )
    api_football_reference_path: Path = Field(
        default=Path("docs/api_football_reference.json"),
        validation_alias="API_FOOTBALL_REFERENCE_PATH",
    )
    api_football_players_reference_path: Path = Field(
        default=Path("docs/api_football_players_reference.json"),
        validation_alias="API_FOOTBALL_PLAYERS_REFERENCE_PATH",
    )
    api_football_players_cache_path: Path = Field(
        default=Path("docs/api_football_players_cache.json"),
        validation_alias="API_FOOTBALL_PLAYERS_CACHE_PATH",
    )
    market_1x2_bet_name: str = Field(
        default="Match Winner",
        validation_alias="MARKET_1X2_BET_NAME",
    )
    market_1x2_bet_id: int | None = Field(
        default=None,
        validation_alias="MARKET_1X2_BET_ID",
    )
    market_ou25_bet_name: str = Field(
        default="Goals Over/Under",
        validation_alias="MARKET_OU25_BET_NAME",
    )
    market_ou25_bet_id: int = Field(
        default=5,
        validation_alias="MARKET_OU25_BET_ID",
    )
    ou_model_dir: Path = Field(
        default=Path("data/models/ou-v1"),
        validation_alias="OU_MODEL_DIR",
    )
    world_cup_1x2_enabled: bool = Field(
        default=False,
        validation_alias="WORLD_CUP_1X2_ENABLED",
    )
    world_cup_1x2_model_dir: Path = Field(
        default=Path("data/models/worldcup-1x2"),
        validation_alias="WORLD_CUP_1X2_MODEL_DIR",
    )
    world_cup_fifa_ranking_path: Path = Field(
        default=Path("data/reference/classement_fifa_officiel.csv"),
        validation_alias="WORLD_CUP_FIFA_RANKING_PATH",
    )
    world_cup_elo_data_path: Path = Field(
        default=Path("data/reference/elo_wc_teams_data.tsv"),
        validation_alias="WORLD_CUP_ELO_DATA_PATH",
    )
    world_cup_elo_shortname_path: Path = Field(
        default=Path("data/reference/elo_wc_teams_shortname.tsv"),
        validation_alias="WORLD_CUP_ELO_SHORTNAME_PATH",
    )
    world_cup_historical_results_path: Path = Field(
        default=Path("data/reference/historical_worldcup_result.csv"),
        validation_alias="WORLD_CUP_HISTORICAL_RESULTS_PATH",
    )

    @field_validator("market_1x2_bet_id", mode="before")
    @classmethod
    def _empty_market_bet_id_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    def secret_status_lines(self) -> list[str]:
        return [
            describe_secret("API key", self.api_football_key),
            describe_secret("Discord webhook", self.discord_webhook_url),
            describe_secret("Discord bot token", self.discord_bot_token),
            describe_secret("Discord guild id", self.discord_guild_id),
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
