"""Local diagnostics and data-quality reporting."""

from __future__ import annotations

import platform
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from enum import StrEnum
from pathlib import Path
from typing import Any

from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from football_predictor.config.competitions import load_competition_config
from football_predictor.config.settings import Settings
from football_predictor.db import models
from football_predictor.db.models import Base
from football_predictor.db.session import create_db_engine
from football_predictor.discord.config import (
    load_discord_channels_config,
    load_discord_webhooks_config,
)
from football_predictor.features.data_quality import observability_quality_payload
from football_predictor.reference.loaders import (
    load_api_football_reference,
    load_players_cache,
    load_players_reference,
)
from football_predictor.reference.lookups import ApiFootballReference
from football_predictor.utils.exceptions import DiagnosticsError
from football_predictor.utils.logging import sanitize_text
from football_predictor.utils.secrets import describe_secret
from football_predictor.utils.time import ensure_aware_utc

JsonDict = dict[str, Any]
FINISHED_STATUSES = {"FT", "AET", "PEN"}
FUTURE_STATUSES = {"NS", "TBD"}


class DiagnosticStatus(StrEnum):
    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    status: DiagnosticStatus
    message: str
    details: JsonDict = field(default_factory=dict)
    critical: bool = False

    def as_dict(self) -> JsonDict:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "critical": self.critical,
            "details": self.details,
        }


@dataclass(frozen=True)
class DiagnosticReport:
    checks: list[DiagnosticCheck]

    @property
    def has_errors(self) -> bool:
        return any(check.status == DiagnosticStatus.ERROR for check in self.checks)

    @property
    def has_critical_errors(self) -> bool:
        return any(
            check.status == DiagnosticStatus.ERROR and check.critical for check in self.checks
        )

    def as_dict(self) -> JsonDict:
        return {
            "status": "ERROR" if self.has_errors else "OK",
            "has_critical_errors": self.has_critical_errors,
            "checks": [check.as_dict() for check in self.checks],
        }


def build_diagnostic_report(
    settings: Settings,
    *,
    version: str,
    check_db: bool = True,
) -> DiagnosticReport:
    """Build the local doctor report without network calls."""
    checks: list[DiagnosticCheck] = [
        DiagnosticCheck(
            name="runtime",
            status=DiagnosticStatus.OK,
            message="Runtime disponible",
            details={"version": version, "python": platform.python_version()},
        ),
        DiagnosticCheck(
            name="settings",
            status=DiagnosticStatus.OK,
            message="Configuration chargée",
            details={
                "database_url": mask_database_url(settings.database_url),
                "timezone": settings.app_timezone,
                "api_timeout_seconds": settings.api_football_timeout_seconds,
                "api_max_retries": settings.api_football_max_retries,
                "api_raw_snapshot_dir": str(settings.api_football_raw_snapshot_dir),
                "competitions_config_path": str(settings.competitions_config_path),
                "discord_channels_config_path": str(settings.discord_channels_config_path),
                "discord_webhooks_config_path": str(settings.discord_webhooks_config_path),
            },
        ),
        DiagnosticCheck(
            name="secrets",
            status=DiagnosticStatus.OK,
            message="Secrets masqués",
            details={
                "api_key": describe_secret("API key", settings.api_football_key),
                "discord_webhook": describe_secret(
                    "Discord webhook", settings.discord_webhook_url
                ),
                "discord_bot_token": describe_secret(
                    "Discord bot token", settings.discord_bot_token
                ),
                "discord_guild_id": describe_secret(
                    "Discord guild id", settings.discord_guild_id
                ),
            },
        ),
    ]

    reference_check, reference = _check_api_reference(settings.api_football_reference_path)
    checks.append(
        _check_markdown_reference(
            "api_football_reference_md",
            Path("docs/api_football_reference.md"),
        )
    )
    checks.append(reference_check)
    checks.append(
        _check_markdown_reference(
            "api_football_players_reference_md",
            Path("docs/api_football_players_reference.md"),
        )
    )
    checks.append(_check_players_reference(settings.api_football_players_reference_path))
    checks.append(_check_players_cache(settings.api_football_players_cache_path))
    checks.append(_check_model_dir(Path("data/models")))
    checks.append(_check_competitions_config(settings, reference))
    checks.extend(_check_discord_config(settings, reference))
    if check_db:
        checks.append(_check_database(settings))
    return DiagnosticReport(checks)


