from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import select

from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.discord.config import (
    load_discord_channels_config,
    load_discord_webhooks_config,
)
from football_predictor.discord.service import DiscordDeliveryService
from football_predictor.reference.loaders import load_api_football_reference


def _write_webhooks(path: Path) -> Path:
    path.write_text(
        """
webhooks:
  ligue1:
    predictions:
      webhook_url: "https://example.invalid/l1"
      enabled: true
""",
        encoding="utf-8",
    )
    return path


def test_delivery_dry_run_persists_route(reference_path: Path, tmp_path: Path) -> None:
    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config("config/discord_webhooks.example.yaml", reference)
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'discord.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        result = DiscordDeliveryService(
            session,
            channels_config=channels,
            webhooks_config=webhooks,
        ).send_markdown(
            "```md\nsynthetic\n```",
            competition_key="ligue1",
            message_type="prediction",
            dry_run=True,
        )

    with session_scope(session_factory) as session:
        row = session.scalar(select(models.DiscordMessage))

    assert result.status == "dry_run"
    assert row is not None
    assert row.competition_key == "ligue1"
    assert row.league_id == 61
    assert row.season == 2025
    assert row.channel_key == "predictions"
    assert row.message_type == "prediction"
    assert row.dry_run is True
    assert row.route_json["webhook_configured"] is False
    assert row.payload_json["content"] == "```md\nsynthetic\n```"


def test_delivery_sends_with_mocked_http_and_dedupes(
    reference_path: Path,
    tmp_path: Path,
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config(
        _write_webhooks(tmp_path / "discord_webhooks.yaml"),
        reference,
    )
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'discord.db'}")
    session_factory = create_session_factory(engine)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        session_scope(session_factory) as session,
    ):
        service = DiscordDeliveryService(
            session,
            channels_config=channels,
            webhooks_config=webhooks,
            http_client=client,
        )
        first = service.send_markdown(
            "```md\nsynthetic\n```",
            competition_key="ligue1",
            message_type="prediction",
        )
        second = service.send_markdown(
            "```md\nsynthetic\n```",
            competition_key="ligue1",
            message_type="prediction",
        )

    with session_scope(session_factory) as session:
        statuses = [row.status for row in session.execute(select(models.DiscordMessage)).scalars()]

    assert first.status == "sent"
    assert second.status == "duplicate_skipped"
    assert calls == 1
    assert statuses == ["sent", "duplicate_skipped"]


def test_delivery_wait_stores_discord_api_message_id(
    reference_path: Path,
    tmp_path: Path,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.query.decode() == "wait=true"
        return httpx.Response(200, json={"id": "api-message-1"})

    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config(
        _write_webhooks(tmp_path / "discord_webhooks.yaml"),
        reference,
    )
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'discord_wait.db'}")
    session_factory = create_session_factory(engine)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        session_scope(session_factory) as session,
    ):
        result = DiscordDeliveryService(
            session,
            channels_config=channels,
            webhooks_config=webhooks,
            http_client=client,
        ).send_markdown(
            "```md\nsynthetic\n```",
            competition_key="ligue1",
            message_type="prediction",
            wait=True,
        )

    with session_scope(session_factory) as session:
        row = session.scalar(select(models.DiscordMessage))

    assert result.discord_api_message_id == "api-message-1"
    assert row is not None
    assert row.payload_json["discord_api_message_id"] == "api-message-1"


def test_delivery_persists_prediction_links_and_dedupe_key(
    reference_path: Path,
    tmp_path: Path,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config(
        _write_webhooks(tmp_path / "discord_webhooks.yaml"),
        reference,
    )
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'discord_links.db'}")
    session_factory = create_session_factory(engine)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        session_scope(session_factory) as session,
    ):
        v3_id, ou_id = _seed_prediction_links(session)
        result = DiscordDeliveryService(
            session,
            channels_config=channels,
            webhooks_config=webhooks,
            http_client=client,
        ).send_markdown(
            "```md\nsynthetic linked prediction\n```",
            competition_key="ligue1",
            message_type="prediction",
            v3_model_prediction_id=v3_id,
            ou_model_prediction_id=ou_id,
            dedupe_key="synthetic:dedupe",
        )

    with session_scope(session_factory) as session:
        row = session.get(models.DiscordMessage, result.discord_message_id)

    assert row is not None
    assert row.v3_model_prediction_id == v3_id
    assert row.ou_model_prediction_id == ou_id
    assert row.dedupe_key == "synthetic:dedupe"
    assert row.payload_json["v3_model_prediction_id"] == v3_id
    assert row.payload_json["ou_model_prediction_id"] == ou_id
    assert row.payload_json["dedupe_key"] == "synthetic:dedupe"


def test_delivery_dedupes_live_messages_by_dedupe_key(
    reference_path: Path,
    tmp_path: Path,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config(
        _write_webhooks(tmp_path / "discord_webhooks.yaml"),
        reference,
    )
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'discord_dedupe_key.db'}")
    session_factory = create_session_factory(engine)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        session_scope(session_factory) as session,
    ):
        service = DiscordDeliveryService(
            session,
            channels_config=channels,
            webhooks_config=webhooks,
            http_client=client,
        )
        first = service.send_markdown(
            "```md\nsynthetic O/U prediction v1\n```",
            competition_key="ligue1",
            message_type="ou_prediction",
            dedupe_key="ou25:-501:late:synthetic-ou:ou_prediction",
        )
        second = service.send_markdown(
            "```md\nsynthetic O/U prediction v2 changed text\n```",
            competition_key="ligue1",
            message_type="ou_prediction",
            dedupe_key="ou25:-501:late:synthetic-ou:ou_prediction",
        )

    assert first.status == "sent"
    assert second.status == "duplicate_skipped"
    assert calls == 1


