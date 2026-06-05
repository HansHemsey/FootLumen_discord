"""Shared helpers for Football Predictor CLI command modules."""

from __future__ import annotations

import json
import os
from datetime import date as date_type
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

import typer
from dotenv import dotenv_values
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from football_predictor import __version__
from football_predictor.api.api_football_client import ApiFootballClient
from football_predictor.backtesting.dataset import build_training_dataset, parse_prediction_window
from football_predictor.backtesting.evaluator import BacktestConfig, ReportFormat, run_backtest
from football_predictor.config import Settings, get_settings
from football_predictor.config.competitions import CompetitionConfig, load_competition_config
from football_predictor.db.models import Fixture
from football_predictor.db.session import (
    create_db_engine,
    create_session_factory,
    init_db,
    session_scope,
)
from football_predictor.discord.config import (
    load_discord_channels_config,
    load_discord_webhooks_config,
)
from football_predictor.discord.daily_publication import publish_daily_discord_messages
from football_predictor.discord.formatter import format_prediction_markdown
from football_predictor.discord.match_publication import (
    publish_match_analyses,
    publish_match_results,
)
from football_predictor.discord.provisioning import (
    DiscordWebhookProvisioner,
    provision_webhooks,
    write_local_webhooks_config,
)
from football_predictor.discord.service import DiscordDeliveryService, send_prediction_to_discord
from football_predictor.discord.weekly_score import publish_weekly_prediction_score
from football_predictor.features.odds_features import (
    compute_market_consensus,
    compute_odds_movement,
    resolve_1x2_bet_id,
)
from football_predictor.ingestion.api_reference import ApiReferenceIngestionService
from football_predictor.ingestion.fixtures import (
    FixtureIngestionService,
    MatchIngestionSummary,
    StandingIngestionService,
    seed_fixtures_and_standings_from_reference,
)
from football_predictor.ingestion.ingest_match_details import FixtureDetailsIngestionService
from football_predictor.ingestion.ingest_odds import OddsIngestionService
from football_predictor.ingestion.ingest_reference import (
    ingest_reference_live,
    seed_reference_from_docs,
)
from football_predictor.ingestion.seed_reference import SeedSummary
from football_predictor.ingestion.unknown_players import (
    DEFAULT_UNKNOWN_PLAYERS_PATH,
    UnknownPlayerResolutionService,
)
from football_predictor.modeling.train import train_model_from_dataset
from football_predictor.prediction import (
    DailyPredictionWindow,
    PredictionService,
    run_daily_predictions,
    run_daily_predictions_v3,
)
from football_predictor.prediction.service import RESULT_LABELS_FR, PredictionOutput
from football_predictor.reference.loaders import load_api_football_reference, load_players_reference
from football_predictor.reference.lookups import ApiFootballReference
from football_predictor.utils.diagnostics import (
    build_data_quality_report,
    build_diagnostic_report,
    mask_database_url,
    validate_positive_reference_ids,
)
from football_predictor.utils.exceptions import FootballPredictorError
from football_predictor.utils.time import format_in_timezone, parse_datetime, utc_now

console = Console()

