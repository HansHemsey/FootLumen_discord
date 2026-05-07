"""Over/Under 2.5 market consensus and movement features.

Uses the same odds_snapshots table as 1X2, filtered by the O/U bet_id.
In odds_snapshots:
  odd_home = Over 2.5 odd
  odd_away = Under 2.5 odd
  odd_draw = NULL
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from statistics import pstdev
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.utils.time import ensure_aware_utc

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class OUMarketConsensusResult:
    p_over: float
    p_under: float
    overround: float
    bookmaker_count: int
    dispersion: float
    odd_over_avg: float
    odd_under_avg: float
    first_fetched_at: datetime | None
    latest_fetched_at: datetime


@dataclass(frozen=True)
class OUOddsMovementResult:
    delta_over: float | None
    delta_under: float | None
    bookmaker_count: int


def _parse_odd(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 1 and math.isfinite(parsed) else None


def _implied_ou_probs(odd_over: float, odd_under: float) -> tuple[float, float, float]:
    """Margin-free P(Over), P(Under), overround."""
    q_over = 1 / odd_over
    q_under = 1 / odd_under
    total = q_over + q_under
    return q_over / total, q_under / total, total - 1


def _latest_ou_snapshots_by_bookmaker(
    session: Session,
    fixture_id: int,
    ou_bet_id: int,
    as_of_time: datetime | None,
) -> list[models.OddsSnapshot]:
    conditions: list[Any] = [
        models.OddsSnapshot.fixture_id == fixture_id,
        models.OddsSnapshot.bet_id == ou_bet_id,
        models.OddsSnapshot.is_live.is_(False),
        models.OddsSnapshot.odd_home.is_not(None),
        models.OddsSnapshot.odd_away.is_not(None),
    ]
    if as_of_time is not None:
        conditions.append(models.OddsSnapshot.fetched_at <= ensure_aware_utc(as_of_time))
    all_snapshots = list(
        session.execute(
            select(models.OddsSnapshot)
            .where(*conditions)
            .order_by(
                models.OddsSnapshot.bookmaker_id.asc(),
                models.OddsSnapshot.fetched_at.desc(),
            )
        ).scalars()
    )
    latest_by_bookmaker: dict[int | None, models.OddsSnapshot] = {}
    for snap in all_snapshots:
        latest_by_bookmaker.setdefault(snap.bookmaker_id, snap)
    return list(latest_by_bookmaker.values())


def compute_ou_market_consensus(
    session: Session,
    fixture_id: int,
    ou_bet_id: int,
    as_of_time: datetime | None = None,
) -> OUMarketConsensusResult | None:
    """Compute O/U market consensus from all bookmakers available before as_of_time."""
    session.flush()
    snapshots = _latest_ou_snapshots_by_bookmaker(session, fixture_id, ou_bet_id, as_of_time)
    valid: list[tuple[float, float, float, float, float]] = []
    for snap in snapshots:
        odd_over = _parse_odd(snap.odd_home)
        odd_under = _parse_odd(snap.odd_away)
        if odd_over is None or odd_under is None:
            continue
        p_over, p_under, overround = _implied_ou_probs(odd_over, odd_under)
        valid.append((odd_over, odd_under, p_over, p_under, overround))

    if not valid:
        return None

    weights = [1 / max(row[4], 0.01) for row in valid]
    total_weight = sum(weights)
    p_over_avg = sum(row[2] * w for row, w in zip(valid, weights, strict=True)) / total_weight
    p_under_avg = sum(row[3] * w for row, w in zip(valid, weights, strict=True)) / total_weight
    odd_over_avg = sum(row[0] for row in valid) / len(valid)
    odd_under_avg = sum(row[1] for row in valid) / len(valid)
    overround_avg = sum(row[4] for row in valid) / len(valid)
    dispersion = pstdev([row[2] for row in valid]) if len(valid) > 1 else 0.0

    all_fetched = [ensure_aware_utc(s.fetched_at) for s in snapshots]
    return OUMarketConsensusResult(
        p_over=p_over_avg,
        p_under=p_under_avg,
        overround=overround_avg,
        bookmaker_count=len(valid),
        dispersion=dispersion,
        odd_over_avg=odd_over_avg,
        odd_under_avg=odd_under_avg,
        first_fetched_at=None,
        latest_fetched_at=max(all_fetched),
    )


def compute_ou_odds_movement(
    session: Session,
    fixture_id: int,
    ou_bet_id: int,
    as_of_time: datetime,
) -> OUOddsMovementResult:
    """Compute O/U odds movement (latest minus earliest snapshot before as_of_time)."""
    session.flush()
    cutoff = ensure_aware_utc(as_of_time)
    all_snapshots = list(
        session.execute(
            select(models.OddsSnapshot)
            .where(
                models.OddsSnapshot.fixture_id == fixture_id,
                models.OddsSnapshot.bet_id == ou_bet_id,
                models.OddsSnapshot.is_live.is_(False),
                models.OddsSnapshot.fetched_at <= cutoff,
                models.OddsSnapshot.odd_home.is_not(None),
                models.OddsSnapshot.odd_away.is_not(None),
            )
            .order_by(models.OddsSnapshot.fetched_at.asc())
        ).scalars()
    )
    if not all_snapshots:
        return OUOddsMovementResult(None, None, 0)

    first_time = ensure_aware_utc(all_snapshots[0].fetched_at)
    latest_time = ensure_aware_utc(all_snapshots[-1].fetched_at)
    if first_time == latest_time:
        return OUOddsMovementResult(None, None, len(all_snapshots))

    first_valid = [
        s for s in all_snapshots if ensure_aware_utc(s.fetched_at) == first_time
        and _parse_odd(s.odd_home) is not None and _parse_odd(s.odd_away) is not None
    ]
    latest_valid = [
        s for s in all_snapshots if ensure_aware_utc(s.fetched_at) == latest_time
        and _parse_odd(s.odd_home) is not None and _parse_odd(s.odd_away) is not None
    ]
    if not first_valid or not latest_valid:
        return OUOddsMovementResult(None, None, len(latest_valid))

    avg_first_over = sum(_parse_odd(s.odd_home) for s in first_valid) / len(first_valid)  # type: ignore[arg-type]
    avg_first_under = sum(_parse_odd(s.odd_away) for s in first_valid) / len(first_valid)  # type: ignore[arg-type]
    avg_latest_over = sum(_parse_odd(s.odd_home) for s in latest_valid) / len(latest_valid)  # type: ignore[arg-type]
    avg_latest_under = sum(_parse_odd(s.odd_away) for s in latest_valid) / len(latest_valid)  # type: ignore[arg-type]

    return OUOddsMovementResult(
        delta_over=avg_latest_over - avg_first_over,
        delta_under=avg_latest_under - avg_first_under,
        bookmaker_count=len(latest_valid),
    )


def ou_market_features_dict(
    consensus: OUMarketConsensusResult | None,
    movement: OUOddsMovementResult | None,
) -> JsonDict:
    """Flatten O/U market results into a features dict."""
    if consensus is None:
        return {
            "market_p_over25": None,
            "market_p_under25": None,
            "market_odd_over25": None,
            "market_odd_under25": None,
            "market_ou_overround": None,
            "market_ou_bookmaker_count": 0,
            "market_ou_dispersion": None,
            "market_ou_movement_over": movement.delta_over if movement else None,
            "market_ou_movement_under": movement.delta_under if movement else None,
        }
    return {
        "market_p_over25": consensus.p_over,
        "market_p_under25": consensus.p_under,
        "market_odd_over25": consensus.odd_over_avg,
        "market_odd_under25": consensus.odd_under_avg,
        "market_ou_overround": consensus.overround,
        "market_ou_bookmaker_count": consensus.bookmaker_count,
        "market_ou_dispersion": consensus.dispersion,
        "market_ou_movement_over": movement.delta_over if movement else None,
        "market_ou_movement_under": movement.delta_under if movement else None,
    }
