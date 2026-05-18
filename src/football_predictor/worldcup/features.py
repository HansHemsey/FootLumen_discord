"""Point-in-time feature engineering for international World Cup predictions."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from football_predictor.modeling.poisson import _poisson_pmf
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.worldcup.blend import (
    WorldCupBlendConfig,
    blend_worldcup_probability_sources,
)
from football_predictor.worldcup.references import (
    InternationalMatch,
    WorldCupReferenceBundle,
    normalize_team_name,
)

JsonDict = dict[str, Any]
CLASSES = ("HOME", "DRAW", "AWAY")
OFFICIAL_KEYWORDS = (
    "cup",
    "championship",
    "qualification",
    "qualifier",
    "nations league",
    "copa",
    "gold cup",
    "africa",
    "asian",
    "euro",
)
CONTINENTAL_KEYWORDS = (
    "uefa euro",
    "copa america",
    "africa cup",
    "asian cup",
    "gold cup",
    "concacaf",
    "ofc nations",
    "nations league",
)


@dataclass(frozen=True)
class WorldCupFeatureConfig:
    training_start_year: int = 2016
    recent_start_year: int = 2021
    very_recent_start_year: int = 2024
    form_half_life_days: float = 540.0
    strong_opponent_elo: float = 1600.0
    weak_opponent_elo: float = 1450.0
    initial_elo: float = 1500.0
    elo_k_factor: float = 28.0
    home_elo_advantage: float = 45.0
    home_goal_base: float = 1.35
    away_goal_base: float = 1.10


@dataclass
class RatingState:
    elo: dict[str, float] = field(default_factory=dict)
    attack: dict[str, float] = field(default_factory=dict)
    defense: dict[str, float] = field(default_factory=dict)
    global_rating: dict[str, float] = field(default_factory=dict)
    config: WorldCupFeatureConfig = field(default_factory=WorldCupFeatureConfig)

    def rating(self, team: str) -> float:
        return self.elo.get(_key(team), self.config.initial_elo)

    def power_global(self, team: str) -> float:
        return self.global_rating.get(_key(team), 0.0)

    def attack_rating(self, team: str) -> float:
        return self.attack.get(_key(team), 0.0)

    def defense_rating(self, team: str) -> float:
        return self.defense.get(_key(team), 0.0)

    def update(self, match: InternationalMatch) -> None:
        home = _key(match.home_team)
        away = _key(match.away_team)
        home_elo = self.rating(match.home_team)
        away_elo = self.rating(match.away_team)
        advantage = 0.0 if match.neutral else self.config.home_elo_advantage
        expected_home = _logistic_expectation(home_elo + advantage, away_elo)
        actual_home = 1.0 if match.target == "HOME" else 0.5 if match.target == "DRAW" else 0.0
        delta = self.config.elo_k_factor * (actual_home - expected_home)
        self.elo[home] = home_elo + delta
        self.elo[away] = away_elo - delta

        expected_margin = (home_elo - away_elo + advantage) / 400.0
        margin_error = (match.home_score - match.away_score) - expected_margin
        self.global_rating[home] = self.power_global(match.home_team) + 0.06 * margin_error
        self.global_rating[away] = self.power_global(match.away_team) - 0.06 * margin_error
        self.attack[home] = self.attack_rating(match.home_team) + 0.035 * (
            match.home_score - self.config.home_goal_base
        )
        self.attack[away] = self.attack_rating(match.away_team) + 0.035 * (
            match.away_score - self.config.away_goal_base
        )
        self.defense[home] = self.defense_rating(match.home_team) + 0.035 * (
            self.config.away_goal_base - match.away_score
        )
        self.defense[away] = self.defense_rating(match.away_team) + 0.035 * (
            self.config.home_goal_base - match.home_score
        )


@dataclass(frozen=True)
class TeamMatchRecord:
    match_date: date
    points: float
    goals_for: int
    goals_against: int
    neutral: bool
    tournament: str
    opponent_elo: float

    @property
    def is_win(self) -> bool:
        return self.points == 3.0

    @property
    def is_draw(self) -> bool:
        return self.points == 1.0

    @property
    def clean_sheet(self) -> bool:
        return self.goals_against == 0

    @property
    def failed_to_score(self) -> bool:
        return self.goals_for == 0

    @property
    def btts(self) -> bool:
        return self.goals_for > 0 and self.goals_against > 0

    @property
    def over25(self) -> bool:
        return self.goals_for + self.goals_against > 2.5


def build_worldcup_dataset(
    matches: list[InternationalMatch],
    *,
    config: WorldCupFeatureConfig | None = None,
) -> pd.DataFrame:
    """Build a chronological international dataset without current ranking priors."""
    resolved = config or WorldCupFeatureConfig()
    rows: list[JsonDict] = []
    histories: dict[str, list[TeamMatchRecord]] = defaultdict(list)
    ratings = RatingState(config=resolved)
    for index, match in enumerate(_eligible_matches(matches, resolved.training_start_year)):
        row = build_features_for_match(
            match.home_team,
            match.away_team,
            match.match_date,
            histories=histories,
            ratings=ratings,
            neutral=match.neutral,
            bundle=None,
            include_current_priors=False,
            config=resolved,
        )
        row.update(
            {
                "fixture_id": -(index + 1),
                "fixture_date": match.match_date.isoformat(),
                "prediction_time": match.match_date.isoformat(),
                "home_team": match.home_team,
                "away_team": match.away_team,
                "tournament": match.tournament,
                "neutral": match.neutral,
                "target": match.target,
                "home_goals": match.home_score,
                "away_goals": match.away_score,
            }
        )
        rows.append(row)
        _append_history(match, histories, ratings)
        ratings.update(match)
    return pd.DataFrame(rows)


def build_features_for_fixture(
    home_team: str,
    away_team: str,
    prediction_date: date,
    *,
    bundle: WorldCupReferenceBundle,
    neutral: bool = True,
    config: WorldCupFeatureConfig | None = None,
) -> JsonDict:
    resolved = config or WorldCupFeatureConfig()
    histories: dict[str, list[TeamMatchRecord]] = defaultdict(list)
    ratings = RatingState(config=resolved)
    for match in _eligible_matches(bundle.historical_matches, resolved.training_start_year):
        if match.match_date >= prediction_date:
            break
        _append_history(match, histories, ratings)
        ratings.update(match)
    return build_features_for_match(
        bundle.canonical_name(home_team),
        bundle.canonical_name(away_team),
        prediction_date,
        histories=histories,
        ratings=ratings,
        neutral=neutral,
        bundle=bundle,
        include_current_priors=True,
        config=resolved,
    )


def build_features_for_match(
    home_team: str,
    away_team: str,
    prediction_date: date,
    *,
    histories: dict[str, list[TeamMatchRecord]],
    ratings: RatingState,
    neutral: bool,
    bundle: WorldCupReferenceBundle | None,
    include_current_priors: bool,
    config: WorldCupFeatureConfig,
) -> JsonDict:
    home_key = _key(home_team)
    away_key = _key(away_team)
    home_history = histories.get(home_key, [])
    away_history = histories.get(away_key, [])
    features: JsonDict = {
        "wc_home_team_name": home_team,
        "wc_away_team_name": away_team,
        "wc_neutral_flag": int(neutral),
        "wc_home_history_count": len(home_history),
        "wc_away_history_count": len(away_history),
    }
    for prefix, history in (("wc_home", home_history), ("wc_away", away_history)):
        features.update(_team_features(prefix, history, prediction_date, config=config))
    features.update(_rating_features(home_team, away_team, ratings, neutral=neutral, config=config))
    features.update(_diff_features(features))
    if include_current_priors and bundle is not None:
        features.update(_current_reference_features(home_team, away_team, bundle))
    return features


def data_quality_for_features(features: JsonDict) -> JsonDict:
    home_count = int(features.get("wc_home_history_count") or 0)
    away_count = int(features.get("wc_away_history_count") or 0)
    fifa_available = bool(
        features.get("wc_fifa_home_available") and features.get("wc_fifa_away_available")
    )
    elo_available = bool(
        features.get("wc_current_elo_home_available")
        and features.get("wc_current_elo_away_available")
    )
    score = 0
    score += (
        40
        if home_count >= 20 and away_count >= 20
        else 25
        if home_count >= 10 and away_count >= 10
        else 10
    )
    score += 20 if int(features.get("wc_home_recent2021_matches") or 0) >= 8 else 8
    score += 20 if int(features.get("wc_home_recent2024_matches") or 0) >= 3 else 8
    score += 10 if fifa_available else 0
    score += 10 if elo_available else 0
    score = max(0, min(100, score))
    return {
        "overall_data_quality_score": score,
        "data_quality_score": score,
        "label": "High" if score >= 75 else "Medium" if score >= 50 else "Low",
        "historical_matches_home_count": home_count,
        "historical_matches_away_count": away_count,
        "worldcup_reference_fifa_available": fifa_available,
        "worldcup_reference_elo_available": elo_available,
        "worldcup_dynamic_market_available": bool(
            features.get("wc_dynamic_market_available_flag")
        ),
        "worldcup_dynamic_api_prediction_available": bool(
            features.get("wc_dynamic_api_prediction_available_flag")
        ),
        "worldcup_dynamic_lineups_available": bool(
            features.get("wc_dynamic_lineups_available_flag")
        ),
        "worldcup_dynamic_injuries_available": bool(
            features.get("wc_dynamic_injuries_available_flag")
        ),
        "worldcup_dynamic_source_count": int(features.get("wc_dynamic_source_count") or 0),
        "warnings": [],
    }


def probability_from_rating_diff(diff: float) -> ProbabilityTriple:
    home_expectation = _logistic_expectation(1500.0 + diff, 1500.0)
    draw = max(0.18, min(0.33, 0.30 - abs(home_expectation - 0.5) * 0.12))
    home = home_expectation * (1.0 - draw)
    away = (1.0 - home_expectation) * (1.0 - draw)
    return ProbabilityTriple(home, draw, away).normalized()


def poisson_probabilities(home_lambda: float, away_lambda: float) -> ProbabilityTriple:
    home_lambda = _bounded(home_lambda, 0.2, 4.5)
    away_lambda = _bounded(away_lambda, 0.2, 4.5)
    p_home = p_draw = p_away = total = 0.0
    for home_goals in range(11):
        for away_goals in range(11):
            probability = _poisson_pmf(home_goals, home_lambda) * _poisson_pmf(
                away_goals,
                away_lambda,
            )
            total += probability
            if home_goals > away_goals:
                p_home += probability
            elif home_goals < away_goals:
                p_away += probability
            else:
                p_draw += probability
    return ProbabilityTriple(p_home / total, p_draw / total, p_away / total).normalized()


def blend_worldcup_probabilities(
    *,
    model_probability: ProbabilityTriple | None,
    rating_probability: ProbabilityTriple,
    poisson_probability: ProbabilityTriple,
    market_probability: ProbabilityTriple | None = None,
    api_probability: ProbabilityTriple | None = None,
    blend_config: WorldCupBlendConfig | None = None,
    source_weights: dict[str, float] | None = None,
) -> ProbabilityTriple:
    return blend_worldcup_probability_sources(
        {
            "wc_model": model_probability,
            "wc_rating_dynamic": rating_probability,
            "wc_poisson_dynamic": poisson_probability,
            "wc_market": market_probability,
            "wc_api": api_probability,
        },
        config=blend_config,
        source_weights=source_weights,
    )


def _team_features(
    prefix: str,
    history: list[TeamMatchRecord],
    prediction_date: date,
    *,
    config: WorldCupFeatureConfig,
) -> JsonDict:
    features: JsonDict = {}
    for label, records in (
        ("last5", history[-5:]),
        ("last10", history[-10:]),
        ("last20", history[-20:]),
        (
            "recent2021",
            [row for row in history if row.match_date.year >= config.recent_start_year],
        ),
        (
            "recent2024",
            [row for row in history if row.match_date.year >= config.very_recent_start_year],
        ),
    ):
        features.update(_aggregate(prefix, label, records, prediction_date, config=config))
    features[f"{prefix}_weighted_form"] = _weighted_form(history, prediction_date, config=config)
    return features


def _aggregate(
    prefix: str,
    label: str,
    records: list[TeamMatchRecord],
    prediction_date: date,
    *,
    config: WorldCupFeatureConfig,
) -> JsonDict:
    count = len(records)
    points = [row.points for row in records]
    goals_for = [row.goals_for for row in records]
    goals_against = [row.goals_against for row in records]
    strong = [row for row in records if row.opponent_elo >= config.strong_opponent_elo]
    weak = [row for row in records if row.opponent_elo <= config.weak_opponent_elo]
    neutral = [row for row in records if row.neutral]
    official = [row for row in records if is_official(row.tournament)]
    world_cup = [row for row in records if is_world_cup(row.tournament)]
    qualifiers = [row for row in records if is_world_cup_qualification(row.tournament)]
    continental = [row for row in records if is_continental(row.tournament)]
    return {
        f"{prefix}_{label}_matches": count,
        f"{prefix}_{label}_ppg": _avg(points),
        f"{prefix}_{label}_win_rate": _rate(row.is_win for row in records),
        f"{prefix}_{label}_draw_rate": _rate(row.is_draw for row in records),
        f"{prefix}_{label}_loss_rate": _rate(row.points == 0 for row in records),
        f"{prefix}_{label}_goals_for_avg": _avg(goals_for),
        f"{prefix}_{label}_goals_against_avg": _avg(goals_against),
        f"{prefix}_{label}_goal_diff_avg": _avg(
            [row.goals_for - row.goals_against for row in records]
        ),
        f"{prefix}_{label}_clean_sheet_rate": _rate(row.clean_sheet for row in records),
        f"{prefix}_{label}_failed_to_score_rate": _rate(row.failed_to_score for row in records),
        f"{prefix}_{label}_btts_rate": _rate(row.btts for row in records),
        f"{prefix}_{label}_over25_rate": _rate(row.over25 for row in records),
        f"{prefix}_{label}_attack_strength": (_avg(goals_for) or 1.2) / 1.2,
        f"{prefix}_{label}_defense_strength": 1.2 / max(_avg(goals_against) or 1.2, 0.2),
        f"{prefix}_{label}_strong_ppg": _avg([row.points for row in strong]),
        f"{prefix}_{label}_weak_ppg": _avg([row.points for row in weak]),
        f"{prefix}_{label}_neutral_ppg": _avg([row.points for row in neutral]),
        f"{prefix}_{label}_official_ppg": _avg([row.points for row in official]),
        f"{prefix}_{label}_world_cup_ppg": _avg([row.points for row in world_cup]),
        f"{prefix}_{label}_world_cup_qualifying_ppg": _avg([row.points for row in qualifiers]),
        f"{prefix}_{label}_continental_ppg": _avg([row.points for row in continental]),
        f"{prefix}_{label}_days_since_last_match": _days_since(records, prediction_date),
    }


def _rating_features(
    home_team: str,
    away_team: str,
    ratings: RatingState,
    *,
    neutral: bool,
    config: WorldCupFeatureConfig,
) -> JsonDict:
    home_elo = ratings.rating(home_team)
    away_elo = ratings.rating(away_team)
    advantage = 0.0 if neutral else config.home_elo_advantage
    rating_probability = probability_from_rating_diff((home_elo + advantage) - away_elo)
    home_lambda = (
        config.home_goal_base
        + ratings.attack_rating(home_team)
        - ratings.defense_rating(away_team)
        + (0.0 if neutral else 0.10)
    )
    away_lambda = (
        config.away_goal_base
        + ratings.attack_rating(away_team)
        - ratings.defense_rating(home_team)
    )
    poisson = poisson_probabilities(home_lambda, away_lambda)
    expected_margin = (
        (home_elo + advantage - away_elo) / 400.0
        + ratings.power_global(home_team)
        - ratings.power_global(away_team)
    )
    return {
        "wc_home_internal_elo": home_elo,
        "wc_away_internal_elo": away_elo,
        "wc_internal_elo_diff": home_elo - away_elo,
        "wc_power_rating_diff": ratings.power_global(home_team) - ratings.power_global(away_team),
        "wc_expected_margin": expected_margin,
        "wc_expected_home_goals": _bounded(home_lambda, 0.2, 4.5),
        "wc_expected_away_goals": _bounded(away_lambda, 0.2, 4.5),
        "wc_total_expected_goals": _bounded(home_lambda, 0.2, 4.5)
        + _bounded(away_lambda, 0.2, 4.5),
        "p_wc_rating_home": rating_probability.p_home,
        "p_wc_rating_draw": rating_probability.p_draw,
        "p_wc_rating_away": rating_probability.p_away,
        "p_wc_poisson_home": poisson.p_home,
        "p_wc_poisson_draw": poisson.p_draw,
        "p_wc_poisson_away": poisson.p_away,
    }


def _current_reference_features(
    home_team: str,
    away_team: str,
    bundle: WorldCupReferenceBundle,
) -> JsonDict:
    home_fifa = bundle.fifa_for_team(home_team)
    away_fifa = bundle.fifa_for_team(away_team)
    home_elo = bundle.elo_for_team(home_team)
    away_elo = bundle.elo_for_team(away_team)
    return {
        "wc_fifa_home_available": int(home_fifa is not None),
        "wc_fifa_away_available": int(away_fifa is not None),
        "wc_fifa_home_rank": home_fifa.rank if home_fifa else None,
        "wc_fifa_away_rank": away_fifa.rank if away_fifa else None,
        "wc_fifa_rank_diff": (away_fifa.rank - home_fifa.rank) if home_fifa and away_fifa else None,
        "wc_fifa_home_points": home_fifa.points if home_fifa else None,
        "wc_fifa_away_points": away_fifa.points if away_fifa else None,
        "wc_fifa_points_diff": (home_fifa.points - away_fifa.points)
        if home_fifa and away_fifa
        else None,
        "wc_current_elo_home_available": int(home_elo is not None),
        "wc_current_elo_away_available": int(away_elo is not None),
        "wc_current_elo_home": home_elo.elo if home_elo else None,
        "wc_current_elo_away": away_elo.elo if away_elo else None,
        "wc_current_elo_diff": (home_elo.elo - away_elo.elo) if home_elo and away_elo else None,
    }


def _diff_features(features: JsonDict) -> JsonDict:
    result: JsonDict = {}
    for key, value in list(features.items()):
        if not key.startswith("wc_home_"):
            continue
        away_key = "wc_away_" + key[len("wc_home_") :]
        if away_key not in features:
            continue
        left = _numeric(value)
        right = _numeric(features.get(away_key))
        if left is not None and right is not None:
            result["wc_diff_" + key[len("wc_home_") :]] = left - right
    return result


def _append_history(
    match: InternationalMatch,
    histories: dict[str, list[TeamMatchRecord]],
    ratings: RatingState,
) -> None:
    home_points = 3.0 if match.target == "HOME" else 1.0 if match.target == "DRAW" else 0.0
    away_points = 3.0 if match.target == "AWAY" else 1.0 if match.target == "DRAW" else 0.0
    histories[_key(match.home_team)].append(
        TeamMatchRecord(
            match_date=match.match_date,
            points=home_points,
            goals_for=match.home_score,
            goals_against=match.away_score,
            neutral=match.neutral,
            tournament=match.tournament,
            opponent_elo=ratings.rating(match.away_team),
        )
    )
    histories[_key(match.away_team)].append(
        TeamMatchRecord(
            match_date=match.match_date,
            points=away_points,
            goals_for=match.away_score,
            goals_against=match.home_score,
            neutral=match.neutral,
            tournament=match.tournament,
            opponent_elo=ratings.rating(match.home_team),
        )
    )


def is_official(tournament: str) -> bool:
    normalized = tournament.casefold()
    return "friendly" not in normalized and any(key in normalized for key in OFFICIAL_KEYWORDS)


def is_world_cup(tournament: str) -> bool:
    normalized = tournament.casefold()
    return (
        "world cup" in normalized
        and "qualification" not in normalized
        and "qualifier" not in normalized
    )


def is_world_cup_qualification(tournament: str) -> bool:
    normalized = tournament.casefold()
    return "world cup" in normalized and (
        "qualification" in normalized or "qualifier" in normalized
    )


def is_continental(tournament: str) -> bool:
    normalized = tournament.casefold()
    return any(key in normalized for key in CONTINENTAL_KEYWORDS)


def _eligible_matches(
    matches: list[InternationalMatch],
    start_year: int,
) -> list[InternationalMatch]:
    return [
        match
        for match in sorted(matches, key=lambda item: item.match_date)
        if match.match_date.year >= start_year
    ]


def _weighted_form(
    history: list[TeamMatchRecord],
    prediction_date: date,
    *,
    config: WorldCupFeatureConfig,
) -> float | None:
    weighted: list[tuple[float, float]] = []
    for row in history:
        age_days = max((prediction_date - row.match_date).days, 0)
        weight = 0.5 ** (age_days / config.form_half_life_days)
        weighted.append((row.points / 3.0, weight))
    if not weighted:
        return None
    total = sum(weight for _value, weight in weighted)
    return sum(value * weight for value, weight in weighted) / total


def _avg(values: list[float] | list[int]) -> float | None:
    return None if not values else float(sum(values) / len(values))


def _rate(values: Any) -> float | None:
    items = [bool(value) for value in values]
    return None if not items else float(sum(items) / len(items))


def _days_since(records: list[TeamMatchRecord], prediction_date: date) -> int | None:
    if not records:
        return None
    return max((prediction_date - records[-1].match_date).days, 0)


def _logistic_expectation(left: float, right: float) -> float:
    return 1.0 / (1.0 + 10 ** ((right - left) / 400.0))


def _bounded(value: float, lower: float, upper: float) -> float:
    if not math.isfinite(value):
        return (lower + upper) / 2
    return min(max(value, lower), upper)


def _numeric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _key(team: str) -> str:
    return normalize_team_name(team)
