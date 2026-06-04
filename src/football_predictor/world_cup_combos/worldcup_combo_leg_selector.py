"""Select clean World Cup combo leg candidates from persisted predictions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from football_predictor.world_cup_combos.adapters import WorldCupComboReadAdapters
from football_predictor.world_cup_combos.config import WorldCupComboConfig
from football_predictor.world_cup_combos.cutoff import compute_effective_cutoff
from football_predictor.world_cup_combos.enums import ComboMarketScope, ComboMarketType
from football_predictor.world_cup_combos.models import (
    ComboFixtureNoCandidate,
    ComboLegCandidate,
    ComboLegSelectionResult,
    WorldCupComboFixtureRef,
    WorldCupComboSession,
)

STALE_ODDS_WARNING_MINUTES = 120
STALE_PREDICTION_WARNING_MINUTES = 180
LINEUP_CLOSE_TO_KICKOFF_MINUTES = 90


class WorldCupComboLegSelector:
    """Read existing snapshots and return only candidate legs usable by combo V1."""

    def __init__(
        self,
        db_session: Session,
        config: WorldCupComboConfig,
        *,
        adapters: WorldCupComboReadAdapters | None = None,
    ) -> None:
        self.db_session = db_session
        self.config = config
        self.adapters = adapters or WorldCupComboReadAdapters(db_session)

    def select_candidates(
        self,
        sessions: list[WorldCupComboSession] | tuple[WorldCupComboSession, ...],
        *,
        now: datetime | None = None,
    ) -> ComboLegSelectionResult:
        if not self.config.enabled:
            return ComboLegSelectionResult()

        current_time = _as_utc(now or datetime.now(tz=UTC))
        candidates: list[ComboLegCandidate] = []
        no_candidates: list[ComboFixtureNoCandidate] = []

        for combo_session in sessions:
            data_cutoff_time = compute_effective_cutoff(
                current_time,
                combo_session.lock_time,
            )
            for fixture in combo_session.fixtures:
                fixture_rejection = self._fixture_rejection_reason(fixture, current_time)
                if fixture_rejection is not None:
                    no_candidates.append(
                        ComboFixtureNoCandidate(
                            fixture_id=fixture.fixture_id,
                            session_key=combo_session.session_key,
                            source_type="fixture",
                            reason=fixture_rejection,
                        )
                    )
                    continue

                one_x_two_candidate, reason = self._one_x_two_candidate(
                    combo_session,
                    fixture,
                    current_time=current_time,
                    data_cutoff_time=data_cutoff_time,
                )
                if one_x_two_candidate is not None:
                    candidates.append(one_x_two_candidate)
                elif reason is not None:
                    no_candidates.append(
                        ComboFixtureNoCandidate(
                            fixture_id=fixture.fixture_id,
                            session_key=combo_session.session_key,
                            source_type="worldcup_1x2",
                            reason=reason,
                        )
                    )

                ou_candidate, reason = self._ou_candidate(
                    combo_session,
                    fixture,
                    current_time=current_time,
                    data_cutoff_time=data_cutoff_time,
                )
                if ou_candidate is not None:
                    candidates.append(ou_candidate)
                elif reason is not None:
                    no_candidates.append(
                        ComboFixtureNoCandidate(
                            fixture_id=fixture.fixture_id,
                            session_key=combo_session.session_key,
                            source_type="ou25_v2",
                            reason=reason,
                        )
                    )

        return ComboLegSelectionResult(
            sessions=tuple(sessions),
            candidates=tuple(candidates),
            no_candidates=tuple(no_candidates),
        )

    def _fixture_rejection_reason(
        self,
        fixture: WorldCupComboFixtureRef,
        current_time: datetime,
    ) -> str | None:
        if (fixture.status_short or "").upper() != "NS":
            return "fixture_started"
        if fixture.kickoff_at_utc <= current_time:
            return "fixture_started"
        return None

    def _one_x_two_candidate(
        self,
        combo_session: WorldCupComboSession,
        fixture: WorldCupComboFixtureRef,
        *,
        current_time: datetime,
        data_cutoff_time: datetime,
    ) -> tuple[ComboLegCandidate | None, str | None]:
        prediction = self.adapters.latest_1x2_prediction(
            fixture_id=fixture.fixture_id,
            cutoff_time=data_cutoff_time,
        )
        if prediction is None:
            return None, "missing_prediction"

        market_type = _market_type_from_1x2_prediction(prediction.predicted_result)
        if market_type is None:
            return None, "ambiguous_market"
        market_scope = _market_scope_from_payload(prediction.payload_json)
        if combo_session.is_knockout and market_scope == ComboMarketScope.UNKNOWN:
            return None, "ambiguous_market_scope"

        markets = self.adapters.latest_1x2_market_consensus(
            fixture_id=fixture.fixture_id,
            cutoff_time=data_cutoff_time,
        )
        market = markets.get(market_type)
        if market is None:
            return None, "market_unavailable"

        model_probability = prediction.probabilities.get(market_type)
        if model_probability is None:
            return None, "missing_prediction_probability"
        edge = model_probability - market.market_probability
        ev = model_probability * market.decimal_odd - 1.0
        return self._candidate_or_reason(
            combo_session=combo_session,
            fixture=fixture,
            current_time=current_time,
            data_cutoff_time=data_cutoff_time,
            market_type=market_type,
            market_scope=market_scope,
            selection=_selection_label(market_type, fixture),
            decimal_odd=market.decimal_odd,
            model_probability=model_probability,
            market_probability=market.market_probability,
            edge=edge,
            ev=ev,
            confidence_score=prediction.confidence_score,
            confidence_label=prediction.confidence_label,
            data_quality_score=prediction.data_quality_score,
            odds_snapshot_id=market.odds_snapshot_id,
            prediction_snapshot_id=prediction.prediction_id,
            odds_last_update=market.odds_last_update,
            prediction_generated_at=prediction.generated_at or prediction.prediction_time,
            lineup_status=self.adapters.lineup_status(
                fixture_id=fixture.fixture_id,
                cutoff_time=data_cutoff_time,
            ),
        )

    def _ou_candidate(
        self,
        combo_session: WorldCupComboSession,
        fixture: WorldCupComboFixtureRef,
        *,
        current_time: datetime,
        data_cutoff_time: datetime,
    ) -> tuple[ComboLegCandidate | None, str | None]:
        prediction = self.adapters.latest_ou_value_prediction(
            fixture_id=fixture.fixture_id,
            cutoff_time=data_cutoff_time,
        )
        if prediction is None:
            return None, "no_ou_value_side"

        market_type = _market_type_from_ou_prediction(prediction.value_side)
        if market_type is None:
            return None, "ambiguous_market"
        market_scope = _market_scope_from_payload(prediction.payload_json)
        if combo_session.is_knockout and market_scope == ComboMarketScope.UNKNOWN:
            return None, "ambiguous_market_scope"

        odds_snapshot_id, odds_last_update = self.adapters.latest_ou_odds_update(
            fixture_id=fixture.fixture_id,
            cutoff_time=data_cutoff_time,
        )
        return self._candidate_or_reason(
            combo_session=combo_session,
            fixture=fixture,
            current_time=current_time,
            data_cutoff_time=data_cutoff_time,
            market_type=market_type,
            market_scope=market_scope,
            selection="Over 2.5" if market_type == ComboMarketType.OVER_25 else "Under 2.5",
            decimal_odd=prediction.odd_pick,
            model_probability=prediction.p_pick,
            market_probability=prediction.market_p_pick,
            edge=prediction.edge_pick,
            ev=prediction.ev_pick,
            confidence_score=prediction.confidence_score,
            confidence_label=prediction.confidence_label,
            data_quality_score=prediction.data_quality_score,
            odds_snapshot_id=odds_snapshot_id,
            prediction_snapshot_id=prediction.prediction_id,
            odds_last_update=odds_last_update,
            prediction_generated_at=prediction.generated_at or prediction.prediction_time,
            lineup_status=self.adapters.lineup_status(
                fixture_id=fixture.fixture_id,
                cutoff_time=data_cutoff_time,
            ),
        )

    def _candidate_or_reason(
        self,
        *,
        combo_session: WorldCupComboSession,
        fixture: WorldCupComboFixtureRef,
        current_time: datetime,
        data_cutoff_time: datetime,
        market_type: ComboMarketType,
        market_scope: ComboMarketScope,
        selection: str,
        decimal_odd: float,
        model_probability: float,
        market_probability: float,
        edge: float,
        ev: float,
        confidence_score: float,
        confidence_label: str,
        data_quality_score: float,
        odds_snapshot_id: int | None,
        prediction_snapshot_id: int | None,
        odds_last_update: datetime | None,
        prediction_generated_at: datetime | None,
        lineup_status: str,
    ) -> tuple[ComboLegCandidate | None, str | None]:
        if decimal_odd <= 1.01:
            return None, "invalid_odds"
        if self.config.require_positive_ev_each_leg and ev <= 0:
            return None, "ev_below_threshold"
        if ev < self.config.min_leg_ev:
            return None, "ev_below_threshold"
        if edge < self.config.min_leg_edge:
            return None, "edge_below_threshold"
        if data_quality_score < self.config.min_leg_data_quality:
            return None, "data_quality_below_threshold"
        if confidence_score < self.config.min_leg_confidence:
            return None, "confidence_below_threshold"

        warnings = self._freshness_warnings(
            fixture=fixture,
            current_time=current_time,
            lock_time=combo_session.lock_time,
            odds_last_update=odds_last_update,
            prediction_generated_at=prediction_generated_at,
            lineup_status=lineup_status,
        )
        if combo_session.is_matchday3 and not self.config.allow_public_matchday3:
            warnings.append("matchday3_public_risk")
        if combo_session.is_knockout and not self.config.allow_public_knockout:
            warnings.append("knockout_public_risk")
        return (
            ComboLegCandidate(
                fixture_id=fixture.fixture_id,
                kickoff_at_utc=fixture.kickoff_at_utc,
                kickoff_at_paris=fixture.kickoff_at_paris,
                market_type=market_type,
                market_scope=market_scope,
                selection=selection,
                decimal_odd=decimal_odd,
                model_probability=model_probability,
                market_probability=market_probability,
                edge=edge,
                ev=ev,
                confidence_score=confidence_score,
                confidence_label=confidence_label,
                data_quality_score=data_quality_score,
                odds_snapshot_id=odds_snapshot_id,
                prediction_snapshot_id=prediction_snapshot_id,
                lineup_status=lineup_status,
                odds_last_update=odds_last_update,
                prediction_generated_at=prediction_generated_at,
                freshness_score=_freshness_score(
                    lock_time=combo_session.lock_time,
                    odds_last_update=odds_last_update,
                    prediction_generated_at=prediction_generated_at,
                ),
                data_cutoff_time=data_cutoff_time,
                generated_at=current_time,
                lock_time=combo_session.lock_time,
                warnings=warnings,
            ),
            None,
        )

    def _freshness_warnings(
        self,
        *,
        fixture: WorldCupComboFixtureRef,
        current_time: datetime,
        lock_time: datetime,
        odds_last_update: datetime | None,
        prediction_generated_at: datetime | None,
        lineup_status: str,
    ) -> list[str]:
        warnings: list[str] = []
        if odds_last_update is None:
            warnings.append("odds_freshness_unknown")
        elif lock_time - odds_last_update > timedelta(minutes=STALE_ODDS_WARNING_MINUTES):
            warnings.append("odds_stale")
        if prediction_generated_at is None:
            warnings.append("prediction_freshness_unknown")
        elif lock_time - prediction_generated_at > timedelta(
            minutes=STALE_PREDICTION_WARNING_MINUTES
        ):
            warnings.append("prediction_stale")
        if (
            fixture.kickoff_at_utc - current_time
            <= timedelta(minutes=LINEUP_CLOSE_TO_KICKOFF_MINUTES)
            and lineup_status == "missing"
        ):
            warnings.append("lineup_missing_close_to_kickoff")
        return warnings


def _market_type_from_1x2_prediction(value: str) -> ComboMarketType | None:
    normalized = (value or "").strip().upper()
    if normalized == "HOME":
        return ComboMarketType.HOME
    if normalized == "DRAW":
        return ComboMarketType.DRAW
    if normalized == "AWAY":
        return ComboMarketType.AWAY
    return None


def _market_type_from_ou_prediction(value: str) -> ComboMarketType | None:
    normalized = (value or "").strip().upper()
    if normalized == "OVER":
        return ComboMarketType.OVER_25
    if normalized == "UNDER":
        return ComboMarketType.UNDER_25
    return None


def _market_scope_from_payload(payload: dict | None) -> ComboMarketScope:
    if not isinstance(payload, dict):
        return ComboMarketScope.NINETY_MIN
    raw_value = payload.get("market_scope")
    if raw_value is None:
        return ComboMarketScope.NINETY_MIN
    try:
        return ComboMarketScope(str(raw_value).upper())
    except ValueError:
        return ComboMarketScope.UNKNOWN


def _selection_label(market_type: ComboMarketType, fixture: WorldCupComboFixtureRef) -> str:
    if market_type == ComboMarketType.HOME:
        return fixture.home_team
    if market_type == ComboMarketType.DRAW:
        return "Match nul"
    if market_type == ComboMarketType.AWAY:
        return fixture.away_team
    return market_type.value


def _freshness_score(
    *,
    lock_time: datetime,
    odds_last_update: datetime | None,
    prediction_generated_at: datetime | None,
) -> float:
    scores: list[float] = []
    if odds_last_update is not None:
        odds_age = max((lock_time - odds_last_update).total_seconds() / 60.0, 0.0)
        scores.append(max(0.0, 100.0 - odds_age / 3.0))
    if prediction_generated_at is not None:
        prediction_age = max((lock_time - prediction_generated_at).total_seconds() / 60.0, 0.0)
        scores.append(max(0.0, 100.0 - prediction_age / 4.0))
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 2)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
