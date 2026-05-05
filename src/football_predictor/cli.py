"""Command line interface for Football Predictor."""

from __future__ import annotations

import json
import os
from datetime import date as date_type
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

import typer
from dotenv import dotenv_values
from rich.console import Console
from rich.table import Table

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

app = typer.Typer(help="Football Predictor CLI")
console = Console()


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
        league_id is not None or season is not None,
        fixture_date is not None,
        team_id is not None or last is not None or next_count is not None,
    ]
    if sum(1 for enabled in modes if enabled) != 1:
        raise typer.BadParameter(
            "Use exactly one mode: --league-id/--season, --date, or --team-id with --last/--next"
        )
    if league_id is not None or season is not None:
        if league_id is None or season is None:
            raise typer.BadParameter("--league-id and --season must be provided together")
        _validate_league_id(settings, league_id, season, strict=strict_reference)
    if fixture_date is not None:
        try:
            date_type.fromisoformat(fixture_date)
        except ValueError as exc:
            raise typer.BadParameter("--date must use YYYY-MM-DD format") from exc
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


def _print_healthcheck(*, json_output: bool = False, strict: bool = False) -> None:
    settings = get_settings()
    report = build_diagnostic_report(settings, version=__version__)
    if json_output:
        typer.echo(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        if strict and report.has_critical_errors:
            raise typer.Exit(1)
        return

    console.print("Football Predictor healthcheck")
    console.print(f"Version: {__version__}")
    console.print(f"Database URL: {mask_database_url(settings.database_url)}")
    console.print(f"Timezone: {settings.app_timezone}")
    console.print(f"API timeout seconds: {settings.api_football_timeout_seconds}")
    console.print(f"API max retries: {settings.api_football_max_retries}")
    console.print(f"API raw snapshot dir: {settings.api_football_raw_snapshot_dir}")
    console.print(f"Competitions config path: {settings.competitions_config_path}")
    console.print(f"Reference path: {settings.api_football_reference_path}")
    console.print(f"Players path: {settings.api_football_players_reference_path}")
    console.print(f"Players cache path: {settings.api_football_players_cache_path}")
    for line in settings.secret_status_lines():
        console.print(line)
    for path in (
        settings.api_football_reference_path,
        settings.api_football_players_reference_path,
        settings.api_football_players_cache_path,
    ):
        console.print(f"{path}: {'exists' if path.exists() else 'missing'}")
    _print_diagnostic_table(report)
    if strict and report.has_critical_errors:
        raise typer.Exit(1)


def _print_diagnostic_table(report) -> None:
    table = Table(title="Diagnostics")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Message")
    for check in report.checks:
        table.add_row(check.name, check.status.value, check.message)
    console.print(table)


def _print_data_quality_report(report: dict) -> None:
    console.print("Football Predictor data-quality")
    scope = report.get("scope", {})
    console.print(
        "Scope: "
        f"fixture={scope.get('fixture_id')} "
        f"date={scope.get('date')} "
        f"league={scope.get('league_id')} "
        f"season={scope.get('season')}"
    )
    table = Table(title="Data Quality")
    table.add_column("Metric")
    table.add_column("Value")
    for key, value in report.items():
        if key == "scope":
            continue
        if isinstance(value, dict):
            table.add_row(key, json.dumps(value, sort_keys=True))
        else:
            table.add_row(key, str(value))
    console.print(table)


@app.command("version")
def version_command() -> None:
    """Print the installed package version."""
    console.print(__version__)


@app.command("healthcheck")
def healthcheck(
    json_output: bool = typer.Option(False, "--json", help="Output a machine-readable report."),
    strict: bool = typer.Option(False, "--strict", help="Exit non-zero on critical errors."),
) -> None:
    """Check local configuration without exposing secrets."""
    _print_healthcheck(json_output=json_output, strict=strict)


@app.command()
def doctor(
    json_output: bool = typer.Option(False, "--json", help="Output a machine-readable report."),
    strict: bool = typer.Option(False, "--strict", help="Exit non-zero on critical errors."),
) -> None:
    """Run local diagnostics without API-Football or Discord calls."""
    _print_healthcheck(json_output=json_output, strict=strict)


@app.command("data-quality")
def data_quality_command(
    fixture_id: int | None = typer.Option(None, "--fixture", help="Scope report to a fixture."),
    report_date: str | None = typer.Option(None, "--date", help="Scope report to YYYY-MM-DD."),
    league_id: int | None = typer.Option(None, "--league", help="Scope report to a league."),
    season: int | None = typer.Option(None, "--season", help="Scope report to a season."),
    json_output: bool = typer.Option(False, "--json", help="Output a machine-readable report."),
) -> None:
    """Report local DB coverage for prediction inputs without network calls."""
    settings = get_settings()
    parsed_date = None
    if report_date is not None:
        try:
            parsed_date = date_type.fromisoformat(report_date)
        except ValueError as exc:
            raise typer.BadParameter("--date must use YYYY-MM-DD format") from exc
    if league_id is not None and season is None:
        raise typer.BadParameter("--season is required with --league")

    reference = load_api_football_reference(settings.api_football_reference_path)
    try:
        validate_positive_reference_ids(
            reference,
            fixture_id=fixture_id,
            league_id=league_id,
            season=season,
        )
    except FootballPredictorError as exc:
        raise typer.BadParameter(str(exc)) from exc

    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with session_factory() as session:
        report = build_data_quality_report(
            session,
            fixture_id=fixture_id,
            target_date=parsed_date,
            league_id=league_id,
            season=season,
        )
    if json_output:
        typer.echo(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_data_quality_report(report)


@app.command("init-db")
def init_db_command() -> None:
    """Create local database tables."""
    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    init_db(engine)
    console.print("Database initialized")


@app.command("seed-reference-from-docs")
def seed_reference_from_docs_command(
    reference: Path = typer.Option(
        Path("docs/api_football_reference.json"),
        "--reference",
        help="Machine-readable competitions reference JSON.",
    ),
    players: Path = typer.Option(
        Path("docs/api_football_players_reference.json"),
        "--players",
        help="Machine-readable players reference JSON.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Load and validate docs references, then roll back DB writes.",
    ),
) -> None:
    """Seed local DB from docs JSON without network calls."""
    settings = get_settings()
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    session = session_factory()
    try:
        summary = seed_reference_from_docs(session, reference, players)
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    output = summary.as_dict()
    output["dry_run"] = int(dry_run)
    console.print(output)


@app.command("ingest-reference")
def ingest_reference(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Competitions config resolved against local docs reference.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Run ingestion and roll back DB writes.",
    ),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also write API live payloads to disk through ApiFootballClient.",
    ),
    prefer_docs: bool = typer.Option(
        True,
        "--prefer-docs/--no-prefer-docs",
        help="Seed local docs references before optional live refresh.",
    ),
    refresh_live: bool = typer.Option(
        False,
        "--refresh-live",
        help="Explicitly call API-Football for leagues, teams and squads.",
    ),
) -> None:
    """Ingest reference entities from docs and optionally API-Football live."""
    if not prefer_docs and not refresh_live:
        console.print("Nothing to ingest. Use --prefer-docs and/or --refresh-live.")
        raise typer.Exit(2)

    settings = get_settings()
    competitions = _load_competitions(settings, config or settings.competitions_config_path)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    session = session_factory()
    summary = SeedSummary()
    try:
        if prefer_docs:
            summary.merge(
                seed_reference_from_docs(
                    session,
                    settings.api_football_reference_path,
                    settings.api_football_players_reference_path,
                )
            )
        if refresh_live:
            with _api_client_from_settings(settings) as client:
                summary.merge(
                    ingest_reference_live(
                        session,
                        client,
                        competitions,
                        save_raw=save_raw,
                    )
                )
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    output = summary.as_dict()
    output["dry_run"] = int(dry_run)
    output["prefer_docs"] = int(prefer_docs)
    output["refresh_live"] = int(refresh_live)
    console.print(output)


