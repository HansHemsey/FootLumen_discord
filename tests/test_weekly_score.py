from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import httpx
from typer.testing import CliRunner

from football_predictor.cli import app
from football_predictor.config.settings import get_settings
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.discord.config import (
    DiscordChannelConfig,
    DiscordChannelsConfig,
    DiscordWebhookRouteConfig,
    DiscordWebhooksConfig,
    load_discord_channels_config,
    load_discord_webhooks_config,
)
from football_predictor.discord.service import DiscordDeliveryService
from football_predictor.discord.weekly_score import (
    WeeklyScoreLine,
    WeeklyScoreReport,
    build_weekly_score_reports,
    format_weekly_score_messages,
    publish_weekly_prediction_score,
)
from football_predictor.reference.loaders import load_api_football_reference


def test_weekly_score_monday_includes_previous_and_current_week(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'weekly.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_prediction(
            session,
            fixture_id=-1,
            kickoff=datetime(2026, 5, 3, 18, tzinfo=UTC),
            home_goals=1,
            away_goals=2,
            predicted="AWAY",
        )
        _seed_prediction(
            session,
            fixture_id=-2,
            kickoff=datetime(2026, 5, 4, 18, tzinfo=UTC),
            home_goals=None,
            away_goals=None,
            predicted="HOME",
            status="NS",
        )
        session.flush()
        reports = build_weekly_score_reports(
            session,
            target_date=date(2026, 5, 4),
            timezone_name="Europe/Paris",
        )

    assert [report.week_key for report in reports] == ["2026-W18", "2026-W19"]
    assert reports[0].completed == 1
    assert reports[0].correct == 1
    assert reports[0].title_suffix == " (finalisation lundi)"
    assert reports[1].total_predictions == 0
    assert reports[1].pending == 0


def test_weekly_score_counts_only_late_sent_finished_predictions(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'weekly_late.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_prediction(
            session,
            fixture_id=-1,
            kickoff=datetime(2026, 5, 3, 12, 30, tzinfo=UTC),
            home_goals=0,
            away_goals=0,
            predicted="HOME",
        )
        _seed_prediction(
            session,
            fixture_id=-2,
            kickoff=datetime(2026, 5, 3, 15, tzinfo=UTC),
            home_goals=1,
            away_goals=0,
            predicted="HOME",
            discord_payload={"automation_window": "mid", "daily_window": "mid"},
        )
        _seed_prediction(
            session,
            fixture_id=-3,
            kickoff=datetime(2026, 5, 3, 18, tzinfo=UTC),
            home_goals=None,
            away_goals=None,
            predicted="AWAY",
            status="NS",
        )
        reports = build_weekly_score_reports(
            session,
            target_date=date(2026, 5, 3),
            timezone_name="Europe/Paris",
            include_previous_week_finalization=False,
        )

    assert len(reports) == 1
    assert reports[0].total_predictions == 1
    assert reports[0].completed == 1
    assert reports[0].incorrect == 1
    assert reports[0].pending == 0
    assert reports[0].lines[0].fixture_id == -1


def test_weekly_score_counts_v3_and_ou_only_when_discord_was_sent(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'weekly_v3_ou.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_v3_prediction(
            session,
            fixture_id=-31,
            kickoff=datetime(2026, 5, 3, 12, 30, tzinfo=UTC),
            home_goals=2,
            away_goals=1,
            predicted="HOME",
            published=True,
        )
        _seed_ou_prediction(
            session,
            fixture_id=-32,
            kickoff=datetime(2026, 5, 3, 15, tzinfo=UTC),
            home_goals=3,
            away_goals=1,
            p_over=0.74,
            p_under=0.26,
            published=True,
        )
        _seed_v3_prediction(
            session,
            fixture_id=-33,
            kickoff=datetime(2026, 5, 3, 18, tzinfo=UTC),
            home_goals=0,
            away_goals=1,
            predicted="AWAY",
            published=False,
        )
        reports = build_weekly_score_reports(
            session,
            target_date=date(2026, 5, 3),
            timezone_name="Europe/Paris",
            include_previous_week_finalization=False,
        )

    assert reports[0].total_predictions == 2
    assert reports[0].completed == 2
    assert reports[0].correct == 2
    families = {line.model_family for line in reports[0].lines}
    assert families == {"1X2 V3", "O/U 2.5"}
    assert {-31, -32} == {line.fixture_id for line in reports[0].lines}