__all__ = [
    "Any",
    "ApiFootballClient",
    "ApiReferenceIngestionService",
    "ApiFootballReference",
    "BacktestConfig",
    "CompetitionConfig",
    "Console",
    "DEFAULT_UNKNOWN_PLAYERS_PATH",
    "DailyPredictionWindow",
    "DiscordDeliveryService",
    "DiscordWebhookProvisioner",
    "Fixture",
    "FixtureDetailsIngestionService",
    "FixtureIngestionService",
    "FootballPredictorError",
    "MatchIngestionSummary",
    "OddsIngestionService",
    "Path",
    "PredictionOutput",
    "PredictionService",
    "ReportFormat",
    "SeedSummary",
    "Settings",
    "StandingIngestionService",
    "Table",
    "UnknownPlayerResolutionService",
    "ZoneInfo",
    "__version__",
    "_api_client_from_settings",
    "_competition_key_from_fixture",
    "_emit_json_or_summary",
    "_engine_and_session",
    "_existing_or_example",
    "_load_competitions",
    "_load_discord_routing",
    "_parse_cli_date_or_today",
    "_parse_optional_iso_date",
    "_parse_optional_prediction_time",
    "_print_prediction_summary",
    "_print_prediction_v3_summary",
    "_require_refresh_api",
    "_validate_fixture_details_cli_args",
    "_validate_fixture_id",
    "_validate_fixture_ingestion_args",
    "_validate_league_id",
    "_validate_odds_ingestion_args",
    "_validate_team_id",
    "build_data_quality_report",
    "build_diagnostic_report",
    "build_training_dataset",
    "cast",
    "compute_market_consensus",
    "compute_odds_movement",
    "console",
    "create_db_engine",
    "create_session_factory",
    "date_type",
    "datetime",
    "format_in_timezone",
    "format_prediction_markdown",
    "get_settings",
    "ingest_reference_live",
    "init_db",
    "json",
    "load_api_football_reference",
    "load_competition_config",
    "load_discord_channels_config",
    "load_discord_webhooks_config",
    "load_players_reference",
    "parse_datetime",
    "mask_database_url",
    "parse_prediction_window",
    "provision_webhooks",
    "publish_daily_discord_messages",
    "publish_match_analyses",
    "publish_match_results",
    "publish_weekly_prediction_score",
    "resolve_1x2_bet_id",
    "run_backtest",
    "run_daily_predictions",
    "run_daily_predictions_v3",
    "seed_fixtures_and_standings_from_reference",
    "seed_reference_from_docs",
    "select",
    "send_prediction_to_discord",
    "session_scope",
    "timedelta",
    "train_model_from_dataset",
    "typer",
    "utc_now",
    "validate_positive_reference_ids",
    "write_local_webhooks_config",
]


def _engine_and_session(settings: Settings):
    engine = create_db_engine(settings.database_url)
    return engine, create_session_factory(engine)


def _require_refresh_api(refresh_api: bool) -> None:
    if refresh_api:
        return
    console.print(
        "Live ingestion is disabled. Use seed-reference-from-docs for local refs, "
        "or pass --refresh-api to call API-Football explicitly."
    )
    raise typer.Exit(2)


def _api_client_from_settings(settings: Settings) -> ApiFootballClient:
    if not settings.api_football_key:
        raise typer.BadParameter("API_FOOTBALL_KEY is required for live API refresh")
    return ApiFootballClient(
        base_url=settings.api_football_base_url,
        api_key=settings.api_football_key,
        timeout=settings.api_football_timeout_seconds,
        snapshot_dir=settings.api_football_raw_snapshot_dir,
        retries=settings.api_football_max_retries,
    )


def _load_competitions(settings: Settings, config_path: Path) -> list[CompetitionConfig]:
    reference = load_api_football_reference(settings.api_football_reference_path)
    return load_competition_config(config_path, reference)


def _load_discord_routing(
    settings: Settings,
    *,
    channels_path: Path | None = None,
    webhooks_path: Path | None = None,
):
    reference = load_api_football_reference(settings.api_football_reference_path)
    resolved_channels_path = _existing_or_example(
        channels_path or settings.discord_channels_config_path,
        Path("config/discord_channels.example.yaml"),
    )
    resolved_webhooks_path = _existing_or_example(
        webhooks_path or settings.discord_webhooks_config_path,
        Path("config/discord_webhooks.example.yaml"),
    )
    channels_config = load_discord_channels_config(
        resolved_channels_path,
        reference,
    )
    webhooks_config = load_discord_webhooks_config(
        resolved_webhooks_path,
        reference,
        env=_discord_env(),
        reject_placeholders=resolved_webhooks_path.name.endswith(".local.yaml"),
    )
    return reference, channels_config, webhooks_config


def _discord_env() -> dict[str, str]:
    env = dict(os.environ)
    dotenv_path = Path(".env")
    if dotenv_path.exists():
        for key, value in dotenv_values(dotenv_path).items():
            if value is not None and key not in env:
                env[key] = value
    return env


def _existing_or_example(path: Path, example_path: Path) -> Path:
    return path if path.exists() else example_path