@app.command("ingest-leagues")
def ingest_leagues(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Competitions config resolved against local docs reference.",
    ),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
) -> None:
    """Refresh leagues from API-Football and store raw snapshots."""
    _require_refresh_api(refresh_api)
    settings = get_settings()
    competitions = _load_competitions(settings, config or settings.competitions_config_path)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with _api_client_from_settings(settings) as client, session_scope(session_factory) as session:
        summary = ApiReferenceIngestionService(session, client).ingest_leagues(competitions)
    console.print(summary.as_dict())


@app.command("ingest-teams")
def ingest_teams(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Competitions config resolved against local docs reference.",
    ),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
) -> None:
    """Refresh teams and venues from API-Football and store raw snapshots."""
    _require_refresh_api(refresh_api)
    settings = get_settings()
    competitions = _load_competitions(settings, config or settings.competitions_config_path)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with _api_client_from_settings(settings) as client, session_scope(session_factory) as session:
        summary = ApiReferenceIngestionService(session, client).ingest_teams(competitions)
    console.print(summary.as_dict())


@app.command("ingest-player-squads")
def ingest_player_squads(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Competitions config resolved against local docs reference.",
    ),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
) -> None:
    """Refresh player squads from API-Football and store raw snapshots."""
    _require_refresh_api(refresh_api)
    settings = get_settings()
    competitions = _load_competitions(settings, config or settings.competitions_config_path)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with _api_client_from_settings(settings) as client, session_scope(session_factory) as session:
        summary = ApiReferenceIngestionService(session, client).ingest_player_squads(competitions)
    console.print(summary.as_dict())


@app.command("resolve-unknown-players")
def resolve_unknown_players(
    input_path: Path = typer.Option(
        DEFAULT_UNKNOWN_PLAYERS_PATH,
        "--input",
        help="JSONL file populated during fixture detail ingestion.",
    ),
    league_id: int | None = typer.Option(
        None,
        "--league",
        "--league-id",
        help="Optional league_id filter or fallback context.",
    ),
    season: int | None = typer.Option(
        None,
        "--season",
        help="Optional season filter or fallback context for /players?id&season.",
    ),
    team_id: int | None = typer.Option(
        None,
        "--team",
        "--team-id",
        help="Optional team_id filter or fallback context for /players/squads.",
    ),
    limit: int | None = typer.Option(
        50,
        "--limit",
        help="Maximum deduplicated unknown players to resolve in this run.",
    ),
    delay_seconds: float = typer.Option(
        2.0,
        "--delay-seconds",
        help="Sleep between player resolution attempts to reduce API rate pressure.",
    ),
    squads_fallback: bool = typer.Option(
        True,
        "--squads-fallback/--no-squads-fallback",
        help="Fallback to /players/squads?team=... when direct player lookup is incomplete.",
    ),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run resolution then roll back."),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also write API live payloads to disk through ApiFootballClient.",
    ),
) -> None:
    """Resolve live players missing from local docs into the local DB."""
    _require_refresh_api(refresh_api)
    settings = get_settings()
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    session = session_factory()
    try:
        with _api_client_from_settings(settings) as client:
            summary = UnknownPlayerResolutionService(
                session,
                client,
                save_raw=save_raw,
            ).resolve_unknown_players(
                input_path=input_path,
                league_id=league_id,
                season=season,
                team_id=team_id,
                limit=limit,
                delay_seconds=delay_seconds,
                squads_fallback=squads_fallback,
                prune_resolved=not dry_run,
            )
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    output = summary.as_dict()
    output["dry_run"] = int(dry_run)
    console.print(output)


@app.command("ingest-bookmakers")
def ingest_bookmakers(
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
) -> None:
    """Refresh bookmaker references from API-Football and store raw snapshots."""
    _require_refresh_api(refresh_api)
    settings = get_settings()
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with _api_client_from_settings(settings) as client, session_scope(session_factory) as session:
        summary = ApiReferenceIngestionService(session, client).ingest_bookmakers()
    console.print(summary.as_dict())


@app.command("ingest-bets")
def ingest_bets(
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
) -> None:
    """Refresh bet references from API-Football and store raw snapshots."""
    _require_refresh_api(refresh_api)
    settings = get_settings()
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with _api_client_from_settings(settings) as client, session_scope(session_factory) as session:
        summary = ApiReferenceIngestionService(session, client).ingest_bets()
    console.print(summary.as_dict())


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


@app.command()
def predict(
    fixture: int = typer.Option(..., "--fixture", help="API-Football fixture_id from local docs."),
    prediction_time: str | None = typer.Option(
        None,
        "--prediction-time",
        help="Prediction cutoff timestamp, ISO 8601. Defaults to now.",
    ),
    model_dir: Path | None = typer.Option(
        Path("data/models/v1"),
        "--model-dir",
        help="Model directory or model.joblib path. Missing model falls back safely.",
    ),
    refresh_data: bool = typer.Option(
        False,
        "--refresh-data/--no-refresh",
        help="Explicitly refresh API-Football before prediction.",
    ),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also save raw API payload snapshots to disk during live refresh.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON only."),
    json_output_path: Path | None = typer.Option(
        None,
        "--json-output",
        help="Write prediction JSON to this path.",
    ),
) -> None:
    """Predict a single fixture with point-in-time features and robust fallbacks."""
    settings = get_settings()
    reference = load_api_football_reference(settings.api_football_reference_path)
    players_reference = load_players_reference(settings.api_football_players_reference_path)
    cutoff = _parse_optional_prediction_time(prediction_time)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with session_scope(session_factory) as session:
        service = PredictionService(
            reference,
            session,
            players_reference=players_reference,
            market_1x2_bet_name=settings.market_1x2_bet_name,
            market_1x2_bet_id=settings.market_1x2_bet_id,
        )
        if refresh_data:
            with _api_client_from_settings(settings) as client:
                prediction = service.predict_fixture(
                    fixture,
                    cutoff,
                    model_dir=model_dir,
                    refresh_data=True,
                    save_raw=save_raw,
                    api_client=client,
                )
        else:
            prediction = service.predict_fixture(
                fixture,
                cutoff,
                model_dir=model_dir,
                refresh_data=False,
                save_raw=save_raw,
            )
    prediction_json = json.dumps(prediction.to_dict(), indent=2, sort_keys=True)
    if json_output_path is not None:
        json_output_path.parent.mkdir(parents=True, exist_ok=True)
        json_output_path.write_text(prediction_json + "\n", encoding="utf-8")
    if json_output:
        console.out(prediction_json)
    else:
        _print_prediction_summary(prediction, settings.app_timezone)


