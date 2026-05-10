"""Single-fixture V3 prediction service."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

import pandas as pd  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.api.exceptions import ApiFootballClientError, ApiFootballRateLimitError
from football_predictor.db import models
from football_predictor.db.repositories import upsert_by_fields
from football_predictor.features.data_quality import DataQuality
from football_predictor.features.feature_builder import FeatureBuilderResult, build_feature_snapshot
from football_predictor.ingestion.fixtures import FixtureIngestionService, StandingIngestionService
from football_predictor.ingestion.ingest_match_details import FixtureDetailsIngestionService
from football_predictor.ingestion.ingest_odds import OddsIngestionService
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.modeling.v3.composite import FootballOutcomeV3Model
from football_predictor.modeling.v3.fusion import (
    api_probability_from_row,
    deterministic_v3_fusion,
    market_probability_from_row,
    v2_probability_from_row,
)
from football_predictor.prediction.confidence import confidence_label, confidence_score
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference
from football_predictor.reference.schemas import FixtureRef
from football_predictor.utils.exceptions import PredictionError, ReferenceLookupError
from football_predictor.utils.logging import get_logger
from football_predictor.utils.time import ensure_aware_utc, utc_now

JsonDict = dict[str, Any]
V3_FEATURE_VERSION = "v3.0"
DEFAULT_V3_MODEL_DIR = Path("data/models/v3")

RESULT_LABELS_FR = {
    "HOME": "Victoire domicile",
    "DRAW": "Match nul",
    "AWAY": "Victoire extérieur",
}

logger = get_logger(__name__)


class ApiFootballPayloadClient(Protocol):
    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> Any:
        ...


@dataclass(frozen=True)
class PredictionV3Output:
    """JSON-safe V3 prediction output for CLI, Discord and tests."""

    fixture_id: int
    match_label: str
    competition: str
    match_date: datetime | None
    prediction_time: datetime
    probabilities: ProbabilityTriple
    predicted_result: str
    confidence_label: str
    confidence_score: float
    model_version: str
    fusion_strategy: str
    draw_risk_probability: float | None = None
    home_no_draw_probability: float | None = None
    away_no_draw_probability: float | None = None
    v2_probabilities: ProbabilityTriple | None = None
    market_probabilities: ProbabilityTriple | None = None
    api_probabilities: ProbabilityTriple | None = None
    draw_risk_label: str = "non disponible"
    no_draw_winner_label: str = "non disponible"
    top_factors_draw_risk: list[JsonDict] = field(default_factory=list)
    top_factors_no_draw_winner: list[JsonDict] = field(default_factory=list)
    explanations: list[str] = field(default_factory=list)
    data_quality: DataQuality = field(default_factory=DataQuality)
    data_quality_json: JsonDict = field(default_factory=dict)
    key_absences_json: JsonDict = field(default_factory=dict)
    refresh_summary: JsonDict = field(default_factory=dict)
    feature_snapshot_id: int | None = None
    v3_feature_snapshot_id: int | None = None
    v3_model_prediction_id: int | None = None

    def to_dict(self) -> JsonDict:
        return {
            "fixture_id": self.fixture_id,
            "match_label": self.match_label,
            "competition": self.competition,
            "match_date": self.match_date.isoformat() if self.match_date else None,
            "prediction_time": self.prediction_time.isoformat(),
            "probabilities": _probability_payload(self.probabilities),
            "predicted_result": self.predicted_result,
            "predicted_label_fr": RESULT_LABELS_FR[self.predicted_result],
            "confidence_label": self.confidence_label,
            "confidence_score": self.confidence_score,
            "model_version": self.model_version,
            "fusion_strategy": self.fusion_strategy,
            "components": {
                "p_v3_draw_risk": self.draw_risk_probability,
                "p_v3_home_no_draw": self.home_no_draw_probability,
                "p_v3_away_no_draw": self.away_no_draw_probability,
                "v2": _optional_probability_payload(self.v2_probabilities),
                "market": _optional_probability_payload(self.market_probabilities),
                "api": _optional_probability_payload(self.api_probabilities),
            },
            "draw_risk_label": self.draw_risk_label,
            "no_draw_winner_label": self.no_draw_winner_label,
            "top_factors_draw_risk": self.top_factors_draw_risk,
            "top_factors_no_draw_winner": self.top_factors_no_draw_winner,
            "explanations": self.explanations,
            "data_quality": self.data_quality_json or self.data_quality.as_dict(),
            "key_absences_json": self.key_absences_json,
            "refresh_summary": self.refresh_summary,
            "feature_snapshot_id": self.feature_snapshot_id,
            "v3_feature_snapshot_id": self.v3_feature_snapshot_id,
            "v3_model_prediction_id": self.v3_model_prediction_id,
        }


class PredictionV3Service:
    """V3 point-in-time prediction service for one fixture."""

    def __init__(
        self,
        reference: ApiFootballReference,
        session: Session | None = None,
        *,
        players_reference: PlayersReference | None = None,
        market_1x2_bet_name: str = "Match Winner",
        market_1x2_bet_id: int | None = None,
    ) -> None:
        self.reference = reference
        self.players_reference = players_reference
        self.session = session
        self.market_1x2_bet_name = market_1x2_bet_name
        self.market_1x2_bet_id = market_1x2_bet_id

    def predict_fixture_v3(
        self,
        fixture_id: int,
        prediction_time: datetime | None = None,
        *,
        model_dir: Path | str | None = DEFAULT_V3_MODEL_DIR,
        v2_model_dir: Path | str | None = None,
        refresh_data: bool = False,
        save_raw: bool = False,
        api_client: ApiFootballPayloadClient | None = None,
    ) -> PredictionV3Output:
        """Predict one fixture with V3 M-30 features and persist V3 rows."""
        session = self._require_session()
        refresh_summary: JsonDict = {}
        if refresh_data:
            if api_client is None:
                raise PredictionError("refresh_data=True requires an API-Football client")
            refresh_summary = self._refresh_dynamic_data(
                fixture_id,
                api_client=api_client,
                save_raw=save_raw,
            )

        fixture = self._fixture_from_db_or_reference(fixture_id)
        cutoff = self._resolve_prediction_time(fixture, prediction_time)
        feature_result = build_feature_snapshot(
            session,
            fixture.fixture_id,
            cutoff,
            feature_version=V3_FEATURE_VERSION,
            players_reference=self.players_reference,
            api_reference=self.reference,
        )
        v3_feature_snapshot = self._save_v3_feature_snapshot(feature_result, cutoff)
        model = self._load_model(model_dir, v2_model_dir=v2_model_dir)
        frame = pd.DataFrame([dict(feature_result.features_json)])
        component_frame = model.predict_component_frame(frame)
        component_row = component_frame.iloc[0].to_dict()
        final_probability = self._final_probability(model, component_frame).normalized()
        component_probabilities = self._component_probabilities(component_row)
        data_quality = _data_quality_from_payload(feature_result.data_quality_json)
        score = confidence_score(final_probability, data_quality)
        top_draw = _top_factors(feature_result.features_json, "draw_risk")
        top_no_draw = _top_factors(feature_result.features_json, "ndw")
        output = PredictionV3Output(
            fixture_id=fixture.fixture_id,
            match_label=f"{fixture.home_team} vs {fixture.away_team}",
            competition=self._competition_name(fixture),
            match_date=fixture.date,
            prediction_time=cutoff,
            probabilities=final_probability,
            predicted_result=final_probability.predicted_result(),
            confidence_label=confidence_label(final_probability),
            confidence_score=score,
            model_version=str(getattr(model, "model_version", "v3.0-final")),
            fusion_strategy=_fusion_strategy(model),
            draw_risk_probability=_optional_float(component_row.get("p_v3_draw_risk")),
            home_no_draw_probability=_optional_float(component_row.get("p_v3_home_no_draw")),
            away_no_draw_probability=_optional_float(component_row.get("p_v3_away_no_draw")),
            v2_probabilities=component_probabilities["v2"],
            market_probabilities=component_probabilities["market"],
            api_probabilities=component_probabilities["api"],
            draw_risk_label=_draw_risk_label(component_row.get("p_v3_draw_risk")),
            no_draw_winner_label=_no_draw_winner_label(
                component_row.get("p_v3_home_no_draw")
            ),
            top_factors_draw_risk=top_draw,
            top_factors_no_draw_winner=top_no_draw,
            explanations=_explanation_lines(top_draw, top_no_draw),
            data_quality=data_quality,
            data_quality_json=feature_result.data_quality_json,
            key_absences_json=_key_absences_payload(feature_result.features_json),
            refresh_summary=refresh_summary,
            feature_snapshot_id=feature_result.snapshot.id,
            v3_feature_snapshot_id=v3_feature_snapshot.id,
        )
        record = self._save_v3_prediction(
            output,
            v3_feature_snapshot,
            component_versions=_component_versions(model),
        )
        return _output_with_prediction_id(output, record.id)

    def _require_session(self) -> Session:
        if self.session is None:
            raise PredictionError("PredictionV3Service requires a database session")
        return self.session

    def _resolve_prediction_time(
        self,
        fixture: FixtureRef,
        prediction_time: datetime | None,
    ) -> datetime:
        if prediction_time is not None:
            return ensure_aware_utc(prediction_time)
        now = ensure_aware_utc(utc_now())
        if fixture.date is None:
            return now
        kickoff_minus_30 = ensure_aware_utc(fixture.date) - timedelta(minutes=30)
        return max(now, kickoff_minus_30)

    def _refresh_dynamic_data(
        self,
        fixture_id: int,
        *,
        api_client: ApiFootballPayloadClient,
        save_raw: bool,
    ) -> JsonDict:
        session = self._require_session()
        summary: JsonDict = {"warnings": []}
        try:
            fixtures = FixtureIngestionService(session, api_client, save_raw=save_raw)
            summary["fixtures"] = fixtures.ingest_fixture_by_id(fixture_id).as_dict()
            session.flush()
            fixture = session.get(models.Fixture, fixture_id)
            if fixture is None:
                raise PredictionError(f"fixture_id={fixture_id} was not returned by refresh")

            details = FixtureDetailsIngestionService(
                session,
                api_client,
                reference=self.reference,
                players_reference=self.players_reference,
                save_raw=save_raw,
            )
            summary["details"] = details.ingest_fixture_details(
                fixture_id,
                save_raw=save_raw,
            ).as_dict()
            summary["lineups"] = details.ingest_fixture_lineups(fixture_id).as_dict()
            summary["api_prediction"] = details.ingest_api_prediction(fixture_id).as_dict()

            odds = OddsIngestionService(
                session,
                api_client,
                reference=self.reference,
                market_bet_name=self.market_1x2_bet_name,
                market_bet_id=self.market_1x2_bet_id,
                save_raw=save_raw,
            )
            summary["odds"] = odds.ingest_odds_for_fixture(fixture_id).as_dict()
            if fixture.league_id is not None and fixture.season is not None:
                standings = StandingIngestionService(session, api_client, save_raw=save_raw)
                summary["standings"] = standings.ingest_league_season(
                    fixture.league_id,
                    fixture.season,
                ).as_dict()
        except (ApiFootballRateLimitError, ApiFootballClientError):
            raise
        except Exception as exc:
            logger.warning(
                "Optional V3 prediction refresh failed fixture_id=%s error=%s",
                fixture_id,
                exc,
            )
            summary["warnings"].append(str(exc))
        return summary

    def _fixture_from_db_or_reference(self, fixture_id: int) -> FixtureRef:
        session = self._require_session()
        session.flush()
        fixture = session.get(models.Fixture, fixture_id)
        if fixture is not None:
            return _fixture_ref_from_model(fixture)
        try:
            fixture_ref = self.reference.validate_fixture_reference(fixture_id)
        except ReferenceLookupError as exc:
            raise PredictionError(
                f"fixture_id={fixture_id} is not present in DB or local reference"
            ) from exc
        self._upsert_reference_fixture(fixture_ref)
        session.flush()
        return fixture_ref

    def _upsert_reference_fixture(self, fixture: FixtureRef) -> None:
        session = self._require_session()
        league = self.reference.find_league_by_id(fixture.league_id, fixture.season)
        upsert_by_fields(
            session,
            models.League,
            {"league_id": league.league_id, "season": league.season},
            {
                "name": league.name,
                "country": league.country,
                "category": league.category,
                "payload_json": {**league.raw, "ingestion_source": "docs/reference"},
            },
        )
        for team_id, team_name in (
            (fixture.home_team_id, fixture.home_team),
            (fixture.away_team_id, fixture.away_team),
        ):
            try:
                team = self.reference.find_team_by_id(team_id, league_id=fixture.league_id)
                values = {
                    "name": team.name or team_name,
                    "country": team.country,
                    "venue_id": team.venue_id,
                    "payload_json": {**team.raw, "ingestion_source": "docs/reference"},
                }
            except ReferenceLookupError:
                values = {
                    "name": team_name,
                    "payload_json": {"ingestion_source": "docs/reference"},
                }
            upsert_by_fields(session, models.Team, {"team_id": team_id}, values)
        upsert_by_fields(
            session,
            models.Fixture,
            {"fixture_id": fixture.fixture_id},
            {
                "date": fixture.date,
                "league_id": fixture.league_id,
                "season": fixture.season,
                "status": fixture.status_short,
                "status_short": fixture.status_short,
                "home_team_id": fixture.home_team_id,
                "away_team_id": fixture.away_team_id,
                "home_team": fixture.home_team,
                "away_team": fixture.away_team,
                "payload_json": {**fixture.raw, "ingestion_source": "docs/reference"},
            },
        )

    def _save_v3_feature_snapshot(
        self,
        feature_result: FeatureBuilderResult,
        cutoff: datetime,
    ) -> models.V3FeatureSnapshot:
        session = self._require_session()
        official_lineup = bool(
            feature_result.data_quality_json.get("official_lineup_available_flag")
            or feature_result.features_json.get("official_lineup_available_flag")
        )
        snapshot = upsert_by_fields(
            session,
            models.V3FeatureSnapshot,
            {
                "fixture_id": feature_result.snapshot.fixture_id,
                "prediction_time": cutoff,
                "feature_version": V3_FEATURE_VERSION,
            },
            {
                "official_lineup_available_flag": official_lineup,
                "features_json": feature_result.features_json,
                "data_quality_json": feature_result.data_quality_json,
            },
        )
        session.flush()
        return snapshot

    def _load_model(
        self,
        model_dir: Path | str | None,
        *,
        v2_model_dir: Path | str | None,
    ) -> FootballOutcomeV3Model:
        if model_dir is None:
            raise PredictionError("V3 model_dir is required")
        path = Path(model_dir)
        required = (
            path / "draw_risk" / "model.joblib",
            path / "no_draw_winner" / "model.joblib",
        )
        missing = [str(item) for item in required if not item.exists()]
        if missing:
            raise PredictionError(f"V3 model artifacts not found: {missing}")
        try:
            return FootballOutcomeV3Model.load(
                path,
                v2_model_dir=Path(v2_model_dir) if v2_model_dir is not None else None,
            )
        except Exception as exc:
            raise PredictionError(f"Failed to load V3 model from {path}: {exc}") from exc

    def _final_probability(
        self,
        model: FootballOutcomeV3Model,
        component_frame: pd.DataFrame,
    ) -> ProbabilityTriple:
        row = component_frame.iloc[0]
        if model.stacker_model is not None:
            return model.stacker_model.predict_probability_triples(component_frame)[0]
        return deterministic_v3_fusion(
            draw_probability=float(row.get("p_v3_draw_risk", 1.0 / 3.0)),
            home_no_draw_probability=float(row.get("p_v3_home_no_draw", 0.5)),
            v2_probability=v2_probability_from_row(row),
            market_probability=market_probability_from_row(row),
        )

    def _component_probabilities(
        self,
        row: Mapping[str, Any],
    ) -> dict[str, ProbabilityTriple | None]:
        return {
            "v2": v2_probability_from_row(row),
            "market": market_probability_from_row(row),
            "api": api_probability_from_row(row),
        }

    def _competition_name(self, fixture: FixtureRef) -> str:
        session = self._require_session()
        league = session.execute(
            select(models.League)
            .where(
                models.League.league_id == fixture.league_id,
                models.League.season == fixture.season,
            )
            .limit(1)
        ).scalar_one_or_none()
        if league is not None:
            return league.name
        try:
            return self.reference.find_league_by_id(fixture.league_id, fixture.season).name
        except ReferenceLookupError:
            return f"League {fixture.league_id}"

    def _save_v3_prediction(
        self,
        output: PredictionV3Output,
        feature_snapshot: models.V3FeatureSnapshot,
        *,
        component_versions: JsonDict,
    ) -> models.V3ModelPrediction:
        session = self._require_session()
        record = models.V3ModelPrediction(
            fixture_id=output.fixture_id,
            v3_feature_snapshot_id=feature_snapshot.id,
            prediction_time=output.prediction_time,
            model_version=output.model_version,
            fusion_strategy=output.fusion_strategy,
            p_v3_final_home=output.probabilities.p_home,
            p_v3_final_draw=output.probabilities.p_draw,
            p_v3_final_away=output.probabilities.p_away,
            p_v3_draw_risk=output.draw_risk_probability,
            p_v3_home_no_draw=output.home_no_draw_probability,
            p_v3_away_no_draw=output.away_no_draw_probability,
            p_v2_home=_probability_value(output.v2_probabilities, "HOME"),
            p_v2_draw=_probability_value(output.v2_probabilities, "DRAW"),
            p_v2_away=_probability_value(output.v2_probabilities, "AWAY"),
            p_market_home=_probability_value(output.market_probabilities, "HOME"),
            p_market_draw=_probability_value(output.market_probabilities, "DRAW"),
            p_market_away=_probability_value(output.market_probabilities, "AWAY"),
            p_api_home=_probability_value(output.api_probabilities, "HOME"),
            p_api_draw=_probability_value(output.api_probabilities, "DRAW"),
            p_api_away=_probability_value(output.api_probabilities, "AWAY"),
            data_quality_score=_quality_score(output.data_quality_json),
            official_lineup_available_flag=_official_lineup_available(
                output.data_quality_json
            ),
            confidence_score=output.confidence_score,
            confidence_label=output.confidence_label,
            predicted_result=output.predicted_result,
            expert_probabilities_json={
                "draw_risk": output.draw_risk_probability,
                "home_no_draw": output.home_no_draw_probability,
                "away_no_draw": output.away_no_draw_probability,
                "v2": _optional_probability_payload(output.v2_probabilities),
                "market": _optional_probability_payload(output.market_probabilities),
                "api": _optional_probability_payload(output.api_probabilities),
            },
            explanations_json={
                "draw_risk_label": output.draw_risk_label,
                "no_draw_winner_label": output.no_draw_winner_label,
                "top_factors_draw_risk": output.top_factors_draw_risk,
                "top_factors_no_draw_winner": output.top_factors_no_draw_winner,
                "summary": output.explanations,
            },
            data_quality_json=output.data_quality_json,
            payload_json={
                "model_family": "v3",
                "match_label": output.match_label,
                "competition": output.competition,
                "match_date": output.match_date.isoformat() if output.match_date else None,
                "feature_snapshot_id": output.feature_snapshot_id,
                "v3_feature_snapshot_id": feature_snapshot.id,
                "component_versions": component_versions,
                "refresh_summary": output.refresh_summary,
                "key_absences_json": output.key_absences_json,
            },
        )
        session.add(record)
        session.flush()
        return record


def _fixture_ref_from_model(fixture: models.Fixture) -> FixtureRef:
    return FixtureRef(
        fixture_id=fixture.fixture_id,
        date=fixture.date,
        league_id=fixture.league_id,
        season=fixture.season,
        home_team_id=fixture.home_team_id,
        away_team_id=fixture.away_team_id,
        home_team=fixture.home_team,
        away_team=fixture.away_team,
        status_short=fixture.status_short,
        raw=fixture.payload_json if isinstance(fixture.payload_json, dict) else {},
    )


def _fusion_strategy(model: FootballOutcomeV3Model) -> str:
    stacker = model.stacker_model
    if stacker is not None and getattr(stacker, "estimator", None) is not None:
        return "stacker_lr"
    return "deterministic_fallback"


def _component_versions(model: FootballOutcomeV3Model) -> JsonDict:
    return {
        "final": getattr(model, "model_version", None),
        "draw_risk": getattr(model.draw_risk_model, "model_version", None),
        "no_draw_winner": getattr(model.no_draw_winner_model, "model_version", None),
        "stacker": getattr(model.stacker_model, "model_version", None)
        if model.stacker_model is not None
        else None,
        "v2_available": model.v2_model is not None,
    }


def _data_quality_from_payload(payload: Mapping[str, Any]) -> DataQuality:
    return DataQuality(
        odds_available=bool(payload.get("odds_available_flag") or payload.get("odds_available")),
        injuries_available=bool(
            payload.get("injuries_available_flag") or payload.get("injuries_available")
        ),
        official_lineups_available=bool(
            payload.get("official_lineup_available_flag")
            or payload.get("has_official_lineup")
            or payload.get("target_lineups_available_flag")
        ),
        player_stats_available=(
            float(
                payload.get(
                    "historical_player_stats_available_rate",
                    payload.get("player_stats_available_rate") or 0.0,
                )
                or 0.0
            )
            > 0
        ),
        standings_available=bool(payload.get("standings_available_flag")),
        api_prediction_available=bool(
            payload.get("api_prediction_available_flag")
            or payload.get("api_prediction_available")
        ),
    )


def _draw_risk_label(value: Any) -> str:
    probability = _optional_float(value)
    if probability is None:
        return "non disponible"
    if probability < 0.22:
        return "faible"
    if probability <= 0.32:
        return "moyen"
    return "élevé"


def _no_draw_winner_label(value: Any) -> str:
    probability = _optional_float(value)
    if probability is None:
        return "non disponible"
    if probability > 0.55:
        return "Home"
    if probability < 0.45:
        return "Away"
    return "équilibré"


def _top_factors(features: Mapping[str, Any], prefix: str) -> list[JsonDict]:
    candidates: list[tuple[str, float]] = []
    for key, value in features.items():
        if not str(key).startswith(prefix):
            continue
        numeric = _optional_float(value)
        if numeric is None:
            continue
        candidates.append((str(key), numeric))
    candidates.sort(key=lambda item: abs(item[1]), reverse=True)
    return [
        {"name": name, "value": value, "method": "heuristic_abs_value"}
        for name, value in candidates[:3]
    ]


def _explanation_lines(draw_factors: list[JsonDict], no_draw_factors: list[JsonDict]) -> list[str]:
    lines: list[str] = []
    if draw_factors:
        lines.append(f"Risque de nul porté par {draw_factors[0]['name']}")
    if no_draw_factors:
        lines.append(f"Avantage hors nul porté par {no_draw_factors[0]['name']}")
    return lines or ["Facteurs V3 insuffisants, fallback probabiliste utilisé"]


def _key_absences_payload(features: Mapping[str, Any]) -> JsonDict:
    return {
        "home": _list_payload(features.get("home_team_key_absences_json")),
        "away": _list_payload(features.get("away_team_key_absences_json")),
    }


def _list_payload(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _quality_score(payload: Mapping[str, Any]) -> float | None:
    value = payload.get("overall_data_quality_score", payload.get("data_quality_score"))
    return _optional_float(value)


def _official_lineup_available(payload: Mapping[str, Any]) -> bool:
    return bool(
        payload.get("official_lineup_available_flag")
        or payload.get("has_official_lineup")
        or payload.get("target_lineups_available_flag")
    )


def _probability_value(probability: ProbabilityTriple | None, label: str) -> float | None:
    if probability is None:
        return None
    return probability.as_dict()[label]


def _probability_payload(probability: ProbabilityTriple) -> dict[str, float]:
    normalized = probability.normalized()
    return {
        "HOME": normalized.p_home,
        "DRAW": normalized.p_draw,
        "AWAY": normalized.p_away,
    }


def _optional_probability_payload(probability: ProbabilityTriple | None) -> dict[str, float] | None:
    return None if probability is None else _probability_payload(probability)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric


def _output_with_prediction_id(
    output: PredictionV3Output,
    prediction_id: int,
) -> PredictionV3Output:
    return PredictionV3Output(
        fixture_id=output.fixture_id,
        match_label=output.match_label,
        competition=output.competition,
        match_date=output.match_date,
        prediction_time=output.prediction_time,
        probabilities=output.probabilities,
        predicted_result=output.predicted_result,
        confidence_label=output.confidence_label,
        confidence_score=output.confidence_score,
        model_version=output.model_version,
        fusion_strategy=output.fusion_strategy,
        draw_risk_probability=output.draw_risk_probability,
        home_no_draw_probability=output.home_no_draw_probability,
        away_no_draw_probability=output.away_no_draw_probability,
        v2_probabilities=output.v2_probabilities,
        market_probabilities=output.market_probabilities,
        api_probabilities=output.api_probabilities,
        draw_risk_label=output.draw_risk_label,
        no_draw_winner_label=output.no_draw_winner_label,
        top_factors_draw_risk=output.top_factors_draw_risk,
        top_factors_no_draw_winner=output.top_factors_no_draw_winner,
        explanations=output.explanations,
        data_quality=output.data_quality,
        data_quality_json=output.data_quality_json,
        key_absences_json=output.key_absences_json,
        refresh_summary=output.refresh_summary,
        feature_snapshot_id=output.feature_snapshot_id,
        v3_feature_snapshot_id=output.v3_feature_snapshot_id,
        v3_model_prediction_id=prediction_id,
    )
