"""Point-in-time World Cup 2026 enrichment services.

This module is intentionally separate from the live prediction path. It persists
dated references and builds auditable feature rows without mutating existing
1X2/O-U models.
"""

from __future__ import annotations

import csv
import hashlib
import math
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

import pandas as pd  # type: ignore[import-untyped]
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from football_predictor.api.api_football_client import ApiFootballPayload
from football_predictor.api.endpoints import ODDS
from football_predictor.db import models
from football_predictor.db.repositories import insert_raw_api_snapshot, upsert_by_fields
from football_predictor.security.sanitize import sanitize_value
from football_predictor.utils.time import ensure_aware_utc, parse_datetime, utc_now
from football_predictor.worldcup.coverage_monitor import (
    WORLD_CUP_COMPETITION_KEY,
    WORLD_CUP_LEAGUE_ID,
    WORLD_CUP_SEASON,
)
from football_predictor.worldcup.features import (
    RatingState,
    build_features_for_fixture,
)
from football_predictor.worldcup.references import (
    InternationalMatch,
    WorldCupReferenceBundle,
    load_fifa_rankings,
    normalize_team_name,
)

JsonDict = dict[str, Any]
BTTS_BET_NAME = "Both Teams Score"
BTTS_BET_ID = 8
FINISHED_STATUSES = {"FT", "AET", "PEN"}


class ApiFootballPayloadClient(Protocol):
    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> ApiFootballPayload:
        ...


@dataclass(frozen=True)
class EnrichmentWriteResult:
    dry_run: bool
    rows_seen: int = 0
    rows_written: int = 0
    rows_skipped: int = 0
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> JsonDict:
        return sanitize_value(asdict(self))


@dataclass(frozen=True)
class FeatureMatrixResult:
    dry_run: bool
    rows: int
    output_path: str | None
    report_path: str | None
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> JsonDict:
        return sanitize_value(asdict(self))


@dataclass(frozen=True)
class BttsOddsIngestionResult:
    dry_run: bool
    odds: int = 0
    raw_snapshots: int = 0
    skipped: int = 0
    errors: tuple[str, ...] = ()

    def as_dict(self) -> JsonDict:
        return sanitize_value(asdict(self))


def canonical_team_name(
    session: Session,
    value: str,
    *,
    bundle: WorldCupReferenceBundle | None = None,
    cutoff: date | None = None,
) -> str:
    """Resolve a national team alias without inventing IDs."""
    normalized = normalize_team_name(value)
    statement = (
        select(models.NationalTeamAlias)
        .where(models.NationalTeamAlias.normalized_alias == normalized)
        .order_by(models.NationalTeamAlias.confidence.desc().nullslast())
    )
    if cutoff is not None:
        statement = statement.where(
            or_(
                models.NationalTeamAlias.valid_from.is_(None),
                models.NationalTeamAlias.valid_from <= cutoff,
            ),
            or_(
                models.NationalTeamAlias.valid_to.is_(None),
                models.NationalTeamAlias.valid_to >= cutoff,
            ),
        )
    row = session.execute(statement).scalars().first()
    if row is not None:
        return row.canonical_name
    if bundle is not None:
        return bundle.canonical_name(value)
    return value.strip()


def seed_aliases_from_bundle(
    session: Session,
    bundle: WorldCupReferenceBundle,
    *,
    write: bool = False,
    source: str = "worldcup_reference_bundle",
) -> EnrichmentWriteResult:
    rows_seen = 0
    rows_written = 0
    for alias, code in bundle.elo_alias_to_code.items():
        rows_seen += 1
        canonical = bundle.canonical_aliases.get(alias, code)
        if write:
            upsert_by_fields(
                session,
                models.NationalTeamAlias,
                {"normalized_alias": alias, "source": source},
                {
                    "canonical_name": canonical,
                    "elo_code": code,
                    "confidence": 0.90,
                    "payload_json": {"source": source},
                },
            )
            rows_written += 1
    for alias, canonical in bundle.canonical_aliases.items():
        rows_seen += 1
        if write:
            upsert_by_fields(
                session,
                models.NationalTeamAlias,
                {"normalized_alias": alias, "source": "manual_canonical_alias"},
                {
                    "canonical_name": canonical,
                    "confidence": 0.95,
                    "payload_json": {"source": "manual_canonical_alias"},
                },
            )
            rows_written += 1
    session.flush()
    return EnrichmentWriteResult(
        dry_run=not write,
        rows_seen=rows_seen,
        rows_written=rows_written,
    )