def test_weekly_score_counts_v3_and_ou_from_direct_discord_fks(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'weekly_v3_ou_fks.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_v3_prediction(
            session,
            fixture_id=-131,
            kickoff=datetime(2026, 5, 3, 12, 30, tzinfo=UTC),
            home_goals=2,
            away_goals=1,
            predicted="HOME",
            published=True,
            link_style="columns",
        )
        _seed_ou_prediction(
            session,
            fixture_id=-132,
            kickoff=datetime(2026, 5, 3, 15, tzinfo=UTC),
            home_goals=3,
            away_goals=1,
            p_over=0.74,
            p_under=0.26,
            published=True,
            link_style="columns",
        )
        reports = build_weekly_score_reports(
            session,
            target_date=date(2026, 5, 3),
            timezone_name="Europe/Paris",
            include_previous_week_finalization=False,
        )

    assert reports[0].total_predictions == 2
    assert reports[0].correct == 2
    assert {-131, -132} == {line.fixture_id for line in reports[0].lines}


def test_weekly_score_excludes_non_publication_statuses(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'weekly_non_publication.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        cases = [
            (-201, "duplicate_skipped", False, False),
            (-202, "confidence_skipped", False, False),
            (-203, "deleted_replaced", False, False),
            (-204, "sent", True, False),
            (-205, "sent", False, True),
        ]
        for fixture_id, discord_status, dry_run, print_only in cases:
            _seed_prediction(
                session,
                fixture_id=fixture_id,
                kickoff=datetime(2026, 5, 3, 13, tzinfo=UTC),
                home_goals=1,
                away_goals=0,
                predicted="HOME",
                discord_status=discord_status,
                dry_run=dry_run,
                print_only=print_only,
            )
        reports = build_weekly_score_reports(
            session,
            target_date=date(2026, 5, 3),
            timezone_name="Europe/Paris",
            include_previous_week_finalization=False,
        )

    assert reports[0].total_predictions == 0


def test_weekly_score_excludes_deleted_prediction_messages(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'weekly_deleted_prediction.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        prediction, old_message = _seed_prediction(
            session,
            fixture_id=-211,
            kickoff=datetime(2026, 5, 3, 13, tzinfo=UTC),
            home_goals=1,
            away_goals=0,
            predicted="HOME",
            discord_status="deleted_replaced",
            sent_at=datetime(2026, 5, 3, 11, 40, tzinfo=UTC),
        )
        new_message = _prediction_message(
            fixture_id=-211,
            prediction_id=prediction.id,
            message_hash="prediction-new--211",
            sent_at=datetime(2026, 5, 3, 11, 50, tzinfo=UTC),
        )
        session.add(new_message)
        reports = build_weekly_score_reports(
            session,
            target_date=date(2026, 5, 3),
            timezone_name="Europe/Paris",
            include_previous_week_finalization=False,
        )

    assert reports[0].total_predictions == 1
    assert reports[0].lines[0].discord_message_id == new_message.id
    assert reports[0].lines[0].discord_message_id != old_message.id


def test_weekly_score_payload_contains_audit_refs(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'weekly_payload_audit.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        v2_prediction, v2_message = _seed_prediction(
            session,
            fixture_id=-221,
            kickoff=datetime(2026, 5, 3, 13, tzinfo=UTC),
            home_goals=1,
            away_goals=0,
            predicted="HOME",
        )
        _seed_ou_prediction(
            session,
            fixture_id=-222,
            kickoff=datetime(2026, 5, 3, 15, tzinfo=UTC),
            home_goals=3,
            away_goals=1,
            p_over=0.74,
            p_under=0.26,
            published=True,
            link_style="columns",
        )
        summary = publish_weekly_prediction_score(
            session=session,
            delivery=DiscordDeliveryService(
                session,
                channels_config=_channels_config(),
                webhooks_config=_webhooks_config(),
            ),
            target_date=date(2026, 5, 3),
            dry_run=True,
            include_previous_week_finalization=False,
        )
        weekly_message = session.get(
            models.DiscordMessage,
            summary.results[0].discord_message_ids[0],
        )

    assert weekly_message is not None
    payload = weekly_message.payload_json
    assert payload["model_family_counts"] == {"1X2 V2": 1, "O/U 2.5": 1}
    counted = payload["counted_predictions"]
    assert isinstance(counted, list)
    assert {
        "fixture_id": -221,
        "model_family": "1X2 V2",
        "prediction_table": "model_predictions",
        "prediction_id": v2_prediction.id,
        "discord_message_id": v2_message.id,
        "status": "FT",
        "correct": True,
    } in counted
    assert any(
        item["fixture_id"] == -222
        and item["model_family"] == "O/U 2.5"
        and item["prediction_table"] == "ou_model_predictions"
        and item["discord_message_id"] is not None
        for item in counted
    )


