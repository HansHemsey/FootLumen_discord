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
    # Match context (resolved at prediction time)
    kickoff_time: datetime | None = None
    match_label: str | None = None
    competition: str | None = None
    # Expert breakdown
    expert_probabilities: dict[str, float] = field(default_factory=dict)
    data_quality_json: JsonDict = field(default_factory=dict)
    ou_model_prediction_id: int | None = None


def _ou_confidence_score(p_over: float, edge: float | None) -> float:
    """Rough confidence score in [0, 100] for O/U predictions."""
    separation = abs(p_over - 0.5) * 2  # 0 = no edge vs coin flip, 1 = certainty
    edge_factor = abs(edge) if edge is not None else 0.0
    raw = (separation * 60.0) + (edge_factor * 200.0)
    return round(max(0.0, min(100.0, raw)), 1)


def _ou_confidence_label(score: float) -> str:
    if score >= 85:
        return "Very High"
    if score >= 70:
        return "High"
    if score >= 45:
        return "Medium"
    if score >= 20:
        return "Low"
    return "Uncertain"


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
        edge_over: float | None = None
        edge_under: float | None = None
        ev_over: float | None = None
        ev_under: float | None = None

        if (
            odd_over_f is not None
            and odd_under_f is not None
            and odd_over_f > 1
            and odd_under_f > 1
        ):
            market_p_over = _compute_market_p_over(odd_over_f, odd_under_f)
            market_p_under = 1.0 - market_p_over
            edge_over = p_over - market_p_over
            edge_under = p_under - market_p_under
            ev_over = p_over * odd_over_f - 1
            ev_under = p_under * odd_under_f - 1

        conf_score = _ou_confidence_score(p_over, edge_over)
        conf_label = _ou_confidence_label(conf_score)

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
            edge_over=edge_over,
            edge_under=edge_under,
            ev_over=ev_over,
            ev_under=ev_under,
            confidence_score=conf_score,
            confidence_label=conf_label,
            kickoff_time=kickoff_time,
            match_label=match_label,
            competition=competition,
            expert_probabilities=expert_probs,
            data_quality_json=builder_result.data_quality_json,
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
                    "expert_probabilities_json": output.expert_probabilities,
                    "data_quality_json": output.data_quality_json,
                    "payload_json": {},
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