def ingest_national_results_csv(
    session: Session,
    csv_path: Path | str,
    *,
    bundle: WorldCupReferenceBundle | None = None,
    source: str = "national_results_csv",
    write: bool = False,
) -> EnrichmentWriteResult:
    path = Path(csv_path)
    rows_seen = rows_written = rows_skipped = 0
    warnings: list[str] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            rows_seen += 1
            try:
                match_date = _parse_date(raw.get("date") or raw.get("match_date"))
                home_team = str(raw.get("home_team") or "").strip()
                away_team = str(raw.get("away_team") or "").strip()
                home_score = int(raw.get("home_score") or raw.get("home_goals"))
                away_score = int(raw.get("away_score") or raw.get("away_goals"))
            except (TypeError, ValueError) as exc:
                rows_skipped += 1
                warnings.append(f"row_{rows_seen}_invalid:{exc}")
                continue
            home = canonical_team_name(session, home_team, bundle=bundle, cutoff=match_date)
            away = canonical_team_name(session, away_team, bundle=bundle, cutoff=match_date)
            source_match_id = str(raw.get("source_match_id") or "").strip() or _match_id(
                match_date,
                home,
                away,
                home_score,
                away_score,
                raw.get("tournament"),
            )
            if write:
                upsert_by_fields(
                    session,
                    models.NationalTeamMatch,
                    {"source": source, "source_match_id": source_match_id},
                    {
                        "match_date": match_date,
                        "home_team_canonical": home,
                        "away_team_canonical": away,
                        "home_team_id": _optional_int(raw.get("home_team_id")),
                        "away_team_id": _optional_int(raw.get("away_team_id")),
                        "home_score": home_score,
                        "away_score": away_score,
                        "tournament": _optional_text(raw.get("tournament")),
                        "competition_type": _competition_type(raw.get("tournament")),
                        "neutral": _bool(raw.get("neutral")),
                        "city": _optional_text(raw.get("city")),
                        "country": _optional_text(raw.get("country")),
                        "payload_json": sanitize_value(dict(raw)),
                    },
                )
                rows_written += 1
    session.flush()
    return EnrichmentWriteResult(
        dry_run=not write,
        rows_seen=rows_seen,
        rows_written=rows_written,
        rows_skipped=rows_skipped,
        warnings=tuple(warnings[:50]),
    )


def import_fifa_ranking_snapshots(
    session: Session,
    csv_path: Path | str,
    *,
    snapshot_date: date,
    bundle: WorldCupReferenceBundle | None = None,
    source: str = "fifa_csv",
    write: bool = False,
) -> EnrichmentWriteResult:
    rankings = load_fifa_rankings(
        Path(csv_path),
        canonical_aliases=bundle.canonical_aliases if bundle else None,
    )
    rows_written = 0
    for ranking in rankings.values():
        canonical = canonical_team_name(
            session,
            ranking.country,
            bundle=bundle,
            cutoff=snapshot_date,
        )
        if write:
            upsert_by_fields(
                session,
                models.FifaRankingSnapshot,
                {
                    "canonical_team": canonical,
                    "snapshot_date": snapshot_date,
                    "source": source,
                },
                {
                    "rank": ranking.rank,
                    "points": ranking.points,
                    "previous_points": ranking.previous_points,
                    "delta": ranking.delta,
                    "payload_json": sanitize_value(
                        {
                            "country": ranking.country,
                            "source_path": str(csv_path),
                        }
                    ),
                },
            )
            rows_written += 1
    session.flush()
    return EnrichmentWriteResult(
        dry_run=not write,
        rows_seen=len(rankings),
        rows_written=rows_written,
    )


def compute_national_elo_snapshots(
    session: Session,
    *,
    snapshot_date: date | None = None,
    bundle: WorldCupReferenceBundle | None = None,
    source: str = "computed_national_history",
    write: bool = False,
) -> EnrichmentWriteResult:
    session.flush()
    statement = select(models.NationalTeamMatch).order_by(
        models.NationalTeamMatch.match_date.asc(),
        models.NationalTeamMatch.id.asc(),
    )
    if snapshot_date is not None:
        statement = statement.where(models.NationalTeamMatch.match_date <= snapshot_date)
    rows = list(session.execute(statement).scalars())
    grouped: dict[date, list[models.NationalTeamMatch]] = defaultdict(list)
    for row in rows:
        grouped[row.match_date].append(row)

    ratings = RatingState()
    rows_written = 0
    teams_seen: set[str] = set()
    for match_date in sorted(grouped):
        for row in grouped[match_date]:
            match = _international_match_from_db(row)
            teams_seen.update({match.home_team, match.away_team})
            ratings.update(match)
        ranked = sorted(
            ((team, ratings.rating(team)) for team in teams_seen),
            key=lambda item: item[1],
            reverse=True,
        )
        for rank, (team, elo) in enumerate(ranked, start=1):
            if write:
                upsert_by_fields(
                    session,
                    models.NationalEloSnapshot,
                    {
                        "canonical_team": team,
                        "snapshot_date": match_date,
                        "source": source,
                    },
                    {
                        "elo_code": _elo_code_for_team(bundle, team),
                        "rank": rank,
                        "elo": float(elo),
                        "payload_json": {"source": source, "generated_from_matches": True},
                    },
                )
                rows_written += 1
    session.flush()
    return EnrichmentWriteResult(
        dry_run=not write,
        rows_seen=len(rows),
        rows_written=rows_written,
    )


def latest_fifa_snapshot(
    session: Session,
    canonical_team: str,
    cutoff: datetime,
) -> models.FifaRankingSnapshot | None:
    return session.execute(
        select(models.FifaRankingSnapshot)
        .where(models.FifaRankingSnapshot.canonical_team == canonical_team)
        .where(models.FifaRankingSnapshot.snapshot_date <= ensure_aware_utc(cutoff).date())
        .order_by(models.FifaRankingSnapshot.snapshot_date.desc())
    ).scalars().first()


