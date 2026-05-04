from __future__ import annotations

import pytest

from football_predictor.modeling.baselines import (
    api_prediction_predict,
    odds_only_predict,
    uniform_predict,
)
from football_predictor.modeling.constants import CLASSES
from football_predictor.modeling.poisson import (
    estimate_lambda_home_away,
    poisson_predict,
    score_matrix,
)


def test_classes_are_in_fixed_order() -> None:
    assert CLASSES == ["HOME", "DRAW", "AWAY"]


def test_odds_only_uses_market_probabilities_and_fallback_prior() -> None:
    probabilities = odds_only_predict(
        {"p_market_home": 0.50, "p_market_draw": 0.25, "p_market_away": 0.25}
    )
    fallback = odds_only_predict({})

    assert probabilities == pytest.approx([0.50, 0.25, 0.25])
    assert fallback == pytest.approx([0.45, 0.27, 0.28])
    assert sum(fallback) == pytest.approx(1.0)


def test_api_and_uniform_baselines_return_valid_probabilities() -> None:
    api = api_prediction_predict(
        {"api_pred_home": 45, "api_pred_draw": 25, "api_pred_away": 30}
    )
    uniform = uniform_predict()

    assert api == pytest.approx([0.45, 0.25, 0.30])
    assert uniform == pytest.approx([1 / 3, 1 / 3, 1 / 3])
    assert sum(api or []) == pytest.approx(1.0)
    assert sum(uniform) == pytest.approx(1.0)


def test_poisson_estimates_lambdas_and_valid_probabilities() -> None:
    features = {
        "home_team_global_goals_for_avg_last10": 2.2,
        "away_team_global_goals_against_avg_last10": 1.8,
        "away_team_global_goals_for_avg_last10": 0.8,
        "home_team_global_goals_against_avg_last10": 0.7,
        "home_team_global_pseudo_xg_avg_last10": 2.0,
    }

    home_lambda, away_lambda = estimate_lambda_home_away(features)
    matrix = score_matrix(home_lambda, away_lambda)
    probabilities = poisson_predict(features)

    assert home_lambda > away_lambda
    assert len(matrix) == 9
    assert len(matrix[0]) == 9
    assert sum(probabilities) == pytest.approx(1.0)
    assert probabilities[0] > probabilities[2]
