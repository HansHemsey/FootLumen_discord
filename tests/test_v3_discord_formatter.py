from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from football_predictor.discord.v3_formatter import format_prediction_v3_markdown
from football_predictor.modeling.probabilities import ProbabilityTriple


def test_v3_message_uses_compact_bettor_format_and_closed_block() -> None:
    message = format_prediction_v3_markdown(_prediction())

    assert message.startswith("```md")
    assert message.endswith("\n```")
    assert "🏟️ FOOT — PRÉDICTION V3 | M-30" in message
    assert "Angers vs Strasbourg · Ligue 1" in message
    assert "10/05/2026 · 21:00 Europe/Paris" in message
    assert "🎯 PICK PRINCIPAL" in message
    assert "▶ Strasbourg gagne" in message
    assert "Confiance : VERY HIGH · Score : 100/100" in message
    assert "📊 PROBABILITÉS" in message
    assert "Modèle" in message and "Marché" in message and "Écart" in message
    assert "Strasbourg" in message
    assert "+38.5 pts" in message
    assert "💡 LECTURE PARIEUR" in message
    assert "forte value côté Strasbourg" in message
    assert "🔁 CONFIRMATION V2 → V3" in message
    assert "XI : probable, lineups officielles indisponibles" in message
    assert "✅ QUALITÉ DATA" in message
    assert "⚠️ Modèle probabiliste à M-30, pas une certitude." in message


def test_v3_factors_are_translated_without_technical_feature_names() -> None:
    message = format_prediction_v3_markdown(_prediction())

    assert "faibles" in message
    assert "dynamique globale" in message
    assert "cotes marché" in message
    assert "draw_risk_" not in message
    assert "ndw_" not in message


def test_v3_formatter_hides_v2_section_when_missing() -> None:
    message = format_prediction_v3_markdown(_prediction(v2_probabilities=None))

    assert "CONFIRMATION V2" not in message


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
    prediction.match_label = f"Angers vs {webhook}"

    message = format_prediction_v3_markdown(prediction, limit=700)

    assert len(message) <= 700
    assert message.endswith("\n```")
    assert webhook not in message
    assert "synthetic-secret-value" not in message
    assert "abc123syntheticsecret" not in message
    assert "[secret masqué]" in message


def _prediction(
    *,
    v2_probabilities: ProbabilityTriple | None = ProbabilityTriple(0.192, 0.245, 0.563),
    top_factors_draw_risk: list[dict] | None = None,
    key_absences_json: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        match_label="Angers vs Strasbourg",
        competition="Ligue 1",
        match_date=datetime(2026, 5, 10, 19, 0, tzinfo=UTC),
        prediction_time=datetime(2026, 5, 10, 18, 30, tzinfo=UTC),
        probabilities=ProbabilityTriple(0.123, 0.122, 0.755),
        predicted_result="AWAY",
        confidence_label="Very High",
        confidence_score=100.0,
        draw_risk_probability=0.256,
        home_no_draw_probability=0.343,
        away_no_draw_probability=0.657,
        v2_probabilities=v2_probabilities,
        market_probabilities=ProbabilityTriple(0.355, 0.275, 0.370),
        draw_risk_label="moyen",
        no_draw_winner_label="Away",
        top_factors_draw_risk=top_factors_draw_risk
        if top_factors_draw_risk is not None
        else [
            {"name": "draw_risk_attacking_weakness", "value": 0.90},
            {"name": "draw_risk_xg_gap_abs", "value": 0.81},
        ],
        top_factors_no_draw_winner=[
            {"name": "ndw_away_ppg_global", "value": 1.60},
            {"name": "ndw_odds_away_prob", "value": 0.51},
        ],
        key_absences_json=key_absences_json
        if key_absences_json is not None
        else {
            "home": [
                {"player_name": "A. Sbaï", "reason": "Red Card"},
                {"player_name": "Y. Belkhdim", "reason": "Arm Injury"},
                {"player_name": "M. Courcoul", "reason": "Injury"},
            ],
            "away": [
                {"player_name": "A. Omobamidele", "reason": "Yellow Cards"},
                {"player_name": "S. El Mourabet", "reason": "Injury"},
                {"player_name": "J. Panichelli", "reason": "Knee Injury"},
            ],
        },
        data_quality_json={
            "overall_data_quality_score": 90,
            "odds_available_flag": True,
            "official_lineup_available_flag": False,
            "injuries_available_flag": True,
            "historical_player_stats_available_rate": 1.0,
        },
    )