def test_weekly_score_counts_latest_sent_per_model_family_fixture(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'weekly_latest_sent.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        prediction, old_sent = _seed_ou_prediction(
            session,
            fixture_id=-231,
            kickoff=datetime(2026, 5, 3, 15, tzinfo=UTC),
            home_goals=3,
            away_goals=1,
            p_over=0.74,
            p_under=0.26,
            published=True,
            link_style="columns",
            sent_at=datetime(2026, 5, 3, 14, 30, tzinfo=UTC),
        )
        latest_sent = _ou_prediction_message(
            fixture_id=-231,
            ou_prediction_id=prediction.id,
            message_hash="ou-latest--231",
            sent_at=datetime(2026, 5, 3, 14, 40, tzinfo=UTC),
        )
        duplicate = _ou_prediction_message(
            fixture_id=-231,
            ou_prediction_id=prediction.id,
            message_hash="ou-duplicate--231",
            status="duplicate_skipped",
            sent_at=datetime(2026, 5, 3, 14, 50, tzinfo=UTC),
        )
        session.add_all([latest_sent, duplicate])
        reports = build_weekly_score_reports(
            session,
            target_date=date(2026, 5, 3),
            timezone_name="Europe/Paris",
            include_previous_week_finalization=False,
        )

    assert reports[0].total_predictions == 1
    assert reports[0].lines[0].discord_message_id == latest_sent.id
    assert reports[0].lines[0].discord_message_id != old_sent.id
    assert reports[0].lines[0].model_family == "O/U 2.5"


def test_weekly_score_replaces_only_same_week_messages(tmp_path: Path) -> None:
    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, str(request.url)))
        if request.method == "POST":
            return httpx.Response(200, json={"id": f"new-{len(requests)}"})
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'weekly_replace.db'}")
    session_factory = create_session_factory(engine)
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        session_scope(session_factory) as session,
    ):
        _seed_prediction(
            session,
            fixture_id=-1,
            kickoff=datetime(2026, 5, 3, 18, tzinfo=UTC),
            home_goals=1,
            away_goals=2,
            predicted="AWAY",
        )
        session.add(_weekly_message("2026-W17", "old-w17"))
        session.add(_weekly_message("2026-W18", "old-w18"))
        session.flush()
        summary = publish_weekly_prediction_score(
            session=session,
            delivery=DiscordDeliveryService(
                session,
                channels_config=_channels_config(),
                webhooks_config=_webhooks_config(),
                http_client=http_client,
            ),
            target_date=date(2026, 5, 4),
            dry_run=False,
            include_previous_week_finalization=True,
        )
        rows = session.query(models.DiscordMessage).all()

    statuses = {row.message_hash: row.status for row in rows}
    assert summary.sent == 2
    assert statuses["old-w17"] == "sent"
    assert statuses["old-w18"] == "deleted_replaced"
    assert any(method == "DELETE" and "old-w18" in url for method, url in requests)
    assert not any(method == "DELETE" and "old-w17" in url for method, url in requests)


def test_weekly_score_formatter_splits_under_discord_limit() -> None:
    lines = []
    for index in range(70):
        lines.append(
            _line(
                fixture_id=-1000 - index,
                match_label=f"Synthetic Home {index} - Synthetic Away {index}",
            )
        )
    messages = format_weekly_score_messages(
        WeeklyScoreReport(
            week_key="2026-W18",
            week_start=date(2026, 4, 27),
            week_end=date(2026, 5, 4),
            title_suffix="",
            lines=lines,
        )
    )

    assert len(messages) > 1
    assert all(message.startswith("```md") and message.endswith("\n```") for message in messages)
    assert all(len(message) <= 1900 for message in messages)