def _competition_key_from_fixture(
    reference: ApiFootballReference,
    fixture_row: Fixture | None,
    explicit_key: str | None,
) -> str | None:
    if explicit_key:
        return explicit_key
    if fixture_row is None:
        return None
    try:
        key = reference.find_league_by_id(fixture_row.league_id, fixture_row.season).key
        return str(key) if key else None
    except Exception:
        return None


def _validate_league_id(
    settings: Settings,
    league_id: int,
    season: int | None = None,
    *,
    strict: bool = True,
) -> None:
    reference = load_api_football_reference(settings.api_football_reference_path)
    try:
        if season is None:
            matches = [league for league in reference.leagues() if league.league_id == league_id]
            if not matches:
                reference.find_league_by_id(league_id, season)
        else:
            reference.find_league_by_id(league_id, season)
    except FootballPredictorError as exc:
        if strict:
            raise typer.BadParameter(str(exc)) from exc
        console.print(f"Warning: {exc}; continuing live ingestion.")


def _validate_team_id(settings: Settings, team_id: int, *, strict: bool = True) -> None:
    reference = load_api_football_reference(settings.api_football_reference_path)
    try:
        reference.find_team_by_id(team_id)
    except FootballPredictorError as exc:
        if strict:
            raise typer.BadParameter(str(exc)) from exc
        console.print(f"Warning: {exc}; continuing live ingestion.")


def _validate_fixture_id(settings: Settings, fixture_id: int, *, strict: bool = True) -> None:
    reference = load_api_football_reference(settings.api_football_reference_path)
    try:
        reference.validate_fixture_reference(fixture_id)
    except FootballPredictorError as exc:
        if strict:
            raise typer.BadParameter(str(exc)) from exc
        console.print(f"Warning: {exc}; continuing live ingestion.")


def _validate_fixture_ingestion_args(
    settings: Settings,
    league_id: int | None,
    season: int | None,
    fixture_date: str | None,
    team_id: int | None,
    last: int | None,
    next_count: int | None,
    *,
    strict_reference: bool = True,
) -> None:
    modes = [
        fixture_date is not None,
        fixture_date is None and (league_id is not None or season is not None),
        team_id is not None or last is not None or next_count is not None,
    ]
    if sum(1 for enabled in modes if enabled) != 1:
        raise typer.BadParameter(
            "Use exactly one mode: --date [--league-id --season], "
            "--league-id/--season, or --team-id with --last/--next"
        )
    if fixture_date is not None:
        try:
            date_type.fromisoformat(fixture_date)
        except ValueError as exc:
            raise typer.BadParameter("--date must use YYYY-MM-DD format") from exc
        if (league_id is None) != (season is None):
            raise typer.BadParameter(
                "--date with league filtering requires both --league-id and --season"
            )
        if league_id is not None and season is not None:
            _validate_league_id(settings, league_id, season, strict=strict_reference)
    elif league_id is not None or season is not None:
        if league_id is None or season is None:
            raise typer.BadParameter("--league-id and --season must be provided together")
        _validate_league_id(settings, league_id, season, strict=strict_reference)
    if team_id is not None or last is not None or next_count is not None:
        if team_id is None:
            raise typer.BadParameter("--team-id is required with --last or --next")
        if (last is None) == (next_count is None):
            raise typer.BadParameter("Use exactly one of --last or --next with --team-id")
        if last is not None and last < 1:
            raise typer.BadParameter("--last must be greater than 0")
        if next_count is not None and next_count < 1:
            raise typer.BadParameter("--next must be greater than 0")
        _validate_team_id(settings, team_id, strict=strict_reference)