def latest_elo_snapshot(
    session: Session,
    canonical_team: str,
    cutoff: datetime,
) -> models.NationalEloSnapshot | None:
    return session.execute(
        select(models.NationalEloSnapshot)
        .where(models.NationalEloSnapshot.canonical_team == canonical_team)
        .where(models.NationalEloSnapshot.snapshot_date <= ensure_aware_utc(cutoff).date())
        .order_by(models.NationalEloSnapshot.snapshot_date.desc())
    ).scalars().first()


def point_in_time_reference_features(
    session: Session,
    home_team: str,
    away_team: str,
    cutoff: datetime,
    *,
    bundle: WorldCupReferenceBundle | None = None,
) -> JsonDict:
    session.flush()
    cutoff_utc = ensure_aware_utc(cutoff)
    home = canonical_team_name(session, home_team, bundle=bundle, cutoff=cutoff_utc.date())
    away = canonical_team_name(session, away_team, bundle=bundle, cutoff=cutoff_utc.date())
    home_fifa = latest_fifa_snapshot(session, home, cutoff_utc)
    away_fifa = latest_fifa_snapshot(session, away, cutoff_utc)
    home_elo = latest_elo_snapshot(session, home, cutoff_utc)
    away_elo = latest_elo_snapshot(session, away, cutoff_utc)
    return {
        "wc_reference_cutoff": cutoff_utc.isoformat(),
        "wc_home_team_canonical": home,
        "wc_away_team_canonical": away,
        "wc_fifa_home_available": int(home_fifa is not None),
        "wc_fifa_away_available": int(away_fifa is not None),
        "wc_fifa_home_snapshot_id": home_fifa.id if home_fifa else None,
        "wc_fifa_away_snapshot_id": away_fifa.id if away_fifa else None,
        "wc_fifa_home_rank": home_fifa.rank if home_fifa else None,
        "wc_fifa_away_rank": away_fifa.rank if away_fifa else None,
        "wc_fifa_rank_diff": _diff(
            away_fifa.rank if away_fifa else None,
            home_fifa.rank if home_fifa else None,
        ),
        "wc_fifa_home_points": home_fifa.points if home_fifa else None,
        "wc_fifa_away_points": away_fifa.points if away_fifa else None,
        "wc_fifa_points_diff": _diff(
            home_fifa.points if home_fifa else None,
            away_fifa.points if away_fifa else None,
        ),
        "wc_current_elo_home_available": int(home_elo is not None),
        "wc_current_elo_away_available": int(away_elo is not None),
        "wc_current_elo_home_snapshot_id": home_elo.id if home_elo else None,
        "wc_current_elo_away_snapshot_id": away_elo.id if away_elo else None,
        "wc_current_elo_home": home_elo.elo if home_elo else None,
        "wc_current_elo_away": away_elo.elo if away_elo else None,
        "wc_current_elo_diff": _diff(
            home_elo.elo if home_elo else None,
            away_elo.elo if away_elo else None,
        ),
    }


def build_enriched_worldcup_features_for_fixture(
    session: Session,
    fixture: models.Fixture,
    *,
    prediction_time: datetime,
    bundle: WorldCupReferenceBundle | None = None,
) -> JsonDict:
    session.flush()
    cutoff = ensure_aware_utc(prediction_time)
    history_bundle = _db_history_bundle(session, cutoff=cutoff, bundle=bundle)
    features = build_features_for_fixture(
        fixture.home_team,
        fixture.away_team,
        cutoff.date(),
        bundle=history_bundle,
        neutral=True,
    )
    features.update(
        point_in_time_reference_features(
            session,
            fixture.home_team,
            fixture.away_team,
            cutoff,
            bundle=bundle,
        )
    )
    features.update(_odds_market_flags(session, fixture.fixture_id, cutoff))
    features.update(_group_state_features(session, fixture, cutoff))
    features.update(_squad_strength_feature_pair(session, fixture, cutoff))
    features["wc_feature_cutoff"] = cutoff.isoformat()
    return sanitize_value(features)


def build_worldcup_feature_matrix(
    session: Session,
    *,
    league_id: int = WORLD_CUP_LEAGUE_ID,
    season: int = WORLD_CUP_SEASON,
    prediction_offset_hours: float = 24.0,
    bundle: WorldCupReferenceBundle | None = None,
) -> pd.DataFrame:
    session.flush()
    fixtures = list(
        session.execute(
            select(models.Fixture)
            .where(models.Fixture.league_id == league_id)
            .where(models.Fixture.season == season)
            .where(models.Fixture.date.is_not(None))
            .order_by(models.Fixture.date.asc(), models.Fixture.fixture_id.asc())
        ).scalars()
    )
    rows: list[JsonDict] = []
    for fixture in fixtures:
        if fixture.date is None:
            continue
        prediction_time = ensure_aware_utc(fixture.date) - timedelta(
            hours=prediction_offset_hours
        )
        features = build_enriched_worldcup_features_for_fixture(
            session,
            fixture,
            prediction_time=prediction_time,
            bundle=bundle,
        )
        features.update(
            {
                "fixture_id": fixture.fixture_id,
                "fixture_date": ensure_aware_utc(fixture.date).isoformat(),
                "prediction_time": prediction_time.isoformat(),
                "home_team": fixture.home_team,
                "away_team": fixture.away_team,
                "league_id": fixture.league_id,
                "season": fixture.season,
            }
        )
        rows.append(features)
    return pd.DataFrame(rows)