def test_weekly_score_cli_dry_run(tmp_path: Path, reference_path: Path) -> None:
    db_path = tmp_path / "weekly_cli.db"
    engine = create_db_and_tables(f"sqlite:///{db_path}")
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        _seed_prediction(
            session,
            fixture_id=-1,
            kickoff=datetime(2026, 5, 3, 18, tzinfo=UTC),
            home_goals=1,
            away_goals=2,
            predicted="AWAY",
        )
    channels_path = tmp_path / "channels.yaml"
    webhooks_path = tmp_path / "webhooks.yaml"
    channels_path.write_text(
        """
global_channels:
  score_pronos_semaine:
    channel_name: "score"
    channel_id: "synthetic"
    enabled: true
competitions: {}
""".strip(),
        encoding="utf-8",
    )
    webhooks_path.write_text(
        """
webhooks:
  global:
    score_pronos_semaine:
      webhook_url: "https://example.invalid/weekly"
      enabled: true
""".strip(),
        encoding="utf-8",
    )

    get_settings.cache_clear()
    result = CliRunner().invoke(
        app,
        [
            "publish-weekly-score",
            "--date",
            "2026-05-04",
            "--dry-run",
        ],
        env={
            "DATABASE_URL": f"sqlite:///{db_path}",
            "API_FOOTBALL_REFERENCE_PATH": str(reference_path),
            "DISCORD_CHANNELS_CONFIG_PATH": str(channels_path),
            "DISCORD_WEBHOOKS_CONFIG_PATH": str(webhooks_path),
        },
    )
    get_settings.cache_clear()

    assert result.exit_code == 0, result.stdout
    assert "2026-W18" in result.stdout
    assert "2026-W19" in result.stdout


def test_discord_example_config_supports_weekly_score(reference_path: Path) -> None:
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config("config/discord_webhooks.example.yaml", reference)

    assert channels.find_global_channel("score_pronos_semaine") is not None
    assert (
        webhooks.find_route(
            competition_key=None,
            league_id=None,
            season=None,
            channel_key="score_pronos_semaine",
        )
        is not None
    )


def _seed_prediction(
    session,
    *,
    fixture_id: int,
    kickoff: datetime,
    home_goals: int | None,
    away_goals: int | None,
    predicted: str,
    status: str = "FT",
    discord_payload: dict[str, object] | None = None,
    discord_status: str = "sent",
    dry_run: bool = False,
    print_only: bool = False,
    sent_at: datetime | None = None,
):
    session.merge(models.Team(team_id=-10, name="Synthetic Home", payload_json={"synthetic": True}))
    session.merge(models.Team(team_id=-20, name="Synthetic Away", payload_json={"synthetic": True}))
    fixture = models.Fixture(
        fixture_id=fixture_id,
        date=kickoff,
        league_id=-100,
        season=2026,
        status=status,
        status_short=status,
        home_team_id=-10,
        away_team_id=-20,
        home_team=f"Synthetic Home {fixture_id}",
        away_team=f"Synthetic Away {fixture_id}",
        home_goals=home_goals,
        away_goals=away_goals,
        payload_json={"synthetic": True},
    )
    session.add(fixture)
    feature = models.FeatureSnapshot(
        fixture_id=fixture_id,
        prediction_time=datetime(2026, 5, 3, 12, tzinfo=UTC),
        feature_version=f"weekly-{fixture_id}",
        features_json={},
        data_quality_json={},
    )
    session.add(feature)
    session.flush()
    prediction = models.ModelPrediction(
        fixture_id=fixture_id,
        feature_snapshot_id=feature.id,
        prediction_time=datetime(2026, 5, 3, 12, tzinfo=UTC),
        model_version="synthetic-weekly",
        p_home=0.25,
        p_draw=0.25,
        p_away=0.50,
        predicted_outcome=predicted,
        predicted_result=predicted,
        confidence=40.0,
        confidence_label="Medium",
        confidence_score=40.0,
        explanation_json=[],
        explanations_json=[],
        data_quality_json={},
        payload_json={},
    )
    session.add(prediction)
    session.flush()
    message = _prediction_message(
        fixture_id=fixture_id,
        prediction_id=prediction.id,
        message_hash=f"prediction-{fixture_id}",
        status=discord_status,
        dry_run=dry_run,
        print_only=print_only,
        sent_at=sent_at,
        payload_json=discord_payload or {"automation_window": "late", "daily_window": "late"},
    )
    session.add(message)
    session.flush()
    return prediction, message


