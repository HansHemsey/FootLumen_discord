"""Point-in-time O/U 2.5 feature snapshot builder."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.db.repositories import upsert_by_fields
from football_predictor.features.data_quality import (
    count_quality_ratio,
    publication_quality_payload,
    source_quality_payload,
)
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
        exclude_fixture_id=fixture_id,
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

    base_quality = dict(base_feature_result.data_quality_json)
    source_quality = _publication_source_quality_ou(
        home_history_count=len(home_matches),
        away_history_count=len(away_matches),
        base_quality=base_quality,
        h2h_matches_available=int(h2h_features.get("h2h_matches_available") or 0),
        ou_consensus=ou_consensus,
        prediction_time=cutoff,
        market_features=market_features,
        fatigue_features=fatigue_features,
        shot_features=shot_features,
        corner_features=corner_features,
    )
    publication_quality = publication_quality_payload(source_quality)
    ou_quality_score = publication_quality["publication_data_quality_score"]
    data_quality: JsonDict = {
        **base_quality,
        "ou_odds_available": ou_consensus is not None,
        "ou_market_bookmaker_count": ou_consensus.bookmaker_count if ou_consensus else 0,
        "h2h_matches_available": h2h_features.get("h2h_matches_available", 0),
        "ou_feature_version": feature_version,
        "ou_data_quality_score": ou_quality_score,
        **publication_quality,
    }
    features["ou_data_quality_score"] = ou_quality_score
    features["publication_data_quality_score"] = ou_quality_score
    features["data_quality_version"] = data_quality["data_quality_version"]

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


def _publication_source_quality_ou(
    *,
    home_history_count: int,
    away_history_count: int,
    base_quality: JsonDict,
    h2h_matches_available: int,
    ou_consensus: Any,
    prediction_time: datetime,
    market_features: JsonDict,
    fatigue_features: JsonDict,
    shot_features: JsonDict,
    corner_features: JsonDict,
) -> dict[str, JsonDict]:
    min_history = min(home_history_count, away_history_count)
    shot_signal_count = sum(
        1
        for value in (
            shot_features.get("combined_shots_avg_last5"),
            shot_features.get("combined_shots_on_goal_avg_last5"),
            shot_features.get("combined_pseudo_xg_total_avg_last5"),
            corner_features.get("combined_corners_avg_last5"),
        )
        if value is not None
    )
    standings_available = bool(base_quality.get("standings_available"))
    context_count = sum(
        1
        for value in (
            fatigue_features.get("rest_days_diff"),
            fatigue_features.get("combined_matches_last_14_days"),
            standings_available,
        )
        if value is not None and value is not False
    )
    inherited_ratio = _inherited_lineups_injuries_ratio(base_quality)
    return {
        "ou_history": source_quality_payload(
            available=min_history > 0,
            checked=min_history > 0,
            count=min_history,
            weight=30,
            base_ratio=count_quality_ratio(min_history, full_count=10, partial_count=5),
        ),
        "ou_intensity_stats": source_quality_payload(
            available=shot_signal_count > 0,
            checked=shot_signal_count > 0,
            count=shot_signal_count,
            weight=15,
            base_ratio=min(shot_signal_count / 4, 1.0),
        ),
        "ou_odds": source_quality_payload(
            available=ou_consensus is not None,
            checked=ou_consensus is not None,
            count=int(market_features.get("market_ou_bookmaker_count") or 0),
            weight=30,
            prediction_time=prediction_time,
            latest_fetched_at=ou_consensus.latest_fetched_at if ou_consensus else None,
            fresh_minutes=6 * 60,
            partial_minutes=24 * 60,
        ),
        "ou_h2h": source_quality_payload(
            available=h2h_matches_available > 0,
            checked=h2h_matches_available > 0,
            count=h2h_matches_available,
            weight=10,
            base_ratio=count_quality_ratio(
                h2h_matches_available, full_count=3, partial_count=1
            ),
        ),
        "ou_context": source_quality_payload(
            available=context_count > 0,
            checked=context_count > 0,
            count=context_count,
            weight=10,
            base_ratio=min(context_count / 3, 1.0),
        ),
        "ou_inherited_lineups_injuries": source_quality_payload(
            available=inherited_ratio > 0,
            checked=inherited_ratio > 0,
            count=round(inherited_ratio * 4),
            weight=5,
            base_ratio=inherited_ratio,
        ),
    }


def _inherited_lineups_injuries_ratio(base_quality: JsonDict) -> float:
    lineups = (
        (1 if base_quality.get("target_lineups_home_available_flag") else 0)
        + (1 if base_quality.get("target_lineups_away_available_flag") else 0)
    ) / 2
    injuries = (
        1.0
        if base_quality.get("source_quality_json", {})
        .get("injuries", {})
        .get("checked")
        else 0.0
    )
    return (lineups + injuries) / 2


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