def build_data_quality_report(
    session: Session,
    *,
    fixture_id: int | None = None,
    target_date: date | None = None,
    league_id: int | None = None,
    season: int | None = None,
    reference_docs_available: bool = True,
) -> JsonDict:
    """Summarize local DB coverage without recalculating features or calling APIs."""
    fixtures = _select_fixtures(
        session,
        fixture_id=fixture_id,
        target_date=target_date,
        league_id=league_id,
        season=season,
    )
    fixture_ids = [fixture.fixture_id for fixture in fixtures]
    fixture_id_set = set(fixture_ids)
    fixture_league_ids = {fixture.league_id for fixture in fixtures}
    fixture_seasons = {fixture.season for fixture in fixtures}
    effective_league_id = (
        league_id if league_id is not None else next(iter(fixture_league_ids), None)
    )
    if len(fixture_league_ids) != 1 and league_id is None:
        effective_league_id = None
    effective_season = season if season is not None else next(iter(fixture_seasons), None)
    if len(fixture_seasons) != 1 and season is None:
        effective_season = None
    status_short = [fixture.status_short or fixture.status or "" for fixture in fixtures]
    history_home_count, history_away_count = _history_counts_for_fixtures(session, fixtures)

    feature_rows = _scoped_rows(
        session,
        models.FeatureSnapshot,
        fixture_ids=fixture_ids,
        league_id=effective_league_id,
        season=effective_season,
    )
    quality_scores: list[float] = []
    for row in feature_rows:
        if isinstance(row.data_quality_json, dict):
            score = _extract_quality_score(row.data_quality_json)
            if score is not None:
                quality_scores.append(score)

    fixture_statistics_count = _count_rows(
        session,
        models.FixtureStatistics,
        fixture_ids=fixture_ids,
        league_id=effective_league_id,
        season=effective_season,
    )
    odds_count = _count_rows(
        session,
        models.OddsSnapshot,
        fixture_ids=fixture_ids,
        league_id=effective_league_id,
        season=effective_season,
    )
    standings_count = _count_rows(
        session,
        models.StandingSnapshot,
        fixture_ids=fixture_ids,
        league_id=effective_league_id,
        season=effective_season,
    )
    injuries_count = _count_rows(
        session,
        models.Injury,
        fixture_ids=fixture_ids,
        league_id=effective_league_id,
        season=effective_season,
    )
    lineups_count = _count_rows(
        session,
        models.FixtureLineup,
        fixture_ids=fixture_ids,
        league_id=effective_league_id,
        season=effective_season,
    )
    player_stats_count = _count_rows(
        session,
        models.FixturePlayerStats,
        fixture_ids=fixture_ids,
        league_id=effective_league_id,
        season=effective_season,
    )
    api_predictions_count = _count_rows(
        session,
        models.ApiPredictionSnapshot,
        fixture_ids=fixture_ids,
        league_id=effective_league_id,
        season=effective_season,
    )
    availability = observability_quality_payload(
        historical_home_count=history_home_count,
        historical_away_count=history_away_count,
        match_statistics_count=fixture_statistics_count,
        lineups_count=lineups_count,
        player_stats_count=player_stats_count,
        injuries_count=injuries_count,
        odds_count=odds_count,
        api_prediction_count=api_predictions_count,
        reference_docs_available=reference_docs_available,
        standings_count=standings_count,
    )
    average_quality_score = (
        round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else None
    )

    return {
        "scope": {
            "fixture_id": fixture_id,
            "date": target_date.isoformat() if target_date else None,
            "league_id": league_id,
            "season": season,
        },
        "fixtures_total": len(fixtures),
        "fixtures_future": sum(status in FUTURE_STATUSES for status in status_short),
        "fixtures_finished": sum(status in FINISHED_STATUSES for status in status_short),
        "historical_home_count": history_home_count,
        "historical_away_count": history_away_count,
        "historical_home_available": availability["historical_home_available"],
        "historical_away_available": availability["historical_away_available"],
        "fixtures_with_odds": _distinct_fixture_count(
            session,
            models.OddsSnapshot,
            fixture_id_set,
            league_id=effective_league_id,
            season=effective_season,
        ),
        "odds_snapshots": odds_count,
        "standing_snapshots": standings_count,
        "fixture_statistics": fixture_statistics_count,
        "injuries": injuries_count,
        "lineups": lineups_count,
        "player_stats": player_stats_count,
        "api_predictions": api_predictions_count,
        "availability": availability,
        "feature_snapshots": len(feature_rows),
        "latest_fetched_at": {
            "odds": _latest_fetched_at(
                session,
                models.OddsSnapshot,
                fixture_ids=fixture_ids,
                league_id=effective_league_id,
                season=effective_season,
            ),
            "standings": _latest_fetched_at(
                session,
                models.StandingSnapshot,
                fixture_ids=fixture_ids,
                league_id=effective_league_id,
                season=effective_season,
            ),
            "injuries": _latest_fetched_at(
                session,
                models.Injury,
                fixture_ids=fixture_ids,
                league_id=effective_league_id,
                season=effective_season,
            ),
            "lineups": _latest_fetched_at(
                session,
                models.FixtureLineup,
                fixture_ids=fixture_ids,
                league_id=effective_league_id,
                season=effective_season,
            ),
            "player_stats": _latest_fetched_at(
                session,
                models.FixturePlayerStats,
                fixture_ids=fixture_ids,
                league_id=effective_league_id,
                season=effective_season,
            ),
            "api_predictions": _latest_fetched_at(
                session,
                models.ApiPredictionSnapshot,
                fixture_ids=fixture_ids,
                league_id=effective_league_id,
                season=effective_season,
            ),
            "fixture_statistics": _latest_fetched_at(
                session,
                models.FixtureStatistics,
                fixture_ids=fixture_ids,
                league_id=effective_league_id,
                season=effective_season,
            ),
        },
        "average_overall_data_quality_score": average_quality_score,
        "overall_data_quality_score": average_quality_score
        if average_quality_score is not None
        else availability["overall_data_quality_score"],
    }