@app.command("predict-and-send")
def predict_and_send(
    fixture: int = typer.Option(..., "--fixture", help="API-Football fixture_id from local docs."),
    prediction_time: str | None = typer.Option(
        None,
        "--prediction-time",
        help="Prediction cutoff timestamp, ISO 8601. Defaults to now.",
    ),
    model_dir: Path | None = typer.Option(
        Path("data/models/v1"),
        "--model-dir",
        help="Model directory or model.joblib path. Missing model falls back safely.",
    ),
    refresh_data: bool = typer.Option(
        False,
        "--refresh-data/--no-refresh",
        help="Explicitly refresh API-Football before prediction.",
    ),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also save raw API payload snapshots to disk during live refresh.",
    ),
    competition_key: str | None = typer.Option(
        None,
        "--competition-key",
        help="Discord competition key. Defaults to fixture league from local reference.",
    ),
    channel: str = typer.Option("predictions", "--channel", help="Discord channel key."),
    discord_webhooks: Path | None = typer.Option(
        None,
        "--discord-webhooks",
        help="Discord webhook config path. Defaults to settings.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist route without sending."),
    print_only: bool = typer.Option(
        False,
        "--print-only",
        help="Print markdown and persist trace without sending.",
    ),
    force: bool = typer.Option(False, "--force", help="Bypass Discord message dedupe."),
) -> None:
    """Predict a fixture and send the markdown block to Discord."""
    settings = get_settings()
    reference, channels_config, webhooks_config = _load_discord_routing(
        settings,
        webhooks_path=discord_webhooks,
    )
    players_reference = load_players_reference(settings.api_football_players_reference_path)
    cutoff = _parse_optional_prediction_time(prediction_time)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with session_scope(session_factory) as session:
        service = PredictionService(
            reference,
            session,
            players_reference=players_reference,
            market_1x2_bet_name=settings.market_1x2_bet_name,
            market_1x2_bet_id=settings.market_1x2_bet_id,
        )
        if refresh_data:
            with _api_client_from_settings(settings) as api_client:
                prediction = service.predict_fixture(
                    fixture,
                    cutoff,
                    model_dir=model_dir,
                    refresh_data=True,
                    save_raw=save_raw,
                    api_client=api_client,
                )
        else:
            prediction = service.predict_fixture(
                fixture,
                cutoff,
                model_dir=model_dir,
                refresh_data=False,
                save_raw=save_raw,
            )
        fixture_row = session.get(Fixture, fixture)
        markdown = format_prediction_markdown(prediction, settings.app_timezone)
        if print_only:
            console.print(markdown)
        delivery = DiscordDeliveryService(
            session,
            channels_config=channels_config,
            webhooks_config=webhooks_config,
            legacy_webhook_url=settings.discord_webhook_url,
            timeout=settings.discord_timeout_seconds,
        )
        result = delivery.send_markdown(
            markdown,
            competition_key=_competition_key_from_fixture(
                reference,
                fixture_row,
                competition_key,
            ),
            league_id=fixture_row.league_id if fixture_row is not None else None,
            season=fixture_row.season if fixture_row is not None else None,
            channel_key=channel,
            message_type="prediction",
            fixture_id=fixture,
            model_prediction_id=prediction.model_prediction_id,
            dry_run=dry_run,
            print_only=print_only,
            force=force,
        )
    console.print(
        "Discord route "
        f"status={result.status} channel={result.route.channel_key} "
        f"webhook_hash={result.webhook_hash or 'none'}"
    )


@app.command("discord-check-config")
def discord_check_config(
    channels: Path | None = typer.Option(None, "--channels", help="Discord channels YAML."),
    webhooks: Path | None = typer.Option(None, "--webhooks", help="Discord webhooks YAML."),
) -> None:
    """Validate Discord routing config without sending messages."""
    settings = get_settings()
    _, channels_config, webhooks_config = _load_discord_routing(
        settings,
        channels_path=channels,
        webhooks_path=webhooks,
    )
    configured = sum(1 for route in webhooks_config.routes if route.webhook_url)
    console.print(
        "Discord config OK: "
        f"competitions={len(channels_config.competitions)} "
        f"routes={len(webhooks_config.routes)} configured_webhooks={configured}"
    )


