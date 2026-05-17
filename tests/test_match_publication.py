from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from football_predictor.cli import app
from football_predictor.config.competitions import CompetitionConfig
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.discord.config import (
    load_discord_channels_config,
    load_discord_webhooks_config,
)
from football_predictor.discord.match_formatters import (
    format_match_analysis_message,
    format_match_result_message,
)
from football_predictor.discord.match_publication import (
    publish_match_analyses,
    publish_match_results,
)
from football_predictor.discord.service import DiscordDeliveryService
from football_predictor.reference.loaders import load_api_football_reference


def test_match_analysis_formatter_is_closed_and_under_limit() -> None:
    fixture, prediction, snapshot = _fixture_prediction_snapshot(
        fixture_date=datetime(2026, 5, 3, 18, tzinfo=UTC),
        prediction_time=datetime(2026, 5, 3, 12, tzinfo=UTC),
    )

    message = format_match_analysis_message(
        fixture=fixture,
        prediction=prediction,
        features=snapshot.features_json,
    )

    assert message.startswith("```md")
    assert message.endswith("```")
    assert len(message) <= 2000
    assert "ANALYSE AVANT-MATCH H-6" in message
    assert "Forme récente" in message
    assert "Marché" in message
    assert "Conclusion" in message


def test_match_result_formatter_compares_prediction() -> None:
    fixture, prediction, _snapshot = _fixture_prediction_snapshot(
        fixture_date=datetime(2026, 5, 3, 18, tzinfo=UTC),
        prediction_time=datetime(2026, 5, 3, 12, tzinfo=UTC),
    )
    fixture.status_short = "FT"
    fixture.home_goals = 2
    fixture.away_goals = 1

    message = format_match_result_message(fixture=fixture, prediction=prediction)

    assert message.startswith("```md")
    assert message.endswith("```")
    assert len(message) <= 2000
    assert "Score final : 2-1" in message
    assert "Pronostic : correct" in message


def test_publish_match_analyses_due_and_dedupe(tmp_path: Path, reference_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'analyses.db'}")
    session_factory = create_session_factory(engine)
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config(_channels_config(tmp_path), reference)
    webhooks = load_discord_webhooks_config(_webhooks_config(tmp_path), reference)
    competition = _competition()

    with session_scope(session_factory) as session:
        fixture, prediction, snapshot = _fixture_prediction_snapshot(
            fixture_date=datetime(2026, 5, 3, 18, tzinfo=UTC),
            prediction_time=datetime(2026, 5, 3, 12, tzinfo=UTC),
        )
        _persist_fixture_prediction(session, fixture, prediction, snapshot)
        summary = publish_match_analyses(
            session=session,
            competitions=[competition],
            delivery=DiscordDeliveryService(
                session,
                channels_config=channels,
                webhooks_config=webhooks,
            ),
            reference=reference,
            target_date=date(2026, 5, 3),
            now=datetime(2026, 5, 3, 12, 10, tzinfo=UTC),
            dry_run=True,
        )
        sent = session.query(models.DiscordMessage).one()
        sent.status = "sent"
        sent.dry_run = False
        sent.payload_json = {
            **(sent.payload_json if isinstance(sent.payload_json, dict) else {}),
            "analysis_window": "T-6",
        }
        session.flush()
        second = publish_match_analyses(
            session=session,
            competitions=[competition],
            delivery=DiscordDeliveryService(
                session,
                channels_config=channels,
                webhooks_config=webhooks,
            ),
            reference=reference,
            target_date=date(2026, 5, 3),
            now=datetime(2026, 5, 3, 12, 12, tzinfo=UTC),
            dry_run=True,
        )

    assert summary.dry_run == 1
    assert sent.channel_key == "analyses"
    assert second.duplicate_skipped == 1


def test_publish_match_analyses_respects_h6_grace_window(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'analyses_window.db'}")
    session_factory = create_session_factory(engine)
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config(_channels_config(tmp_path), reference)
    webhooks = load_discord_webhooks_config(_webhooks_config(tmp_path), reference)
    competition = _competition()

    with session_scope(session_factory) as session:
        fixture, prediction, snapshot = _fixture_prediction_snapshot(
            fixture_date=datetime(2026, 5, 3, 18, tzinfo=UTC),
            prediction_time=datetime(2026, 5, 3, 12, tzinfo=UTC),
        )
        _persist_fixture_prediction(session, fixture, prediction, snapshot)
        before = publish_match_analyses(
            session=session,
            competitions=[competition],
            delivery=DiscordDeliveryService(
                session,
                channels_config=channels,
                webhooks_config=webhooks,
            ),
            reference=reference,
            target_date=date(2026, 5, 3),
            now=datetime(2026, 5, 3, 11, 59, tzinfo=UTC),
            dry_run=True,
        )
        after = publish_match_analyses(
            session=session,
            competitions=[competition],
            delivery=DiscordDeliveryService(
                session,
                channels_config=channels,
                webhooks_config=webhooks,
            ),
            reference=reference,
            target_date=date(2026, 5, 3),
            now=datetime(2026, 5, 3, 12, 16, tzinfo=UTC),
            dry_run=True,
        )

    assert before.skipped == 1
    assert before.results[0].reason == "not_in_h6_grace_window"
    assert after.skipped == 1
    assert after.results[0].reason == "not_in_h6_grace_window"


