"""Point-in-time training dataset construction."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pandas as pd  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.features.global_features import (
    GlobalFeatureConfig,
    build_feature_snapshot,
)
from football_predictor.reference.lookups import PlayersReference
from football_predictor.utils.time import ensure_aware_utc

FINISHED_STATUSES = {"FT", "AET", "PEN"}
JsonDict = dict[str, Any]


def build_training_dataset(
    session: Session,
    league_ids: Sequence[int],
    seasons: Sequence[int],
    prediction_offset: timedelta = timedelta(hours=24),
    output_path: Path | None = None,
    output_format: str | None = None,
    players_reference: PlayersReference | None = None,
    *,
    limit: int | None = None,
    min_quality: int = 0,
    config: GlobalFeatureConfig | None = None,
) -> pd.DataFrame:
    """Build a historical point-in-time dataset for model training."""
    session.flush()
    fixtures = _training_fixtures(session, league_ids, seasons, limit=limit)
    rows: list[JsonDict] = []
    for fixture in fixtures:
        if fixture.date is None:
            continue
        prediction_time = ensure_aware_utc(fixture.date) - prediction_offset
        snapshot = build_feature_snapshot(
            session,
            fixture.fixture_id,
            prediction_time,
            players_reference=players_reference,
            config=config,
        )
        quality_payload = (
            snapshot.data_quality_json if isinstance(snapshot.data_quality_json, dict) else {}
        )
        features_payload = (
            snapshot.features_json if isinstance(snapshot.features_json, dict) else {}
        )
        quality_score = int(quality_payload.get("data_quality_score") or 0)
        if quality_score < min_quality:
            continue
        feature_row = _flatten_for_dataframe(cast(JsonDict, features_payload))
        feature_row.update(
            {
                "fixture_id": fixture.fixture_id,
                "feature_snapshot_id": snapshot.id,
                "fixture_date": ensure_aware_utc(fixture.date).isoformat(),
                "prediction_time": prediction_time.isoformat(),
                "target": _target_for_fixture(fixture),
                "home_goals": fixture.home_goals,
                "away_goals": fixture.away_goals,
                "data_quality_score": quality_score,
            }
        )
        rows.append(feature_row)
    frame = pd.DataFrame(rows)
    if output_path is not None:
        export_dataset(frame, output_path, output_format=output_format)
    return frame


def parse_prediction_window(value: str) -> timedelta:
    normalized = value.strip().casefold()
    if normalized == "24h":
        return timedelta(hours=24)
    if normalized == "6h":
        return timedelta(hours=6)
    if normalized == "40m":
        return timedelta(minutes=40)
    raise ValueError("prediction_window must be one of: 24h, 6h, 40m")


def export_dataset(
    frame: pd.DataFrame,
    output_path: Path,
    *,
    output_format: str | None = None,
) -> None:
    resolved_format = (output_format or output_path.suffix.lstrip(".")).casefold()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if resolved_format == "csv":
        frame.to_csv(output_path, index=False)
        return
    if resolved_format == "parquet":
        frame.to_parquet(output_path, index=False, engine="pyarrow")
        return
    raise ValueError("output_format must be csv or parquet")


def _training_fixtures(
    session: Session,
    league_ids: Sequence[int],
    seasons: Sequence[int],
    *,
    limit: int | None,
) -> list[models.Fixture]:
    stmt = (
        select(models.Fixture)
        .where(
            models.Fixture.league_id.in_(list(league_ids)),
            models.Fixture.season.in_(list(seasons)),
            models.Fixture.status_short.in_(FINISHED_STATUSES),
            models.Fixture.home_goals.is_not(None),
            models.Fixture.away_goals.is_not(None),
            models.Fixture.date.is_not(None),
        )
        .order_by(models.Fixture.date.asc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(session.execute(stmt).scalars())


def _target_for_fixture(fixture: models.Fixture) -> str:
    if fixture.home_goals is None or fixture.away_goals is None:
        raise ValueError(f"Fixture {fixture.fixture_id} has no final score")
    if fixture.home_goals > fixture.away_goals:
        return "HOME"
    if fixture.home_goals < fixture.away_goals:
        return "AWAY"
    return "DRAW"


def _flatten_for_dataframe(payload: JsonDict) -> JsonDict:
    flattened: JsonDict = {}
    for key, value in payload.items():
        if key in {"target", "home_goals", "away_goals"}:
            continue
        if isinstance(value, dict | list):
            flattened[key] = json.dumps(value, sort_keys=True)
        elif isinstance(value, datetime):
            flattened[key] = value.isoformat()
        else:
            flattened[key] = value
    return flattened
