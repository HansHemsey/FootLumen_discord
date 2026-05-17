"""Point-in-time O/U 2.5 feature snapshot builder."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.db.repositories import upsert_by_fields
from football_predictor.features.feature_builder import (
    FeatureBuilderResult,
    build_feature_snapshot,
)
from football_predictor.features.team_features import get_historical_matches_for_team
from football_predictor.ou_model.constants import FEATURE_VERSION, LEAKAGE_FIELDS, OU_THRESHOLD
from football_predictor.ou_model.features.corner_features import build_combined_corner_features
from football_predictor.ou_model.features.fatigue_features import build_fatigue_features
from football_predictor.ou_model.features.goals_pace_features import (
    build_combined_goals_features,
    build_goals_pace_features,
)
from football_predictor.ou_model.features.h2h_features import build_h2h_features
from football_predictor.ou_model.features.ou_odds_features import (
    compute_ou_market_consensus,
    compute_ou_odds_movement,
    ou_market_features_dict,
)
from football_predictor.ou_model.features.shot_intensity_features import (
    build_combined_shot_features,
)
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference
from football_predictor.utils.exceptions import DataQualityError
from football_predictor.utils.time import ensure_aware_utc

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class OUFeatureBuilderResult:
    snapshot: models.OUFeatureSnapshot
    features_json: JsonDict
    data_quality_json: JsonDict


def build_ou_feature_snapshot(
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
    ou_bet_id: int,
    feature_version: str = FEATURE_VERSION,
    threshold: float = OU_THRESHOLD,
    *,
    base_feature_result: FeatureBuilderResult | None = None,
    players_reference: PlayersReference | None = None,
    api_reference: ApiFootballReference | None = None,
) -> OUFeatureBuilderResult:
    """Build, store and return a complete O/U point-in-time feature snapshot.

    If base_feature_result is provided (from a prior 1X2 build_feature_snapshot call),
    it is reused to avoid duplicate DB queries.
    """
    session.flush()
    cutoff = ensure_aware_utc(prediction_time)
    fixture = session.get(models.Fixture, fixture_id)
    if fixture is None:
        raise DataQualityError(f"Unknown fixture_id={fixture_id}")

    if base_feature_result is None:
        base_feature_result = build_feature_snapshot(
            session,
            fixture_id,
            cutoff,
            players_reference=players_reference,
            api_reference=api_reference,
        )
    base_features = base_feature_result.features_json

    home_team_id = fixture.home_team_id
    away_team_id = fixture.away_team_id

    home_matches = get_historical_matches_for_team(session, fixture_id, home_team_id, cutoff)
    away_matches = get_historical_matches_for_team(session, fixture_id, away_team_id, cutoff)

    home_home = [m for m in home_matches if m.side == "home"]
    home_away = [m for m in home_matches if m.side == "away"]
    away_home = [m for m in away_matches if m.side == "home"]
    away_away = [m for m in away_matches if m.side == "away"]

    home_goals_features = build_goals_pace_features(
        "home_team",
        home_matches,
        home_matches=home_home,
        away_matches=home_away,
    )
    away_goals_features = build_goals_pace_features(
        "away_team",
        away_matches,
        home_matches=away_home,
        away_matches=away_away,
    )
    combined_goals = build_combined_goals_features(home_goals_features, away_goals_features)
    shot_features = build_combined_shot_features(base_features)
    corner_features = build_combined_corner_features(base_features)
    fatigue_features = build_fatigue_features(base_features)
    h2h_features = build_h2h_features(
        session,
        home_team_id,
        away_team_id,
        cutoff,
        league_id=fixture.league_id,
    )

    ou_consensus = compute_ou_market_consensus(session, fixture_id, ou_bet_id, cutoff)
    ou_movement = compute_ou_odds_movement(session, fixture_id, ou_bet_id, cutoff)
    market_features = ou_market_features_dict(ou_consensus, ou_movement)

    features: JsonDict = {
        **base_features,
        **home_goals_features,
        **away_goals_features,
        **combined_goals,
        **shot_features,
        **corner_features,
        **fatigue_features,
        **h2h_features,
        **market_features,
        "ou_feature_version": feature_version,
        "ou_threshold": threshold,
    }
    _remove_ou_leakage_fields(features)

    ou_odds_available = ou_consensus is not None
    data_quality: JsonDict = {
        **base_feature_result.data_quality_json,
        "ou_odds_available": ou_odds_available,
        "ou_market_bookmaker_count": ou_consensus.bookmaker_count if ou_consensus else 0,
        "h2h_matches_available": h2h_features.get("h2h_matches_available", 0),
        "ou_feature_version": feature_version,
    }
    features["ou_data_quality_score"] = _ou_quality_score(data_quality, ou_odds_available)

    snapshot = upsert_by_fields(
        session,
        models.OUFeatureSnapshot,
        {
            "fixture_id": fixture_id,
            "prediction_time": cutoff,
            "feature_version": feature_version,
            "threshold": threshold,
        },
        {
            "features_json": features,
            "data_quality_json": data_quality,
        },
    )
    session.flush()
    return OUFeatureBuilderResult(
        snapshot=snapshot,
        features_json=features,
        data_quality_json=data_quality,
    )


def _remove_ou_leakage_fields(features: JsonDict) -> None:
    for key in LEAKAGE_FIELDS:
        features.pop(key, None)


def _ou_quality_score(data_quality: JsonDict, ou_odds_available: bool) -> float:
    score = 0.0
    home_history = int(data_quality.get("home_team_history_count") or 0)
    away_history = int(data_quality.get("away_team_history_count") or 0)
    score += min(home_history / 10, 1.0) * 30
    score += min(away_history / 10, 1.0) * 30
    if ou_odds_available:
        score += 30
    if int(data_quality.get("h2h_matches_available") or 0) >= 3:
        score += 10
    return round(score, 1)