def test_publish_match_analyses_skips_insufficient_data(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'analyses_quality.db'}")
    session_factory = create_session_factory(engine)
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config(_channels_config(tmp_path), reference)
    webhooks = load_discord_webhooks_config(_webhooks_config(tmp_path), reference)
    competition = _competition()

    with session_scope(session_factory) as session:
        fixture, prediction, snapshot = _fixture_prediction_snapshot(
            fixture_date=datetime(2026, 5, 3, 18, tzinfo=UTC),
            prediction_time=datetime(2026, 5, 3, 12, tzinfo=UTC),
        )
        snapshot.features_json = {}
        snapshot.data_quality_json = {"overall_data_quality_score": 20}
        _persist_fixture_prediction(session, fixture, prediction, snapshot)
        summary = publish_match_analyses(
            session=session,
            competitions=[competition],
            delivery=DiscordDeliveryService(
                session,
                channels_config=channels,
                webhooks_config=webhooks,
            ),
            reference=reference,
            target_date=date(2026, 5, 3),
            now=datetime(2026, 5, 3, 12, 10, tzinfo=UTC),
            dry_run=True,
        )
        messages = list(session.query(models.DiscordMessage).all())

    assert summary.skipped == 1
    assert summary.results[0].reason == "insufficient_analysis_data"
    assert messages == []


def test_publish_match_results_uses_published_prediction(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'results.db'}")
    session_factory = create_session_factory(engine)
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config(_channels_config(tmp_path), reference)
    webhooks = load_discord_webhooks_config(_webhooks_config(tmp_path), reference)
    competition = _competition()

    with session_scope(session_factory) as session:
        fixture, prediction, snapshot = _fixture_prediction_snapshot(
            fixture_date=datetime(2026, 5, 3, 18, tzinfo=UTC),
            prediction_time=datetime(2026, 5, 3, 12, tzinfo=UTC),
        )
        fixture.status_short = "FT"
        fixture.home_goals = 2
        fixture.away_goals = 1
        _persist_fixture_prediction(session, fixture, prediction, snapshot)
        session.add(
            models.DiscordMessage(
                fixture_id=fixture.fixture_id,
                model_prediction_id=prediction.id,
                league_id=61,
                season=2025,
                channel_key="predictions",
                message_type="prediction",
                status="sent",
                dry_run=False,
                print_only=False,
                webhook_hash="synthetic",
                webhook_url_hash="synthetic",
                message_hash="prediction-message",
                message_markdown="```md\nprediction\n```",
                payload_json={},
                route_json={},
                response_json={},
            )
        )
        summary = publish_match_results(
            session=session,
            competitions=[competition],
            delivery=DiscordDeliveryService(
                session,
                channels_config=channels,
                webhooks_config=webhooks,
            ),
            target_date=date(2026, 5, 3),
            dry_run=True,
        )
        result_message = (
            session.query(models.DiscordMessage)
            .filter(models.DiscordMessage.message_type == "result")
            .one()
        )

    assert summary.dry_run == 1
    assert "Pronostic : correct" in result_message.message_markdown
    assert result_message.model_prediction_id == prediction.id


def test_publish_match_results_does_not_use_unpublished_internal_prediction(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'results_unpublished.db'}")
    session_factory = create_session_factory(engine)
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config(_channels_config(tmp_path), reference)
    webhooks = load_discord_webhooks_config(_webhooks_config(tmp_path), reference)
    competition = _competition()

    with session_scope(session_factory) as session:
        fixture, prediction, snapshot = _fixture_prediction_snapshot(
            fixture_date=datetime(2026, 5, 3, 18, tzinfo=UTC),
            prediction_time=datetime(2026, 5, 3, 12, tzinfo=UTC),
        )
        fixture.status_short = "FT"
        fixture.home_goals = 2
        fixture.away_goals = 1
        _persist_fixture_prediction(session, fixture, prediction, snapshot)
        summary = publish_match_results(
            session=session,
            competitions=[competition],
            delivery=DiscordDeliveryService(
                session,
                channels_config=channels,
                webhooks_config=webhooks,
            ),
            target_date=date(2026, 5, 3),
            dry_run=True,
        )
        result_message = (
            session.query(models.DiscordMessage)
            .filter(models.DiscordMessage.message_type == "result")
            .one()
        )

    assert summary.dry_run == 1
    assert "Choix : non disponible" in result_message.message_markdown
    assert "aucune prédiction pré-match retrouvée" in result_message.message_markdown
    assert result_message.model_prediction_id is None