def write_worldcup_feature_matrix_reports(
    frame: pd.DataFrame,
    *,
    output_path: Path,
    report_path: Path,
    dry_run: bool = True,
) -> FeatureMatrixResult:
    warnings: list[str] = []
    if dry_run:
        return FeatureMatrixResult(
            dry_run=True,
            rows=len(frame),
            output_path=None,
            report_path=None,
            warnings=tuple(warnings),
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix == ".csv":
        frame.to_csv(output_path, index=False)
    else:
        frame.to_parquet(output_path, index=False)
    report_path.write_text(_feature_matrix_report(frame), encoding="utf-8")
    return FeatureMatrixResult(
        dry_run=False,
        rows=len(frame),
        output_path=str(output_path),
        report_path=str(report_path),
        warnings=tuple(warnings),
    )


def build_group_state_snapshots(
    session: Session,
    *,
    cutoff: datetime,
    competition_key: str = WORLD_CUP_COMPETITION_KEY,
    league_id: int = WORLD_CUP_LEAGUE_ID,
    season: int = WORLD_CUP_SEASON,
    bundle: WorldCupReferenceBundle | None = None,
    write: bool = False,
) -> EnrichmentWriteResult:
    session.flush()
    cutoff_utc = ensure_aware_utc(cutoff)
    fixtures = list(
        session.execute(
            select(models.Fixture)
            .where(models.Fixture.league_id == league_id)
            .where(models.Fixture.season == season)
            .order_by(models.Fixture.date.asc(), models.Fixture.fixture_id.asc())
        ).scalars()
    )
    grouped: dict[str, list[models.Fixture]] = defaultdict(list)
    for fixture in fixtures:
        grouped[_group_name(fixture)].append(fixture)

    rows_written = 0
    for group_name, group_fixtures in grouped.items():
        team_rows = _group_table(group_fixtures, cutoff_utc)
        max_matchday = max((_matchday(row) or 0 for row in group_fixtures), default=0)
        for team_id, table_row in team_rows.items():
            team_name = table_row["team_name"]
            remaining = _remaining_group_fixtures(group_fixtures, team_id, cutoff_utc)
            incentives = _group_incentives(table_row, max_matchday, remaining, team_rows)
            if write:
                upsert_by_fields(
                    session,
                    models.WorldCupGroupStateSnapshot,
                    {
                        "competition_key": competition_key,
                        "league_id": league_id,
                        "season": season,
                        "group_name": group_name,
                        "team_id": team_id,
                        "snapshot_at": cutoff_utc,
                    },
                    {
                        "canonical_team": canonical_team_name(
                            session,
                            team_name,
                            bundle=bundle,
                            cutoff=cutoff_utc.date(),
                        ),
                        "matchday": max_matchday or None,
                        "played": table_row["played"],
                        "points": table_row["points"],
                        "goals_for": table_row["goals_for"],
                        "goals_against": table_row["goals_against"],
                        "goal_diff": table_row["goal_diff"],
                        "remaining_fixtures_json": remaining,
                        "incentives_json": incentives,
                        "qualification_risk_json": incentives.get("qualification_risk", {}),
                        "payload_json": {
                            "source": "derived_from_fixtures",
                            "cutoff": cutoff_utc.isoformat(),
                        },
                    },
                )
                rows_written += 1
    session.flush()
    return EnrichmentWriteResult(
        dry_run=not write,
        rows_seen=sum(len(items) for items in grouped.values()),
        rows_written=rows_written,
    )


def build_squad_strength_features(
    session: Session,
    *,
    snapshot_at: datetime,
    competition_key: str = WORLD_CUP_COMPETITION_KEY,
    league_id: int = WORLD_CUP_LEAGUE_ID,
    season: int = WORLD_CUP_SEASON,
    bundle: WorldCupReferenceBundle | None = None,
    write: bool = False,
) -> EnrichmentWriteResult:
    session.flush()
    cutoff = ensure_aware_utc(snapshot_at)
    teams = session.execute(
        select(models.Team)
        .join(
            models.PlayerSquad,
            models.PlayerSquad.team_id == models.Team.team_id,
        )
        .where(models.PlayerSquad.league_id == league_id)
        .where(models.PlayerSquad.season == season)
        .where(models.PlayerSquad.fetched_at <= cutoff)
        .group_by(models.Team.team_id)
        .order_by(models.Team.name.asc())
    ).scalars()
    rows_seen = rows_written = 0
    for team in teams:
        rows_seen += 1
        squad_rows = list(
            session.execute(
                select(models.PlayerSquad, models.Player)
                .join(models.Player, models.Player.player_id == models.PlayerSquad.player_id)
                .where(models.PlayerSquad.team_id == team.team_id)
                .where(models.PlayerSquad.league_id == league_id)
                .where(models.PlayerSquad.season == season)
                .where(models.PlayerSquad.fetched_at <= cutoff)
            ).all()
        )
        payload = _squad_strength_payload(team, squad_rows)
        if write:
            upsert_by_fields(
                session,
                models.SquadStrengthFeature,
                {
                    "competition_key": competition_key,
                    "league_id": league_id,
                    "season": season,
                    "team_id": team.team_id,
                    "snapshot_at": cutoff,
                },
                {
                    "canonical_team": canonical_team_name(
                        session,
                        team.name,
                        bundle=bundle,
                        cutoff=cutoff.date(),
                    ),
                    **payload,
                },
            )
            rows_written += 1
    session.flush()
    return EnrichmentWriteResult(
        dry_run=not write,
        rows_seen=rows_seen,
        rows_written=rows_written,
    )


def parse_btts_odds_rows(
    payload: JsonDict,
    *,
    target_bet_id: int,
    fetched_at: datetime,
    ingestion_source: str = "api-football",
) -> list[JsonDict]:
    rows: list[JsonDict] = []
    for fixture_row in payload.get("response", []):
        fixture_info = _dict(fixture_row.get("fixture"))
        fixture_id = fixture_info.get("id") or fixture_row.get("fixture_id")
        if fixture_id is None:
            continue
        league_info = _dict(fixture_row.get("league"))
        for bookmaker in fixture_row.get("bookmakers") or []:
            bookmaker_row = _dict(bookmaker)
            for bet in bookmaker_row.get("bets") or []:
                bet_row = _dict(bet)
                if _optional_int(bet_row.get("id")) != target_bet_id:
                    continue
                pair = _extract_yes_no_pair(bet_row.get("values") or [])
                if pair is None:
                    continue
                yes, no = pair
                rows.append(
                    {
                        "fixture_id": int(fixture_id),
                        "league_id": _optional_int(league_info.get("id")),
                        "season": _optional_int(league_info.get("season")),
                        "bookmaker_id": _optional_int(bookmaker_row.get("id")),
                        "bookmaker_name": bookmaker_row.get("name"),
                        "bet_id": target_bet_id,
                        "bet_name": bet_row.get("name") or BTTS_BET_NAME,
                        "fetched_at": ensure_aware_utc(fetched_at),
                        "is_live": False,
                        "odd_home": yes,
                        "odd_draw": None,
                        "odd_away": no,
                        "values_json": bet_row.get("values") or [],
                        "odds_json": {"yes": yes, "no": no},
                        "payload_json": {
                            "fixture": fixture_info,
                            "league": league_info,
                            "bookmaker": bookmaker_row,
                            "bet": bet_row,
                            "labels": {"odd_home": "Yes", "odd_away": "No"},
                            "ingestion_source": ingestion_source,
                        },
                    }
                )
    return rows


class BTTSOddsIngestionService:
    """Ingest prematch BTTS odds into OddsSnapshot as Yes/No labels."""

    def __init__(
        self,
        session: Session,
        client: ApiFootballPayloadClient,
        *,
        bet_id: int = BTTS_BET_ID,
        save_raw: bool = False,
    ) -> None:
        self.session = session
        self.client = client
        self.bet_id = bet_id
        self.save_raw = save_raw

    def ingest_by_fixture(self, fixture_id: int) -> BttsOddsIngestionResult:
        return self._ingest({"fixture": fixture_id})

    def ingest_by_date(
        self,
        target_date: date,
        *,
        league_id: int | None = None,
        season: int | None = None,
    ) -> BttsOddsIngestionResult:
        params: JsonDict = {"date": target_date.isoformat()}
        if league_id is not None:
            params["league"] = league_id
        if season is not None:
            params["season"] = season
        return self._ingest(params)

    def ingest_by_league_season(self, league_id: int, season: int) -> BttsOddsIngestionResult:
        return self._ingest({"league": league_id, "season": season})

    def _ingest(self, params: JsonDict) -> BttsOddsIngestionResult:
        odds = raw_snapshots = skipped = 0
        errors: list[str] = []
        page = 1
        total = 1
        while page <= total:
            page_params = {**params, "bet": self.bet_id, "page": page}
            try:
                payload = self.client.get_payload(ODDS, page_params, save_raw=self.save_raw)
            except Exception as exc:
                errors.append(str(exc))
                break
            raw_snapshots += 1
            self._insert_raw_snapshot(payload)
            fetched_at = parse_datetime(payload.fetched_at) or utc_now()
            rows = parse_btts_odds_rows(
                payload.payload,
                target_bet_id=self.bet_id,
                fetched_at=fetched_at,
                ingestion_source=payload.source,
            )
            if not rows:
                skipped += 1
            for row in rows:
                self._upsert_odds(row)
                odds += 1
            paging = payload.payload.get("paging") or {}
            total = int(paging.get("total") or 1)
            page += 1
        self.session.flush()
        return BttsOddsIngestionResult(
            dry_run=False,
            odds=odds,
            raw_snapshots=raw_snapshots,
            skipped=skipped,
            errors=tuple(errors),
        )

    def _insert_raw_snapshot(self, payload: ApiFootballPayload) -> None:
        insert_raw_api_snapshot(
            self.session,
            endpoint=payload.endpoint,
            params_json=payload.params,
            payload_json=payload.payload,
            fetched_at=parse_datetime(payload.fetched_at) or utc_now(),
            status_code=payload.status_code,
            source=payload.source,
        )

    def _upsert_odds(self, row: JsonDict) -> None:
        bookmaker_id = row.get("bookmaker_id")
        if bookmaker_id is not None:
            upsert_by_fields(
                self.session,
                models.Bookmaker,
                {"bookmaker_id": bookmaker_id},
                {
                    "name": row.get("bookmaker_name") or "",
                    "payload_json": {
                        "id": bookmaker_id,
                        "name": row.get("bookmaker_name"),
                        "ingestion_source": row["payload_json"].get("ingestion_source"),
                    },
                },
            )
        upsert_by_fields(
            self.session,
            models.Bet,
            {"bet_id": row["bet_id"], "bet_type": "prematch"},
            {
                "name": row.get("bet_name") or BTTS_BET_NAME,
                "bet_type": "prematch",
                "payload_json": {
                    "id": row["bet_id"],
                    "name": row.get("bet_name"),
                    "ingestion_source": row["payload_json"].get("ingestion_source"),
                },
            },
        )
        match_fields = {
            "fixture_id": row.pop("fixture_id"),
            "bookmaker_id": row.pop("bookmaker_id"),
            "bet_id": row.pop("bet_id"),
            "fetched_at": row.pop("fetched_at"),
            "is_live": False,
        }
        upsert_by_fields(self.session, models.OddsSnapshot, match_fields, row)


def _db_history_bundle(
    session: Session,
    *,
    cutoff: datetime,
    bundle: WorldCupReferenceBundle | None,
) -> WorldCupReferenceBundle:
    matches = [
        _international_match_from_db(row)
        for row in session.execute(
            select(models.NationalTeamMatch)
            .where(models.NationalTeamMatch.match_date < cutoff.date())
            .order_by(models.NationalTeamMatch.match_date.asc(), models.NationalTeamMatch.id.asc())
        ).scalars()
    ]
    return WorldCupReferenceBundle(
        fifa_rankings={},
        elo_by_code={},
        elo_alias_to_code=bundle.elo_alias_to_code if bundle else {},
        historical_matches=matches,
        canonical_aliases=bundle.canonical_aliases if bundle else {},
    )


def _international_match_from_db(row: models.NationalTeamMatch) -> InternationalMatch:
    return InternationalMatch(
        match_date=row.match_date,
        home_team=row.home_team_canonical,
        away_team=row.away_team_canonical,
        home_score=row.home_score,
        away_score=row.away_score,
        tournament=row.tournament or "",
        city=row.city,
        country=row.country,
        neutral=row.neutral,
    )


def _odds_market_flags(session: Session, fixture_id: int, cutoff: datetime) -> JsonDict:
    return {
        "wc_odds_1x2_available": int(_has_market_odds(session, fixture_id, 1, cutoff)),
        "wc_odds_ou25_available": int(_has_market_odds(session, fixture_id, 5, cutoff)),
        "wc_odds_btts_available": int(_has_market_odds(session, fixture_id, BTTS_BET_ID, cutoff)),
    }


def _has_market_odds(session: Session, fixture_id: int, bet_id: int, cutoff: datetime) -> bool:
    statement = (
        select(func.count(models.OddsSnapshot.id))
        .where(models.OddsSnapshot.fixture_id == fixture_id)
        .where(models.OddsSnapshot.bet_id == bet_id)
        .where(models.OddsSnapshot.is_live.is_(False))
        .where(models.OddsSnapshot.fetched_at <= cutoff)
        .where(models.OddsSnapshot.odd_home.is_not(None))
        .where(models.OddsSnapshot.odd_away.is_not(None))
    )
    if bet_id == 1:
        statement = statement.where(models.OddsSnapshot.odd_draw.is_not(None))
    return int(session.execute(statement).scalar() or 0) > 0


def _group_state_features(
    session: Session,
    fixture: models.Fixture,
    cutoff: datetime,
) -> JsonDict:
    rows = list(
        session.execute(
            select(models.WorldCupGroupStateSnapshot)
            .where(models.WorldCupGroupStateSnapshot.team_id.in_(
                [fixture.home_team_id, fixture.away_team_id]
            ))
            .where(models.WorldCupGroupStateSnapshot.league_id == fixture.league_id)
            .where(models.WorldCupGroupStateSnapshot.season == fixture.season)
            .where(models.WorldCupGroupStateSnapshot.snapshot_at <= cutoff)
            .order_by(models.WorldCupGroupStateSnapshot.snapshot_at.desc())
        ).scalars()
    )
    by_team: dict[int, models.WorldCupGroupStateSnapshot] = {}
    for row in rows:
        by_team.setdefault(row.team_id, row)
    home = by_team.get(fixture.home_team_id)
    away = by_team.get(fixture.away_team_id)
    return {
        "wc_group_state_available": int(home is not None and away is not None),
        "wc_home_group_points": home.points if home else None,
        "wc_away_group_points": away.points if away else None,
        "wc_group_points_diff": _diff(home.points if home else None, away.points if away else None),
        "wc_home_group_state_snapshot_id": home.id if home else None,
        "wc_away_group_state_snapshot_id": away.id if away else None,
    }


def _squad_strength_feature_pair(
    session: Session,
    fixture: models.Fixture,
    cutoff: datetime,
) -> JsonDict:
    rows = list(
        session.execute(
            select(models.SquadStrengthFeature)
            .where(models.SquadStrengthFeature.team_id.in_(
                [fixture.home_team_id, fixture.away_team_id]
            ))
            .where(models.SquadStrengthFeature.league_id == fixture.league_id)
            .where(models.SquadStrengthFeature.season == fixture.season)
            .where(models.SquadStrengthFeature.snapshot_at <= cutoff)
            .order_by(models.SquadStrengthFeature.snapshot_at.desc())
        ).scalars()
    )
    by_team: dict[int, models.SquadStrengthFeature] = {}
    for row in rows:
        by_team.setdefault(row.team_id, row)
    home = by_team.get(fixture.home_team_id)
    away = by_team.get(fixture.away_team_id)
    return {
        "wc_squad_strength_available": int(home is not None and away is not None),
        "wc_home_squad_strength": home.strength_score if home else None,
        "wc_away_squad_strength": away.strength_score if away else None,
        "wc_squad_strength_diff": _diff(
            home.strength_score if home else None,
            away.strength_score if away else None,
        ),
        "wc_home_squad_strength_snapshot_id": home.id if home else None,
        "wc_away_squad_strength_snapshot_id": away.id if away else None,
    }


def _group_table(
    fixtures: Sequence[models.Fixture],
    cutoff: datetime,
) -> dict[int, JsonDict]:
    table: dict[int, JsonDict] = {}
    for fixture in fixtures:
        _ensure_team_row(table, fixture.home_team_id, fixture.home_team)
        _ensure_team_row(table, fixture.away_team_id, fixture.away_team)
        if not _fixture_finished_before_cutoff(fixture, cutoff):
            continue
        home_goals = _goal_value(fixture.home_goals, fixture.goals_home)
        away_goals = _goal_value(fixture.away_goals, fixture.goals_away)
        if home_goals is None or away_goals is None:
            continue
        home = table[fixture.home_team_id]
        away = table[fixture.away_team_id]
        home["played"] += 1
        away["played"] += 1
        home["goals_for"] += home_goals
        home["goals_against"] += away_goals
        away["goals_for"] += away_goals
        away["goals_against"] += home_goals
        home["goal_diff"] = home["goals_for"] - home["goals_against"]
        away["goal_diff"] = away["goals_for"] - away["goals_against"]
        if home_goals > away_goals:
            home["points"] += 3
        elif away_goals > home_goals:
            away["points"] += 3
        else:
            home["points"] += 1
            away["points"] += 1
    return table


def _ensure_team_row(table: dict[int, JsonDict], team_id: int, team_name: str) -> None:
    table.setdefault(
        team_id,
        {
            "team_name": team_name,
            "played": 0,
            "points": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_diff": 0,
        },
    )


def _remaining_group_fixtures(
    fixtures: Sequence[models.Fixture],
    team_id: int,
    cutoff: datetime,
) -> list[JsonDict]:
    remaining = []
    for fixture in fixtures:
        if fixture.date is None or ensure_aware_utc(fixture.date) <= cutoff:
            continue
        if team_id not in {fixture.home_team_id, fixture.away_team_id}:
            continue
        remaining.append(
            {
                "fixture_id": fixture.fixture_id,
                "kickoff": ensure_aware_utc(fixture.date).isoformat(),
                "home_team": fixture.home_team,
                "away_team": fixture.away_team,
                "matchday": _matchday(fixture),
            }
        )
    return remaining


def _group_incentives(
    row: JsonDict,
    max_matchday: int,
    remaining: list[JsonDict],
    table: dict[int, JsonDict],
) -> JsonDict:
    sorted_rows = sorted(
        table.values(),
        key=lambda item: (item["points"], item["goal_diff"], item["goals_for"]),
        reverse=True,
    )
    rank = next(
        (index for index, item in enumerate(sorted_rows, start=1) if item is row),
        len(sorted_rows),
    )
    leader_points = int(sorted_rows[0]["points"]) if sorted_rows else 0
    points_to_leader = max(leader_points - int(row["points"]), 0)
    return {
        "rank": rank,
        "matchday": max_matchday or None,
        "is_matchday3_context": bool(max_matchday >= 3),
        "remaining_count": len(remaining),
        "points_to_group_leader": points_to_leader,
        "needs_result_flag": bool(max_matchday >= 2 and rank > 2),
        "rotation_risk_flag": bool(max_matchday >= 3 and rank <= 2 and points_to_leader == 0),
        "qualification_risk": {
            "rank": rank,
            "high_risk_flag": bool(rank > 2 and max_matchday >= 2),
        },
    }


def _squad_strength_payload(
    team: models.Team,
    squad_rows: Iterable[tuple[models.PlayerSquad, models.Player]],
) -> JsonDict:
    rows = list(squad_rows)
    positions = {str(squad.position or "").upper() for squad, _player in rows}
    player_count = len(rows)
    position_diversity = len({value for value in positions if value})
    count_component = min(player_count, 26) / 26 * 70.0
    diversity_component = min(position_diversity, 4) / 4 * 20.0
    national_component = 10.0 if team.national else 0.0
    strength_score = max(
        0.0,
        min(100.0, count_component + diversity_component + national_component),
    )
    warnings = []
    if player_count < 20:
        warnings.append("squad_player_count_low")
    return {
        "squad_status": "final_candidate" if player_count >= 23 else "partial",
        "player_count": player_count,
        "strength_score": round(strength_score, 2),
        "club_level_score": None,
        "minutes_weighted_score": None,
        "availability_score": 100.0 if player_count >= 20 else 65.0,
        "key_players_json": [
            {
                "player_id": player.player_id,
                "name": player.name,
                "position": squad.position,
            }
            for squad, player in rows[:8]
        ],
        "warnings_json": warnings,
        "payload_json": {
            "source": "player_squads",
            "position_diversity": position_diversity,
        },
    }


def _feature_matrix_report(frame: pd.DataFrame) -> str:
    rows = len(frame)
    fields = [
        "wc_fifa_home_available",
        "wc_current_elo_home_available",
        "wc_odds_1x2_available",
        "wc_odds_ou25_available",
        "wc_odds_btts_available",
        "wc_group_state_available",
        "wc_squad_strength_available",
    ]
    lines = [
        "# World Cup Feature Matrix",
        "",
        f"- Rows: {rows}",
    ]
    for field_name in fields:
        if field_name in frame:
            lines.append(f"- {field_name}: {float(frame[field_name].fillna(0).mean()):.2%}")
    lines.append("")
    lines.append(
        "Point-in-time rule: every enrichment source is filtered with cutoff <= prediction_time."
    )
    return "\n".join(lines) + "\n"


def _parse_date(value: object) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value or ""))


