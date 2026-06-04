"""Read-only adapters for World Cup combo leg selection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db.models import (
    FixtureLineup,
    ModelPrediction,
    OddsSnapshot,
    OUModelPrediction,
)
from football_predictor.world_cup_combos.enums import ComboMarketType

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class OneXTwoPredictionRecord:
    prediction_id: int
    prediction_time: datetime
    generated_at: datetime | None
    predicted_result: str
    probabilities: dict[ComboMarketType, float]
    confidence_score: float
    confidence_label: str
    data_quality_score: float
    payload_json: JsonDict


@dataclass(frozen=True)
class OUPredictionRecord:
    prediction_id: int
    prediction_time: datetime
    generated_at: datetime | None
    value_side: str
    p_pick: float
    market_p_pick: float
    odd_pick: float
    edge_pick: float
    ev_pick: float
    confidence_score: float
    confidence_label: str
    data_quality_score: float
    payload_json: JsonDict


@dataclass(frozen=True)
class MarketConsensus:
    market_type: ComboMarketType
    decimal_odd: float
    market_probability: float
    edge_source_probability: float | None
    odds_snapshot_id: int | None
    odds_last_update: datetime | None
    bookmaker_count: int


class WorldCupComboReadAdapters:
    """Small read adapters around existing DB tables.

    These methods intentionally do not call predictors or external APIs. They only
    load persisted snapshots that already exist before the combo lock time.
    """

    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def latest_1x2_prediction(
        self,
        *,
        fixture_id: int,
        lock_time: datetime,
    ) -> OneXTwoPredictionRecord | None:
        statement = (
            select(ModelPrediction)
            .where(ModelPrediction.fixture_id == fixture_id)
            .where(ModelPrediction.prediction_time <= lock_time)
            .order_by(ModelPrediction.prediction_time.desc(), ModelPrediction.id.desc())
        )
        prediction = self.db_session.execute(statement).scalars().first()
        if prediction is None:
            return None

        confidence_score = _first_float(
            prediction.confidence_score,
            _payload_value(prediction.payload_json, ("confidence_score", "confidence")),
            default=0.0,
        )
        return OneXTwoPredictionRecord(
            prediction_id=prediction.id,
            prediction_time=_as_utc(prediction.prediction_time),
            generated_at=_optional_utc(prediction.created_at),
            predicted_result=_normalize_1x2_result(
                prediction.predicted_result or prediction.predicted_outcome
            ),
            probabilities={
                ComboMarketType.HOME: float(prediction.p_home),
                ComboMarketType.DRAW: float(prediction.p_draw),
                ComboMarketType.AWAY: float(prediction.p_away),
            },
            confidence_score=confidence_score,
            confidence_label=prediction.confidence_label or _label_from_score(confidence_score),
            data_quality_score=_data_quality_score(prediction.data_quality_json),
            payload_json=prediction.payload_json or {},
        )

    def latest_ou_value_prediction(
        self,
        *,
        fixture_id: int,
        lock_time: datetime,
    ) -> OUPredictionRecord | None:
        statement = (
            select(OUModelPrediction)
            .where(OUModelPrediction.fixture_id == fixture_id)
            .where(OUModelPrediction.prediction_time <= lock_time)
            .order_by(OUModelPrediction.prediction_time.desc(), OUModelPrediction.id.desc())
        )
        for prediction in self.db_session.execute(statement).scalars():
            if not prediction.is_value_pick or not prediction.value_side:
                continue
            values = (
                prediction.p_pick,
                prediction.market_p_pick,
                prediction.odd_pick,
                prediction.edge_pick,
                prediction.ev_pick,
            )
            if any(value is None for value in values):
                continue
            confidence_score = _first_float(
                prediction.confidence_score_v2,
                prediction.confidence_score,
                default=0.0,
            )
            return OUPredictionRecord(
                prediction_id=prediction.id,
                prediction_time=_as_utc(prediction.prediction_time),
                generated_at=_optional_utc(prediction.created_at),
                value_side=str(prediction.value_side).upper(),
                p_pick=float(prediction.p_pick),
                market_p_pick=float(prediction.market_p_pick),
                odd_pick=float(prediction.odd_pick),
                edge_pick=float(prediction.edge_pick),
                ev_pick=float(prediction.ev_pick),
                confidence_score=confidence_score,
                confidence_label=(
                    prediction.confidence_label_v2
                    or prediction.confidence_label
                    or _label_from_score(confidence_score)
                ),
                data_quality_score=_data_quality_score(prediction.data_quality_json),
                payload_json=prediction.payload_json or {},
            )
        return None

    def latest_1x2_market_consensus(
        self,
        *,
        fixture_id: int,
        lock_time: datetime,
    ) -> dict[ComboMarketType, MarketConsensus]:
        snapshots = self._load_odds_snapshots(
            fixture_id=fixture_id,
            lock_time=lock_time,
            bet_id=1,
            bet_name="match winner",
        )
        valid = [
            snapshot
            for snapshot in snapshots
            if _valid_odd(snapshot.odd_home)
            and _valid_odd(snapshot.odd_draw)
            and _valid_odd(snapshot.odd_away)
        ]
        if not valid:
            return {}

        implied_rows: list[tuple[OddsSnapshot, float, float, float]] = []
        for snapshot in valid:
            q_home = 1.0 / float(snapshot.odd_home)
            q_draw = 1.0 / float(snapshot.odd_draw)
            q_away = 1.0 / float(snapshot.odd_away)
            total = q_home + q_draw + q_away
            if total <= 0:
                continue
            implied_rows.append((snapshot, q_home / total, q_draw / total, q_away / total))
        if not implied_rows:
            return {}

        bookmaker_count = len(
            {row[0].bookmaker_id or row[0].bookmaker_name for row in implied_rows}
        )
        latest = max(implied_rows, key=lambda row: (_as_utc(row[0].fetched_at), row[0].id))
        odds_last_update = _as_utc(latest[0].fetched_at)
        return {
            ComboMarketType.HOME: MarketConsensus(
                market_type=ComboMarketType.HOME,
                decimal_odd=_mean(snapshot.odd_home for snapshot, *_ in implied_rows),
                market_probability=_mean(row[1] for row in implied_rows),
                edge_source_probability=None,
                odds_snapshot_id=latest[0].id,
                odds_last_update=odds_last_update,
                bookmaker_count=bookmaker_count,
            ),
            ComboMarketType.DRAW: MarketConsensus(
                market_type=ComboMarketType.DRAW,
                decimal_odd=_mean(snapshot.odd_draw for snapshot, *_ in implied_rows),
                market_probability=_mean(row[2] for row in implied_rows),
                edge_source_probability=None,
                odds_snapshot_id=latest[0].id,
                odds_last_update=odds_last_update,
                bookmaker_count=bookmaker_count,
            ),
            ComboMarketType.AWAY: MarketConsensus(
                market_type=ComboMarketType.AWAY,
                decimal_odd=_mean(snapshot.odd_away for snapshot, *_ in implied_rows),
                market_probability=_mean(row[3] for row in implied_rows),
                edge_source_probability=None,
                odds_snapshot_id=latest[0].id,
                odds_last_update=odds_last_update,
                bookmaker_count=bookmaker_count,
            ),
        }

    def latest_ou_odds_update(
        self,
        *,
        fixture_id: int,
        lock_time: datetime,
    ) -> tuple[int | None, datetime | None]:
        snapshots = self._load_odds_snapshots(
            fixture_id=fixture_id,
            lock_time=lock_time,
            bet_id=5,
            bet_name="goals over/under",
        )
        if not snapshots:
            return None, None
        latest = max(snapshots, key=lambda snapshot: (_as_utc(snapshot.fetched_at), snapshot.id))
        return latest.id, _as_utc(latest.fetched_at)

    def lineup_status(self, *, fixture_id: int, lock_time: datetime) -> str:
        statement = (
            select(FixtureLineup.team_id)
            .where(FixtureLineup.fixture_id == fixture_id)
            .where(FixtureLineup.fetched_at <= lock_time)
        )
        teams = {row[0] for row in self.db_session.execute(statement).all()}
        if len(teams) >= 2:
            return "available"
        if len(teams) == 1:
            return "partial"
        return "missing"

    def _load_odds_snapshots(
        self,
        *,
        fixture_id: int,
        lock_time: datetime,
        bet_id: int,
        bet_name: str,
    ) -> list[OddsSnapshot]:
        statement = (
            select(OddsSnapshot)
            .where(OddsSnapshot.fixture_id == fixture_id)
            .where(OddsSnapshot.fetched_at <= lock_time)
            .where(OddsSnapshot.is_live.is_(False))
            .order_by(OddsSnapshot.fetched_at.desc(), OddsSnapshot.id.desc())
        )
        snapshots = self.db_session.execute(statement).scalars().all()
        normalized_name = bet_name.lower()
        return [
            snapshot
            for snapshot in snapshots
            if snapshot.bet_id == bet_id
            or (snapshot.bet_name or "").strip().lower() == normalized_name
        ]


def _normalize_1x2_result(value: str | None) -> str:
    normalized = (value or "").strip().upper()
    if normalized in {"HOME", "H", "1"}:
        return "HOME"
    if normalized in {"DRAW", "D", "X"}:
        return "DRAW"
    if normalized in {"AWAY", "A", "2"}:
        return "AWAY"
    return normalized or "UNKNOWN"


def _data_quality_score(payload: JsonDict | None) -> float:
    return _first_float(
        _payload_value(
            payload,
            (
                "combo_data_quality_score",
                "publication_data_quality_score",
                "overall_data_quality_score",
                "ou_data_quality_score",
                "data_quality_score",
                "score",
            ),
        ),
        default=0.0,
    )


def _payload_value(payload: JsonDict | None, keys: tuple[str, ...]) -> Any:
    if not isinstance(payload, dict):
        return None
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _first_float(*values: Any, default: float) -> float:
    for value in values:
        try:
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            continue
    return default


def _label_from_score(score: float) -> str:
    if score >= 80:
        return "Very High"
    if score >= 65:
        return "High"
    if score >= 50:
        return "Medium"
    if score >= 35:
        return "Low"
    return "Uncertain"


def _valid_odd(value: float | None) -> bool:
    try:
        return value is not None and float(value) > 1.01
    except (TypeError, ValueError):
        return False


def _mean(values: Any) -> float:
    numbers = [float(value) for value in values if value is not None]
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)


def _optional_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return _as_utc(value)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