def _prediction_message(
    *,
    fixture_id: int,
    prediction_id: int,
    message_hash: str,
    status: str = "sent",
    dry_run: bool = False,
    print_only: bool = False,
    sent_at: datetime | None = None,
    payload_json: dict[str, object] | None = None,
) -> models.DiscordMessage:
    return models.DiscordMessage(
        fixture_id=fixture_id,
        model_prediction_id=prediction_id,
        channel_key="predictions",
        message_type="prediction",
        status=status,
        dry_run=dry_run,
        print_only=print_only,
        sent_at=sent_at,
        webhook_hash="synthetic",
        webhook_url_hash="synthetic",
        message_hash=message_hash,
        message_markdown="```md\nprediction\n```",
        payload_json=payload_json or {"automation_window": "late", "daily_window": "late"},
        route_json={},
        response_json={},
    )


def _seed_v3_prediction(
    session,
    *,
    fixture_id: int,
    kickoff: datetime,
    home_goals: int,
    away_goals: int,
    predicted: str,
    published: bool,
    link_style: str = "payload",
) -> None:
    _seed_base_fixture(
        session,
        fixture_id=fixture_id,
        kickoff=kickoff,
        home_goals=home_goals,
        away_goals=away_goals,
    )
    snapshot = models.V3FeatureSnapshot(
        fixture_id=fixture_id,
        prediction_time=datetime(2026, 5, 3, 12, tzinfo=UTC),
        feature_version=f"weekly-v3-{fixture_id}",
        official_lineup_available_flag=False,
        features_json={},
        data_quality_json={},
    )
    session.add(snapshot)
    session.flush()
    prediction = models.V3ModelPrediction(
        fixture_id=fixture_id,
        v3_feature_snapshot_id=snapshot.id,
        prediction_time=datetime(2026, 5, 3, 12, tzinfo=UTC),
        model_version="synthetic-v3-weekly",
        fusion_strategy="deterministic_fallback",
        p_v3_final_home=0.62,
        p_v3_final_draw=0.21,
        p_v3_final_away=0.17,
        p_v3_draw_risk=0.21,
        p_v3_home_no_draw=0.78,
        p_v3_away_no_draw=0.22,
        confidence_score=78.0,
        confidence_label="High",
        predicted_result=predicted,
        expert_probabilities_json={},
        explanations_json=[],
        data_quality_json={},
        payload_json={},
    )
    session.add(prediction)
    session.flush()
    if published:
        session.add(
            models.DiscordMessage(
                fixture_id=fixture_id,
                model_prediction_id=None,
                v3_model_prediction_id=prediction.id if link_style == "columns" else None,
                channel_key="predictions",
                message_type="prediction",
                status="sent",
                dry_run=False,
                print_only=False,
                webhook_hash="synthetic",
                webhook_url_hash="synthetic",
                message_hash=f"v3-prediction-{fixture_id}",
                message_markdown="```md\nv3 prediction\n```",
                payload_json={
                    "automation_window": "late",
                    "daily_window": "late",
                    "model_family": "v3",
                    **(
                        {"v3_model_prediction_id": prediction.id}
                        if link_style == "payload"
                        else {}
                    ),
                },
                route_json={},
                response_json={},
            )
        )


