from __future__ import annotations

from football_predictor.discord.formatter import format_prediction_markdown
from football_predictor.features.data_quality import DataQuality
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.prediction.service import PredictionOutput
from football_predictor.utils.time import utc_now


def test_discord_formatter_contains_required_sections_and_closed_block() -> None:
    markdown = format_prediction_markdown(_prediction())

    assert markdown.startswith("```md")
    assert markdown.endswith("\n```")
    assert "🏟️ PRÉDICTION FOOTBALL" in markdown
    assert "Match : Equipe A vs Equipe B" in markdown
    assert "Compétition : Competition synthetique" in markdown
    assert "Résultat prédit : victoire domicile" in markdown
    assert "Confiance : Very High" in markdown
    assert "Probabilités modèle :" in markdown
    assert "Probabilités marché :" in markdown
    assert "Facteurs clés :" in markdown
    assert "Absences clés :" in markdown
    assert "Qualité des données :" in markdown
    assert "Lineups officielles cible :" in markdown
    assert "Historique lineups :" in markdown
    assert "Stats joueurs historiques :" in markdown
    assert "Note : prédiction probabiliste, pas une certitude." in markdown


def test_discord_formatter_uses_real_market_probabilities_when_available() -> None:
    markdown = format_prediction_markdown(
        _prediction(market_probabilities=ProbabilityTriple(0.50, 0.30, 0.20))
    )

    assert "Probabilités marché :" in markdown
    assert "- Domicile  : 50.0%" in markdown
    assert "indisponibles" not in markdown


def test_discord_formatter_marks_missing_market_as_unavailable() -> None:
    markdown = format_prediction_markdown(_prediction(market_probabilities=None))

    assert "Probabilités marché : non disponible" in markdown
    assert "- Domicile  : 33.3%" not in markdown


def test_discord_formatter_outputs_absences_without_inventing_when_empty() -> None:
    markdown = format_prediction_markdown(_prediction(key_absences_json={}))

    assert "- non disponible avant prediction_time" in markdown
    assert "Joueur inventé" not in markdown


def test_discord_formatter_outputs_existing_absences_only() -> None:
    markdown = format_prediction_markdown(
        _prediction(
            key_absences_json={
                "home": [
                    {
                        "player_name": "Joueur Synthetique A",
                        "reason": "Blessure",
                        "absence_impact": 0.42,
                    }
                ],
                "away": [],
            }
        )
    )

    assert "Joueur Synthetique A" in markdown
    assert "Blessure" in markdown
    assert "impact 0.42" in markdown


def test_discord_formatter_closes_block_when_truncated() -> None:
    prediction = _prediction(explanations=["x" * 500, "y" * 500, "z" * 500])

    markdown = format_prediction_markdown(prediction, limit=500)

    assert markdown.startswith("```md")
    assert markdown.endswith("\n```")
    assert len(markdown) <= 500
    assert "message tronqué" in markdown


def test_discord_formatter_masks_secrets_in_free_text() -> None:
    webhook = "https://discord.com/api/webhooks/123/very-secret"
    markdown = format_prediction_markdown(
        _prediction(
            explanations=[
                f"Webhook {webhook}",
                "api_key=synthetic-secret-value",
            ],
            key_absences_json={
                "home": [{"player_name": "token=abc123", "reason": webhook}],
            },
        )
    )

    assert webhook not in markdown
    assert "synthetic-secret-value" not in markdown
    assert "[secret masqué]" in markdown


def _prediction(
    *,
    market_probabilities: ProbabilityTriple | None = ProbabilityTriple(0.45, 0.30, 0.25),
    explanations: list[str] | None = None,
    key_absences_json: dict | None = None,
) -> PredictionOutput:
    now = utc_now()
    return PredictionOutput(
        fixture_id=0,  # synthetic formatter-only object
        match_label="Equipe A vs Equipe B",
        competition="Competition synthetique",
        match_date=now,
        prediction_time=now,
        probabilities=ProbabilityTriple(0.60, 0.25, 0.15),
        predicted_result="HOME",
        confidence_label="Very High",
        confidence_score=78.4,
        explanations=explanations or ["Facteur synthetique 1", "Facteur synthetique 2"],
        data_quality=DataQuality(
            odds_available=market_probabilities is not None,
            injuries_available=True,
            official_lineups_available=True,
            player_stats_available=True,
        ),
        data_quality_json={
            "overall_data_quality_score": 82,
            "target_lineups_available_flag": True,
            "historical_lineups_available_flag": True,
            "historical_player_stats_available_rate": 1.0,
        },
        market_probabilities=market_probabilities,
        key_absences_json=key_absences_json
        if key_absences_json is not None
        else {
            "home": [{"player_name": "Joueur Synthetique", "reason": "Suspendu"}],
            "away": [],
        },
    )
