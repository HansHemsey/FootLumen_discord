"""Single-fixture World Cup prediction service."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from football_predictor.config.settings import Settings
from football_predictor.db import models
from football_predictor.db.repositories import upsert_by_fields
from football_predictor.features.data_quality import DataQuality
from football_predictor.ingestion.fixtures import FixtureIngestionService
from football_predictor.ingestion.ingest_match_details import FixtureDetailsIngestionService
from football_predictor.ingestion.ingest_odds import OddsIngestionService
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.prediction.confidence import confidence_label
from football_predictor.prediction.draw_safety import (
    DrawSafetyConfig,
    DrawSafetySignals,
    evaluate_draw_safety,
)
from football_predictor.prediction.service import ApiFootballPayloadClient, PredictionOutput
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference
from football_predictor.utils.exceptions import PredictionError
from football_predictor.utils.logging import get_logger
from football_predictor.utils.time import ensure_aware_utc, utc_now
from football_predictor.worldcup.coverage_monitor import WorldCupCoverageMonitor
from football_predictor.worldcup.dynamic import (
    apply_dynamic_probability_features,
    build_worldcup_dynamic_features,
)
from football_predictor.worldcup.features import (
    build_features_for_fixture,
    data_quality_for_features,
)
from football_predictor.worldcup.model import (
    WorldCup1X2Model,
    fallback_probability_from_features,
    probability_source_from_features,
    worldcup_blend_weights,
)
from football_predictor.worldcup.references import WorldCupReferenceBundle

JsonDict = dict[str, Any]
WORLD_CUP_LEAGUE_ID = 1
WORLD_CUP_SEASON = 2026
WORLD_CUP_FEATURE_VERSION = "worldcup-1x2-v1"
logger = get_logger(__name__)


class WorldCupPredictionService:
    def __init__(
        self,
        session: Session,
        bundle: WorldCupReferenceBundle,
        *,
        model_dir: Path | str | None = None,
        reference: ApiFootballReference | None = None,
        players_reference: PlayersReference | None = None,
        market_1x2_bet_name: str = "Match Winner",
        market_1x2_bet_id: int | None = None,
        draw_safety_config: DrawSafetyConfig | None = None,
    ) -> None:
        self.session = session
        self.bundle = bundle
        self.model_dir = Path(model_dir) if model_dir is not None else None
        self.reference = reference
        self.players_reference = players_reference
        self.market_1x2_bet_name = market_1x2_bet_name
        self.market_1x2_bet_id = market_1x2_bet_id
        self.draw_safety_config = draw_safety_config or DrawSafetyConfig.from_settings(Settings())

    def predict_fixture(
        self,
        fixture_id: int,
        prediction_time: datetime | None = None,
        *,
        save_to_db: bool = True,
        refresh_data: bool = False,
        save_raw: bool = False,
        api_client: ApiFootballPayloadClient | None = None,
    ) -> PredictionOutput:
        refresh_summary: JsonDict = {}
        if refresh_data:
            if api_client is None:
                raise PredictionError("refresh_data=True requires an API-Football client")
            refresh_summary = self._refresh_dynamic_data(
                fixture_id,
                api_client=api_client,
                save_raw=save_raw,
            )
        fixture = self.session.get(models.Fixture, fixture_id)
        if fixture is None:
            raise PredictionError(f"fixture_id={fixture_id} not found in local DB")
        if fixture.league_id != WORLD_CUP_LEAGUE_ID or fixture.season != WORLD_CUP_SEASON:
            raise PredictionError(
                "predict-worldcup only accepts FIFA World Cup 2026 fixtures "
                f"(got league_id={fixture.league_id} season={fixture.season})"
            )
        cutoff = ensure_aware_utc(prediction_time or utc_now())
        prediction_date = cutoff.date()
        features = build_features_for_fixture(
            fixture.home_team,
            fixture.away_team,
            prediction_date,
            bundle=self.bundle,
            neutral=True,
        )
        features.update(
            build_worldcup_dynamic_features(
                self.session,
                fixture,
                cutoff,
                players_reference=self.players_reference,
            )
        )
        features.update(apply_dynamic_probability_features(features))
        data_quality = data_quality_for_features(features)
        fixture_quality = WorldCupCoverageMonitor(
            self.session,
            bundle=self.bundle,
        ).fixture_quality_matrix(fixture, now=cutoff)
        data_quality = _with_fixture_quality(data_quality, fixture_quality)
        model = self._load_model()
        blend_config = getattr(model, "blend_config", None) if model is not None else None
        if model is None:
            probabilities = fallback_probability_from_features(features, blend_config=blend_config)
            model_version = "worldcup-1x2-fallback"
            sources_used = ["wc_rating_dynamic", "wc_poisson_dynamic"]
        else:
            probabilities = ProbabilityTriple.from_vector(
                model.predict_proba(pd.DataFrame([features]))[0]
            )
            model_version = model.model_version
            sources_used = ["wc_model", "wc_rating_dynamic", "wc_poisson_dynamic"]
        market_probability = probability_source_from_features(features, "p_wc_market")
        api_probability = probability_source_from_features(features, "p_wc_api")
        if market_probability is not None:
            sources_used.append("wc_market")
        if api_probability is not None:
            sources_used.append("wc_api")
        rating_probability = (
            probability_source_from_features(features, "p_wc_rating_dynamic")
            or probability_source_from_features(features, "p_wc_rating")
        )
        poisson_probability = (
            probability_source_from_features(features, "p_wc_poisson_dynamic")
            or probability_source_from_features(features, "p_wc_poisson")
        )
        score = _confidence_score(probabilities, data_quality)
        raw_confidence_label = confidence_label(probabilities)
        draw_safety = evaluate_draw_safety(
            DrawSafetySignals(
                model_family="worldcup_1x2",
                p_home=probabilities.p_home,
                p_draw=probabilities.p_draw,
                p_away=probabilities.p_away,
                confidence_label=raw_confidence_label,
                confidence_score=score,
                source_draw_probability=_max_draw_probability(
                    rating_probability,
                    poisson_probability,
                    market_probability,
                    api_probability,
                ),
                market_draw_probability=_probability_value(market_probability, "DRAW"),
                is_worldcup=True,
            ),
            config=self.draw_safety_config,
        )
        explanations = _explanations(features)
        if fixture_quality.data_quality_score < 70:
            explanations.append(_coverage_explanation(fixture_quality.to_json_dict()))
        if draw_safety.public_note:
            explanations.append(draw_safety.public_note)
        effective_label = draw_safety.effective_confidence_label
        effective_score = (
            draw_safety.effective_confidence_score
            if draw_safety.effective_confidence_score is not None
            else score
        )
        effective_label, effective_score = _apply_fixture_quality_cap(
            effective_label,
            effective_score,
            fixture_quality.to_json_dict(),
        )
        output = PredictionOutput(
            fixture_id=fixture.fixture_id,
            match_label=f"{fixture.home_team} vs {fixture.away_team}",
            competition="FIFA World Cup 2026",
            match_date=fixture.date,
            prediction_time=cutoff,
            probabilities=probabilities,
            predicted_result=probabilities.predicted_result(),
            confidence_label=effective_label,
            confidence_score=effective_score,
            explanations=explanations,
            data_quality=DataQuality(standings_available=True),
            data_quality_json=data_quality,
            market_probabilities=market_probability,
            sport_probabilities=probabilities,
            poisson_probabilities=poisson_probability,
            api_probabilities=api_probability,
            stacking_weights=worldcup_blend_weights(
                has_model=model is not None,
                has_market=market_probability is not None,
                has_api=api_probability is not None,
                blend_config=blend_config,
            ),
            sources_used=sources_used,
            sport_source="worldcup_1x2",
            model_version=model_version,
            refresh_summary=refresh_summary,
            key_absences_json={
                "home": features.get("wc_home_key_absences_json") or [],
                "away": features.get("wc_away_key_absences_json") or [],
            },
            draw_safety_json=draw_safety.as_dict(),
            expert_probabilities={
                **({"wc_rating_dynamic": rating_probability} if rating_probability else {}),
                **({"wc_poisson_dynamic": poisson_probability} if poisson_probability else {}),
                **({"wc_market": market_probability} if market_probability else {}),
                **({"wc_api": api_probability} if api_probability else {}),
            },
        )
        if not save_to_db:
            return output
        snapshot = self._save_feature_snapshot(fixture.fixture_id, cutoff, features, data_quality)
        record = self._save_prediction(output, snapshot.id, features)
        return _with_ids(output, snapshot.id, record.id)

    def _load_model(self) -> WorldCup1X2Model | None:
        if self.model_dir is None:
            return None
        model_path = self.model_dir / "model.joblib" if self.model_dir.is_dir() else self.model_dir
        if not model_path.exists():
            return None
        return WorldCup1X2Model.load(model_path)

    def _refresh_dynamic_data(
        self,
        fixture_id: int,
        *,
        api_client: ApiFootballPayloadClient,
        save_raw: bool,
    ) -> JsonDict:
        if self.reference is None:
            raise PredictionError("World Cup refresh_data=True requires API reference")
        summary: JsonDict = {"warnings": []}
        try:
            fixtures = FixtureIngestionService(self.session, api_client, save_raw=save_raw)
            summary["fixtures"] = fixtures.ingest_fixture_by_id(fixture_id).as_dict()
            self.session.flush()
            fixture = self.session.get(models.Fixture, fixture_id)
            if fixture is None:
                raise PredictionError(f"fixture_id={fixture_id} was not returned by refresh")
            details = FixtureDetailsIngestionService(
                self.session,
                api_client,
                reference=self.reference,
                players_reference=self.players_reference,
                save_raw=save_raw,
            )
            summary["injuries"] = details.ingest_injuries_for_fixture(fixture_id).as_dict()
            summary["api_prediction"] = details.ingest_api_prediction(fixture_id).as_dict()
            summary["lineups"] = details.ingest_fixture_lineups(fixture_id).as_dict()
            odds = OddsIngestionService(
                self.session,
                api_client,
                reference=self.reference,
                market_bet_name=self.market_1x2_bet_name,
                market_bet_id=self.market_1x2_bet_id,
                save_raw=save_raw,
            )
            summary["odds"] = odds.ingest_odds_for_fixture(fixture_id).as_dict()
        except Exception as exc:
            logger.warning(
                "Optional World Cup dynamic refresh failed fixture_id=%s error=%s",
                fixture_id,
                exc,
            )
            summary["warnings"].append(str(exc))
        return summary

    def _save_feature_snapshot(
        self,
        fixture_id: int,
        prediction_time: datetime,
        features: JsonDict,
        data_quality: JsonDict,
    ) -> models.FeatureSnapshot:
        snapshot = upsert_by_fields(
            self.session,
            models.FeatureSnapshot,
            {
                "fixture_id": fixture_id,
                "prediction_time": prediction_time,
                "feature_version": WORLD_CUP_FEATURE_VERSION,
            },
            {
                "features_json": features,
                "data_quality_json": data_quality,
            },
        )
        self.session.flush()
        return snapshot

    def _save_prediction(
        self,
        output: PredictionOutput,
        feature_snapshot_id: int,
        features: JsonDict,
    ) -> models.ModelPrediction:
        record = models.ModelPrediction(
            fixture_id=output.fixture_id,
            feature_snapshot_id=feature_snapshot_id,
            prediction_time=output.prediction_time,
            model_version=output.model_version,
            p_home=output.probabilities.p_home,
            p_draw=output.probabilities.p_draw,
            p_away=output.probabilities.p_away,
            predicted_outcome=output.predicted_result,
            predicted_result=output.predicted_result,
            confidence=output.confidence_score,
            confidence_label=output.confidence_label,
            confidence_score=output.confidence_score,
            explanation_json=output.explanations,
            explanations_json=output.explanations,
            data_quality_json=output.data_quality_json,
            payload_json={
                "model_family": "worldcup_1x2",
                "match_label": output.match_label,
                "competition": output.competition,
                "sources_used": output.sources_used,
                "features_summary": _features_summary(features),
                "dynamic_sources": {
                    "market": bool(features.get("wc_dynamic_market_available_flag")),
                    "api_prediction": bool(
                        features.get("wc_dynamic_api_prediction_available_flag")
                    ),
                    "lineups": bool(features.get("wc_dynamic_lineups_available_flag")),
                    "injuries": bool(features.get("wc_dynamic_injuries_available_flag")),
                },
                "draw_safety": output.draw_safety_json,
                "worldcup_fixture_quality": output.data_quality_json.get(
                    "worldcup_fixture_quality"
                ),
            },
        )
        self.session.add(record)
        self.session.flush()
        return record


def _confidence_score(probabilities: ProbabilityTriple, data_quality: JsonDict) -> float:
    edge = probabilities.max_probability() - (1 / 3)
    quality = float(data_quality.get("overall_data_quality_score") or 0.0)
    return round(max(0.0, min(100.0, (edge * 140) + ((quality / 100.0) * 35))), 1)


def _with_fixture_quality(
    data_quality: JsonDict,
    fixture_quality: Any,
) -> JsonDict:
    payload = dict(data_quality)
    quality_payload = fixture_quality.to_json_dict()
    score = float(quality_payload.get("data_quality_score") or 0.0)
    current_score = float(payload.get("overall_data_quality_score") or score)
    adjusted_score = min(current_score, score)
    payload["overall_data_quality_score"] = adjusted_score
    payload["data_quality_score"] = min(
        float(payload.get("data_quality_score") or adjusted_score),
        score,
    )
    payload["label"] = (
        "High" if adjusted_score >= 75 else "Medium" if adjusted_score >= 50 else "Low"
    )
    payload["worldcup_fixture_quality_score"] = score
    payload["worldcup_fixture_quality"] = quality_payload
    warnings = list(payload.get("warnings") or [])
    warnings.extend(quality_payload.get("warnings") or [])
    payload["warnings"] = sorted(set(str(warning) for warning in warnings))
    return payload


def _coverage_explanation(fixture_quality: JsonDict) -> str:
    missing = fixture_quality.get("missing_sources") or []
    if missing:
        return "Qualité données CDM: sources manquantes " + ", ".join(missing[:4]) + "."
    return "Qualité données CDM: couverture partielle."


def _apply_fixture_quality_cap(
    confidence: str,
    score: float,
    fixture_quality: JsonDict,
) -> tuple[str, float]:
    quality_score = float(fixture_quality.get("data_quality_score") or 0.0)
    warnings = set(fixture_quality.get("warnings") or [])
    if quality_score < 55.0 or "lineups_expected_missing" in warnings:
        return _lower_confidence_label(confidence, "Low"), min(score, 54.0)
    if quality_score < 70.0 or "odds_1x2_missing" in warnings:
        return _lower_confidence_label(confidence, "Medium"), min(score, 67.0)
    return confidence, score


def _lower_confidence_label(current: str, cap: str) -> str:
    rank = {
        "Uncertain": 0,
        "Low": 1,
        "Medium": 2,
        "High": 3,
        "Very High": 4,
    }
    return current if rank.get(current, 0) <= rank.get(cap, 0) else cap


def _explanations(features: JsonDict) -> list[str]:
    elo_diff = float(features.get("wc_internal_elo_diff") or 0)
    ppg_diff = float(features.get("wc_diff_last10_ppg") or 0)
    home_goals = float(features.get("wc_expected_home_goals") or 0)
    away_goals = float(features.get("wc_expected_away_goals") or 0)
    return [
        f"Rating international: écart Elo interne {elo_diff:+.0f}.",
        f"Forme récente: diff PPG last10 {ppg_diff:+.2f}.",
        f"Buts attendus: {home_goals:.2f} - {away_goals:.2f}.",
    ]


def _features_summary(features: JsonDict) -> JsonDict:
    keys = (
        "wc_home_history_count",
        "wc_away_history_count",
        "wc_internal_elo_diff",
        "wc_expected_home_goals",
        "wc_expected_away_goals",
        "wc_expected_home_goals_dynamic",
        "wc_expected_away_goals_dynamic",
        "wc_fifa_rank_diff",
        "wc_current_elo_diff",
        "wc_dynamic_source_count",
        "wc_home_dynamic_penalty",
        "wc_away_dynamic_penalty",
    )
    return {key: features.get(key) for key in keys if key in features}


def _with_ids(
    output: PredictionOutput,
    feature_snapshot_id: int,
    model_prediction_id: int,
) -> PredictionOutput:
    return PredictionOutput(
        fixture_id=output.fixture_id,
        match_label=output.match_label,
        competition=output.competition,
        match_date=output.match_date,
        prediction_time=output.prediction_time,
        probabilities=output.probabilities,
        predicted_result=output.predicted_result,
        confidence_label=output.confidence_label,
        confidence_score=output.confidence_score,
        explanations=output.explanations,
        data_quality=output.data_quality,
        data_quality_json=output.data_quality_json,
        market_probabilities=output.market_probabilities,
        sport_probabilities=output.sport_probabilities,
        poisson_probabilities=output.poisson_probabilities,
        api_probabilities=output.api_probabilities,
        stacking_weights=output.stacking_weights,
        sources_used=output.sources_used,
        sport_source=output.sport_source,
        model_version=output.model_version,
        feature_snapshot_id=feature_snapshot_id,
        model_prediction_id=model_prediction_id,
        refresh_summary=output.refresh_summary,
        key_absences_json=output.key_absences_json,
        expert_probabilities=output.expert_probabilities,
        draw_safety_json=output.draw_safety_json,
    )


def _max_draw_probability(*probabilities: ProbabilityTriple | None) -> float | None:
    values = [
        probability.as_dict()["DRAW"]
        for probability in probabilities
        if probability is not None
    ]
    return max(values) if values else None


def _probability_value(probability: ProbabilityTriple | None, label: str) -> float | None:
    if probability is None:
        return None
    return probability.as_dict()[label]
