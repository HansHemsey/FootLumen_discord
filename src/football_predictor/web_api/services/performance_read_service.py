"""Read-only performance summaries for the API."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.utils.time import utc_now
from football_predictor.web_api.schemas.performance import (
    CompetitionPerformanceSummary,
    MarketPerformanceSummary,
    PerformanceMetric,
    PerformanceSummaryDTO,
)
from football_predictor.web_api.services.fixture_read_service import FixtureReadService

_FINISHED_STATUSES = {"FT", "AET", "PEN"}


class PerformanceReadService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._fixtures = FixtureReadService(session)

    def summary(
        self,
        *,
        competition_key: str | None = None,
        days: int = 30,
    ) -> PerformanceSummaryDTO:
        period_end_dt = datetime.now(UTC)
        period_start_dt = period_end_dt - timedelta(days=days)
        competition = self._fixtures.get_competition(competition_key) if competition_key else None
        total_1x2 = self._count_1x2(period_start_dt, period_end_dt, competition_key)
        total_ou = self._count_ou(period_start_dt, period_end_dt, competition_key)
        total_combos = self._count_combos(
            period_start_dt.date(),
            period_end_dt.date(),
            competition_key,
        )
        total_public = self._count_public_messages(period_start_dt, period_end_dt, competition_key)
        total_no_bet = self._count_no_bet(period_start_dt, period_end_dt, competition_key)
        settled_predictions, successful_predictions = self._prediction_outcome_counts(
            period_start_dt,
            period_end_dt,
            competition_key,
        )
        by_competition = []
        if competition_key:
            by_competition.append(
                CompetitionPerformanceSummary(
                    competition_key=competition_key,
                    total_predictions=total_1x2,
                    total_ou_predictions=total_ou,
                    total_combos=total_combos,
                )
            )
        notes = [
            "ROI non expose tant que les mises, cotes executables et settlements "
            "ne sont pas complets.",
            "Les publications publiques sont estimees via discord_messages envoyes.",
        ]
        if competition_key and competition is None:
            notes.append("Competition inconnue: les compteurs retournent zero.")
        return PerformanceSummaryDTO(
            generated_at=utc_now(),
            scope=competition_key or "global",
            period_start=period_start_dt.date(),
            period_end=period_end_dt.date(),
            total_predictions=total_1x2,
            total_public_predictions=total_public,
            total_no_bet=total_no_bet,
            total_ou_predictions=total_ou,
            total_combos=total_combos,
            settled_predictions=settled_predictions,
            successful_predictions=successful_predictions,
            roi=None,
            by_market=[
                MarketPerformanceSummary(
                    market="1X2",
                    total_predictions=total_1x2,
                    public_predictions=total_public,
                    settled_predictions=settled_predictions,
                    successful_predictions=successful_predictions,
                    note="Inclut V3 et legacy quand disponibles.",
                ),
                MarketPerformanceSummary(
                    market="O/U",
                    total_predictions=total_ou,
                    no_bet=self._count_ou_no_bet(period_start_dt, period_end_dt, competition_key),
                ),
                MarketPerformanceSummary(
                    market="COMBO",
                    total_predictions=total_combos,
                    no_bet=self._count_combo_no_bet(
                        period_start_dt.date(),
                        period_end_dt.date(),
                        competition_key,
                    ),
                ),
            ],
            by_competition=by_competition,
            notes=notes,
            metrics=[
                PerformanceMetric(name="1x2_predictions", value=total_1x2),
                PerformanceMetric(name="ou_predictions", value=total_ou),
                PerformanceMetric(name="combo_tickets", value=total_combos),
            ],
        )

    def _count_1x2(
        self,
        start_at: datetime,
        end_at: datetime,
        competition_key: str | None,
    ) -> int:
        legacy = self._count_prediction_table(
            models.ModelPrediction,
            start_at,
            end_at,
            competition_key,
        )
        v3 = self._count_prediction_table(
            models.V3ModelPrediction,
            start_at,
            end_at,
            competition_key,
        )
        return legacy + v3

    def _count_ou(
        self,
        start_at: datetime,
        end_at: datetime,
        competition_key: str | None,
    ) -> int:
        return self._count_prediction_table(
            models.OUModelPrediction,
            start_at,
            end_at,
            competition_key,
        )

    def _count_prediction_table(
        self,
        model,
        start_at: datetime,
        end_at: datetime,
        competition_key: str | None,
    ) -> int:
        stmt = (
            select(func.count(model.id))
            .join(models.Fixture, models.Fixture.fixture_id == model.fixture_id)
            .where(model.prediction_time >= start_at, model.prediction_time <= end_at)
        )
        stmt = self._fixtures._filter_by_competition(stmt, competition_key)
        return int(self._session.scalar(stmt) or 0)

    def _count_combos(
        self,
        start_date: date,
        end_date: date,
        competition_key: str | None,
    ) -> int:
        stmt = select(func.count(models.ComboTicket.id)).where(
            models.ComboTicket.combo_date >= start_date,
            models.ComboTicket.combo_date <= end_date,
        )
        if competition_key:
            stmt = stmt.where(models.ComboTicket.competition_key == competition_key)
        return int(self._session.scalar(stmt) or 0)

    def _count_public_messages(
        self,
        start_at: datetime,
        end_at: datetime,
        competition_key: str | None,
    ) -> int:
        stmt = select(func.count(models.DiscordMessage.id)).where(
            models.DiscordMessage.created_at >= start_at,
            models.DiscordMessage.created_at <= end_at,
            models.DiscordMessage.model_prediction_id.is_not(None),
            models.DiscordMessage.dry_run.is_(False),
            models.DiscordMessage.status.in_(("sent", "success", "published")),
        )
        if competition_key:
            stmt = stmt.where(models.DiscordMessage.competition_key == competition_key)
        return int(self._session.scalar(stmt) or 0)

    def _count_no_bet(
        self,
        start_at: datetime,
        end_at: datetime,
        competition_key: str | None,
    ) -> int:
        return self._count_ou_no_bet(start_at, end_at, competition_key) + self._count_combo_no_bet(
            start_at.date(),
            end_at.date(),
            competition_key,
        )

    def _count_ou_no_bet(
        self,
        start_at: datetime,
        end_at: datetime,
        competition_key: str | None,
    ) -> int:
        stmt = (
            select(func.count(models.OUModelPrediction.id))
            .join(models.Fixture, models.Fixture.fixture_id == models.OUModelPrediction.fixture_id)
            .where(
                models.OUModelPrediction.prediction_time >= start_at,
                models.OUModelPrediction.prediction_time <= end_at,
                models.OUModelPrediction.no_bet_reason.is_not(None),
            )
        )
        stmt = self._fixtures._filter_by_competition(stmt, competition_key)
        return int(self._session.scalar(stmt) or 0)

    def _count_combo_no_bet(
        self,
        start_date: date,
        end_date: date,
        competition_key: str | None,
    ) -> int:
        stmt = select(func.count(models.ComboTicket.id)).where(
            models.ComboTicket.combo_date >= start_date,
            models.ComboTicket.combo_date <= end_date,
            models.ComboTicket.status == "NO_BET",
        )
        if competition_key:
            stmt = stmt.where(models.ComboTicket.competition_key == competition_key)
        return int(self._session.scalar(stmt) or 0)

    def _prediction_outcome_counts(
        self,
        start_at: datetime,
        end_at: datetime,
        competition_key: str | None,
    ) -> tuple[int, int | None]:
        stmt = (
            select(
                models.ModelPrediction.predicted_result,
                models.Fixture.home_goals,
                models.Fixture.away_goals,
            )
            .join(models.Fixture, models.Fixture.fixture_id == models.ModelPrediction.fixture_id)
            .where(
                models.ModelPrediction.prediction_time >= start_at,
                models.ModelPrediction.prediction_time <= end_at,
                models.Fixture.status_short.in_(_FINISHED_STATUSES),
            )
        )
        stmt = self._fixtures._filter_by_competition(stmt, competition_key)
        settled = 0
        successful = 0
        for predicted_result, home_goals, away_goals in self._session.execute(stmt).all():
            result = _result_1x2(home_goals, away_goals)
            if result is None:
                continue
            settled += 1
            if _matches_1x2(predicted_result, result):
                successful += 1
        return settled, successful if settled else None


def _result_1x2(home_goals: int | None, away_goals: int | None) -> str | None:
    if home_goals is None or away_goals is None:
        return None
    if home_goals > away_goals:
        return "HOME"
    if away_goals > home_goals:
        return "AWAY"
    return "DRAW"


def _matches_1x2(predicted_result: str | None, result_1x2: str | None) -> bool:
    if predicted_result is None or result_1x2 is None:
        return False
    normalized = predicted_result.upper()
    if normalized in {"1", "HOME", "H"}:
        normalized = "HOME"
    elif normalized in {"X", "DRAW", "D"}:
        normalized = "DRAW"
    elif normalized in {"2", "AWAY", "A"}:
        normalized = "AWAY"
    return normalized == result_1x2
