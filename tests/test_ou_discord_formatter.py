from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from football_predictor.ou_model.discord.ou_formatter import format_ou_prediction_markdown


def test_ou_message_uses_compact_bettor_format_and_closed_block() -> None:
    message = format_ou_prediction_markdown(_prediction())

    assert message.startswith("```md")
    assert message.endswith("\n```")
    assert "⚽ FOOT — PRÉDICTION O/U 2.5 | M-30" in message
    assert "Synthetic Home vs Synthetic Away · Synthetic League" in message
    assert "03/05/2026 · 21:00 Europe/Paris" in message
    assert "▶ Plus de 2.5 buts" in message
    assert "Confiance : VERY HIGH · Score : 88/100" in message
    assert "Plus 2.5" in message
    assert "72.0%" in message
    assert "55.0%" in message
    assert "+17.0 pts" in message
    assert "forte value côté plus de 2.5 buts" in message
    assert "xG attendu : 1.40 + 1.35 = 2.75" in message
    assert "EV estimée : +36.0% / unité" in message
    assert "✅ QUALITÉ DATA" in message


def test_ou_formatter_hides_raw_expert_names() -> None:
    message = format_ou_prediction_markdown(_prediction())

    assert "logistic" not in message
    assert "lgbm" not in message
    assert "poisson" not in message


def test_ou_formatter_handles_missing_market_values_with_na() -> None:
    prediction = _prediction(
        market_p_over=None,
        market_p_under=None,
        edge_over=None,
        edge_under=None,
        xg_home=None,
        xg_away=None,
        xg_total=None,
    )

    message = format_ou_prediction_markdown(prediction)

    assert "N/A" in message
    assert "marché O/U est indisponible" in message
    assert message.endswith("\n```")


def test_ou_formatter_truncates_and_masks_secrets() -> None:
    webhook = "https://discord.com/api/webhooks/123456/synthetic-secret"
    prediction = _prediction(match_label=f"Synthetic Home vs {webhook}")

    message = format_ou_prediction_markdown(prediction, limit=500)

    assert len(message) <= 500
    assert message.endswith("\n```")
    assert webhook not in message
    assert "[secret masqué]" in message


def _prediction(**overrides) -> SimpleNamespace:
    data = {
        "fixture_id": -501,
        "prediction_time": datetime(2026, 5, 3, 18, 30, tzinfo=UTC),
        "model_version": "synthetic-ou",
        "threshold": 2.5,
        "p_over": 0.72,
        "p_under": 0.28,
        "xg_home": 1.40,
        "xg_away": 1.35,
        "xg_total": 2.75,
        "market_p_over": 0.55,
        "market_p_under": 0.45,
        "market_odd_over": 1.90,
        "market_odd_under": 1.90,
        "edge_over": 0.17,
        "edge_under": -0.17,
        "ev_over": 0.36,
        "ev_under": -0.47,
        "confidence_score": 88.0,
        "confidence_label": "Very High",
        "kickoff_time": datetime(2026, 5, 3, 19, 0, tzinfo=UTC),
        "match_label": "Synthetic Home vs Synthetic Away",
        "competition": "Synthetic League",
        "expert_probabilities": {"logistic": 0.71, "lgbm": 0.73, "poisson": 0.62},
        "data_quality_json": {"overall_data_quality_score": 65, "ou_odds_available": True},
        "ou_model_prediction_id": 1,
    }
    data.update(overrides)
    return SimpleNamespace(**data)