def validate_positive_reference_ids(
    reference: ApiFootballReference,
    *,
    fixture_id: int | None = None,
    league_id: int | None = None,
    season: int | None = None,
) -> None:
    """Validate positive API-Football IDs; negative IDs are treated as synthetic tests."""
    try:
        if fixture_id is not None and fixture_id >= 0:
            reference.validate_fixture_reference(fixture_id)
        if league_id is not None and league_id >= 0:
            reference.find_league_by_id(league_id, season)
    except Exception as exc:
        raise DiagnosticsError(sanitize_text(str(exc))) from exc


def mask_database_url(database_url: str) -> str:
    try:
        url = make_url(database_url)
    except Exception:
        return sanitize_text(database_url)
    if url.password is not None:
        url = url.set(password="<redacted>")
    return str(url)


def _check_api_reference(path: Path) -> tuple[DiagnosticCheck, ApiFootballReference | None]:
    if not path.exists():
        return _missing_file_check("api_football_reference", path), None
    try:
        reference = load_api_football_reference(path)
    except Exception as exc:
        return _invalid_file_check("api_football_reference", path, exc), None
    return (
        DiagnosticCheck(
            name="api_football_reference",
            status=DiagnosticStatus.OK,
            message="Référentiel API-Football lisible",
            details={
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "counts": reference.counts(),
            },
            critical=True,
        ),
        reference,
    )


