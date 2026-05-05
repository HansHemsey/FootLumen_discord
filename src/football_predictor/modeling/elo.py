"""Temporal Elo features for V2 modeling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd  # type: ignore[import-untyped]


@dataclass(frozen=True)
class EloConfig:
    initial_rating: float = 1500.0
    k_factor: float = 28.0
    home_advantage: float = 55.0


@dataclass
class EloRatingState:
    ratings: dict[str, float] = field(default_factory=dict)
    config: EloConfig = field(default_factory=EloConfig)

    def rating(self, team_key: object) -> float:
        key = _team_key(team_key)
        return self.ratings.get(key, self.config.initial_rating)

    def update(self, home_key: object, away_key: object, actual: str) -> None:
        home = _team_key(home_key)
        away = _team_key(away_key)
        home_rating = self.rating(home)
        away_rating = self.rating(away)
        expected_home = _expected_score(
            home_rating + self.config.home_advantage,
            away_rating,
        )
        actual_home = 1.0 if actual == "HOME" else 0.5 if actual == "DRAW" else 0.0
        delta = self.config.k_factor * (actual_home - expected_home)
        self.ratings[home] = home_rating + delta
        self.ratings[away] = away_rating - delta


def add_elo_features_to_dataset(
    frame: pd.DataFrame,
    *,
    config: EloConfig | None = None,
) -> tuple[pd.DataFrame, EloRatingState]:
    """Add pre-match Elo columns using only rows earlier in fixture_date order."""
    config = config or EloConfig()
    ordered = (
        frame.assign(__fixture_date_dt=pd.to_datetime(frame["fixture_date"], utc=True))
        .sort_values("__fixture_date_dt")
        .copy()
    )
    state = EloRatingState(config=config)
    rows: list[dict[str, float]] = []
    for _, row in ordered.iterrows():
        home_key = _home_key(row)
        away_key = _away_key(row)
        home_elo = state.rating(home_key)
        away_elo = state.rating(away_key)
        expected_home = _expected_score(home_elo + config.home_advantage, away_elo)
        rows.append(
            {
                "elo_home_rating": home_elo,
                "elo_away_rating": away_elo,
                "elo_diff": home_elo - away_elo,
                "elo_home_win_expectation": expected_home,
            }
        )
        target = str(row.get("target", ""))
        if target in {"HOME", "DRAW", "AWAY"}:
            state.update(home_key, away_key, target)
    elo_frame = pd.DataFrame(rows, index=ordered.index)
    output = ordered.drop(columns=["__fixture_date_dt"]).join(elo_frame)
    return output.sort_index(), state


def elo_features_for_row(row: dict[str, Any], state: EloRatingState) -> dict[str, float]:
    home_elo = state.rating(row.get("home_team_id"))
    away_elo = state.rating(row.get("away_team_id"))
    return {
        "elo_home_rating": home_elo,
        "elo_away_rating": away_elo,
        "elo_diff": home_elo - away_elo,
        "elo_home_win_expectation": _expected_score(
            home_elo + state.config.home_advantage,
            away_elo,
        ),
    }


def elo_probability_from_diff(elo_diff: float, *, home_advantage: float = 55.0) -> list[float]:
    home_expectation = _expected_score(1500.0 + elo_diff + home_advantage, 1500.0)
    draw = max(0.18, min(0.32, 0.29 - abs(home_expectation - 0.5) * 0.12))
    home = home_expectation * (1.0 - draw)
    away = (1.0 - home_expectation) * (1.0 - draw)
    total = home + draw + away
    return [home / total, draw / total, away / total]


def _expected_score(left: float, right: float) -> float:
    return 1.0 / (1.0 + 10 ** ((right - left) / 400.0))


def _home_key(row: pd.Series) -> object:
    return row.get("home_team_id", row.get("home_team"))


def _away_key(row: pd.Series) -> object:
    return row.get("away_team_id", row.get("away_team"))


def _team_key(value: object) -> str:
    return "unknown" if value is None or pd.isna(value) else str(value)