def _seed_ou_prediction(
    session,
    *,
    fixture_id: int,
    kickoff: datetime,
    home_goals: int,
    away_goals: int,
    p_over: float,
    p_under: float,
    published: bool,
    link_style: str = "payload",
    sent_at: datetime | None = None,
):
    _seed_base_fixture(
        session,
        fixture_id=fixture_id,
        kickoff=kickoff,
        home_goals=home_goals,
        away_goals=away_goals,
    )
    snapshot = models.OUFeatureSnapshot(
        fixture_id=fixture_id,
        prediction_time=datetime(2026, 5, 3, 12, tzinfo=UTC),
        feature_version=f"weekly-ou-{fixture_id}",
        threshold=2.5,
        features_json={},
        data_quality_json={},
    )
    session.add(snapshot)
    session.flush()
    prediction = models.OUModelPrediction(
        fixture_id=fixture_id,
        ou_feature_snapshot_id=snapshot.id,
        prediction_time=datetime(2026, 5, 3, 12, tzinfo=UTC),
        model_version="synthetic-ou-weekly",
        threshold=2.5,
        p_over=p_over,
        p_under=p_under,
        confidence_score=82.0,
        confidence_label="Very High",
        expert_probabilities_json={},
        data_quality_json={},
        payload_json={},
    )
    session.add(prediction)
    session.flush()
    message = None
    if published:
        message = _ou_prediction_message(
            fixture_id=fixture_id,
            ou_prediction_id=prediction.id,
            message_hash=f"ou-prediction-{fixture_id}",
            link_style=link_style,
            sent_at=sent_at,
        )
        session.add(message)
        session.flush()
    return prediction, message


def _ou_prediction_message(
    *,
    fixture_id: int,
    ou_prediction_id: int,
    message_hash: str,
    status: str = "sent",
    link_style: str = "columns",
    sent_at: datetime | None = None,
) -> models.DiscordMessage:
    return models.DiscordMessage(
        fixture_id=fixture_id,
        model_prediction_id=None,
        ou_model_prediction_id=ou_prediction_id if link_style == "columns" else None,
        channel_key="predictions",
        message_type="ou_prediction",
        status=status,
        dry_run=False,
        print_only=False,
        sent_at=sent_at,
        webhook_hash="synthetic",
        webhook_url_hash="synthetic",
        message_hash=message_hash,
        message_markdown="```md\nou prediction\n```",
        payload_json={
            "automation_window": "late",
            "daily_window": "late",
            "model_family": "ou25",
            **({"ou_model_prediction_id": ou_prediction_id} if link_style == "payload" else {}),
        },
        route_json={},
        response_json={},
    )


def _seed_base_fixture(
    session,
    *,
    fixture_id: int,
    kickoff: datetime,
    home_goals: int,
    away_goals: int,
) -> None:
    session.merge(models.Team(team_id=-10, name="Synthetic Home", payload_json={"synthetic": True}))
    session.merge(models.Team(team_id=-20, name="Synthetic Away", payload_json={"synthetic": True}))
    session.add(
        models.Fixture(
            fixture_id=fixture_id,
            date=kickoff,
            league_id=-100,
            season=2026,
            status="FT",
            status_short="FT",
            home_team_id=-10,
            away_team_id=-20,
            home_team=f"Synthetic Home {fixture_id}",
            away_team=f"Synthetic Away {fixture_id}",
            home_goals=home_goals,
            away_goals=away_goals,
            payload_json={"synthetic": True},
        )
    )


def _line(fixture_id: int, match_label: str):
    return WeeklyScoreLine(
        fixture_id=fixture_id,
        fixture_date=datetime(2026, 5, 3, 18, tzinfo=UTC),
        match_label=match_label,
        predicted="domicile",
        actual="extérieur",
        score_label="1-2",
        confidence_label="Medium",
        confidence_score=40.0,
        status="FT",
        correct=False,
    )


def _weekly_message(week_key: str, message_hash: str) -> models.DiscordMessage:
    return models.DiscordMessage(
        channel_key="score_pronos_semaine",
        message_type="weekly_prediction_score",
        status="sent",
        dry_run=False,
        print_only=False,
        webhook_hash="synthetic",
        webhook_url_hash="synthetic",
        message_hash=message_hash,
        message_markdown="```md\nold\n```",
        payload_json={
            "report_kind": "weekly_prediction_score",
            "week_key": week_key,
            "discord_api_message_id": message_hash,
        },
        route_json={},
        response_json={"id": message_hash},
    )


def _channels_config() -> DiscordChannelsConfig:
    return DiscordChannelsConfig(
        competitions={},
        global_channels={
            "score_pronos_semaine": DiscordChannelConfig(
                channel_key="score_pronos_semaine",
                channel_id="synthetic",
                channel_name="score",
            )
        },
    )


def _webhooks_config() -> DiscordWebhooksConfig:
    return DiscordWebhooksConfig(
        routes=[
            DiscordWebhookRouteConfig(
                competition_key="global",
                channel_key="score_pronos_semaine",
                webhook_url="https://example.invalid/weekly",
            )
        ]
    )