def _check_players_reference(path: Path) -> DiagnosticCheck:
    if not path.exists():
        return _missing_file_check("api_football_players_reference", path)
    try:
        reference = load_players_reference(path)
    except Exception as exc:
        return _invalid_file_check("api_football_players_reference", path, exc)
    return DiagnosticCheck(
        name="api_football_players_reference",
        status=DiagnosticStatus.OK,
        message="Référentiel joueurs lisible",
        details={
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "counts": reference.counts(),
        },
        critical=True,
    )


def _check_players_cache(path: Path) -> DiagnosticCheck:
    if not path.exists():
        return _missing_file_check("api_football_players_cache", path)
    try:
        payload = load_players_cache(path)
    except Exception as exc:
        return _invalid_file_check("api_football_players_cache", path, exc)
    teams = payload.get("teams")
    return DiagnosticCheck(
        name="api_football_players_cache",
        status=DiagnosticStatus.OK,
        message="Cache technique joueurs lisible",
        details={
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "teams": len(teams) if isinstance(teams, dict | list) else 0,
            "source_role": "technical_cache_only",
            "business_source": False,
        },
        critical=True,
    )


def _check_markdown_reference(name: str, path: Path) -> DiagnosticCheck:
    if not path.exists():
        return _missing_file_check(name, path)
    return DiagnosticCheck(
        name=name,
        status=DiagnosticStatus.OK,
        message="Documentation référentielle Markdown présente",
        details={"path": str(path), "size_bytes": path.stat().st_size},
        critical=True,
    )


def _check_model_dir(path: Path) -> DiagnosticCheck:
    if not path.exists():
        return DiagnosticCheck(
            name="model_dir",
            status=DiagnosticStatus.WARNING,
            message="Répertoire modèles absent",
            details={"path": str(path)},
        )
    return DiagnosticCheck(
        name="model_dir",
        status=DiagnosticStatus.OK,
        message="Répertoire modèles présent",
        details={"path": str(path), "is_dir": path.is_dir()},
    )


def _check_competitions_config(
    settings: Settings,
    reference: ApiFootballReference | None,
) -> DiagnosticCheck:
    path = settings.competitions_config_path
    if not path.exists():
        return DiagnosticCheck(
            name="competitions_config",
            status=DiagnosticStatus.WARNING,
            message="Config compétitions absente",
            details={"path": str(path)},
        )
    if reference is None:
        return DiagnosticCheck(
            name="competitions_config",
            status=DiagnosticStatus.WARNING,
            message="Config non validée car le référentiel API est indisponible",
            details={"path": str(path)},
        )
    try:
        competitions = load_competition_config(path, reference)
    except Exception as exc:
        return DiagnosticCheck(
            name="competitions_config",
            status=DiagnosticStatus.ERROR,
            message=sanitize_text(str(exc)),
            details={"path": str(path)},
        )
    return DiagnosticCheck(
        name="competitions_config",
        status=DiagnosticStatus.OK,
        message="Config compétitions valide",
        details={"path": str(path), "enabled_competitions": len(competitions)},
    )