def _validate_fixture_details_cli_args(
    settings: Settings,
    fixture_id: int | None,
    league_id: int | None,
    season: int | None,
    fixture_date: str | None,
    date_from: str | None,
    date_to: str | None,
    days_back: int | None,
    statuses: list[str] | None,
    limit: int | None,
) -> tuple[date_type | None, date_type | None, date_type | None, list[str] | None]:
    batch_requested = any(
        value is not None
        for value in (
            league_id,
            season,
            fixture_date,
            date_from,
            date_to,
            days_back,
            statuses,
            limit,
        )
    )
    if fixture_id is not None and batch_requested:
        raise typer.BadParameter("Use either --fixture or batch filters, not both")
    if fixture_id is not None:
        _validate_fixture_id(settings, fixture_id, strict=False)
        return None, None, None, None

    if league_id is not None or season is not None:
        if league_id is None or season is None:
            raise typer.BadParameter("--league and --season must be provided together")
        _validate_league_id(settings, league_id, season, strict=False)
    if fixture_date is not None and any(
        value is not None for value in (date_from, date_to, days_back)
    ):
        raise typer.BadParameter("Use --date or a date range, not both")
    if days_back is not None and any(value is not None for value in (date_from, date_to)):
        raise typer.BadParameter("Use --days-back or --from-date/--to-date, not both")
    parsed_date = None
    if fixture_date is not None:
        try:
            parsed_date = date_type.fromisoformat(fixture_date)
        except ValueError as exc:
            raise typer.BadParameter("--date must use YYYY-MM-DD format") from exc
    parsed_from = _parse_optional_iso_date(date_from, "--from-date")
    parsed_to = _parse_optional_iso_date(date_to, "--to-date")
    if days_back is not None:
        if days_back < 1:
            raise typer.BadParameter("--days-back must be greater than 0")
        parsed_to = datetime.now(ZoneInfo(settings.app_timezone)).date()
        parsed_from = parsed_to - timedelta(days=days_back)
    if parsed_from is not None and parsed_to is not None and parsed_from > parsed_to:
        raise typer.BadParameter("--from-date must be before or equal to --to-date")
    if limit is not None and limit < 1:
        raise typer.BadParameter("--limit must be greater than 0")
    status_values = _normalize_fixture_status_values(statuses)
    if (
        league_id is None
        and parsed_date is None
        and parsed_from is None
        and parsed_to is None
        and not status_values
    ):
        raise typer.BadParameter(
            "Provide --fixture or at least one batch filter: --league/--season, --date, "
            "--from-date/--to-date, --days-back or --status"
        )
    return parsed_date, parsed_from, parsed_to, status_values


def _parse_optional_iso_date(value: str | None, option_name: str) -> date_type | None:
    if value is None:
        return None
    try:
        return date_type.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter(f"{option_name} must use YYYY-MM-DD format") from exc


def _normalize_fixture_status_values(statuses: list[str] | None) -> list[str] | None:
    if not statuses:
        return None
    values: list[str] = []
    for item in statuses:
        values.extend(token.upper() for token in item.replace(",", " ").split() if token.strip())
    normalized = list(dict.fromkeys(values))
    return normalized or None


def _validate_odds_ingestion_args(
    settings: Settings,
    fixture_id: int | None,
    league_id: int | None,
    season: int | None,
    odds_date: str | None,
    bookmaker_ids: list[int] | None,
) -> date_type | None:
    if fixture_id is not None and (
        odds_date is not None or league_id is not None or season is not None
    ):
        raise typer.BadParameter("Use --fixture without --date, --league or --season")
    if fixture_id is None and odds_date is None and league_id is None and season is None:
        raise typer.BadParameter(
            "Use exactly one odds mode: --fixture, --date, or --league/--season"
        )
    if fixture_id is not None:
        _validate_fixture_id(settings, fixture_id, strict=False)
    if odds_date is None and (league_id is not None or season is not None):
        if league_id is None or season is None:
            raise typer.BadParameter("--league and --season must be provided together")
        _validate_league_id(settings, league_id, season, strict=False)
    if odds_date is not None:
        if league_id is None and season is not None:
            raise typer.BadParameter("--season with --date requires --league")
        if league_id is not None:
            _validate_league_id(settings, league_id, season, strict=False)
    parsed_date = None
    if odds_date is not None:
        try:
            parsed_date = date_type.fromisoformat(odds_date)
        except ValueError as exc:
            raise typer.BadParameter("--date must use YYYY-MM-DD format") from exc

    reference = load_api_football_reference(settings.api_football_reference_path)
    for bookmaker_id in bookmaker_ids or []:
        try:
            reference.find_bookmaker_by_id(bookmaker_id)
        except FootballPredictorError as exc:
            console.print(f"Warning: {exc}; continuing live odds ingestion.")
    return parsed_date