@app.command("discord-send")
def discord_send(
    prediction_id: int = typer.Option(..., "--prediction-id", help="ModelPrediction ID."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist route without sending."),
    print_only: bool = typer.Option(False, "--print-only", help="Print only, no send."),
    force: bool = typer.Option(False, "--force", help="Bypass message dedupe."),
) -> None:
    """Send a stored model prediction to the competition predictions channel."""
    settings = get_settings()
    _, channels_config, webhooks_config = _load_discord_routing(settings)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with session_scope(session_factory) as session:
        result = send_prediction_to_discord(
            DiscordDeliveryService(
                session,
                channels_config=channels_config,
                webhooks_config=webhooks_config,
                legacy_webhook_url=settings.discord_webhook_url,
                timeout=settings.discord_timeout_seconds,
            ),
            prediction_id,
            dry_run=dry_run,
            print_only=print_only,
            force=force,
            timezone_name=settings.app_timezone,
        )
    console.print(
        f"Discord prediction status={result.status} webhook_hash={result.webhook_hash or 'none'}"
    )


@app.command("discord-send-message")
def discord_send_message(
    competition_key: str | None = typer.Option(None, "--competition-key", help="Competition key."),
    competition_alias: str | None = typer.Option(
        None,
        "--competition",
        help="Alias for --competition-key.",
    ),
    channel: str = typer.Option(..., "--channel", help="Discord channel key."),
    message_type: str = typer.Option("analysis", "--message-type", help="Message type."),
    content_file: Path = typer.Option(..., "--content-file", help="Markdown content file."),
    season: int | None = typer.Option(None, "--season", help="Optional season."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist route without sending."),
    print_only: bool = typer.Option(False, "--print-only", help="Print only, no send."),
    force: bool = typer.Option(False, "--force", help="Bypass message dedupe."),
) -> None:
    """Send an already formatted message through the Discord router."""
    settings = get_settings()
    _, channels_config, webhooks_config = _load_discord_routing(settings)
    resolved_competition_key = competition_alias or competition_key
    if not resolved_competition_key:
        raise typer.BadParameter("--competition or --competition-key is required")
    competition = channels_config.find_competition(
        competition_key=resolved_competition_key,
        season=season,
    )
    if competition is None:
        raise typer.BadParameter("Unknown Discord competition route")
    markdown = content_file.read_text(encoding="utf-8")
    if print_only:
        console.print(markdown)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with session_scope(session_factory) as session:
        result = DiscordDeliveryService(
            session,
            channels_config=channels_config,
            webhooks_config=webhooks_config,
            legacy_webhook_url=settings.discord_webhook_url,
            timeout=settings.discord_timeout_seconds,
        ).send_markdown(
            markdown,
            competition_key=resolved_competition_key,
            league_id=competition.league_id,
            season=competition.season,
            channel_key=channel,
            message_type=message_type,
            dry_run=dry_run,
            print_only=print_only,
            force=force,
        )
    console.print(
        f"Discord message status={result.status} webhook_hash={result.webhook_hash or 'none'}"
    )


@app.command("publish-daily-discord")
def publish_daily_discord(
    publish_date: str | None = typer.Option(
        None,
        "--date",
        help="Local date to publish, format YYYY-MM-DD. Defaults to today in APP_TIMEZONE.",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Competitions YAML/JSON config. Defaults to settings.",
    ),
    standings: bool = typer.Option(
        True,
        "--standings/--no-standings",
        help="Publish standings to the classement channel.",
    ),
    calendar: bool = typer.Option(
        True,
        "--calendar/--no-calendar",
        help="Publish next round calendar to the calendrier channel.",
    ),
    daily_matches: bool = typer.Option(
        True,
        "--daily-matches/--no-daily-matches",
        help="Publish target-date fixtures to the matchs_du_jour channel.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist routes without sending."),
    print_only: bool = typer.Option(False, "--print-only", help="Print messages without sending."),
    force: bool = typer.Option(False, "--force", help="Bypass Discord message dedupe."),
    replace_previous: bool = typer.Option(
        True,
        "--replace-previous/--no-replace-previous",
        help=(
            "Delete previous operational messages for the same competition/channel "
            "before sending."
        ),
    ),
) -> None:
    """Publish standings, next round calendar and daily matches to routed Discord channels."""
    settings = get_settings()
    if publish_date is None:
        target_date = datetime.now(ZoneInfo(settings.app_timezone)).date()
    else:
        try:
            target_date = date_type.fromisoformat(publish_date)
        except ValueError as exc:
            raise typer.BadParameter("--date must use YYYY-MM-DD format") from exc
    competitions = _load_competitions(settings, config or settings.competitions_config_path)
    _, channels_config, webhooks_config = _load_discord_routing(settings)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with session_scope(session_factory) as session:
        summary = publish_daily_discord_messages(
            session=session,
            competitions=competitions,
            delivery=DiscordDeliveryService(
                session,
                channels_config=channels_config,
                webhooks_config=webhooks_config,
                legacy_webhook_url=settings.discord_webhook_url,
                timeout=settings.discord_timeout_seconds,
            ),
            target_date=target_date,
            timezone_name=settings.app_timezone,
            include_standings=standings,
            include_calendar=calendar,
            include_daily_matches=daily_matches,
            dry_run=dry_run,
            print_only=print_only,
            force=force,
            replace_previous=replace_previous,
            echo=console.print,
        )
    console.print(summary.as_dict())


@app.command("publish-weekly-score")
def publish_weekly_score(
    publish_date: str | None = typer.Option(
        None,
        "--date",
        help="Local date to publish, format YYYY-MM-DD. Defaults to today in APP_TIMEZONE.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist route without sending."),
    print_only: bool = typer.Option(False, "--print-only", help="Print messages without sending."),
    force: bool = typer.Option(False, "--force", help="Bypass Discord message dedupe."),
    include_previous_week_finalization: bool = typer.Option(
        True,
        "--include-previous-week-finalization/--no-include-previous-week-finalization",
        help="On Mondays, also update the previous week scorecard.",
    ),
    replace_current_week: bool = typer.Option(
        True,
        "--replace-current-week/--no-replace-current-week",
        help="Replace previous score messages with the same week_key.",
    ),
) -> None:
    """Publish the weekly scorecard for Discord predictions."""
    settings = get_settings()
    if publish_date is None:
        target_date = datetime.now(ZoneInfo(settings.app_timezone)).date()
    else:
        try:
            target_date = date_type.fromisoformat(publish_date)
        except ValueError as exc:
            raise typer.BadParameter("--date must use YYYY-MM-DD format") from exc
    _, channels_config, webhooks_config = _load_discord_routing(settings)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with session_scope(session_factory) as session:
        summary = publish_weekly_prediction_score(
            session=session,
            delivery=DiscordDeliveryService(
                session,
                channels_config=channels_config,
                webhooks_config=webhooks_config,
                legacy_webhook_url=settings.discord_webhook_url,
                timeout=settings.discord_timeout_seconds,
            ),
            target_date=target_date,
            timezone_name=settings.app_timezone,
            include_previous_week_finalization=include_previous_week_finalization,
            dry_run=dry_run,
            print_only=print_only,
            force=force,
            replace_current_week=replace_current_week,
            echo=console.print,
        )
    console.print(summary.as_dict())


@app.command("publish-match-analyses")
def publish_match_analyses_cli(
    publish_date: str | None = typer.Option(
        None,
        "--date",
        help="Local match date, format YYYY-MM-DD. Defaults to today in APP_TIMEZONE.",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Competitions YAML/JSON config. Defaults to settings.",
    ),
    model_dir: Path | None = typer.Option(
        Path("data/models/v1"),
        "--model-dir",
        help="Model directory or model.joblib path. Missing model falls back safely.",
    ),
    refresh_data: bool = typer.Option(
        False,
        "--refresh-data/--no-refresh-data",
        help="Explicitly refresh API-Football before building missing H-6 predictions.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist route without sending."),
    print_only: bool = typer.Option(False, "--print-only", help="Print messages only."),
    force: bool = typer.Option(False, "--force", help="Bypass analysis dedupe."),
    limit: int | None = typer.Option(None, "--limit", help="Maximum due analyses."),
    analysis_grace_minutes: int = typer.Option(
        15,
        "--analysis-grace-minutes",
        help="Minutes after H-6 during which an analysis may still be sent.",
    ),
    save_raw: bool = typer.Option(False, "--save-raw", help="Save raw API payload snapshots."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON summary only."),
    json_output_path: Path | None = typer.Option(
        None,
        "--json-output",
        help="Write JSON summary to this path.",
    ),
) -> None:
    """Publish one H-6 analysis per due followed fixture to the analyses channel."""
    settings = get_settings()
    target_date = _parse_cli_date_or_today(publish_date, settings.app_timezone)
    if limit is not None and limit < 1:
        raise typer.BadParameter("--limit must be greater than 0")
    if analysis_grace_minutes < 0:
        raise typer.BadParameter("--analysis-grace-minutes must be positive")
    reference = load_api_football_reference(settings.api_football_reference_path)
    players_reference = load_players_reference(settings.api_football_players_reference_path)
    competitions = _load_competitions(settings, config or settings.competitions_config_path)
    _, channels_config, webhooks_config = _load_discord_routing(settings)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    api_client = _api_client_from_settings(settings) if refresh_data else None
    with session_scope(session_factory) as session:
        try:
            summary = publish_match_analyses(
                session=session,
                competitions=competitions,
                delivery=DiscordDeliveryService(
                    session,
                    channels_config=channels_config,
                    webhooks_config=webhooks_config,
                    legacy_webhook_url=settings.discord_webhook_url,
                    timeout=settings.discord_timeout_seconds,
                ),
                reference=reference,
                players_reference=players_reference,
                target_date=target_date,
                model_dir=model_dir,
                api_client=api_client,
                refresh_data=refresh_data,
                save_raw=save_raw,
                timezone_name=settings.app_timezone,
                dry_run=dry_run,
                print_only=print_only,
                force=force,
                limit=limit,
                analysis_grace_minutes=analysis_grace_minutes,
                echo=console.print,
            )
        finally:
            if api_client is not None:
                api_client.close()
    _emit_json_or_summary(
        summary.as_dict(),
        json_output=json_output,
        json_output_path=json_output_path,
        fallback_label="Match analyses",
    )


@app.command("publish-match-results")
def publish_match_results_cli(
    publish_date: str | None = typer.Option(
        None,
        "--date",
        help="Local match date, format YYYY-MM-DD. Defaults to today in APP_TIMEZONE.",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Competitions YAML/JSON config. Defaults to settings.",
    ),
    refresh_data: bool = typer.Option(
        False,
        "--refresh-data/--no-refresh-data",
        help="Explicitly refresh fixtures before selecting finished matches.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist route without sending."),
    print_only: bool = typer.Option(False, "--print-only", help="Print messages only."),
    force: bool = typer.Option(False, "--force", help="Bypass result dedupe."),
    limit: int | None = typer.Option(None, "--limit", help="Maximum finished results."),
    save_raw: bool = typer.Option(False, "--save-raw", help="Save raw API payload snapshots."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON summary only."),
    json_output_path: Path | None = typer.Option(
        None,
        "--json-output",
        help="Write JSON summary to this path.",
    ),
) -> None:
    """Publish one post-match result summary per finished followed fixture."""
    settings = get_settings()
    target_date = _parse_cli_date_or_today(publish_date, settings.app_timezone)
    if limit is not None and limit < 1:
        raise typer.BadParameter("--limit must be greater than 0")
    competitions = _load_competitions(settings, config or settings.competitions_config_path)
    _, channels_config, webhooks_config = _load_discord_routing(settings)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    api_client = _api_client_from_settings(settings) if refresh_data else None
    with session_scope(session_factory) as session:
        try:
            summary = publish_match_results(
                session=session,
                competitions=competitions,
                delivery=DiscordDeliveryService(
                    session,
                    channels_config=channels_config,
                    webhooks_config=webhooks_config,
                    legacy_webhook_url=settings.discord_webhook_url,
                    timeout=settings.discord_timeout_seconds,
                ),
                target_date=target_date,
                api_client=api_client,
                refresh_data=refresh_data,
                save_raw=save_raw,
                timezone_name=settings.app_timezone,
                dry_run=dry_run,
                print_only=print_only,
                force=force,
                limit=limit,
                echo=console.print,
            )
        finally:
            if api_client is not None:
                api_client.close()
    _emit_json_or_summary(
        summary.as_dict(),
        json_output=json_output,
        json_output_path=json_output_path,
        fallback_label="Match results",
    )


@app.command("discord-test-route")
def discord_test_route(
    competition_key: str = typer.Option(..., "--competition-key", help="Competition key."),
    channel: str = typer.Option("predictions", "--channel", help="Discord channel key."),
    message_type: str = typer.Option("prediction", "--message-type", help="Message type."),
    send: bool = typer.Option(False, "--send", help="Actually send the test message."),
) -> None:
    """Resolve and optionally send a synthetic Discord routing test."""
    settings = get_settings()
    _, channels_config, webhooks_config = _load_discord_routing(settings)
    competition = channels_config.find_competition(competition_key=competition_key)
    if competition is None:
        raise typer.BadParameter("Unknown Discord competition route")
    markdown = "```md\nTest routage Discord Football Predictor\n```"
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with session_scope(session_factory) as session:
        result = DiscordDeliveryService(
            session,
            channels_config=channels_config,
            webhooks_config=webhooks_config,
            legacy_webhook_url=settings.discord_webhook_url,
            timeout=settings.discord_timeout_seconds,
        ).send_markdown(
            markdown,
            competition_key=competition_key,
            league_id=competition.league_id,
            season=competition.season,
            channel_key=channel,
            message_type=message_type,
            dry_run=not send,
            force=True,
        )
    console.print(
        f"Discord test status={result.status} route={competition_key}/{channel} "
        f"webhook_hash={result.webhook_hash or 'none'}"
    )


@app.command("discord-provision-webhooks")
def discord_provision_webhooks(
    channels: Path | None = typer.Option(
        None,
        "--channels-config",
        "--channels",
        help="Discord channels YAML.",
    ),
    output: Path = typer.Option(
        Path("config/discord_webhooks.local.yaml"),
        "--output",
        help="Local gitignored webhook config output.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Actually provision webhooks and write local config.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview routes without creating Discord webhooks.",
    ),
    force: bool = typer.Option(False, "--force", help="Reserved for future overwrite support."),
    only_competition: str | None = typer.Option(None, "--only-competition"),
    only_channel: str | None = typer.Option(None, "--only-channel"),
) -> None:
    """Optionally create Discord webhooks from configured channel IDs."""
    settings = get_settings()
    if yes and dry_run:
        raise typer.BadParameter("Use either --dry-run or --yes, not both")
    reference = load_api_football_reference(settings.api_football_reference_path)
    resolved_channels_path = _existing_or_example(
        channels or settings.discord_channels_config_path,
        Path("config/discord_channels.example.yaml"),
    )
    channels_config = load_discord_channels_config(
        resolved_channels_path,
        reference,
    )
    should_write = yes or (settings.discord_provision_webhooks_enabled and not dry_run)
    if should_write and not settings.discord_provision_webhooks_enabled and not yes:
        raise typer.BadParameter("Set DISCORD_PROVISION_WEBHOOKS_ENABLED=true or pass --yes")
    provisioner = None
    if should_write:
        if not settings.discord_bot_token:
            raise typer.BadParameter("DISCORD_BOT_TOKEN is required for provisioning")
        provisioner = DiscordWebhookProvisioner(
            settings.discord_bot_token,
            base_url=settings.discord_api_base_url,
            timeout=settings.discord_timeout_seconds,
        )
    routes = provision_webhooks(
        channels_config,
        provisioner=provisioner,
        dry_run=dry_run or not should_write,
        only_competition=only_competition,
        only_channel=only_channel,
    )
    if should_write:
        write_local_webhooks_config(output, routes)
        console.print(f"Discord webhooks written to {output} force={force}")
    else:
        console.print(f"Discord provisioning dry-run routes={len(routes)}")


@app.command("predict-today")
def predict_today(
    prediction_date: str | None = typer.Option(
        None,
        "--date",
        help="Date to scan, format YYYY-MM-DD. Defaults to the local date at prediction time.",
    ),
    window: DailyPredictionWindow = typer.Option(
        DailyPredictionWindow.NOW,
        "--window",
        help="Prediction window: early, mid, late, now, or all.",
    ),
    league: list[int] | None = typer.Option(
        None,
        "--league",
        help="Repeatable API-Football league_id filter, validated against docs reference.",
    ),
    season: int | None = typer.Option(None, "--season", help="Optional season filter."),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Competitions YAML/JSON config. Defaults to settings.",
    ),
    model_dir: Path | None = typer.Option(
        Path("data/models/v1"),
        "--model-dir",
        help="Model directory or model.joblib path. Missing model falls back safely.",
    ),
    prediction_time: str | None = typer.Option(
        None,
        "--prediction-time",
        help="Prediction cutoff timestamp, ISO 8601. Defaults to now.",
    ),
    refresh_data: bool = typer.Option(
        False,
        "--refresh-data/--no-refresh-data",
        help="Explicitly refresh API-Football before prediction.",
    ),
    send_discord: bool = typer.Option(
        False,
        "--send-discord",
        help="Send each prediction to the routed Discord predictions channel.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist Discord route without sending."),
    print_only: bool = typer.Option(False, "--print-only", help="Print only, no Discord send."),
    force: bool = typer.Option(False, "--force", help="Bypass Discord automation dedupe."),
    limit: int | None = typer.Option(None, "--limit", help="Maximum selected fixtures to predict."),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also save raw API payload snapshots to disk during live refresh.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON summary only."),
    json_output_path: Path | None = typer.Option(
        None,
        "--json-output",
        help="Write JSON summary to this path.",
    ),
) -> None:
    """Automate predictions for fixtures scheduled on a date."""
    target_date = None
    if prediction_date is not None:
        try:
            target_date = date_type.fromisoformat(prediction_date)
        except ValueError as exc:
            raise typer.BadParameter("--date must use YYYY-MM-DD format") from exc
    if limit is not None and limit < 1:
        raise typer.BadParameter("--limit must be greater than 0")
    settings = get_settings()
    cutoff = _parse_optional_prediction_time(prediction_time)
    reference = load_api_football_reference(settings.api_football_reference_path)
    players_reference = load_players_reference(settings.api_football_players_reference_path)
    competitions = _load_competitions(settings, config or settings.competitions_config_path)
    if league:
        for league_id in league:
            _validate_league_id(settings, league_id, season, strict=True)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    api_client = None
    if refresh_data:
        api_client = _api_client_from_settings(settings)
    with session_scope(session_factory) as session:
        delivery = None
        if send_discord:
            _, channels_config, webhooks_config = _load_discord_routing(settings)
            delivery = DiscordDeliveryService(
                session,
                channels_config=channels_config,
                webhooks_config=webhooks_config,
                legacy_webhook_url=settings.discord_webhook_url,
                timeout=settings.discord_timeout_seconds,
            )
        try:
            summary = run_daily_predictions(
                target_date,
                league_ids=tuple(league or ()),
                window=window,
                send_discord=send_discord,
                refresh_data=refresh_data,
                dry_run=dry_run,
                session=session,
                reference=reference,
                players_reference=players_reference,
                competitions=competitions,
                season=season,
                model_dir=model_dir,
                api_client=api_client,
                discord_delivery=delivery,
                timezone_name=settings.app_timezone,
                force=force,
                print_only=print_only,
                limit=limit,
                save_raw=save_raw,
                now=cutoff,
            )
        finally:
            if api_client is not None:
                api_client.close()
    summary_payload = summary.as_dict()
    summary_json = json.dumps(summary_payload, indent=2, sort_keys=True)
    if json_output_path is not None:
        json_output_path.parent.mkdir(parents=True, exist_ok=True)
        json_output_path.write_text(summary_json + "\n", encoding="utf-8")
    if json_output:
        console.out(summary_json)
    else:
        console.print(
            "Prediction automation "
            f"date={summary.target_date.isoformat()} window={summary.window.value} "
            f"found={summary.found} predicted={summary.predicted} sent={summary.sent} "
            f"duplicates={summary.duplicate_skipped} skipped={summary.skipped} "
            f"failed={summary.failed}"
        )


@app.command("ingest-fixtures")
def ingest_fixtures(
    league_id: int | None = typer.Option(
        None,
        "--league",
        "--league-id",
        help="Validated API-Football league_id.",
    ),
    season: int | None = typer.Option(None, "--season", help="API-Football season."),
    fixture_date: str | None = typer.Option(
        None,
        "--date",
        help="Fixture date for API-Football /fixtures, format YYYY-MM-DD.",
    ),
    team_id: int | None = typer.Option(None, "--team-id", help="Validated API-Football team_id."),
    last: int | None = typer.Option(None, "--last", help="Fetch last N fixtures for team_id."),
    next_count: int | None = typer.Option(
        None,
        "--next",
        help="Fetch next N fixtures for team_id.",
    ),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
    prefer_docs: bool = typer.Option(
        False,
        "--prefer-docs",
        help="Seed fixtures and standings from docs reference instead of live API.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run ingestion then roll back."),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also write API live payloads to disk through ApiFootballClient.",
    ),
) -> None:
    """Ingest fixtures from docs/reference or API-Football live."""
    docs_supported = team_id is None
    effective_prefer_docs = prefer_docs or (not refresh_api and docs_supported)
    if not refresh_api and not effective_prefer_docs:
        console.print("Fixture ingestion requires --prefer-docs or explicit --refresh-api.")
        raise typer.Exit(2)
    settings = get_settings()
    _validate_fixture_ingestion_args(
        settings,
        league_id,
        season,
        fixture_date,
        team_id,
        last,
        next_count,
        strict_reference=effective_prefer_docs or not refresh_api,
    )
    if effective_prefer_docs and fixture_date is None and (league_id is None or season is None):
        raise typer.BadParameter("--prefer-docs fixture seed requires --league-id and --season")

    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    session = session_factory()
    summary = MatchIngestionSummary()
    try:
        if effective_prefer_docs:
            summary.merge(
                seed_fixtures_and_standings_from_reference(
                    session,
                    settings.api_football_reference_path,
                    league_id=league_id,
                    season=season,
                    fixture_date=date_type.fromisoformat(fixture_date)
                    if fixture_date is not None
                    else None,
                    include_fixtures=True,
                    include_standings=fixture_date is None,
                )
            )
        if refresh_api:
            with _api_client_from_settings(settings) as client:
                service = FixtureIngestionService(session, client, save_raw=save_raw)
                if league_id is not None and season is not None:
                    summary.merge(service.ingest_league_season(league_id, season))
                elif fixture_date is not None:
                    summary.merge(service.ingest_date(date_type.fromisoformat(fixture_date)))
                elif team_id is not None and last is not None:
                    summary.merge(service.ingest_team_last(team_id, last))
                elif team_id is not None and next_count is not None:
                    summary.merge(service.ingest_team_next(team_id, next_count))
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    output = summary.as_dict()
    output["dry_run"] = int(dry_run)
    console.print(output)


@app.command("ingest-standings")
def ingest_standings(
    league_id: int = typer.Option(
        ...,
        "--league",
        "--league-id",
        help="Validated API-Football league_id.",
    ),
    season: int = typer.Option(..., "--season", help="API-Football season."),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
    prefer_docs: bool = typer.Option(
        False,
        "--prefer-docs",
        help="Seed standings from docs reference instead of live API.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run ingestion then roll back."),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also write API live payloads to disk through ApiFootballClient.",
    ),
) -> None:
    """Ingest standings snapshots from docs/reference or API-Football live."""
    effective_prefer_docs = prefer_docs or not refresh_api
    settings = get_settings()
    _validate_league_id(
        settings,
        league_id,
        season,
        strict=effective_prefer_docs or not refresh_api,
    )
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    session = session_factory()
    summary = MatchIngestionSummary()
    try:
        if effective_prefer_docs:
            summary.merge(
                seed_fixtures_and_standings_from_reference(
                    session,
                    settings.api_football_reference_path,
                    league_id=league_id,
                    season=season,
                    include_fixtures=False,
                    include_standings=True,
                )
            )
        if refresh_api:
            with _api_client_from_settings(settings) as client:
                service = StandingIngestionService(session, client, save_raw=save_raw)
                summary.merge(
                    service.ingest_league_season(
                        league_id,
                        season,
                    )
                )
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    output = summary.as_dict()
    output["dry_run"] = int(dry_run)
    console.print(output)


@app.command("ingest-fixture-details")
def ingest_fixture_details(
    fixture: int | None = typer.Option(
        None,
        "--fixture",
        help="API-Football fixture_id already stored in the local DB.",
    ),
    league_id: int | None = typer.Option(
        None,
        "--league",
        "--league-id",
        help="Optional API-Football league_id filter for batch mode.",
    ),
    season: int | None = typer.Option(None, "--season", help="Optional season filter."),
    fixture_date: str | None = typer.Option(
        None,
        "--date",
        help="Optional fixture date filter for batch mode, format YYYY-MM-DD.",
    ),
    date_from: str | None = typer.Option(
        None,
        "--from-date",
        help="Optional inclusive start date for batch mode, format YYYY-MM-DD.",
    ),
    date_to: str | None = typer.Option(
        None,
        "--to-date",
        help="Optional inclusive end date for batch mode, format YYYY-MM-DD.",
    ),
    days_back: int | None = typer.Option(
        None,
        "--days-back",
        help="Use fixtures from APP_TIMEZONE today minus N days through today.",
    ),
    status: list[str] | None = typer.Option(
        None,
        "--status",
        help=(
            "Repeatable fixture status_short filter. Also accepts whitespace lists "
            "like 'FT AET PEN'."
        ),
    ),
    limit: int | None = typer.Option(None, "--limit", help="Maximum fixtures in batch mode."),
    include_upcoming: bool = typer.Option(
        False,
        "--include-upcoming",
        help="In batch mode, include upcoming fixtures when --status is not provided.",
    ),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
    only: list[str] | None = typer.Option(
        None,
        "--only",
        help="Repeatable detail key: statistics, events, lineups, players, injuries, predictions.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run ingestion then roll back."),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also write API live payloads to disk through ApiFootballClient.",
    ),
    delay_seconds: float = typer.Option(
        0.0,
        "--delay-seconds",
        help="Sleep between fixtures in batch mode to reduce API rate pressure.",
    ),
    stop_on_rate_limit: bool = typer.Option(
        True,
        "--stop-on-rate-limit/--continue-on-rate-limit",
        help="Stop batch ingestion after the first API-Football rate-limit response.",
    ),
) -> None:
    """Ingest detailed dynamic data for one fixture or DB-filtered fixture batch."""
    _require_refresh_api(refresh_api)
    settings = get_settings()
    parsed_date, parsed_from, parsed_to, status_values = _validate_fixture_details_cli_args(
        settings,
        fixture,
        league_id,
        season,
        fixture_date,
        date_from,
        date_to,
        days_back,
        status,
        limit,
    )
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    session = session_factory()
    try:
        reference = load_api_football_reference(settings.api_football_reference_path)
        players_reference = load_players_reference(settings.api_football_players_reference_path)
        with _api_client_from_settings(settings) as client:
            service = FixtureDetailsIngestionService(
                session,
                client,
                reference=reference,
                players_reference=players_reference,
                save_raw=save_raw,
                unknown_players_path=DEFAULT_UNKNOWN_PLAYERS_PATH,
            )
            if fixture is not None:
                if only:
                    summary = service.ingest_fixture_details(fixture, include=only)
                else:
                    summary = service.ingest_full_fixture_details(fixture)
            else:
                effective_statuses = status_values
                if effective_statuses is None and not include_upcoming:
                    effective_statuses = ["FT"]
                summary = service.ingest_fixture_details_for_filters(
                    league_id=league_id,
                    season=season,
                    fixture_date=parsed_date,
                    date_from=parsed_from,
                    date_to=parsed_to,
                    statuses=effective_statuses,
                    limit=limit,
                    include=only,
                    stop_on_rate_limit=stop_on_rate_limit,
                    delay_seconds=delay_seconds,
                )
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    output = summary.as_dict()
    output["dry_run"] = int(dry_run)
    console.print(output)