def _check_discord_config(
    settings: Settings,
    reference: ApiFootballReference | None,
) -> list[DiagnosticCheck]:
    checks: list[DiagnosticCheck] = []
    if reference is None:
        return [
            DiagnosticCheck(
                name="discord_config",
                status=DiagnosticStatus.WARNING,
                message="Config Discord non validée car le référentiel API est indisponible",
            )
        ]

    channels_path = settings.discord_channels_config_path
    if not channels_path.exists():
        checks.append(
            DiagnosticCheck(
                name="discord_channels_config",
                status=DiagnosticStatus.WARNING,
                message="Config channels Discord absente",
                details={
                    "path": str(channels_path),
                    "example": "config/discord_channels.example.yaml",
                },
            )
        )
    else:
        try:
            channels = load_discord_channels_config(channels_path, reference)
        except Exception as exc:
            checks.append(
                DiagnosticCheck(
                    name="discord_channels_config",
                    status=DiagnosticStatus.ERROR,
                    message=sanitize_text(str(exc)),
                    details={"path": str(channels_path)},
                )
            )
        else:
            checks.append(
                DiagnosticCheck(
                    name="discord_channels_config",
                    status=DiagnosticStatus.OK,
                    message="Config channels Discord valide",
                    details={
                        "path": str(channels_path),
                        "competitions": len(channels.competitions),
                    },
                )
            )

    webhooks_path = settings.discord_webhooks_config_path
    if not webhooks_path.exists():
        status = DiagnosticStatus.OK if settings.discord_webhook_url else DiagnosticStatus.WARNING
        message = (
            "Fallback DISCORD_WEBHOOK_URL configuré"
            if settings.discord_webhook_url
            else "Config webhooks Discord absente"
        )
        checks.append(
            DiagnosticCheck(
                name="discord_webhooks_config",
                status=status,
                message=message,
                details={
                    "path": str(webhooks_path),
                    "fallback_legacy": bool(settings.discord_webhook_url),
                },
            )
        )
    else:
        try:
            webhooks = load_discord_webhooks_config(
                webhooks_path,
                reference,
                reject_placeholders=webhooks_path.name.endswith(".local.yaml"),
            )
        except Exception as exc:
            checks.append(
                DiagnosticCheck(
                    name="discord_webhooks_config",
                    status=DiagnosticStatus.ERROR,
                    message=sanitize_text(str(exc)),
                    details={"path": str(webhooks_path)},
                )
            )
        else:
            checks.append(
                DiagnosticCheck(
                    name="discord_webhooks_config",
                    status=DiagnosticStatus.OK,
                    message="Config webhooks Discord valide",
                    details={
                        "path": str(webhooks_path),
                        "routes": len(webhooks.routes),
                        "configured_urls": sum(1 for route in webhooks.routes if route.webhook_url),
                    },
                )
            )
    return checks


def _check_database(settings: Settings) -> DiagnosticCheck:
    try:
        engine = create_db_engine(settings.database_url)
        with engine.connect() as connection:
            connection.execute(text("select 1"))
            inspector = inspect(connection)
            existing_tables = set(inspector.get_table_names())
    except Exception as exc:
        return DiagnosticCheck(
            name="database",
            status=DiagnosticStatus.ERROR,
            message=sanitize_text(str(exc)),
            details={"database_url": mask_database_url(settings.database_url)},
            critical=True,
        )
    expected_tables = set(Base.metadata.tables)
    missing_tables = sorted(expected_tables - existing_tables)
    status = DiagnosticStatus.WARNING if missing_tables else DiagnosticStatus.OK
    message = "DB accessible, tables manquantes" if missing_tables else "DB accessible"
    return DiagnosticCheck(
        name="database",
        status=status,
        message=message,
        details={
            "database_url": mask_database_url(settings.database_url),
            "tables_present": len(existing_tables),
            "tables_expected": len(expected_tables),
            "missing_tables": missing_tables[:20],
        },
    )


def _missing_file_check(name: str, path: Path) -> DiagnosticCheck:
    return DiagnosticCheck(
        name=name,
        status=DiagnosticStatus.ERROR,
        message="Fichier référentiel manquant",
        details={"path": str(path)},
        critical=True,
    )


def _invalid_file_check(name: str, path: Path, exc: Exception) -> DiagnosticCheck:
    return DiagnosticCheck(
        name=name,
        status=DiagnosticStatus.ERROR,
        message=sanitize_text(str(exc)),
        details={"path": str(path), "size_bytes": path.stat().st_size if path.exists() else None},
        critical=True,
    )


def _select_fixtures(
    session: Session,
    *,
    fixture_id: int | None,
    target_date: date | None,
    league_id: int | None,
    season: int | None,
) -> list[models.Fixture]:
    stmt = select(models.Fixture)
    if fixture_id is not None:
        stmt = stmt.where(models.Fixture.fixture_id == fixture_id)
    if target_date is not None:
        start = datetime.combine(target_date, time.min, tzinfo=UTC)
        end = datetime.combine(target_date, time.max, tzinfo=UTC)
        stmt = stmt.where(models.Fixture.date >= start, models.Fixture.date <= end)
    if league_id is not None:
        stmt = stmt.where(models.Fixture.league_id == league_id)
    if season is not None:
        stmt = stmt.where(models.Fixture.season == season)
    return list(session.execute(stmt.order_by(models.Fixture.date.asc())).scalars())


