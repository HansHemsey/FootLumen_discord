from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from football_predictor.discord.formatter import (
    format_prediction_markdown,
    truncate_discord_message,
)
from football_predictor.modeling.probabilities import ProbabilityTriple


def test_message_starts_and_ends_with_markdown_code_block() -> None:
    message = format_prediction_markdown(_prediction(), _fixture())

    assert message.startswith("```md")
    assert message.endswith("\n```")
    assert "PRÉDICTION FOOTBALL" in message
    assert "Match : Equipe synthetique A vs Equipe synthetique B" in message
    assert "Compétition : Competition synthetique" in message
    assert "Note : prédiction probabiliste, pas une certitude." in message


def test_probabilities_are_formatted_as_percentages() -> None:
    message = format_prediction_markdown(_prediction(), _fixture())

    assert "- Domicile  : 60.0%" in message
    assert "- Nul       : 25.0%" in message
    assert "- Extérieur : 15.0%" in message
    assert "Écart de confiance : 35.0 pts" in message


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        ("HOME", "Résultat prédit : victoire domicile"),
        ("DRAW", "Résultat prédit : match nul"),
        ("AWAY", "Résultat prédit : victoire extérieur"),
    ],
)
def test_predicted_outcome_is_translated(outcome: str, expected: str) -> None:
    message = format_prediction_markdown(_prediction(predicted_outcome=outcome), _fixture())

    assert expected in message


def test_missing_data_is_displayed_as_unavailable() -> None:
    prediction = SimpleNamespace(
        predicted_outcome="HOME",
        probabilities=ProbabilityTriple(0.50, 0.30, 0.20),
        confidence_label=None,
        confidence_score=None,
        explanations=[],
        data_quality_json={},
        market_probabilities=None,
        key_absences_json={},
    )

    message = format_prediction_markdown(prediction, _fixture())

    assert "Confiance : non disponible" in message
    assert "Score de confiance : non disponible" in message
    assert "Probabilités marché : non disponible" in message
    assert "- non disponible avant prediction_time" in message
    assert "Lineups officielles cible : non disponible" in message
    assert "Historique lineups : non disponible" in message
    assert "Stats joueurs historiques : non disponible" in message


def test_features_can_provide_market_probabilities_and_absences() -> None:
    features = {
        "p_market_home": 0.48,
        "p_market_draw": 0.28,
        "p_market_away": 0.24,
        "home_team_key_absences_json": [
            {"player_name": "Joueur synthetique", "reason": "Suspendu"}
        ],
        "away_team_key_absences_json": [],
    }

    message = format_prediction_markdown(
        _prediction(market_probabilities=None, key_absences_json={}),
        _fixture(),
        features,
    )

    assert "Probabilités marché :" in message
    assert "- Domicile  : 48.0%" in message
    assert "Joueur synthetique" in message
    assert "Suspendu" in message


def test_truncation_preserves_code_block_closure() -> None:
    lines = "\n".join(f"Ligne {index} " + "x" * 80 for index in range(80))
    long_message = f"```md\n{lines}\n```"

    truncated = truncate_discord_message(long_message, max_chars=500)

    assert len(truncated) <= 500
    assert truncated.startswith("```md")
    assert truncated.endswith("\n```")
    assert "message tronqué" in truncated


def test_secrets_are_masked_from_rendered_message() -> None:
    webhook = "https://discord.com/api/webhooks/123456/synthetic-secret"
    prediction = _prediction(
        explanations=[
            f"Signal contenant {webhook}",
            "api_key=synthetic-secret-value",
        ],
        key_absences_json={
            "home": [{"player_name": "token=abc123syntheticsecret", "reason": webhook}],
            "away": [],
        },
    )

    message = format_prediction_markdown(prediction, _fixture())

    assert webhook not in message
    assert "synthetic-secret-value" not in message
    assert "abc123syntheticsecret" not in message
    assert "[secret masqué]" in message


def _fixture() -> SimpleNamespace:
    return SimpleNamespace(
        home_team_name="Equipe synthetique A",
        away_team_name="Equipe synthetique B",
        league_name="Competition synthetique",
        date=datetime(2026, 5, 2, 18, 0, tzinfo=UTC),
    )


def _prediction(
    *,
    predicted_outcome: str = "HOME",
    market_probabilities: ProbabilityTriple | None = ProbabilityTriple(0.45, 0.30, 0.25),
    key_absences_json: dict | None = None,
    explanations: list[str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        predicted_outcome=predicted_outcome,
        probabilities=ProbabilityTriple(0.60, 0.25, 0.15),
        confidence_label="High",
        confidence_score=72.4,
        explanations=explanations or ["Facteur synthetique"],
        data_quality_json={
            "overall_data_quality_score": 81,
            "odds_available": market_probabilities is not None,
            "injuries_available": True,
            "target_lineups_available_flag": False,
            "historical_lineups_available_flag": True,
            "historical_player_stats_available_rate": 1.0,
        },
        market_probabilities=market_probabilities,
        key_absences_json=key_absences_json
        if key_absences_json is not None
        else {"home": [], "away": []},
    )