def _parse_optional_prediction_time(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        raise typer.BadParameter("--prediction-time must be an ISO 8601 timestamp")
    return parsed


def _parse_cli_date_or_today(value: str | None, timezone_name: str) -> date_type:
    if value is None:
        return datetime.now(ZoneInfo(timezone_name)).date()
    try:
        return date_type.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter("--date must use YYYY-MM-DD format") from exc


def _emit_json_or_summary(
    payload: dict[str, object],
    *,
    json_output: bool,
    json_output_path: Path | None,
    fallback_label: str,
) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if json_output_path is not None:
        json_output_path.parent.mkdir(parents=True, exist_ok=True)
        json_output_path.write_text(rendered + "\n", encoding="utf-8")
    if json_output:
        console.out(rendered)
    else:
        console.print(f"{fallback_label} {payload}")


def _print_prediction_summary(prediction: PredictionOutput, timezone_name: str) -> None:
    probabilities = prediction.probabilities.normalized()
    table = Table(title="Prediction Football")
    table.add_column("Champ", style="cyan")
    table.add_column("Valeur")
    table.add_row("Match", prediction.match_label)
    table.add_row("Competition", prediction.competition)
    table.add_row(
        "Date",
        format_in_timezone(prediction.match_date, timezone_name)
        if prediction.match_date is not None
        else "date inconnue",
    )
    table.add_row("Prediction time", prediction.prediction_time.isoformat())
    table.add_row("Resultat", RESULT_LABELS_FR[prediction.predicted_result])
    table.add_row("Confiance", prediction.confidence_label)
    table.add_row("Score", f"{prediction.confidence_score:.1f} pts")
    table.add_row("P(Home)", f"{probabilities.p_home * 100:.1f}%")
    table.add_row("P(Draw)", f"{probabilities.p_draw * 100:.1f}%")
    table.add_row("P(Away)", f"{probabilities.p_away * 100:.1f}%")
    table.add_row("Sources", ", ".join(prediction.sources_used) or "fallback")
    quality_score = prediction.data_quality_json.get(
        "overall_data_quality_score",
        prediction.data_quality.score(),
    )
    table.add_row(
        "Qualite",
        f"{quality_score}/100",
    )
    console.print(table)
    console.print("Facteurs cles:")
    for index, explanation in enumerate(prediction.explanations, start=1):
        console.print(f"{index}. {explanation}")


def _print_prediction_v3_summary(prediction: Any, timezone_name: str) -> None:
    probabilities = prediction.probabilities.normalized()
    table = Table(title="Prediction Football V3")
    table.add_column("Champ", style="cyan")
    table.add_column("Valeur")
    table.add_row("Match", prediction.match_label)
    table.add_row("Competition", prediction.competition)
    table.add_row(
        "Date",
        format_in_timezone(prediction.match_date, timezone_name)
        if prediction.match_date is not None
        else "date inconnue",
    )
    table.add_row("Prediction time", prediction.prediction_time.isoformat())
    table.add_row("Resultat", RESULT_LABELS_FR[prediction.predicted_result])
    table.add_row("Confiance", prediction.confidence_label)
    table.add_row("Score", f"{prediction.confidence_score:.1f} pts")
    table.add_row("Fusion", prediction.fusion_strategy)
    table.add_row("P(Home)", f"{probabilities.p_home * 100:.1f}%")
    table.add_row("P(Draw)", f"{probabilities.p_draw * 100:.1f}%")
    table.add_row("P(Away)", f"{probabilities.p_away * 100:.1f}%")
    table.add_row("Risque nul", prediction.draw_risk_label)
    table.add_row("Hors nul", prediction.no_draw_winner_label)
    quality_score = prediction.data_quality_json.get("overall_data_quality_score")
    table.add_row("Qualite", f"{quality_score}/100" if quality_score is not None else "unknown")
    console.print(table)
    console.print("Facteurs V3:")
    for index, explanation in enumerate(prediction.explanations, start=1):
        console.print(f"{index}. {explanation}")