@app.command("ingest-fixture-details-batch")
def ingest_fixture_details_batch(
    league_id: int | None = typer.Option(
        None,
        "--league",
        "--league-id",
        help="Optional API-Football league_id filter.",
    ),
    season: int | None = typer.Option(None, "--season", help="Optional season filter."),
    fixture_date: str | None = typer.Option(
        None,
        "--date",
        help="Optional fixture date filter, format YYYY-MM-DD.",
    ),
    date_from: str | None = typer.Option(
        None,
        "--from-date",
        help="Optional inclusive start date filter, format YYYY-MM-DD.",
    ),
    date_to: str | None = typer.Option(
        None,
        "--to-date",
        help="Optional inclusive end date filter, format YYYY-MM-DD.",
    ),
    days_back: int | None = typer.Option(
        None,
        "--days-back",
        help="Use fixtures from APP_TIMEZONE today minus N days through today.",
    ),
    status: list[str] | None = typer.Option(
        None,
        "--status",
        help="Repeatable fixture status_short filter such as FT, AET or PEN.",
    ),
    limit: int | None = typer.Option(None, "--limit", help="Maximum fixtures to process."),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
    only: list[str] | None = typer.Option(
        None,
        "--only",
        help="Repeatable detail key: statistics, events, lineups, players, injuries, predictions.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run ingestion then roll back."),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also write API live payloads to disk through ApiFootballClient.",
    ),
    delay_seconds: float = typer.Option(
        0.0,
        "--delay-seconds",
        help="Sleep between fixtures in batch mode to reduce API rate pressure.",
    ),
    stop_on_rate_limit: bool = typer.Option(
        True,
        "--stop-on-rate-limit/--continue-on-rate-limit",
        help="Stop batch ingestion after the first API-Football rate-limit response.",
    ),
) -> None:
    """Compatibility command for fixture detail batch ingestion."""
    ingest_fixture_details(
        fixture=None,
        league_id=league_id,
        season=season,
        fixture_date=fixture_date,
        date_from=date_from,
        date_to=date_to,
        days_back=days_back,
        status=status,
        limit=limit,
        include_upcoming=False,
        refresh_api=refresh_api,
        only=only,
        dry_run=dry_run,
        save_raw=save_raw,
        delay_seconds=delay_seconds,
        stop_on_rate_limit=stop_on_rate_limit,
    )