def test_publish_match_results_compares_published_v3_prediction(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'results_v3.db'}")
    session_factory = create_session_factory(engine)
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config(_channels_config(tmp_path), reference)
    webhooks = load_discord_webhooks_config(_webhooks_config(tmp_path), reference)
    competition = _competition()

    with session_scope(session_factory) as session:
        fixture, _prediction, _snapshot = _fixture_prediction_snapshot(
            fixture_date=datetime(2026, 5, 3, 18, tzinfo=UTC),
            prediction_time=datetime(2026, 5, 3, 12, tzinfo=UTC),
        )
        fixture.status_short = "FT"
        fixture.home_goals = 2
        fixture.away_goals = 1
        session.add_all(
            [
                models.Team(team_id=fixture.home_team_id, name=fixture.home_team),
                models.Team(team_id=fixture.away_team_id, name=fixture.away_team),
                models.League(league_id=fixture.league_id, season=fixture.season, name="Ligue 1"),
                fixture,
            ]
        )
        session.flush()
        snapshot = models.V3FeatureSnapshot(
            fixture_id=fixture.fixture_id,
            prediction_time=datetime(2026, 5, 3, 12, tzinfo=UTC),
            feature_version="v3-test-result",
            official_lineup_available_flag=False,
            features_json={},
            data_quality_json={},
        )
        session.add(snapshot)
        session.flush()
        prediction = models.V3ModelPrediction(
            fixture_id=fixture.fixture_id,
            v3_feature_snapshot_id=snapshot.id,
            prediction_time=datetime(2026, 5, 3, 12, tzinfo=UTC),
            model_version="synthetic-v3",
            fusion_strategy="deterministic_fallback",
            p_v3_final_home=0.64,
            p_v3_final_draw=0.20,
            p_v3_final_away=0.16,
            p_v3_draw_risk=0.20,
            p_v3_home_no_draw=0.80,
            p_v3_away_no_draw=0.20,
            confidence_score=76.0,
            confidence_label="High",
            predicted_result="HOME",
            expert_probabilities_json={},
            explanations_json=[],
            data_quality_json={},
            payload_json={"competition": "Ligue 1"},
        )
        session.add(prediction)
        session.flush()
        session.add(
            models.DiscordMessage(
                fixture_id=fixture.fixture_id,
                model_prediction_id=None,
                league_id=61,
                season=2025,
                channel_key="predictions",
                message_type="prediction",
                status="sent",
                dry_run=False,
                print_only=False,
                webhook_hash="synthetic",
                webhook_url_hash="synthetic",
                message_hash="prediction-v3-message",
                message_markdown="```md\nv3 prediction\n```",
                payload_json={"v3_model_prediction_id": prediction.id, "daily_window": "late"},
                route_json={},
                response_json={},
            )
        )
        summary = publish_match_results(
            session=session,
            competitions=[competition],
            delivery=DiscordDeliveryService(
                session,
                channels_config=channels,
                webhooks_config=webhooks,
            ),
            target_date=date(2026, 5, 3),
            dry_run=True,
        )
        result_message = (
            session.query(models.DiscordMessage)
            .filter(models.DiscordMessage.message_type == "result")
            .one()
        )

    assert summary.dry_run == 1
    assert "Pronostic : correct" in result_message.message_markdown
    assert result_message.model_prediction_id is None


def test_publish_match_cli_and_scripts(repo_root: Path) -> None:
    help_result = CliRunner().invoke(app, ["publish-match-analyses", "--help"])
    result_help = CliRunner().invoke(app, ["publish-match-results", "--help"])

    assert help_result.exit_code == 0
    assert result_help.exit_code == 0
    assert "--refresh-data" in help_result.stdout
    assert "Minutes after H-6" in help_result.stdout
    assert "--dry-run" in result_help.stdout
    analyses_script = (repo_root / "scripts" / "publish_match_analyses.sh").read_text(
        encoding="utf-8"
    )
    results_script = (repo_root / "scripts" / "publish_match_results.sh").read_text(
        encoding="utf-8"
    )
    daily_late = (repo_root / "scripts" / "daily_late.sh").read_text(encoding="utf-8")
    assert "publish-match-analyses" in analyses_script
    assert 'ANALYSIS_GRACE_MINUTES="${ANALYSIS_GRACE_MINUTES:-15}"' in analyses_script
    assert "publish-match-results" in results_script
    assert 'DRY_RUN="${DRY_RUN:-true}"' in analyses_script
    assert 'DRY_RUN="${DRY_RUN:-true}"' in results_script
    assert 'PUBLISH_ANALYSES="${PUBLISH_ANALYSES:-false}"' in daily_late
    assert 'PUBLISH_RESULTS="${PUBLISH_RESULTS:-false}"' in daily_late


