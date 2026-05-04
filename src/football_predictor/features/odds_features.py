"""Odds conversion and consensus for prematch 1X2 markets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import pstdev
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.reference.lookups import ApiFootballReference
from football_predictor.utils.time import ensure_aware_utc


@dataclass(frozen=True)
class OddsQuote:
    bookmaker_id: int | None
    odd_home: float
    odd_draw: float
    odd_away: float


@dataclass(frozen=True)
class ImpliedProbabilities:
    probabilities: ProbabilityTriple
    overround: float
    bookmaker_id: int | None = None


@dataclass(frozen=True)
class OddsConsensus:
    probabilities: ProbabilityTriple
    overround: float
    bookmaker_count: int
    dispersion: float


@dataclass(frozen=True)
class OddsMovement:
    bookmaker_count: int
    odd_home_delta: float | None
    odd_draw_delta: float | None
    odd_away_delta: float | None
    p_home_delta: float | None
    p_draw_delta: float | None
    p_away_delta: float | None

    def as_dict(self) -> dict[str, float | int | None]:
        return {
            "bookmaker_count": self.bookmaker_count,
            "odd_home_delta": self.odd_home_delta,
            "odd_draw_delta": self.odd_draw_delta,
            "odd_away_delta": self.odd_away_delta,
            "p_home_delta": self.p_home_delta,
            "p_draw_delta": self.p_draw_delta,
            "p_away_delta": self.p_away_delta,
        }


@dataclass(frozen=True)
class MarketProbabilityFeatures:
    probabilities: ProbabilityTriple
    overround: float
    bookmaker_count: int
    dispersion: float
    movement: OddsMovement
    fetched_at: datetime


@dataclass(frozen=True)
class Extracted1X2Odds:
    odd_home: float
    odd_draw: float
    odd_away: float


@dataclass(frozen=True)
class MarketConsensusResult:
    p_market_home: float
    p_market_draw: float
    p_market_away: float
    overround: float
    bookmaker_count: int
    market_dispersion: float
    market_confidence: float
    fetched_at: datetime

    @property
    def probabilities(self) -> ProbabilityTriple:
        return ProbabilityTriple(
            p_home=self.p_market_home,
            p_draw=self.p_market_draw,
            p_away=self.p_market_away,
        ).normalized()


@dataclass(frozen=True)
class OddsMovementResult:
    delta_home: float | None
    delta_draw: float | None
    delta_away: float | None
    first_fetched_at: datetime | None
    latest_fetched_at: datetime | None
    bookmaker_count: int


def decimal_odds_to_implied_probabilities(
    home: float,
    draw: float,
    away: float,
) -> ImpliedProbabilities:
    """Convert decimal 1X2 odds to margin-free implied probabilities."""
    return implied_probabilities_without_margin(
        OddsQuote(bookmaker_id=None, odd_home=home, odd_draw=draw, odd_away=away)
    )


def implied_probabilities_without_margin(quote: OddsQuote) -> ImpliedProbabilities:
    if quote.odd_home <= 1 or quote.odd_draw <= 1 or quote.odd_away <= 1:
        raise ValueError("Decimal odds must be greater than 1")
    q_home = 1 / quote.odd_home
    q_draw = 1 / quote.odd_draw
    q_away = 1 / quote.odd_away
    total = q_home + q_draw + q_away
    return ImpliedProbabilities(
        probabilities=ProbabilityTriple(
            p_home=q_home / total,
            p_draw=q_draw / total,
            p_away=q_away / total,
        ),
        overround=total - 1,
        bookmaker_id=quote.bookmaker_id,
    )


def extract_1x2_values(
    values_json: list[dict[str, Any]],
    *,
    home_team_name: str | None = None,
    away_team_name: str | None = None,
) -> Extracted1X2Odds | None:
    """Extract Home/Draw/Away odds from API-Football bet values."""
    parsed: dict[str, float] = {}
    for value_row in values_json:
        label = _normalize_1x2_label(
            value_row.get("value"),
            home_team_name=home_team_name,
            away_team_name=away_team_name,
        )
        odd = _parse_decimal_odd(value_row.get("odd"))
        if label is not None and odd is not None:
            parsed[label] = odd
    if {"home", "draw", "away"}.issubset(parsed):
        return Extracted1X2Odds(
            odd_home=parsed["home"],
            odd_draw=parsed["draw"],
            odd_away=parsed["away"],
        )
    return None


def consensus_probabilities(quotes: list[OddsQuote]) -> OddsConsensus | None:
    if not quotes:
        return None
    implied = [implied_probabilities_without_margin(quote) for quote in quotes]
    weights = [1 / max(item.overround, 0.01) for item in implied]
    total_weight = sum(weights)
    p_home = sum(
        item.probabilities.p_home * weight for item, weight in zip(implied, weights, strict=True)
    )
    p_draw = sum(
        item.probabilities.p_draw * weight for item, weight in zip(implied, weights, strict=True)
    )
    p_away = sum(
        item.probabilities.p_away * weight for item, weight in zip(implied, weights, strict=True)
    )
    probabilities = ProbabilityTriple(
        p_home=p_home / total_weight,
        p_draw=p_draw / total_weight,
        p_away=p_away / total_weight,
    ).normalized()
    max_probs = [item.probabilities.max_probability() for item in implied]
    dispersion = pstdev(max_probs) if len(max_probs) > 1 else 0.0
    return OddsConsensus(
        probabilities=probabilities,
        overround=sum(item.overround for item in implied) / len(implied),
        bookmaker_count=len(implied),
        dispersion=dispersion,
    )


def compute_market_consensus(
    session: Session,
    fixture_id: int,
    as_of_time: datetime | None = None,
    *,
    bet_id: int | None = None,
) -> MarketConsensusResult | None:
    """Compute latest prematch market consensus without reading future snapshots."""
    snapshots = _latest_snapshots_by_bookmaker(
        session,
        fixture_id=fixture_id,
        as_of_time=as_of_time,
        bet_id=bet_id,
    )
    quotes = [
        quote
        for quote in (quote_from_odds_snapshot(snapshot) for snapshot in snapshots)
        if quote is not None
    ]
    consensus = consensus_probabilities(quotes)
    if consensus is None:
        return None
    probabilities = consensus.probabilities.normalized()
    values = sorted(probabilities.as_dict().values(), reverse=True)
    return MarketConsensusResult(
        p_market_home=probabilities.p_home,
        p_market_draw=probabilities.p_draw,
        p_market_away=probabilities.p_away,
        overround=consensus.overround,
        bookmaker_count=consensus.bookmaker_count,
        market_dispersion=consensus.dispersion,
        market_confidence=values[0] - values[1],
        fetched_at=ensure_aware_utc(max(snapshot.fetched_at for snapshot in snapshots)),
    )


def compute_odds_movement(
    session: Session,
    fixture_id: int,
    current_time: datetime,
    *,
    bet_id: int | None = None,
) -> OddsMovementResult:
    """Compare first available odds snapshot with latest snapshot before current_time."""
    session.flush()
    snapshots = list(
        session.execute(
            select(models.OddsSnapshot)
            .where(
                models.OddsSnapshot.fixture_id == fixture_id,
                models.OddsSnapshot.is_live.is_(False),
                models.OddsSnapshot.fetched_at <= ensure_aware_utc(current_time),
                models.OddsSnapshot.odd_home.is_not(None),
                models.OddsSnapshot.odd_draw.is_not(None),
                models.OddsSnapshot.odd_away.is_not(None),
            )
            .order_by(models.OddsSnapshot.fetched_at.asc())
        ).scalars()
    )
    if bet_id is not None:
        snapshots = [snapshot for snapshot in snapshots if snapshot.bet_id == bet_id]
    if not snapshots:
        return OddsMovementResult(None, None, None, None, None, 0)
    first_time = min(ensure_aware_utc(snapshot.fetched_at) for snapshot in snapshots)
    latest_time = max(ensure_aware_utc(snapshot.fetched_at) for snapshot in snapshots)
    first_snapshots = [
        snapshot for snapshot in snapshots if ensure_aware_utc(snapshot.fetched_at) == first_time
    ]
    latest_snapshots = [
        snapshot for snapshot in snapshots if ensure_aware_utc(snapshot.fetched_at) == latest_time
    ]
    first_average = _average_odds(first_snapshots)
    latest_average = _average_odds(latest_snapshots)
    if first_average is None or latest_average is None or first_time == latest_time:
        return OddsMovementResult(None, None, None, first_time, latest_time, len(latest_snapshots))
    return OddsMovementResult(
        delta_home=latest_average.odd_home - first_average.odd_home,
        delta_draw=latest_average.odd_draw - first_average.odd_draw,
        delta_away=latest_average.odd_away - first_average.odd_away,
        first_fetched_at=first_time,
        latest_fetched_at=latest_time,
        bookmaker_count=len(latest_snapshots),
    )


def resolve_1x2_bet_id(
    reference: ApiFootballReference,
    *,
    configured_bet_id: int | None = None,
    configured_bet_name: str = "Match Winner",
) -> int:
    """Resolve the prematch 1X2 bet from local references without guessing IDs."""
    if configured_bet_id is not None:
        return reference.find_bet_by_id(configured_bet_id).bet_id
    return reference.find_bet_by_name(configured_bet_name).bet_id


def quote_from_odds_snapshot(snapshot: models.OddsSnapshot) -> OddsQuote | None:
    if snapshot.odd_home is None or snapshot.odd_draw is None or snapshot.odd_away is None:
        return None
    return OddsQuote(
        bookmaker_id=snapshot.bookmaker_id,
        odd_home=snapshot.odd_home,
        odd_draw=snapshot.odd_draw,
        odd_away=snapshot.odd_away,
    )


def market_probabilities_for_fixture(
    session: Session,
    *,
    fixture_id: int,
    prediction_time: datetime,
    bet_id: int,
) -> MarketProbabilityFeatures | None:
    """Build market probabilities from prematch odds available at prediction_time."""
    snapshots = _snapshot_history(
        session,
        fixture_id=fixture_id,
        as_of_time=prediction_time,
        bet_id=bet_id,
    )
    latest_by_bookmaker: dict[int | None, models.OddsSnapshot] = {}
    previous_by_bookmaker: dict[int | None, models.OddsSnapshot] = {}
    for snapshot in snapshots:
        bookmaker_id = snapshot.bookmaker_id
        if bookmaker_id not in latest_by_bookmaker:
            latest_by_bookmaker[bookmaker_id] = snapshot
        elif bookmaker_id not in previous_by_bookmaker:
            previous_by_bookmaker[bookmaker_id] = snapshot

    latest_quotes = [
        quote
        for quote in (
            quote_from_odds_snapshot(snapshot) for snapshot in latest_by_bookmaker.values()
        )
        if quote is not None
    ]
    consensus = consensus_probabilities(latest_quotes)
    if consensus is None:
        return None
    return MarketProbabilityFeatures(
        probabilities=consensus.probabilities,
        overround=consensus.overround,
        bookmaker_count=consensus.bookmaker_count,
        dispersion=consensus.dispersion,
        movement=_movement_from_snapshots(latest_by_bookmaker, previous_by_bookmaker),
        fetched_at=ensure_aware_utc(
            max(snapshot.fetched_at for snapshot in latest_by_bookmaker.values())
        ),
    )


def _movement_from_snapshots(
    latest_by_bookmaker: dict[int | None, models.OddsSnapshot],
    previous_by_bookmaker: dict[int | None, models.OddsSnapshot],
) -> OddsMovement:
    odds_deltas: list[tuple[float, float, float]] = []
    probability_deltas: list[tuple[float, float, float]] = []
    for bookmaker_id, latest_snapshot in latest_by_bookmaker.items():
        previous_snapshot = previous_by_bookmaker.get(bookmaker_id)
        latest_quote = quote_from_odds_snapshot(latest_snapshot)
        previous_quote = (
            quote_from_odds_snapshot(previous_snapshot) if previous_snapshot is not None else None
        )
        if latest_quote is None or previous_quote is None:
            continue
        odds_deltas.append(
            (
                latest_quote.odd_home - previous_quote.odd_home,
                latest_quote.odd_draw - previous_quote.odd_draw,
                latest_quote.odd_away - previous_quote.odd_away,
            )
        )
        latest_probabilities = implied_probabilities_without_margin(latest_quote).probabilities
        previous_probabilities = implied_probabilities_without_margin(previous_quote).probabilities
        probability_deltas.append(
            (
                latest_probabilities.p_home - previous_probabilities.p_home,
                latest_probabilities.p_draw - previous_probabilities.p_draw,
                latest_probabilities.p_away - previous_probabilities.p_away,
            )
        )
    return OddsMovement(
        bookmaker_count=len(odds_deltas),
        odd_home_delta=_mean_delta(odds_deltas, 0),
        odd_draw_delta=_mean_delta(odds_deltas, 1),
        odd_away_delta=_mean_delta(odds_deltas, 2),
        p_home_delta=_mean_delta(probability_deltas, 0),
        p_draw_delta=_mean_delta(probability_deltas, 1),
        p_away_delta=_mean_delta(probability_deltas, 2),
    )


def _mean_delta(values: list[tuple[float, float, float]], index: int) -> float | None:
    if not values:
        return None
    return sum(item[index] for item in values) / len(values)


def _snapshot_history(
    session: Session,
    *,
    fixture_id: int,
    as_of_time: datetime | None,
    bet_id: int | None,
) -> list[models.OddsSnapshot]:
    session.flush()
    conditions: list[Any] = [
        models.OddsSnapshot.fixture_id == fixture_id,
        models.OddsSnapshot.is_live.is_(False),
        models.OddsSnapshot.odd_home.is_not(None),
        models.OddsSnapshot.odd_draw.is_not(None),
        models.OddsSnapshot.odd_away.is_not(None),
    ]
    if bet_id is not None:
        conditions.append(models.OddsSnapshot.bet_id == bet_id)
    if as_of_time is not None:
        conditions.append(models.OddsSnapshot.fetched_at <= ensure_aware_utc(as_of_time))
    return list(
        session.execute(
            select(models.OddsSnapshot)
            .where(*conditions)
            .order_by(
                models.OddsSnapshot.bookmaker_id.asc(),
                models.OddsSnapshot.fetched_at.desc(),
            )
        ).scalars()
    )


def _latest_snapshots_by_bookmaker(
    session: Session,
    *,
    fixture_id: int,
    as_of_time: datetime | None,
    bet_id: int | None,
) -> list[models.OddsSnapshot]:
    snapshots = _snapshot_history(
        session,
        fixture_id=fixture_id,
        as_of_time=as_of_time,
        bet_id=bet_id,
    )
    latest_by_bookmaker: dict[int | None, models.OddsSnapshot] = {}
    for snapshot in snapshots:
        latest_by_bookmaker.setdefault(snapshot.bookmaker_id, snapshot)
    return list(latest_by_bookmaker.values())


def _average_odds(snapshots: list[models.OddsSnapshot]) -> OddsQuote | None:
    quotes = [
        quote
        for quote in (quote_from_odds_snapshot(snapshot) for snapshot in snapshots)
        if quote is not None
    ]
    if not quotes:
        return None
    return OddsQuote(
        bookmaker_id=None,
        odd_home=sum(quote.odd_home for quote in quotes) / len(quotes),
        odd_draw=sum(quote.odd_draw for quote in quotes) / len(quotes),
        odd_away=sum(quote.odd_away for quote in quotes) / len(quotes),
    )


def _normalize_1x2_label(
    value: Any,
    *,
    home_team_name: str | None,
    away_team_name: str | None,
) -> str | None:
    if value is None:
        return None
    normalized = _normalize_label(value)
    if normalized in {"home", "1"}:
        return "home"
    if normalized in {"draw", "x"}:
        return "draw"
    if normalized in {"away", "2"}:
        return "away"
    if home_team_name is not None and normalized == _normalize_label(home_team_name):
        return "home"
    if away_team_name is not None and normalized == _normalize_label(away_team_name):
        return "away"
    return None


def _normalize_label(value: Any) -> str:
    return " ".join(str(value).strip().casefold().split())


def _parse_decimal_odd(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 1 else None
