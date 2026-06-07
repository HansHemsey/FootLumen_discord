"""Read-only fixture and competition queries for the API."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.web_api.schemas.common import CompetitionSummary
from football_predictor.web_api.schemas.fixtures import (
    FixtureSummaryDTO,
    fixture_summary_from_model,
)


class FixtureReadService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_competitions(self) -> list[CompetitionSummary]:
        leagues = self._session.scalars(
            select(models.League).order_by(models.League.name.asc(), models.League.season.desc())
        ).all()
        keys = self._competition_keys_for_pairs(
            (league.league_id, league.season) for league in leagues
        )
        return [self._competition_from_league(league, keys) for league in leagues]

    def get_competition(self, competition_key: str) -> CompetitionSummary | None:
        leagues = self._session.scalars(select(models.League)).all()
        keys = self._competition_keys_for_pairs(
            (league.league_id, league.season) for league in leagues
        )
        for league in leagues:
            summary = self._competition_from_league(league, keys)
            if summary.competition_key == competition_key:
                return summary
        return None

    def fixtures_today(
        self,
        *,
        target_date: date | None = None,
        competition_key: str | None = None,
        timezone_name: str = "Europe/Paris",
    ) -> list[FixtureSummaryDTO]:
        tz = _zoneinfo(timezone_name)
        resolved_date = target_date or datetime.now(tz).date()
        start_utc, end_utc = _local_day_bounds_utc(resolved_date, tz)
        stmt = (
            select(models.Fixture)
            .where(models.Fixture.date >= start_utc, models.Fixture.date < end_utc)
            .order_by(models.Fixture.date.asc(), models.Fixture.fixture_id.asc())
        )
        stmt = self._filter_by_competition(stmt, competition_key)
        fixtures = self._session.scalars(stmt).all()
        return self._summaries(fixtures, competition_key=competition_key)

    def fixtures_upcoming(
        self,
        *,
        days: int = 7,
        competition_key: str | None = None,
        limit: int = 100,
        status: str | None = None,
        timezone_name: str = "Europe/Paris",
    ) -> list[FixtureSummaryDTO]:
        tz = _zoneinfo(timezone_name)
        now_utc = datetime.now(tz).astimezone(UTC)
        end_utc = now_utc + timedelta(days=days)
        stmt = (
            select(models.Fixture)
            .where(models.Fixture.date >= now_utc, models.Fixture.date < end_utc)
            .order_by(models.Fixture.date.asc(), models.Fixture.fixture_id.asc())
            .limit(min(limit, 100))
        )
        stmt = self._filter_by_competition(stmt, competition_key)
        if status:
            stmt = stmt.where(models.Fixture.status_short == status)
        fixtures = self._session.scalars(stmt).all()
        return self._summaries(fixtures, competition_key=competition_key)

    def get_fixture(self, fixture_id: int) -> FixtureSummaryDTO | None:
        fixture = self._session.get(models.Fixture, fixture_id)
        if fixture is None:
            return None
        return self._summary(fixture)

    def list_upcoming(
        self,
        *,
        limit: int = 25,
        date_from: datetime | None = None,
        competition_key: str | None = None,
    ) -> list[FixtureSummaryDTO]:
        stmt = select(models.Fixture).order_by(models.Fixture.date.asc()).limit(min(limit, 100))
        if date_from is not None:
            stmt = stmt.where(models.Fixture.date >= date_from)
        stmt = self._filter_by_competition(stmt, competition_key)
        fixtures = self._session.scalars(stmt).all()
        return self._summaries(fixtures, competition_key=competition_key)

    def _summaries(
        self,
        fixtures: Iterable[models.Fixture],
        *,
        competition_key: str | None = None,
    ) -> list[FixtureSummaryDTO]:
        return [self._summary(fixture, competition_key=competition_key) for fixture in fixtures]

    def _summary(
        self,
        fixture: models.Fixture,
        *,
        competition_key: str | None = None,
    ) -> FixtureSummaryDTO:
        latest_1x2 = self._latest_1x2_prediction(fixture.fixture_id)
        latest_ou = self._latest_ou_prediction(fixture.fixture_id)
        has_combo = self._has_combo(fixture.fixture_id)
        latest_prediction_time = _latest_datetime(latest_1x2, latest_ou)
        data_quality_score = self._data_quality_score(latest_1x2, latest_ou)
        return fixture_summary_from_model(
            fixture,
            competition_key=competition_key or self._competition_key_for_fixture(fixture),
            has_1x2_prediction=latest_1x2 is not None,
            has_ou_prediction=latest_ou is not None,
            has_combo=has_combo,
            latest_prediction_time=latest_prediction_time,
            data_quality_score=data_quality_score,
        )

    def _latest_1x2_prediction(self, fixture_id: int) -> models.ModelPrediction | None:
        return self._session.scalar(
            select(models.ModelPrediction)
            .where(models.ModelPrediction.fixture_id == fixture_id)
            .order_by(
                models.ModelPrediction.prediction_time.desc(),
                models.ModelPrediction.id.desc(),
            )
            .limit(1)
        )

    def _latest_ou_prediction(self, fixture_id: int) -> models.OUModelPrediction | None:
        return self._session.scalar(
            select(models.OUModelPrediction)
            .where(models.OUModelPrediction.fixture_id == fixture_id)
            .order_by(
                models.OUModelPrediction.prediction_time.desc(),
                models.OUModelPrediction.id.desc(),
            )
            .limit(1)
        )

    def _has_combo(self, fixture_id: int) -> bool:
        return (
            self._session.scalar(
                select(func.count(models.ComboTicketLeg.id)).where(
                    models.ComboTicketLeg.fixture_id == fixture_id
                )
            )
            or 0
        ) > 0

    def _data_quality_score(
        self,
        prediction: models.ModelPrediction | None,
        ou_prediction: models.OUModelPrediction | None,
    ) -> float | None:
        from football_predictor.web_api.schemas.common import data_quality_score_from_json

        if prediction is not None:
            score = data_quality_score_from_json(prediction.data_quality_json)
            if score is not None:
                return score
        if ou_prediction is not None:
            return data_quality_score_from_json(ou_prediction.data_quality_json)
        return None

    def _competition_key_for_fixture(self, fixture: models.Fixture) -> str | None:
        keys = self._competition_keys_for_pairs([(fixture.league_id, fixture.season)])
        return keys.get((fixture.league_id, fixture.season)) or _fallback_competition_key(
            fixture.league_id,
            fixture.season,
        )

    def _competition_keys_for_pairs(
        self,
        pairs: Iterable[tuple[int, int]],
    ) -> dict[tuple[int, int], str]:
        normalized_pairs = {(int(league_id), int(season)) for league_id, season in pairs}
        if not normalized_pairs:
            return {}
        keys: dict[tuple[int, int], str] = {}
        for league_id, season in normalized_pairs:
            key = self._session.scalar(
                select(models.TeamSeason.competition_key)
                .where(
                    models.TeamSeason.league_id == league_id,
                    models.TeamSeason.season == season,
                    models.TeamSeason.competition_key.is_not(None),
                )
                .limit(1)
            )
            if key:
                keys[(league_id, season)] = str(key)
        return keys

    def _competition_from_league(
        self,
        league: models.League,
        keys: dict[tuple[int, int], str],
    ) -> CompetitionSummary:
        return CompetitionSummary(
            competition_key=keys.get((league.league_id, league.season))
            or _fallback_competition_key(league.league_id, league.season),
            league_id=league.league_id,
            season=league.season,
            name=league.name,
            country=league.country,
            type=league.type,
            enabled=True,
            logo=league.logo,
            category=league.category,
        )

    def _filter_by_competition(self, stmt, competition_key: str | None):
        if not competition_key:
            return stmt
        competition = self.get_competition(competition_key)
        if competition is None:
            return stmt.where(models.Fixture.fixture_id == -1)
        return stmt.where(
            models.Fixture.league_id == competition.league_id,
            models.Fixture.season == competition.season,
        )


def _fallback_competition_key(league_id: int, season: int) -> str:
    if league_id == 1 and season == 2026:
        return "fifa_world_cup_2026"
    return f"league_{league_id}_{season}"


def _zoneinfo(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("Europe/Paris")


def _local_day_bounds_utc(target_date: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start_local = datetime.combine(target_date, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def _latest_datetime(*values: object) -> datetime | None:
    dates: list[datetime] = []
    for value in values:
        prediction_time = getattr(value, "prediction_time", None)
        if isinstance(prediction_time, datetime):
            dates.append(prediction_time)
    return max(dates) if dates else None