def _fixture_prediction_snapshot(
    *,
    fixture_date: datetime,
    prediction_time: datetime,
) -> tuple[models.Fixture, models.ModelPrediction, models.FeatureSnapshot]:
    fixture = models.Fixture(
        fixture_id=-91001,
        date=fixture_date,
        league_id=61,
        season=2025,
        round="Regular Season - 1",
        status="NS",
        status_short="NS",
        home_team_id=-91011,
        away_team_id=-91012,
        home_team="Synthetic Home",
        away_team="Synthetic Away",
        venue_name="Synthetic Stadium",
        payload_json={"synthetic": True},
    )
    snapshot = models.FeatureSnapshot(
        fixture_id=fixture.fixture_id,
        prediction_time=prediction_time,
        feature_version="v1",
        features_json={
            "home_team_global_last5_ppg": 2.0,
            "away_team_global_last5_ppg": 1.1,
            "home_team_global_goal_diff_avg_last5": 0.8,
            "away_team_global_goal_diff_avg_last5": -0.2,
            "home_team_global_pseudo_xg_avg_last5": 1.7,
            "away_team_global_pseudo_xg_avg_last5": 0.9,
            "rank_diff": -3,
            "points_diff": 5,
            "market_home": 0.52,
            "market_draw": 0.27,
            "market_away": 0.21,
            "market_bookmaker_count": 4,
            "odds_movement_home": -0.02,
            "home_team_availability_score": 0.92,
            "away_team_availability_score": 0.78,
            "home_team_probable_formation": "4-3-3",
            "away_team_probable_formation": "4-2-3-1",
            "home_team_xi_stability_score": 0.81,
            "away_team_xi_stability_score": 0.69,
            "home_team_key_absences_json": [
                {"name": "Synthetic Starter", "reason": "Missing Fixture"}
            ],
        },
        data_quality_json={"overall_data_quality_score": 72},
    )
    prediction = models.ModelPrediction(
        fixture_id=fixture.fixture_id,
        feature_snapshot_id=0,
        prediction_time=prediction_time,
        model_version="synthetic-v1",
        p_home=0.55,
        p_draw=0.25,
        p_away=0.20,
        predicted_outcome="HOME",
        predicted_result="HOME",
        confidence=44.0,
        confidence_label="Medium",
        confidence_score=44.0,
        explanation_json=["Synthétique"],
        explanations_json=["Synthétique"],
        data_quality_json={"overall_data_quality_score": 72},
        payload_json={"competition": "Ligue 1"},
    )
    return fixture, prediction, snapshot


def _persist_fixture_prediction(
    session,
    fixture: models.Fixture,
    prediction: models.ModelPrediction,
    snapshot: models.FeatureSnapshot,
) -> None:
    session.add_all(
        [
            models.Team(team_id=fixture.home_team_id, name=fixture.home_team),
            models.Team(team_id=fixture.away_team_id, name=fixture.away_team),
            models.League(league_id=fixture.league_id, season=fixture.season, name="Ligue 1"),
            fixture,
        ]
    )
    session.flush()
    session.add(snapshot)
    session.flush()
    prediction.feature_snapshot_id = snapshot.id
    session.add(prediction)
    session.flush()


def _competition() -> CompetitionConfig:
    return CompetitionConfig(
        key="ligue1",
        league_id=61,
        season=2025,
        name="Ligue 1",
        country="France",
        enabled=True,
    )


def _channels_config(tmp_path: Path) -> Path:
    path = tmp_path / "discord_channels.yaml"
    path.write_text(
        """
competitions:
  ligue1:
    display_name: "Ligue 1"
    league_id: 61
    season: 2025
    enabled: true
    channels:
      analyses:
        channel_name: "analyses"
        enabled: true
      resultats:
        channel_name: "resultats"
        enabled: true
      predictions:
        channel_name: "predictions"
        enabled: true
""".lstrip(),
        encoding="utf-8",
    )
    return path


def _webhooks_config(tmp_path: Path) -> Path:
    path = tmp_path / "discord_webhooks.yaml"
    path.write_text(
        """
webhooks:
  ligue1:
    analyses:
      webhook_url: ""
      enabled: true
    resultats:
      webhook_url: ""
      enabled: true
    predictions:
      webhook_url: ""
      enabled: true
""".lstrip(),
        encoding="utf-8",
    )
    return path
