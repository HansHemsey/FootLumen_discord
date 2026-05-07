"""Build O/U 2.5 training datasets with strict PIT safety."""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.ou_model.constants import FEATURE_VERSION, OU_THRESHOLD
from football_predictor.ou_model.features.ou_feature_builder import build_ou_feature_snapshot
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference

logger = logging.getLogger(__name__)

FINISHED_STATUSES = {"FT", "AET", "PEN"}
TARGET_COL = "target_ou25"
DATE_COL = "fixture_date"


def build_ou_training_dataset(
    session: Session,
    ou_bet_id: int,
    *,
    league_ids: list[int] | None = None,
    seasons: list[int] | None = None,
    prediction_offset_hours: int = 24,
    save_path: Path | None = None,
    feature_version: str = FEATURE_VERSION,
    threshold: float = OU_THRESHOLD,
    players_reference: PlayersReference | None = None,
    api_reference: ApiFootballReference | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Build a PIT-safe O/U training dataset.

    For each finished fixture with a known score:
      - prediction_time = fixture.date - prediction_offset_hours
      - target_ou25 = int(home_goals + away_goals > threshold)
      - Calls build_ou_feature_snapshot() for point-in-time features
    """
    stmt = select(models.Fixture).where(
        models.Fixture.status.in_(list(FINISHED_STATUSES)),
        models.Fixture.home_goals.is_not(None),
        models.Fixture.away_goals.is_not(None),
        models.Fixture.date.is_not(None),
    )
    if league_ids:
        stmt = stmt.where(models.Fixture.league_id.in_(league_ids))
    if seasons:
        stmt = stmt.where(models.Fixture.season.in_(seasons))
    stmt = stmt.order_by(models.Fixture.date.asc())

    fixtures = list(session.execute(stmt).scalars())
    if limit is not None:
        fixtures = fixtures[:limit]

    logger.info("Building O/U dataset: %d fixtures", len(fixtures))

    rows: list[dict[str, Any]] = []
    for i, fixture in enumerate(fixtures):
        if fixture.date is None:
            continue
        home_goals = fixture.home_goals or fixture.goals_home or 0
        away_goals = fixture.away_goals or fixture.goals_away or 0
        total_goals = home_goals + away_goals

        prediction_time = fixture.date - timedelta(hours=prediction_offset_hours)
        try:
            result = build_ou_feature_snapshot(
                session,
                fixture.fixture_id,
                prediction_time,
                ou_bet_id=ou_bet_id,
                feature_version=feature_version,
                threshold=threshold,
                players_reference=players_reference,
                api_reference=api_reference,
            )
            row = dict(result.features_json)
        except Exception as exc:
            logger.warning(
                "Skipping fixture_id=%d: %s", fixture.fixture_id, exc
            )
            continue

        row[TARGET_COL] = int(total_goals > threshold)
        row[DATE_COL] = fixture.date.isoformat()
        row["fixture_id"] = fixture.fixture_id
        row["league_id"] = fixture.league_id
        row["season"] = fixture.season
        row["home_goals"] = home_goals
        row["away_goals"] = away_goals
        row["total_goals"] = total_goals

        market_odd_over = result.features_json.get("market_odd_over25")
        market_odd_under = result.features_json.get("market_odd_under25")
        row["ou_market_odd_over"] = market_odd_over
        row["ou_market_odd_under"] = market_odd_under

        rows.append(row)

        if (i + 1) % 100 == 0:
            logger.info("  Processed %d/%d fixtures", i + 1, len(fixtures))
            session.flush()

    if not rows:
        return pd.DataFrame()

    frame = pd.DataFrame(rows)
    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        if save_path.suffix in (".parquet", ".pq"):
            frame.to_parquet(save_path, index=False)
        else:
            frame.to_csv(save_path, index=False)
        logger.info("Saved O/U dataset to %s (%d rows)", save_path, len(frame))

    return frame