@app.command("ingest-odds")
def ingest_odds(
    fixture: int | None = typer.Option(
        None,
        "--fixture",
        help="API-Football fixture_id for prematch odds.",
    ),
    odds_date: str | None = typer.Option(
        None,
        "--date",
        help="Odds date for API-Football /odds, format YYYY-MM-DD.",
    ),
    league_id: int | None = typer.Option(
        None,
        "--league",
        "--league-id",
        help="API-Football league_id for odds ingestion.",
    ),
    season: int | None = typer.Option(None, "--season", help="API-Football season."),
    bookmaker_ids: list[int] | None = typer.Option(
        None,
        "--bookmaker",
        help="Repeatable bookmaker_id filter validated against local docs when possible.",
    ),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run ingestion then roll back."),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also write API live payloads to disk through ApiFootballClient.",
    ),
) -> None:
    """Ingest prematch 1X2 odds from API-Football."""
    _require_refresh_api(refresh_api)
    settings = get_settings()
    parsed_date = _validate_odds_ingestion_args(
        settings,
        fixture,
        league_id,
        season,
        odds_date,
        bookmaker_ids,
    )
    reference = load_api_football_reference(settings.api_football_reference_path)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    session = session_factory()
    try:
        with _api_client_from_settings(settings) as client:
            service = OddsIngestionService(
                session,
                client,
                reference=reference,
                market_bet_name=settings.market_1x2_bet_name,
                market_bet_id=settings.market_1x2_bet_id,
                save_raw=save_raw,
            )
            if fixture is not None:
                summary = service.ingest_odds_for_fixture(
                    fixture,
                    bookmaker_ids=bookmaker_ids,
                )
            elif parsed_date is not None:
                summary = service.ingest_odds_by_date(
                    parsed_date,
                    league_id=league_id,
                    season=season,
                    bookmaker_ids=bookmaker_ids,
                )
            else:
                if league_id is None or season is None:
                    raise typer.BadParameter("--league and --season must be provided together")
                summary = service.ingest_odds_by_league_season(
                    league_id,
                    season,
                    bookmaker_ids=bookmaker_ids,
                )
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    output = summary.as_dict()
    output["dry_run"] = int(dry_run)
    console.print(output)


