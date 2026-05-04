"""Public Sprint 10 dataset builder API."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.features.feature_builder import build_feature_snapshot
from football_predictor.reference.lookups import PlayersReference
from football_predictor.utils.time import ensure_aware_utc

JsonDict = dict[str, Any]
FINISHED_STATUSES = {"FT", "AET", "PEN"}


def build_training_dataset(
    session: Session,
    league_ids: list[int],
    seasons: list[int],
    prediction_offset_hours: int = 24,
    save_path: Path | None = None,
    players_reference: PlayersReference | None = None,
    *,
    limit: int | None = None,
    feature_version: str = "v1",
) -> pd.DataFrame:
    """Build a point-in-time training dataset from local DB snapshots."""
    session.flush()
    rows: list[JsonDict] = []
    offset = timedelta(hours=prediction_offset_hours)
    for fixture in _finished_fixtures(session, league_ids, seasons, limit=limit):
        if fixture.date is None:
            continue
        prediction_time = ensure_aware_utc(fixture.date) - offset
        result = build_feature_snapshot(
            session,
            fixture.fixture_id,
            prediction_time,
            feature_version=feature_version,
            players_reference=players_reference,
        )
        row = _flatten_features(result.features_json)
        row.update(
            {
                "fixture_id": fixture.fixture_id,
                "fixture_date": ensure_aware_utc(fixture.date).isoformat(),
                "prediction_time": prediction_time.isoformat(),
                "feature_snapshot_id": result.snapshot.id,
                "target": _target(fixture),
                "home_goals": fixture.home_goals,
                "away_goals": fixture.away_goals,
                "overall_data_quality_score": result.data_quality_json[
                    "overall_data_quality_score"
                ],
            }
        )
        rows.append(row)
    frame = pd.DataFrame(rows)
    if save_path is not None:
        _save_frame(frame, save_path)
    return frame


def create_time_based_split(
    df: pd.DataFrame,
    train_until: datetime | str,
    valid_until: datetime | str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split by fixture_date without shuffling."""
    if "fixture_date" not in df.columns:
        raise ValueError("DataFrame must contain fixture_date")
    ordered = df.sort_values("fixture_date").reset_index(drop=True)
    dates = pd.to_datetime(ordered["fixture_date"], utc=True)
    train_cutoff = pd.Timestamp(train_until).tz_convert("UTC")
    valid_cutoff = pd.Timestamp(valid_until).tz_convert("UTC")
    train = ordered.loc[dates <= train_cutoff].copy()
    valid = ordered.loc[(dates > train_cutoff) & (dates <= valid_cutoff)].copy()
    test = ordered.loc[dates > valid_cutoff].copy()
    return train, valid, test


def _finished_fixtures(
    session: Session,
    league_ids: list[int],
    seasons: list[int],
    *,
    limit: int | None,
) -> list[models.Fixture]:
    stmt = (
        select(models.Fixture)
        .where(
            models.Fixture.league_id.in_(league_ids),
            models.Fixture.season.in_(seasons),
            models.Fixture.status_short.in_(FINISHED_STATUSES),
            models.Fixture.date.is_not(None),
            models.Fixture.home_goals.is_not(None),
            models.Fixture.away_goals.is_not(None),
        )
        .order_by(models.Fixture.date.asc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(session.execute(stmt).scalars())


def _target(fixture: models.Fixture) -> str:
    if fixture.home_goals is None or fixture.away_goals is None:
        raise ValueError(f"Fixture {fixture.fixture_id} has no final score")
    if fixture.home_goals > fixture.away_goals:
        return "HOME"
    if fixture.home_goals < fixture.away_goals:
        return "AWAY"
    return "DRAW"


def _flatten_features(features: JsonDict) -> JsonDict:
    flattened: JsonDict = {}
    for key, value in features.items():
        if key in {"target", "home_goals", "away_goals"}:
            continue
        if isinstance(value, dict | list):
            flattened[key] = json.dumps(value, sort_keys=True)
        elif isinstance(value, datetime):
            flattened[key] = value.isoformat()
        else:
            flattened[key] = value
    return flattened


def _save_frame(frame: pd.DataFrame, save_path: Path) -> None:
    save_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = save_path.suffix.casefold()
    if suffix == ".csv":
        frame.to_csv(save_path, index=False)
        return
    if suffix == ".parquet":
        frame.to_parquet(save_path, index=False, engine="pyarrow")
        return
    raise ValueError("save_path must end with .csv or .parquet")
