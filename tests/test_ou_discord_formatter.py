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
    assert "🎯 SCÉNARIO MODÈLE" in message
    assert "💰 PICK VALUE" in message
    assert "Scénario le plus probable : Plus de 2.5 buts — 72.0%" in message
    assert "Côté : Plus de 2.5 buts" in message
    assert "Confiance V2 : 88/100 · VERY HIGH" in message
    assert "Data quality : 85/100" in message
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


def test_ou_formatter_separates_forecast_and_value_side() -> None:
    prediction = _prediction(
        p_over=0.54,
        p_under=0.46,
        forecast_side="OVER",
        value_side="UNDER",
        edge_over=-0.09,
        edge_under=0.09,
        ev_over=-0.19,
        ev_under=0.13,
        p_pick=0.46,
        market_p_pick=0.37,
        odd_pick=2.45,
        edge_pick=0.09,
        ev_pick=0.13,
        value_edge=0.09,
        value_ev=0.13,
        confidence_score=72.0,
        confidence_label="High",
    )

    message = format_ou_prediction_markdown(prediction)

    assert "Scénario le plus probable : Plus de 2.5 buts — 54.0%" in message
    assert "Côté : Moins de 2.5 buts" in message
    assert "Edge : +9.0 pts" in message
    assert "EV : +13.0%" in message


def test_ou_formatter_displays_no_bet_reason() -> None:
    prediction = _prediction(
        forecast_side="OVER",
        value_side=None,
        no_bet_reason="ev_below_threshold",
        confidence_score=0.0,
        confidence_label="Uncertain",
        value_edge=None,
        value_ev=None,
    )

    message = format_ou_prediction_markdown(prediction)

    assert "💰 PICK VALUE\nAucun pick public" in message
    assert "Aucun pick value publiable" in message
    assert "Raison no bet : EV insuffisante" in message


def test_ou_formatter_does_not_promote_legacy_forecast_as_value_pick() -> None:
    prediction = _prediction(
        value_side=None,
        p_pick=None,
        market_p_pick=None,
        odd_pick=None,
        edge_pick=None,
        ev_pick=None,
        value_edge=None,
        value_ev=None,
        no_bet_reason=None,
        non_publication_reason="legacy_decision_version",
        publication_decision="staff",
        decision_version=None,
        ou_decision_version=None,
    )

    message = format_ou_prediction_markdown(prediction)

    assert "Scénario le plus probable : Plus de 2.5 buts — 72.0%" in message
    assert "💰 PICK VALUE\nAucun pick public" in message
    assert "Côté : Plus de 2.5 buts" not in message
    assert "staff-only / non publiable" in message
    assert "version de décision O/U legacy" in message


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
        "forecast_side": "OVER",
        "forecast_probability": 0.72,
        "value_side": "OVER",
        "p_pick": 0.72,
        "market_p_pick": 0.55,
        "odd_pick": 1.90,
        "edge_pick": 0.17,
        "ev_pick": 0.36,
        "is_value_pick": True,
        "value_edge": 0.17,
        "value_ev": 0.36,
        "no_bet_reason": None,
        "non_publication_reason": None,
        "confidence_score_v2": 88.0,
        "confidence_label_v2": "Very High",
        "publication_decision": "public",
        "decision_version": "ou_decision_v2",
        "confidence_score": 88.0,
        "confidence_label": "Very High",
        "kickoff_time": datetime(2026, 5, 3, 19, 0, tzinfo=UTC),
        "match_label": "Synthetic Home vs Synthetic Away",
        "competition": "Synthetic League",
        "expert_probabilities": {"logistic": 0.71, "lgbm": 0.73, "poisson": 0.62},
        "data_quality_json": {"overall_data_quality_score": 85, "ou_odds_available": True},
        "ou_model_prediction_id": 1,
    }
    data.update(overrides)
    return SimpleNamespace(**data)