@app.command("odds-features")
def odds_features_command(
    fixture: int = typer.Option(
        ...,
        "--fixture",
        help="API-Football fixture_id used to read local prematch odds snapshots.",
    ),
    as_of: str | None = typer.Option(
        None,
        "--as-of",
        help="Point-in-time cutoff for odds snapshots. Defaults to now.",
    ),
) -> None:
    """Compute local market probabilities and odds movement without live API calls."""
    settings = get_settings()
    _validate_fixture_id(settings, fixture, strict=False)
    parsed_as_of = parse_datetime(as_of) if as_of is not None else utc_now()
    if parsed_as_of is None:
        raise typer.BadParameter("--as-of must be an ISO datetime")
    reference = load_api_football_reference(settings.api_football_reference_path)
    bet_id = resolve_1x2_bet_id(
        reference,
        configured_bet_id=settings.market_1x2_bet_id,
        configured_bet_name=settings.market_1x2_bet_name,
    )
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with session_scope(session_factory) as session:
        consensus = compute_market_consensus(
            session,
            fixture,
            as_of_time=parsed_as_of,
            bet_id=bet_id,
        )
        movement = compute_odds_movement(
            session,
            fixture,
            parsed_as_of,
            bet_id=bet_id,
        )

    if consensus is None:
        console.print("No prematch 1X2 odds snapshots available before the requested time.")
        raise typer.Exit(2)
    console.print(
        {
            "fixture_id": fixture,
            "as_of_time": parsed_as_of.isoformat(),
            "p_market_home": round(consensus.p_market_home, 6),
            "p_market_draw": round(consensus.p_market_draw, 6),
            "p_market_away": round(consensus.p_market_away, 6),
            "market_confidence": round(consensus.market_confidence, 6),
            "market_dispersion": round(consensus.market_dispersion, 6),
            "bookmaker_count": consensus.bookmaker_count,
            "delta_home": movement.delta_home,
            "delta_draw": movement.delta_draw,
            "delta_away": movement.delta_away,
        }
    )