def test_delivery_dry_run_and_print_only_do_not_block_live_dedupe_key(
    reference_path: Path,
    tmp_path: Path,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config(
        _write_webhooks(tmp_path / "discord_webhooks.yaml"),
        reference,
    )
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'discord_dedupe_preview.db'}")
    session_factory = create_session_factory(engine)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        session_scope(session_factory) as session,
    ):
        service = DiscordDeliveryService(
            session,
            channels_config=channels,
            webhooks_config=webhooks,
            http_client=client,
        )
        dry_run = service.send_markdown(
            "```md\nsynthetic dry run\n```",
            competition_key="ligue1",
            message_type="ou_prediction",
            dedupe_key="ou25:-501:late:synthetic-ou:ou_prediction",
            dry_run=True,
        )
        print_only = service.send_markdown(
            "```md\nsynthetic print only\n```",
            competition_key="ligue1",
            message_type="ou_prediction",
            dedupe_key="ou25:-501:late:synthetic-ou:ou_prediction",
            print_only=True,
        )
        live = service.send_markdown(
            "```md\nsynthetic live\n```",
            competition_key="ligue1",
            message_type="ou_prediction",
            dedupe_key="ou25:-501:late:synthetic-ou:ou_prediction",
        )

    assert dry_run.status == "dry_run"
    assert print_only.status == "print_only"
    assert live.status == "sent"
    assert calls == 1


def test_delivery_force_bypasses_dedupe_key(
    reference_path: Path,
    tmp_path: Path,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config(
        _write_webhooks(tmp_path / "discord_webhooks.yaml"),
        reference,
    )
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'discord_dedupe_force.db'}")
    session_factory = create_session_factory(engine)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        session_scope(session_factory) as session,
    ):
        service = DiscordDeliveryService(
            session,
            channels_config=channels,
            webhooks_config=webhooks,
            http_client=client,
        )
        first = service.send_markdown(
            "```md\nsynthetic O/U prediction v1\n```",
            competition_key="ligue1",
            message_type="ou_prediction",
            dedupe_key="ou25:-501:late:synthetic-ou:ou_prediction",
        )
        second = service.send_markdown(
            "```md\nsynthetic O/U prediction v2 changed text\n```",
            competition_key="ligue1",
            message_type="ou_prediction",
            dedupe_key="ou25:-501:late:synthetic-ou:ou_prediction",
            force=True,
        )

    assert first.status == "sent"
    assert second.status == "sent"
    assert calls == 2


def test_delivery_print_only_does_not_send(reference_path: Path, tmp_path: Path) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    reference = load_api_football_reference(reference_path)
    channels = load_discord_channels_config("config/discord_channels.example.yaml", reference)
    webhooks = load_discord_webhooks_config(
        _write_webhooks(tmp_path / "discord_webhooks.yaml"),
        reference,
    )
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'discord.db'}")
    session_factory = create_session_factory(engine)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        session_scope(session_factory) as session,
    ):
        result = DiscordDeliveryService(
            session,
            channels_config=channels,
            webhooks_config=webhooks,
            http_client=client,
        ).send_markdown(
            "```md\nsynthetic\n```",
            competition_key="ligue1",
            message_type="prediction",
            print_only=True,
        )

    assert result.status == "print_only"
    assert calls == 0


def _seed_prediction_links(session) -> tuple[int, int]:
    now = datetime(2026, 5, 2, 12, tzinfo=UTC)
    session.add_all(
        [
            models.Team(team_id=-10, name="Synthetic Home", payload_json={"synthetic": True}),
            models.Team(team_id=-20, name="Synthetic Away", payload_json={"synthetic": True}),
            models.Fixture(
                fixture_id=-501,
                date=now,
                league_id=61,
                season=2025,
                status="NS",
                status_short="NS",
                home_team_id=-10,
                away_team_id=-20,
                home_team="Synthetic Home",
                away_team="Synthetic Away",
                payload_json={"synthetic": True},
            ),
        ]
    )
    v3_snapshot = models.V3FeatureSnapshot(
        fixture_id=-501,
        prediction_time=now,
        feature_version="synthetic-v3",
        official_lineup_available_flag=False,
        features_json={},
        data_quality_json={},
    )
    ou_snapshot = models.OUFeatureSnapshot(
        fixture_id=-501,
        prediction_time=now,
        feature_version="synthetic-ou",
        threshold=2.5,
        features_json={},
        data_quality_json={},
    )
    session.add_all([v3_snapshot, ou_snapshot])
    session.flush()
    v3_prediction = models.V3ModelPrediction(
        fixture_id=-501,
        v3_feature_snapshot_id=v3_snapshot.id,
        prediction_time=now,
        model_version="synthetic-v3",
        fusion_strategy="deterministic_fallback",
        p_v3_final_home=0.5,
        p_v3_final_draw=0.25,
        p_v3_final_away=0.25,
        confidence_score=70.0,
        confidence_label="High",
        predicted_result="HOME",
        expert_probabilities_json={},
        explanations_json=[],
        data_quality_json={},
        payload_json={},
    )
    ou_prediction = models.OUModelPrediction(
        fixture_id=-501,
        ou_feature_snapshot_id=ou_snapshot.id,
        prediction_time=now,
        model_version="synthetic-ou",
        threshold=2.5,
        p_over=0.7,
        p_under=0.3,
        confidence_score=80.0,
        confidence_label="Very High",
        expert_probabilities_json={},
        data_quality_json={},
        payload_json={},
    )
    session.add_all([v3_prediction, ou_prediction])
    session.flush()
    return v3_prediction.id, ou_prediction.id
