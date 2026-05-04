from __future__ import annotations

from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.prediction.explain import explain_prediction


def test_explain_prediction_returns_french_factors_for_available_edges() -> None:
    explanations = explain_prediction(
        features={
            "market_home": 0.58,
            "market_draw": 0.24,
            "market_away": 0.18,
            "home_team_global_last5_ppg": 2.0,
            "away_team_global_last5_ppg": 1.1,
            "home_team_home_last5_ppg": 2.2,
            "away_team_away_last5_ppg": 0.8,
            "home_team_absence_impact_score": 0.1,
            "away_team_absence_impact_score": 0.4,
            "home_team_xi_stability_score": 0.82,
            "away_team_xi_stability_score": 0.61,
            "points_diff": 8,
            "home_team_global_pseudo_xg_avg_last5": 1.7,
            "away_team_global_pseudo_xg_avg_last5": 1.0,
            "odds_movement_home": -0.15,
        },
        probabilities=ProbabilityTriple(0.58, 0.24, 0.18),
        data_quality={"overall_data_quality_score": 76},
        sources_used=("sport", "market"),
        sport_source="model",
        home_team_name="Equipe Domicile",
        away_team_name="Equipe Exterieure",
        max_items=6,
    )

    assert explanations
    assert any("marche" in item.casefold() for item in explanations)
    assert any("Equipe Domicile" in item for item in explanations)


def test_explain_prediction_mentions_missing_sources_without_inventing_values() -> None:
    explanations = explain_prediction(
        features={},
        probabilities=ProbabilityTriple(0.40, 0.31, 0.29),
        data_quality={"overall_data_quality_score": 18},
        sources_used=(),
        max_items=5,
    )

    assert any("indisponible" in item.casefold() for item in explanations)
    assert any("fallback" in item.casefold() for item in explanations)
