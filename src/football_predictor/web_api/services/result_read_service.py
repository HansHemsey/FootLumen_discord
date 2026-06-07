"""Read-only recent result queries for the API."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.web_api.schemas.fixtures import fixture_summary_from_model
from football_predictor.web_api.schemas.results import (
    RecentResultDTO,
    ResultOUPredictionSummary,
    ResultPredictionSummary,
)
from football_predictor.web_api.services.fixture_read_service import FixtureReadService
from football_predictor.web_api.services.ou_read_service import OUReadService
from football_predictor.web_api.services.prediction_read_service import PredictionReadService

_FINISHED_STATUSES = {"FT", "AET", "PEN"}


class ResultReadService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._fixtures = FixtureReadService(session)
        self._predictions = PredictionReadService(session)
        self._ou = OUReadService(session)

    def list_recent(
        self,
        *,
        competition_key: str | None = None,
        days: int = 7,
        limit: int = 50,
    ) -> list[RecentResultDTO]:
        end_utc = datetime.now(UTC)
        start_utc = end_utc - timedelta(days=days)
        stmt = (
            select(models.Fixture)
            .where(
                models.Fixture.date >= start_utc,
                models.Fixture.date <= end_utc,
                models.Fixture.status_short.in_(_FINISHED_STATUSES),
            )
            .order_by(models.Fixture.date.desc(), models.Fixture.fixture_id.desc())
            .limit(min(limit, 100))
        )
        stmt = self._fixtures._filter_by_competition(stmt, competition_key)
        return [self._result_from_fixture(fixture) for fixture in self._session.scalars(stmt).all()]

    def _result_from_fixture(self, fixture: models.Fixture) -> RecentResultDTO:
        home_goals = _goal_value(fixture.home_goals, fixture.goals_home)
        away_goals = _goal_value(fixture.away_goals, fixture.goals_away)
        result_1x2 = _result_1x2(home_goals, away_goals)
        latest_prediction = self._predictions.get_latest_for_fixture(fixture.fixture_id)
        latest_ou = self._ou.get_latest_for_fixture(fixture.fixture_id)
        combo_count, combo_statuses = self._combo_impact(fixture.fixture_id)
        ou_result = _ou_result(home_goals, away_goals, latest_ou.threshold if latest_ou else None)
        return RecentResultDTO(
            fixture=fixture_summary_from_model(
                fixture,
                competition_key=self._fixtures._competition_key_for_fixture(fixture),
                has_1x2_prediction=latest_prediction is not None,
                has_ou_prediction=latest_ou is not None,
                has_combo=combo_count > 0,
            ),
            home_goals=home_goals,
            away_goals=away_goals,
            result_1x2=result_1x2,
            ou_result=ou_result,
            prediction_1x2=_prediction_summary(latest_prediction, result_1x2),
            ou_prediction=_ou_summary(latest_ou, ou_result),
            combo_ticket_count=combo_count,
            combo_statuses=combo_statuses,
        )

    def _combo_impact(self, fixture_id: int) -> tuple[int, list[str]]:
        rows = self._session.execute(
            select(models.ComboTicket.status, func.count(models.ComboTicket.id))
            .join(models.ComboTicketLeg, models.ComboTicketLeg.ticket_id == models.ComboTicket.id)
            .where(models.ComboTicketLeg.fixture_id == fixture_id)
            .group_by(models.ComboTicket.status)
        ).all()
        statuses = sorted(str(status) for status, count in rows if int(count or 0) > 0)
        total = sum(int(count or 0) for _status, count in rows)
        return total, statuses


def _prediction_summary(prediction, result_1x2: str | None) -> ResultPredictionSummary | None:
    if prediction is None:
        return None
    predicted_result = prediction.predicted_result
    return ResultPredictionSummary(
        prediction_id=prediction.prediction_id,
        model_version=prediction.model_version,
        predicted_result=predicted_result,
        confidence_label=prediction.confidence_label,
        confidence_score=prediction.confidence_score,
        publication_decision=prediction.publication_decision,
        correct=_matches_1x2(predicted_result, result_1x2),
    )


def _ou_summary(prediction, ou_result: str | None) -> ResultOUPredictionSummary | None:
    if prediction is None:
        return None
    pick = prediction.value_side or prediction.forecast_side
    return ResultOUPredictionSummary(
        prediction_id=prediction.prediction_id,
        model_version=prediction.model_version,
        threshold=prediction.threshold,
        forecast_side=prediction.forecast_side,
        value_side=prediction.value_side,
        confidence_label=prediction.confidence_label_v2,
        confidence_score=prediction.confidence_score_v2,
        publication_decision=prediction.publication_decision,
        pick_result=_matches_ou_pick(pick, ou_result),
    )


def _goal_value(*values: int | None) -> int | None:
    for value in values:
        if value is not None:
            return int(value)
    return None


def _result_1x2(home_goals: int | None, away_goals: int | None) -> str | None:
    if home_goals is None or away_goals is None:
        return None
    if home_goals > away_goals:
        return "HOME"
    if away_goals > home_goals:
        return "AWAY"
    return "DRAW"


def _ou_result(
    home_goals: int | None,
    away_goals: int | None,
    threshold: float | None,
) -> str | None:
    if home_goals is None or away_goals is None or threshold is None:
        return None
    return "OVER" if home_goals + away_goals > threshold else "UNDER"


def _matches_1x2(predicted_result: str | None, result_1x2: str | None) -> bool | None:
    if predicted_result is None or result_1x2 is None:
        return None
    normalized = predicted_result.upper()
    if normalized in {"1", "HOME", "H"}:
        normalized = "HOME"
    elif normalized in {"X", "DRAW", "D"}:
        normalized = "DRAW"
    elif normalized in {"2", "AWAY", "A"}:
        normalized = "AWAY"
    return normalized == result_1x2


def _matches_ou_pick(pick: str | None, ou_result: str | None) -> str | None:
    if pick is None or ou_result is None:
        return None
    return "WON" if pick.upper() == ou_result else "LOST"
