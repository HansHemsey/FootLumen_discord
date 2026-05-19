"""O/U 2.5 prediction service — single-fixture inference with edge/EV computation."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from football_predictor.config.settings import Settings
from football_predictor.db import models
from football_predictor.db.repositories import upsert_by_fields
from football_predictor.ou_model.constants import (
    FEATURE_VERSION,
    OU_THRESHOLD,
)
from football_predictor.ou_model.features.ou_feature_builder import (
    OUFeatureBuilderResult,
    build_ou_feature_snapshot,
)
from football_predictor.ou_model.modeling.ou_model import OUCompositeModel
from football_predictor.ou_model.prediction.ou_decision import (
    OUDecision,
    decide_ou_prediction,
)
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference
from football_predictor.utils.time import ensure_aware_utc, utc_now

JsonDict = dict[str, Any]
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OUPredictionOutput:
    fixture_id: int
    prediction_time: datetime
    model_version: str
    threshold: float
    # Core probabilities
    p_over: float
    p_under: float
    # xG
    xg_home: float | None
    xg_away: float | None
    xg_total: float | None
    # Market signals
    market_p_over: float | None
    market_p_under: float | None
    market_odd_over: float | None
    market_odd_under: float | None
    # Edge & EV
    edge_over: float | None
    edge_under: float | None
    ev_over: float | None
    ev_under: float | None
    # Confidence
    confidence_score: float
    confidence_label: str
    # O/U decision v2
    forecast_side: str | None = None
    forecast_probability: float | None = None
    value_side: str | None = None
    value_probability: float | None = None
    value_market_probability: float | None = None
    value_market_odd: float | None = None
    value_edge: float | None = None
    value_ev: float | None = None
    p_pick: float | None = None
    market_p_pick: float | None = None
    odd_pick: float | None = None
    edge_pick: float | None = None
    ev_pick: float | None = None
    is_value_pick: bool = False
    no_bet_reason: str | None = None
    non_publication_reason: str | None = None
    confidence_score_v2: float | None = None
    confidence_label_v2: str | None = None
    publication_decision: str | None = None
    decision_version: str | None = None
    data_quality_score: float | None = None
    bookmaker_count: float | None = None
    # Match context (resolved at prediction time)
    kickoff_time: datetime | None = None
    match_label: str | None = None
    competition: str | None = None
    # Expert breakdown
    expert_probabilities: dict[str, float] = field(default_factory=dict)
    data_quality_json: JsonDict = field(default_factory=dict)
    ou_model_prediction_id: int | None = None


def _compute_market_p_over(odd_over: float, odd_under: float) -> float:
    """Margin-free implied probability for Over."""
    q_o = 1 / odd_over
    q_u = 1 / odd_under
    return q_o / (q_o + q_u)


def _extract_xg(features: JsonDict) -> tuple[float | None, float | None, float | None]:
    xg_home = features.get("home_team_global_pseudo_xg_for_avg_last5")
    xg_away = features.get("away_team_global_pseudo_xg_for_avg_last5")
    if xg_home is not None and xg_away is not None:
        return float(xg_home), float(xg_away), float(xg_home) + float(xg_away)
    return None, None, None


class OUPredictionService:
    """Predict O/U 2.5 for a single fixture."""

    def __init__(
        self,
        session: Session,
        *,
        model_dir: Path | str | None = None,
        ou_bet_id: int | None = None,
        feature_version: str = FEATURE_VERSION,
        threshold: float = OU_THRESHOLD,
        players_reference: PlayersReference | None = None,
        api_reference: ApiFootballReference | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.feature_version = feature_version
        self.threshold = threshold
        self.players_reference = players_reference
        self.api_reference = api_reference

        resolved_settings = settings or Settings()
        self.ou_bet_id = ou_bet_id or resolved_settings.market_ou25_bet_id

        resolved_model_dir = Path(model_dir) if model_dir else resolved_settings.ou_model_dir
        self.model: OUCompositeModel | None = None
        self.model_version = "unknown"
        model_path = resolved_model_dir / "model.joblib"
        if model_path.exists():
            try:
                self.model = OUCompositeModel.load(model_path)
                self.model_version = self.model.model_version
                logger.info("Loaded O/U model from %s (version=%s)", model_path, self.model_version)
            except Exception as exc:
                logger.warning("Could not load O/U model from %s: %s", model_path, exc)
        else:
            logger.warning("No O/U model found at %s — using Poisson fallback", model_path)

    def predict_fixture_ou(
        self,
        fixture_id: int,
        prediction_time: datetime | None = None,
        *,
        save_to_db: bool = True,
    ) -> OUPredictionOutput:
        resolved_time = ensure_aware_utc(prediction_time) if prediction_time else utc_now()

        builder_result: OUFeatureBuilderResult = build_ou_feature_snapshot(
            self.session,
            fixture_id,
            resolved_time,
            ou_bet_id=self.ou_bet_id,
            feature_version=self.feature_version,
            threshold=self.threshold,
            players_reference=self.players_reference,
            api_reference=self.api_reference,
        )
        features = builder_result.features_json

        if self.model is not None:
            p_over, p_under = self.model.predict_ou(features)
            expert_probs = self.model.expert_probabilities_for_row(features)
        else:
            from football_predictor.ou_model.modeling.ou_poisson import poisson_ou_predict
            p_over, p_under = poisson_ou_predict(features, self.threshold)
            expert_probs = {"poisson": p_over}

        xg_home, xg_away, xg_total = _extract_xg(features)

        odd_over = features.get("market_odd_over25")
        odd_under = features.get("market_odd_under25")
        odd_over_f = float(odd_over) if odd_over is not None else None
        odd_under_f = float(odd_under) if odd_under is not None else None

        market_p_over: float | None = None
        market_p_under: float | None = None
        decision_data_quality = {
            **builder_result.data_quality_json,
            "ou_data_quality_score": features.get("ou_data_quality_score"),
        }

        if (
            odd_over_f is not None
            and odd_under_f is not None
            and odd_over_f > 1
            and odd_under_f > 1
        ):
            market_p_over = _compute_market_p_over(odd_over_f, odd_under_f)
            market_p_under = 1.0 - market_p_over

        decision: OUDecision = decide_ou_prediction(
            p_over=p_over,
            p_under=p_under,
            market_p_over=market_p_over,
            market_p_under=market_p_under,
            odd_over=odd_over_f,
            odd_under=odd_under_f,
            data_quality_json=decision_data_quality,
        )

        kickoff_time, match_label, competition = self._resolve_match_context(fixture_id)

        output = OUPredictionOutput(
            fixture_id=fixture_id,
            prediction_time=resolved_time,
            model_version=self.model_version,
            threshold=self.threshold,
            p_over=p_over,
            p_under=p_under,
            xg_home=xg_home,
            xg_away=xg_away,
            xg_total=xg_total,
            market_p_over=market_p_over,
            market_p_under=market_p_under,
            market_odd_over=odd_over_f,
            market_odd_under=odd_under_f,
            edge_over=decision.edge_over,
            edge_under=decision.edge_under,
            ev_over=decision.ev_over,
            ev_under=decision.ev_under,
            confidence_score=decision.confidence_score_v2,
            confidence_label=decision.confidence_label_v2,
            forecast_side=decision.forecast_side,
            forecast_probability=decision.forecast_probability,
            value_side=decision.value_side,
            value_probability=decision.value_probability,
            value_market_probability=decision.value_market_probability,
            value_market_odd=decision.value_market_odd,
            value_edge=decision.value_edge,
            value_ev=decision.value_ev,
            p_pick=decision.p_pick,
            market_p_pick=decision.market_p_pick,
            odd_pick=decision.odd_pick,
            edge_pick=decision.edge_pick,
            ev_pick=decision.ev_pick,
            is_value_pick=decision.is_value_pick,
            no_bet_reason=decision.no_bet_reason,
            non_publication_reason=decision.non_publication_reason,
            confidence_score_v2=decision.confidence_score_v2,
            confidence_label_v2=decision.confidence_label_v2,
            publication_decision=decision.publication_decision,
            decision_version=decision.decision_version,
            data_quality_score=decision.data_quality_score,
            bookmaker_count=decision.bookmaker_count,
            kickoff_time=kickoff_time,
            match_label=match_label,
            competition=competition,
            expert_probabilities=expert_probs,
            data_quality_json=decision_data_quality,
        )

        if save_to_db:
            record = self._save_prediction(output, builder_result)
            if record is not None:
                output = replace(output, ou_model_prediction_id=record.id)

        return output

    def _resolve_match_context(
        self, fixture_id: int
    ) -> tuple[datetime | None, str | None, str | None]:
        """Return (kickoff_time, match_label, competition_name) for a fixture."""
        from sqlalchemy import select
        fixture = self.session.get(models.Fixture, fixture_id)
        if fixture is None:
            return None, None, None

        kickoff = fixture.date
        if kickoff is not None:
            kickoff = ensure_aware_utc(kickoff)

        home_team = self.session.execute(
            select(models.Team).where(models.Team.team_id == fixture.home_team_id)
        ).scalar_one_or_none()
        away_team = self.session.execute(
            select(models.Team).where(models.Team.team_id == fixture.away_team_id)
        ).scalar_one_or_none()
        home_name = home_team.name if home_team else f"Team#{fixture.home_team_id}"
        away_name = away_team.name if away_team else f"Team#{fixture.away_team_id}"
        match_label = f"{home_name} vs {away_name}"

        league = self.session.execute(
            select(models.League).where(
                models.League.league_id == fixture.league_id,
                models.League.season == fixture.season,
            )
        ).scalar_one_or_none()
        competition = league.name if league else None

        return kickoff, match_label, competition

    def _save_prediction(
        self,
        output: OUPredictionOutput,
        builder_result: OUFeatureBuilderResult,
    ) -> models.OUModelPrediction | None:
        try:
            snapshot_id = (
                builder_result.snapshot.id
                if hasattr(builder_result.snapshot, "id") and builder_result.snapshot.id
                else None
            )
            record = upsert_by_fields(
                self.session,
                models.OUModelPrediction,
                {
                    "fixture_id": output.fixture_id,
                    "prediction_time": output.prediction_time,
                    "model_version": output.model_version,
                },
                {
                    "ou_feature_snapshot_id": snapshot_id,
                    "threshold": output.threshold,
                    "p_over": output.p_over,
                    "p_under": output.p_under,
                    "xg_home": output.xg_home,
                    "xg_away": output.xg_away,
                    "xg_total": output.xg_total,
                    "market_p_over": output.market_p_over,
                    "market_p_under": output.market_p_under,
                    "edge_over": output.edge_over,
                    "edge_under": output.edge_under,
                    "ev_over": output.ev_over,
                    "ev_under": output.ev_under,
                    "market_odd_over": output.market_odd_over,
                    "market_odd_under": output.market_odd_under,
                    "confidence_score": output.confidence_score,
                    "confidence_label": output.confidence_label,
                    "forecast_side": output.forecast_side,
                    "forecast_probability": output.forecast_probability,
                    "value_side": output.value_side,
                    "p_pick": output.p_pick,
                    "market_p_pick": output.market_p_pick,
                    "odd_pick": output.odd_pick,
                    "edge_pick": output.edge_pick,
                    "ev_pick": output.ev_pick,
                    "is_value_pick": output.is_value_pick,
                    "no_bet_reason": output.no_bet_reason,
                    "confidence_score_v2": output.confidence_score_v2,
                    "confidence_label_v2": output.confidence_label_v2,
                    "publication_decision": output.publication_decision,
                    "expert_probabilities_json": output.expert_probabilities,
                    "data_quality_json": output.data_quality_json,
                    "payload_json": {
                        "ou_decision": {
                            "decision_version": output.decision_version,
                            "forecast_side": output.forecast_side,
                            "forecast_probability": output.forecast_probability,
                            "value_side": output.value_side,
                            "value_probability": output.value_probability,
                            "value_market_probability": output.value_market_probability,
                            "value_market_odd": output.value_market_odd,
                            "value_edge": output.value_edge,
                            "value_ev": output.value_ev,
                            "p_pick": output.p_pick,
                            "market_p_pick": output.market_p_pick,
                            "odd_pick": output.odd_pick,
                            "edge_pick": output.edge_pick,
                            "ev_pick": output.ev_pick,
                            "is_value_pick": output.is_value_pick,
                            "no_bet_reason": output.no_bet_reason,
                            "non_publication_reason": output.non_publication_reason,
                            "confidence_score_v2": output.confidence_score_v2,
                            "confidence_label_v2": output.confidence_label_v2,
                            "publication_decision": output.publication_decision,
                            "data_quality_score": output.data_quality_score,
                            "bookmaker_count": output.bookmaker_count,
                        },
                    },
                },
            )
            self.session.flush()
            return record
        except Exception as exc:
            logger.warning(
                "Could not save O/U prediction for fixture %d: %s",
                output.fixture_id,
                exc,
            )
            return None
