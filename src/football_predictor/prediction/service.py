"""Fixture-level prediction pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

import joblib  # type: ignore[import-untyped]
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
from football_predictor.modeling.baselines import api_prediction_probability
from football_predictor.modeling.poisson import poisson_predict
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.modeling.stacking import stack_probabilities_with_details
from football_predictor.prediction.confidence import confidence_label
from football_predictor.prediction.explain import explain_prediction
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference
from football_predictor.reference.schemas import FixtureRef
from football_predictor.utils.exceptions import PredictionError, ReferenceLookupError
from football_predictor.utils.logging import get_logger
from football_predictor.utils.time import ensure_aware_utc, utc_now

RESULT_LABELS_FR = {
    "HOME": "Victoire domicile",
    "DRAW": "Match nul",
    "AWAY": "Victoire exterieur",
}

JsonDict = dict[str, Any]

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
class PredictionRequest:
    fixture_id: int
    prediction_time: datetime | None = None
    model_dir: Path | None = None
    refresh_data: bool = False
    save_raw: bool = False


@dataclass(frozen=True)
class PredictionOutput:
    fixture_id: int
    match_label: str
    competition: str
    match_date: datetime | None
    prediction_time: datetime
    probabilities: ProbabilityTriple
    predicted_result: str
    confidence_label: str
    confidence_score: float
    explanations: list[str]
    data_quality: DataQuality
    data_quality_json: JsonDict = field(default_factory=dict)
    market_probabilities: ProbabilityTriple | None = None
    sport_probabilities: ProbabilityTriple | None = None
    poisson_probabilities: ProbabilityTriple | None = None
    api_probabilities: ProbabilityTriple | None = None
    stacking_weights: dict[str, float] = field(default_factory=dict)
    sources_used: list[str] = field(default_factory=list)
    sport_source: str | None = None
    model_version: str = "v1-fallback"
    feature_snapshot_id: int | None = None
    model_prediction_id: int | None = None
    refresh_summary: JsonDict = field(default_factory=dict)
    key_absences_json: JsonDict = field(default_factory=dict)
    expert_probabilities: dict[str, ProbabilityTriple] = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        """Return a JSON-serializable prediction payload."""
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
            "explanations": self.explanations,
            "data_quality": self.data_quality_json or self.data_quality.as_dict(),
            "sources": {
                "used": self.sources_used,
                "sport_source": self.sport_source,
                "stacking_weights": self.stacking_weights,
                "sport": _optional_probability_payload(self.sport_probabilities),
                "poisson": _optional_probability_payload(self.poisson_probabilities),
                "market": _optional_probability_payload(self.market_probabilities),
                "api": _optional_probability_payload(self.api_probabilities),
                "experts": {
                    name: _optional_probability_payload(probability)
                    for name, probability in self.expert_probabilities.items()
                },
            },
            "model_version": self.model_version,
            "feature_snapshot_id": self.feature_snapshot_id,
            "model_prediction_id": self.model_prediction_id,
            "refresh_summary": self.refresh_summary,
            "key_absences_json": self.key_absences_json,
        }


@dataclass(frozen=True)
class ProbabilitySources:
    sport: ProbabilityTriple
    market: ProbabilityTriple | None
    api: ProbabilityTriple | None
    poisson: ProbabilityTriple
    sport_source: str
    final: ProbabilityTriple | None = None
    expert_probabilities: dict[str, ProbabilityTriple] = field(default_factory=dict)


class PredictionService:
    """Robust single-fixture prediction service with honest fallbacks."""

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

    def predict_fixture(
        self,
        fixture_id: int,
        prediction_time: datetime | None = None,
        *,
        model_dir: Path | str | None = None,
        refresh_data: bool = False,
        save_raw: bool = False,
        api_client: ApiFootballPayloadClient | None = None,
        market_probabilities: ProbabilityTriple | None = None,
    ) -> PredictionOutput:
        """Predict one fixture using point-in-time features and optional live refresh."""
        session = self._require_session()
        cutoff = ensure_aware_utc(prediction_time) if prediction_time is not None else None
        refresh_summary: JsonDict = {}
        if refresh_data:
            if api_client is None:
                raise PredictionError("refresh_data=True requires an API-Football client")
            refresh_summary = self._refresh_dynamic_data(
                fixture_id,
                api_client=api_client,
                save_raw=save_raw,
            )
        if cutoff is None:
            cutoff = ensure_aware_utc(utc_now())

        fixture = self._fixture_from_db_or_reference(fixture_id)
        feature_result = build_feature_snapshot(
            session,
            fixture.fixture_id,
            cutoff,
            feature_version="v1",
            players_reference=self.players_reference,
            api_reference=self.reference,
        )
        model = self._load_model(Path(model_dir) if model_dir is not None else None)
        sources = self._probability_sources(
            feature_result.features_json,
            model=model,
            market_override=market_probabilities,
        )
        if sources.final is not None:
            probabilities = sources.final.normalized()
            stacking_weights = {"v2_composite": 1.0}
            sources_used = [sources.sport_source]
        else:
            stacking = stack_probabilities_with_details(
                sport=sources.sport,
                market=sources.market,
                api=sources.api,
            )
            probabilities = stacking.probabilities.normalized()
            stacking_weights = stacking.normalized_weights
            sources_used = stacking.sources_used
        data_quality = _data_quality_from_payload(feature_result.data_quality_json)
        score = _confidence_score_from_quality(probabilities, feature_result.data_quality_json)
        explanations = explain_prediction(
            features=feature_result.features_json,
            probabilities=probabilities,
            data_quality=feature_result.data_quality_json,
            sport_source=sources.sport_source,
            sources_used=sources_used,
            home_team_name=fixture.home_team,
            away_team_name=fixture.away_team,
        )
        output = PredictionOutput(
            fixture_id=fixture.fixture_id,
            match_label=f"{fixture.home_team} vs {fixture.away_team}",
            competition=self._competition_name(fixture),
            match_date=fixture.date,
            prediction_time=cutoff,
            probabilities=probabilities,
            predicted_result=probabilities.predicted_result(),
            confidence_label=confidence_label(probabilities),
            confidence_score=score,
            explanations=explanations,
            data_quality=data_quality,
            data_quality_json=feature_result.data_quality_json,
            market_probabilities=sources.market,
            sport_probabilities=sources.sport,
            poisson_probabilities=sources.poisson,
            api_probabilities=sources.api,
            stacking_weights=stacking_weights,
            sources_used=sources_used,
            sport_source=sources.sport_source,
            model_version=_model_version(model, fallback_source=sources.sport_source),
            feature_snapshot_id=feature_result.snapshot.id,
            refresh_summary=refresh_summary,
            key_absences_json=_key_absences_payload(feature_result.features_json),
            expert_probabilities=sources.expert_probabilities,
        )
        record = self._save_prediction(output, feature_result)
        return _output_with_model_prediction_id(output, record.id)

    def _require_session(self) -> Session:
        if self.session is None:
            raise PredictionError("PredictionService requires a database session")
        return self.session

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
                raise PredictionError(f"fixture_id={fixture_id} was not returned by live refresh")

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
                "Optional prediction refresh failed fixture_id=%s error=%s",
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

    def _load_model(self, model_dir: Path | None) -> Any | None:
        if model_dir is None:
            return None
        model_path = model_dir / "model.joblib" if model_dir.is_dir() else model_dir
        if not model_path.exists():
            logger.info("No model artifact found at %s; using prediction fallbacks", model_path)
            return None
        model = joblib.load(model_path)
        if not hasattr(model, "predict_proba"):
            raise PredictionError(f"Model artifact has no predict_proba: {model_path}")
        return model

    def _probability_sources(
        self,
        features: Mapping[str, Any],
        *,
        model: Any | None,
        market_override: ProbabilityTriple | None,
    ) -> ProbabilitySources:
        poisson = ProbabilityTriple.from_vector(poisson_predict(features))
        sport_source = "poisson"
        sport = poisson
        expert_probabilities: dict[str, ProbabilityTriple] = {}
        final: ProbabilityTriple | None = None
        if model is not None and getattr(model, "is_v2_composite", False):
            final = ProbabilityTriple.from_vector(
                model.predict_proba(pd.DataFrame([dict(features)]))[0]
            )
            expert_rows = (
                model.predict_expert_probabilities(pd.DataFrame([dict(features)]))
                if hasattr(model, "predict_expert_probabilities")
                else []
            )
            if expert_rows:
                expert_probabilities = {
                    name: ProbabilityTriple.from_vector(values)
                    for name, values in expert_rows[0].items()
                }
            sport = final
            sport_source = "model_v2"
        elif model is not None:
            sport = ProbabilityTriple.from_vector(
                model.predict_proba(pd.DataFrame([dict(features)]))[0]
            )
            sport_source = "model"
        market = market_override or _triple_from_feature_keys(
            features,
            ("market_home", "market_draw", "market_away"),
        )
        api = api_prediction_probability(features)
        return ProbabilitySources(
            sport=sport,
            market=market,
            api=api,
            poisson=poisson,
            sport_source=sport_source,
            final=final,
            expert_probabilities=expert_probabilities,
        )

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

    def _save_prediction(
        self,
        output: PredictionOutput,
        feature_result: FeatureBuilderResult,
    ) -> models.ModelPrediction:
        session = self._require_session()
        record = models.ModelPrediction(
            fixture_id=output.fixture_id,
            feature_snapshot_id=feature_result.snapshot.id,
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
                "match_label": output.match_label,
                "competition": output.competition,
                "match_date": output.match_date.isoformat() if output.match_date else None,
                "sources_used": output.sources_used,
                "stacking_weights": output.stacking_weights,
                "sport_source": output.sport_source,
                "refresh_summary": output.refresh_summary,
                "expert_probabilities": {
                    name: _probability_payload(probability)
                    for name, probability in output.expert_probabilities.items()
                },
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


def _triple_from_feature_keys(
    row: Mapping[str, Any],
    keys: tuple[str, str, str],
) -> ProbabilityTriple | None:
    values: list[float] = []
    for key in keys:
        value = row.get(key)
        if value is None:
            return None
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            return None
    try:
        return ProbabilityTriple.from_vector(values)
    except ValueError:
        return None


def _data_quality_from_payload(payload: Mapping[str, Any]) -> DataQuality:
    return DataQuality(
        odds_available=bool(payload.get("odds_available_flag")),
        injuries_available=bool(payload.get("injuries_available_flag")),
        official_lineups_available=bool(
            payload.get("target_lineups_available_flag")
            if "target_lineups_available_flag" in payload
            else payload.get("lineups_available_flag")
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
        api_prediction_available=bool(payload.get("api_prediction_available_flag")),
    )


def _confidence_score_from_quality(
    probabilities: ProbabilityTriple,
    data_quality: Mapping[str, Any],
) -> float:
    edge = probabilities.max_probability() - (1 / 3)
    quality = float(data_quality.get("overall_data_quality_score") or 0.0)
    return round(max(0.0, min(100.0, (edge * 140) + ((quality / 100) * 35))), 1)


def _model_version(model: Any | None, *, fallback_source: str) -> str:
    if model is not None:
        return str(getattr(model, "model_version", "unknown-model"))
    return f"v1-fallback-{fallback_source}"


def _probability_payload(probability: ProbabilityTriple) -> dict[str, float]:
    normalized = probability.normalized()
    return {
        "HOME": normalized.p_home,
        "DRAW": normalized.p_draw,
        "AWAY": normalized.p_away,
    }


def _optional_probability_payload(probability: ProbabilityTriple | None) -> dict[str, float] | None:
    return None if probability is None else _probability_payload(probability)


def _output_with_model_prediction_id(
    output: PredictionOutput,
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
        feature_snapshot_id=output.feature_snapshot_id,
        model_prediction_id=model_prediction_id,
        refresh_summary=output.refresh_summary,
        key_absences_json=output.key_absences_json,
        expert_probabilities=output.expert_probabilities,
    )


def _key_absences_payload(features: Mapping[str, Any]) -> JsonDict:
    return {
        "home": _list_payload(features.get("home_team_key_absences_json")),
        "away": _list_payload(features.get("away_team_key_absences_json")),
    }


def _list_payload(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []
