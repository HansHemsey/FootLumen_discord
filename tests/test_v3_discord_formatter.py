from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from football_predictor.discord.v3_formatter import format_prediction_v3_markdown
from football_predictor.modeling.probabilities import ProbabilityTriple


def test_v3_message_contains_expected_sections_and_closed_block() -> None:
    message = format_prediction_v3_markdown(_prediction())

    assert message.startswith("```md")
    assert message.endswith("\n```")
    assert "PRÉDICTION FOOTBALL — V3" in message
    assert "Fenêtre : M-30" in message
    assert "Probabilités modèle V3 (finales)" in message
    assert "Décomposition V3" in message
    assert "Risque de nul" in message
    assert "Avantage hors nul" in message
    assert "Qualité des données" in message


def test_v3_probabilities_components_and_v2_are_formatted() -> None:
    message = format_prediction_v3_markdown(_prediction())

    assert "- Domicile  : 52.0%" in message
    assert "- Nul       : 28.0%" in message
    assert "- Extérieur : 20.0%" in message
    assert "Risque de nul        : 28.0% (moyen)" in message
    assert "Home (62.0%)" in message
    assert "Comparaison V2" in message
    assert "- Domicile  : 33.0%" in message


def test_v3_formatter_hides_v2_section_when_missing() -> None:
    message = format_prediction_v3_markdown(_prediction(v2_probabilities=None))

    assert "Comparaison V2" not in message


def test_v3_formatter_truncates_and_masks_secrets() -> None:
    webhook = "https://discord.com/api/webhooks/123456/synthetic-secret"
    prediction = _prediction(
        top_factors_draw_risk=[
            {"name": f"api_key=synthetic-secret-value {webhook}", "value": 0.9}
            for _ in range(20)
        ],
        key_absences_json={
            "home": [{"player_name": "token=abc123syntheticsecret", "reason": webhook}],
            "away": [],
        },
    )
    prediction.match_label = f"Synthetic Home vs {webhook}"

    message = format_prediction_v3_markdown(prediction, limit=700)

    assert len(message) <= 700
    assert message.endswith("\n```")
    assert webhook not in message
    assert "synthetic-secret-value" not in message
    assert "abc123syntheticsecret" not in message
    assert "[secret masqué]" in message


def _prediction(
    *,
    v2_probabilities: ProbabilityTriple | None = ProbabilityTriple(0.33, 0.34, 0.33),
    top_factors_draw_risk: list[dict] | None = None,
    key_absences_json: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        match_label="Synthetic Home vs Synthetic Away",
        competition="Synthetic League",
        match_date=datetime(2026, 5, 3, 19, 0, tzinfo=UTC),
        prediction_time=datetime(2026, 5, 3, 18, 30, tzinfo=UTC),
        probabilities=ProbabilityTriple(0.52, 0.28, 0.20),
        predicted_result="HOME",
        confidence_label="Medium",
        confidence_score=48.2,
        draw_risk_probability=0.28,
        home_no_draw_probability=0.62,
        away_no_draw_probability=0.38,
        v2_probabilities=v2_probabilities,
        market_probabilities=ProbabilityTriple(0.46, 0.29, 0.25),
        draw_risk_label="moyen",
        no_draw_winner_label="Home",
        top_factors_draw_risk=top_factors_draw_risk
        if top_factors_draw_risk is not None
        else [{"name": "draw_risk_parity_score", "value": 0.71}],
        top_factors_no_draw_winner=[
            {"name": "ndw_home_away_strength_edge", "value": 0.43}
        ],
        key_absences_json=key_absences_json
        if key_absences_json is not None
        else {"home": [], "away": []},
        data_quality_json={
            "overall_data_quality_score": 82,
            "odds_available_flag": True,
            "official_lineup_available_flag": False,
            "injuries_available_flag": True,
            "historical_player_stats_available_rate": 1.0,
        },
    )