def _match_id(
    match_date: date,
    home: str,
    away: str,
    home_score: int,
    away_score: int,
    tournament: object,
) -> str:
    raw = "|".join(
        [
            match_date.isoformat(),
            normalize_team_name(home),
            normalize_team_name(away),
            str(home_score),
            str(away_score),
            normalize_team_name(tournament),
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _competition_type(tournament: object) -> str:
    value = normalize_team_name(tournament)
    if "friendly" in value:
        return "friendly"
    if "qualification" in value or "qualifier" in value:
        return "qualifier"
    if "world cup" in value:
        return "world_cup"
    if value:
        return "international"
    return "unknown"


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().casefold() in {"1", "true", "yes", "y"}


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _diff(left: float | int | None, right: float | int | None) -> float | None:
    if left is None or right is None:
        return None
    return float(left) - float(right)


def _elo_code_for_team(bundle: WorldCupReferenceBundle | None, team: str) -> str | None:
    return bundle.elo_code_for_team(team) if bundle is not None else None


def _dict(value: Any) -> JsonDict:
    return value if isinstance(value, dict) else {}


def _parse_decimal(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) and parsed > 1.0 else None


def _extract_yes_no_pair(values: list[JsonDict]) -> tuple[float, float] | None:
    yes = no = None
    for row in values:
        label = normalize_team_name(row.get("value"))
        odd = _parse_decimal(row.get("odd"))
        if odd is None:
            continue
        if label in {"yes", "oui"}:
            yes = odd
        elif label in {"no", "non"}:
            no = odd
    if yes is not None and no is not None:
        return yes, no
    return None


def _group_name(fixture: models.Fixture) -> str:
    payload = fixture.payload_json if isinstance(fixture.payload_json, dict) else {}
    candidates = [
        payload.get("group"),
        _dict(payload.get("league")).get("round"),
        fixture.round,
    ]
    for candidate in candidates:
        text = str(candidate or "")
        match = re.search(r"group\s+([a-z0-9]+)", text, flags=re.IGNORECASE)
        if match:
            return f"Group {match.group(1).upper()}"
    return "Group Unknown"


def _matchday(fixture: models.Fixture) -> int | None:
    text = str(fixture.round or "")
    match = re.search(r"(?:matchday|round|group stage)\D*(\d+)", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    trailing = re.search(r"-\s*(\d+)\s*$", text)
    return int(trailing.group(1)) if trailing else None


def _fixture_finished_before_cutoff(fixture: models.Fixture, cutoff: datetime) -> bool:
    if fixture.date is None or ensure_aware_utc(fixture.date) >= cutoff:
        return False
    return str(fixture.status_short or "").upper() in FINISHED_STATUSES


def _goal_value(left: int | None, right: int | None) -> int | None:
    return left if left is not None else right