def _history_counts_for_fixtures(
    session: Session,
    fixtures: list[models.Fixture],
) -> tuple[int, int]:
    home_count = 0
    away_count = 0
    for fixture in fixtures:
        if fixture.date is None:
            continue
        home_count += _historical_match_count(session, fixture.home_team_id, fixture.date)
        away_count += _historical_match_count(session, fixture.away_team_id, fixture.date)
    return home_count, away_count


def _historical_match_count(session: Session, team_id: int, cutoff: datetime) -> int:
    stmt = (
        select(func.count())
        .select_from(models.Fixture)
        .where(
            models.Fixture.date < cutoff,
            models.Fixture.status_short.in_(FINISHED_STATUSES),
            models.Fixture.home_goals.is_not(None),
            models.Fixture.away_goals.is_not(None),
            (models.Fixture.home_team_id == team_id) | (models.Fixture.away_team_id == team_id),
        )
    )
    return int(session.execute(stmt).scalar_one())


def _count_rows(
    session: Session,
    model: type[Any],
    *,
    fixture_ids: list[int],
    league_id: int | None,
    season: int | None,
) -> int:
    stmt = select(func.count()).select_from(model)
    stmt = _apply_scope(stmt, model, fixture_ids=fixture_ids, league_id=league_id, season=season)
    return int(session.execute(stmt).scalar_one())


def _scoped_rows(
    session: Session,
    model: type[Any],
    *,
    fixture_ids: list[int],
    league_id: int | None,
    season: int | None,
) -> list[Any]:
    stmt = select(model)
    stmt = _apply_scope(stmt, model, fixture_ids=fixture_ids, league_id=league_id, season=season)
    return list(session.execute(stmt).scalars())


def _distinct_fixture_count(
    session: Session,
    model: type[Any],
    fixture_ids: set[int],
    *,
    league_id: int | None,
    season: int | None,
) -> int:
    stmt = select(model.fixture_id)
    stmt = _apply_scope(
        stmt,
        model,
        fixture_ids=list(fixture_ids),
        league_id=league_id,
        season=season,
    )
    return len({row[0] for row in session.execute(stmt).all() if row[0] is not None})


def _latest_fetched_at(
    session: Session,
    model: type[Any],
    *,
    fixture_ids: list[int],
    league_id: int | None,
    season: int | None,
) -> str | None:
    if not hasattr(model, "fetched_at"):
        return None
    stmt = select(func.max(model.fetched_at))
    stmt = _apply_scope(stmt, model, fixture_ids=fixture_ids, league_id=league_id, season=season)
    latest = session.execute(stmt).scalar_one()
    if latest is None:
        return None
    return ensure_aware_utc(latest).isoformat()


def _apply_scope(
    stmt: Any,
    model: type[Any],
    *,
    fixture_ids: list[int],
    league_id: int | None,
    season: int | None,
) -> Any:
    fixture_scoped = bool(fixture_ids) and hasattr(model, "fixture_id")
    if fixture_scoped:
        stmt = stmt.where(model.fixture_id.in_(fixture_ids))
    elif (
        not fixture_ids
        and hasattr(model, "fixture_id")
        and ((league_id is None and season is None) or not hasattr(model, "league_id"))
    ):
        # A scoped fixture/date query with no fixtures should not report global rows.
        stmt = stmt.where(model.fixture_id.is_(None))
    if not fixture_scoped and league_id is not None and hasattr(model, "league_id"):
        stmt = stmt.where(model.league_id == league_id)
    if not fixture_scoped and season is not None and hasattr(model, "season"):
        stmt = stmt.where(model.season == season)
    return stmt


def _extract_quality_score(payload: JsonDict) -> float | None:
    value = payload.get("overall_data_quality_score")
    if value is None:
        value = payload.get("score")
    if not isinstance(value, int | float | str):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