@app.command("build-dataset")
def build_dataset(
    league_ids: list[int] | None = typer.Option(
        None,
        "--league",
        "--league-id",
        help="API-Football league ID. Repeat for multiple leagues.",
    ),
    seasons: list[int] | None = typer.Option(
        None,
        "--season",
        help="API-Football season. Repeat for multiple seasons.",
    ),
    prediction_window: str = typer.Option(
        "24h",
        "--prediction-window",
        help="Point-in-time simulation window: 24h, 6h, 30m, or 40m before fixture date.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Optional CSV or Parquet output path.",
    ),
    output_format: str | None = typer.Option(
        None,
        "--format",
        help="Optional export format override: csv or parquet.",
    ),
    limit: int | None = typer.Option(None, "--limit", help="Maximum fixtures to process."),
    min_quality: int = typer.Option(0, "--min-quality", help="Minimum data quality score."),
) -> None:
    """Build a point-in-time historical training dataset."""
    if not league_ids:
        raise typer.BadParameter("At least one --league is required")
    if not seasons:
        raise typer.BadParameter("At least one --season is required")
    try:
        prediction_offset = parse_prediction_window(prediction_window)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if output_format is not None and output_format.casefold() not in {"csv", "parquet"}:
        raise typer.BadParameter("--format must be csv or parquet")

    settings = get_settings()
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    players_reference = load_players_reference(settings.api_football_players_reference_path)
    with session_scope(session_factory) as session:
        frame = build_training_dataset(
            session,
            league_ids,
            seasons,
            prediction_offset=prediction_offset,
            output_path=output,
            output_format=output_format,
            players_reference=players_reference,
            limit=limit,
            min_quality=min_quality,
        )
    console.print(
        {
            "rows": len(frame),
            "columns": len(frame.columns),
            "prediction_window": prediction_window,
            "output": str(output) if output is not None else None,
        }
    )


@app.command()
def train(
    dataset: Path = typer.Option(..., "--dataset", help="CSV or Parquet training dataset."),
    output_dir: Path = typer.Option(
        Path("data/models/v1"),
        "--output-dir",
        help="Directory where model.joblib and metadata.json are written.",
    ),
    model_version: str = typer.Option("v1", "--model-version", help="Model version label."),
    calibration: str = typer.Option(
        "sigmoid",
        "--calibration",
        help="Calibration method: sigmoid, isotonic, or none.",
    ),
    valid_until: str | None = typer.Option(
        None,
        "--valid-until",
        help="Fixture-date cutoff for train/validation split.",
    ),
    test_until: str | None = typer.Option(
        None,
        "--test-until",
        help="Optional fixture-date cutoff after validation for held-out test rows.",
    ),
) -> None:
    """Train the Sprint 11 sklearn sport model and save an artifact."""
    normalized_calibration = calibration.casefold()
    if normalized_calibration not in {"sigmoid", "isotonic", "none"}:
        raise typer.BadParameter("--calibration must be sigmoid, isotonic, or none")
    if not dataset.exists():
        raise typer.BadParameter(f"Dataset not found: {dataset}")

    if valid_until is not None or test_until is not None:
        console.print(
            "Note: Sprint 11 train_model_from_dataset uses chronological 80/20 split "
            "when fixture_date is present; explicit cutoffs are reserved for backtesting."
        )
    result = train_model_from_dataset(
        dataset,
        output_dir,
        model_version=model_version,
    )
    console.print(
        {
            "model_version": result.model.model_version,
            "output_dir": str(output_dir),
            "features": len(result.model.feature_names),
            "model_path": str(result.model_path),
            "metadata_path": str(result.metadata_path),
            "feature_names_path": str(result.feature_names_path),
            "metrics_path": str(result.metrics_path),
            "feature_coverage_path": str(result.feature_coverage_path)
            if result.feature_coverage_path is not None
            else None,
            "calibration_requested": normalized_calibration,
        }
    )


@app.command()
def backtest(
    dataset: Path = typer.Option(..., "--dataset", help="CSV or Parquet backtest dataset."),
    model_dir: Path | None = typer.Option(
        None,
        "--model-dir",
        help="Directory containing model.joblib. Omit to evaluate baselines only.",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Report directory. Defaults to data/processed/backtests/<timestamp>.",
    ),
    output_format: str = typer.Option(
        "both",
        "--format",
        help="Report format: json, markdown, or both.",
    ),
    train_ratio: float = typer.Option(0.60, "--train-ratio"),
    valid_ratio: float = typer.Option(0.20, "--valid-ratio"),
    test_ratio: float = typer.Option(0.20, "--test-ratio"),
    retrain_v2_model_version: str | None = typer.Option(
        None,
        "--retrain-v2-model-version",
        help=(
            "Train a V2 model inside the temporal backtest on train/validation only, "
            "then evaluate test."
        ),
    ),
) -> None:
    """Backtest a model artifact and baselines with a temporal split."""
    normalized_format = output_format.casefold()
    if normalized_format not in {"json", "markdown", "both"}:
        raise typer.BadParameter("--format must be json, markdown, or both")
    if not dataset.exists():
        raise typer.BadParameter(f"Dataset not found: {dataset}")
    if model_dir is not None and not model_dir.exists():
        raise typer.BadParameter(f"Model directory or file not found: {model_dir}")
    try:
        config = BacktestConfig(
            train_ratio=train_ratio,
            valid_ratio=valid_ratio,
            test_ratio=test_ratio,
            report_format=cast(ReportFormat, normalized_format),
            retrain_v2_model_version=retrain_v2_model_version,
        )
        result = run_backtest(
            dataset,
            model_dir=model_dir,
            output_dir=output_dir,
            config=config,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(
        {
            "test_rows": result.periods["test"].row_count,
            "models": list(result.metrics_by_model),
            "reports": {name: str(path) for name, path in result.report_paths.items()},
            "test_accuracy": {
                name: metrics.get("accuracy")
                for name, metrics in result.metrics_by_model.items()
            },
        }
    )


def main() -> None:
    try:
        app()
    except FootballPredictorError as exc:
        console.print(f"Error: {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    main()
