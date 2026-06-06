from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import select
from typer.testing import CliRunner

from football_predictor.cli import app
from football_predictor.config.competitions import CompetitionConfig
from football_predictor.config.settings import get_settings
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.discord.config import (
    load_discord_channels_config,
    load_discord_webhooks_config,
)
from football_predictor.discord.daily_publication import (
    _calendar_messages,
    _daily_matches_messages,
    _standings_messages,
    publish_daily_discord_messages,
)
from football_predictor.discord.service import DiscordDeliveryService
from football_predictor.reference.loaders import load_api_football_reference


def test_publish_daily_discord_cli_dry_run_persists_messages(tmp_path: Path) -> None:
    db_path = tmp_path / "publish_daily.db"
    engine = create_db_and_tables(f"sqlite:///{db_path}")
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        _seed_daily_publication_data(session)

    competitions_path = _write_competitions_config(tmp_path)
    channels_path = _write_discord_channels_config(tmp_path)
    webhooks_path = _write_discord_webhooks_config(tmp_path)
    get_settings.cache_clear()
    result = CliRunner().invoke(
        app,
        [
            "publish-daily-discord",
            "--date",
            "2026-05-02",
            "--config",
            str(competitions_path),
            "--dry-run",
        ],
        env={
            "DATABASE_URL": f"sqlite:///{db_path}",
            "DISCORD_CHANNELS_CONFIG_PATH": str(channels_path),
            "DISCORD_WEBHOOKS_CONFIG_PATH": str(webhooks_path),
            "DISCORD_WEBHOOK_URL": "",
        },
    )
    get_settings.cache_clear()

    assert result.exit_code == 0, result.stdout
    assert "dry_run" in result.stdout
    with session_scope(session_factory) as session:
        messages = session.query(models.DiscordMessage).order_by(models.DiscordMessage.id).all()
        assert len(messages) == 3
        assert {message.channel_key for message in messages} == {
            "classement",
            "calendrier",
            "matchs_du_jour",
        }
        assert all(message.status == "dry_run" for message in messages)
        assert all(len(message.message_markdown) <= 2000 for message in messages)
        assert all(message.message_markdown.startswith("```md") for message in messages)
        assert all(message.message_markdown.endswith("```") for message in messages)


def test_publish_daily_discord_cli_exposes_replace_previous_option() -> None:
    result = CliRunner().invoke(app, ["publish-daily-discord", "--help"])

    assert result.exit_code == 0
    assert "--replace-previous" in result.stdout
    assert "--no-replace-previous" in result.stdout


def test_daily_morning_script_calls_publish_daily_discord(repo_root: Path) -> None:
    text = (repo_root / "scripts/daily_morning.sh").read_text(encoding="utf-8")

    assert "scripts/publish_daily_discord.sh" in text
    assert 'PUBLISH_DISCORD="${PUBLISH_DISCORD:-true}"' in text
    assert 'REPLACE_PREVIOUS="${REPLACE_PREVIOUS:-true}"' in text


def test_publish_daily_discord_replaces_previous_messages(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    requests: list[tuple[str, str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path, request.url.query.decode()))
        if request.method == "POST":
            return httpx.Response(200, json={"id": f"new-{len(requests)}"})
        return httpx.Response(204)

    reference = load_api_football_reference(reference_path)
    competitions_path = _write_competitions_config(tmp_path)
    channels = load_discord_channels_config(_write_discord_channels_config(tmp_path), reference)
    webhooks = load_discord_webhooks_config(
        _write_real_discord_webhooks_config(tmp_path),
        reference,
    )
    from football_predictor.config.competitions import load_competition_config

    competitions = load_competition_config(competitions_path, reference)
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'publish_replace.db'}")
    session_factory = create_session_factory(engine)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        session_scope(session_factory) as session,
    ):
        _seed_daily_publication_data(session)
        session.add_all(
            [
                _sent_discord_message("classement", "standings", "old-standings-1"),
                _sent_discord_message("classement", "standings", "old-standings-2"),
                _sent_discord_message("calendrier", "schedule", "old-calendar-1"),
                _sent_discord_message("predictions", "prediction", "old-prediction-1"),
            ]
        )
        summary = publish_daily_discord_messages(
            session=session,
            competitions=competitions,
            delivery=DiscordDeliveryService(
                session,
                channels_config=channels,
                webhooks_config=webhooks,
                http_client=client,
            ),
            target_date=datetime(2026, 5, 2, tzinfo=UTC).date(),
            dry_run=False,
            replace_previous=True,
        )
        old_rows = session.execute(
            select(models.DiscordMessage).where(
                models.DiscordMessage.message_hash.like("old-%")
            )
        ).scalars().all()

    delete_paths = [path for method, path, _query in requests if method == "DELETE"]
    assert "/classement/messages/old-standings-1" in delete_paths
    assert "/classement/messages/old-standings-2" in delete_paths
    assert "/calendrier/messages/old-calendar-1" in delete_paths
    assert all("old-prediction-1" not in path for path in delete_paths)
    assert all(query == "wait=true" for method, _path, query in requests if method == "POST")
    assert any(result.replaced_count == 2 for result in summary.results)
    statuses = {row.message_hash: row.status for row in old_rows}
    assert statuses["old-standings-1"] == "deleted_replaced"
    assert statuses["old-standings-2"] == "deleted_replaced"
    assert statuses["old-calendar-1"] == "deleted_replaced"
    assert statuses["old-prediction-1"] == "sent"


def test_publish_daily_discord_no_replace_and_dry_run_do_not_delete(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        return httpx.Response(200, json={"id": "new-message"})

    reference = load_api_football_reference(reference_path)
    competitions_path = _write_competitions_config(tmp_path)
    channels = load_discord_channels_config(_write_discord_channels_config(tmp_path), reference)
    webhooks = load_discord_webhooks_config(
        _write_real_discord_webhooks_config(tmp_path),
        reference,
    )
    from football_predictor.config.competitions import load_competition_config

    competitions = load_competition_config(competitions_path, reference)
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'publish_no_replace.db'}")
    session_factory = create_session_factory(engine)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        session_scope(session_factory) as session,
    ):
        _seed_daily_publication_data(session)
        session.add(_sent_discord_message("classement", "standings", "old-standings-1"))
        publish_daily_discord_messages(
            session=session,
            competitions=competitions,
            delivery=DiscordDeliveryService(
                session,
                channels_config=channels,
                webhooks_config=webhooks,
                http_client=client,
            ),
            target_date=datetime(2026, 5, 2, tzinfo=UTC).date(),
            dry_run=False,
            replace_previous=False,
        )
        publish_daily_discord_messages(
            session=session,
            competitions=competitions,
            delivery=DiscordDeliveryService(
                session,
                channels_config=channels,
                webhooks_config=webhooks,
                http_client=client,
            ),
            target_date=datetime(2026, 5, 2, tzinfo=UTC).date(),
            dry_run=True,
            replace_previous=True,
        )

    assert all(method != "DELETE" for method, _path in requests)


def test_publish_daily_discord_delete_error_warns_and_still_sends(
    tmp_path: Path,
    reference_path: Path,
) -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.method)
        if request.method == "DELETE":
            return httpx.Response(403, json={"message": "forbidden synthetic"})
        return httpx.Response(200, json={"id": "new-after-delete-error"})

    reference = load_api_football_reference(reference_path)
    competitions_path = _write_competitions_config(tmp_path)
    channels = load_discord_channels_config(_write_discord_channels_config(tmp_path), reference)
    webhooks = load_discord_webhooks_config(
        _write_real_discord_webhooks_config(tmp_path),
        reference,
    )
    from football_predictor.config.competitions import load_competition_config

    competitions = load_competition_config(competitions_path, reference)
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'publish_delete_error.db'}")
    session_factory = create_session_factory(engine)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        session_scope(session_factory) as session,
    ):
        _seed_daily_publication_data(session)
        session.add(_sent_discord_message("classement", "standings", "old-standings-1"))
        summary = publish_daily_discord_messages(
            session=session,
            competitions=competitions,
            delivery=DiscordDeliveryService(
                session,
                channels_config=channels,
                webhooks_config=webhooks,
                http_client=client,
            ),
            target_date=datetime(2026, 5, 2, tzinfo=UTC).date(),
            dry_run=False,
            replace_previous=True,
        )

    assert "DELETE" in requests
    assert "POST" in requests
    standings_result = next(
        result for result in summary.results if result.channel_key == "classement"
    )
    assert standings_result.replace_warnings


def test_worldcup_daily_standings_use_groups_from_payload(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'publish_worldcup_groups.db'}")
    session_factory = create_session_factory(engine)
    snapshot_date = datetime(2026, 5, 26, 0, 0, tzinfo=UTC)

    with session_scope(session_factory) as session:
        session.add_all(
            [
                models.Team(team_id=-2001, name="Mexico", payload_json={"synthetic": True}),
                models.Team(team_id=-2002, name="South Africa", payload_json={"synthetic": True}),
                models.Team(team_id=-2003, name="England", payload_json={"synthetic": True}),
            ]
        )
        session.add_all(
            [
                models.StandingSnapshot(
                    league_id=1,
                    season=2026,
                    team_id=-2001,
                    snapshot_date=snapshot_date,
                    fetched_at=snapshot_date,
                    rank=1,
                    points=0,
                    goals_diff=0,
                    played=0,
                    payload_json={"group": "Group A"},
                ),
                models.StandingSnapshot(
                    league_id=1,
                    season=2026,
                    team_id=-2002,
                    snapshot_date=snapshot_date,
                    fetched_at=snapshot_date,
                    rank=2,
                    points=0,
                    goals_diff=0,
                    played=0,
                    payload_json={"raw": {"group": "Group A"}},
                ),
                models.StandingSnapshot(
                    league_id=1,
                    season=2026,
                    team_id=-2003,
                    snapshot_date=snapshot_date,
                    fetched_at=snapshot_date,
                    rank=1,
                    points=0,
                    goals_diff=0,
                    played=0,
                    payload_json={"group": "Group L"},
                ),
            ]
        )
        session.flush()
        messages = _standings_messages(
            session,
            CompetitionConfig(
                key="fifa_world_cup_2026",
                league_id=1,
                season=2026,
                name="FIFA World Cup",
                country="World",
            ),
            "Europe/Paris",
        )

    assert "CLASSEMENTS DE GROUPES - FIFA World Cup" in messages[0]
    assert "Groupe A" in messages[0]
    assert "Groupe L" in messages[0]
    assert messages[0].index("Mexico") < messages[0].index("South Africa")


def test_worldcup_daily_calendar_uses_grouped_formatter_from_standings(
    tmp_path: Path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'publish_worldcup_calendar.db'}")
    session_factory = create_session_factory(engine)
    snapshot_date = datetime(2026, 5, 26, 0, 0, tzinfo=UTC)
    kickoff = datetime(2026, 6, 11, 19, 0, tzinfo=UTC)

    with session_scope(session_factory) as session:
        session.add_all(
            [
                models.Team(team_id=-2101, name="Mexico", payload_json={"synthetic": True}),
                models.Team(team_id=-2102, name="South Africa", payload_json={"synthetic": True}),
                models.Team(team_id=-2103, name="England", payload_json={"synthetic": True}),
                models.Team(team_id=-2104, name="Croatia", payload_json={"synthetic": True}),
            ]
        )
        session.add_all(
            [
                models.StandingSnapshot(
                    league_id=1,
                    season=2026,
                    team_id=-2101,
                    snapshot_date=snapshot_date,
                    fetched_at=snapshot_date,
                    rank=1,
                    points=0,
                    goals_diff=0,
                    played=0,
                    payload_json={"group": "Group A"},
                ),
                models.StandingSnapshot(
                    league_id=1,
                    season=2026,
                    team_id=-2102,
                    snapshot_date=snapshot_date,
                    fetched_at=snapshot_date,
                    rank=2,
                    points=0,
                    goals_diff=0,
                    played=0,
                    payload_json={"raw": {"group": "Group A"}},
                ),
                models.StandingSnapshot(
                    league_id=1,
                    season=2026,
                    team_id=-2103,
                    snapshot_date=snapshot_date,
                    fetched_at=snapshot_date,
                    rank=1,
                    points=0,
                    goals_diff=0,
                    played=0,
                    payload_json={"group": "Group L"},
                ),
                models.StandingSnapshot(
                    league_id=1,
                    season=2026,
                    team_id=-2104,
                    snapshot_date=snapshot_date,
                    fetched_at=snapshot_date,
                    rank=2,
                    points=0,
                    goals_diff=0,
                    played=0,
                    payload_json={"group": "Group L"},
                ),
            ]
        )
        session.add_all(
            [
                models.Fixture(
                    fixture_id=-9101,
                    league_id=1,
                    season=2026,
                    round="Group Stage - 1",
                    date=kickoff,
                    status="NS",
                    status_short="NS",
                    home_team_id=-2101,
                    away_team_id=-2102,
                    home_team="Mexico",
                    away_team="South Africa",
                    payload_json={"synthetic": True},
                ),
                models.Fixture(
                    fixture_id=-9102,
                    league_id=1,
                    season=2026,
                    round="Group Stage - 1",
                    date=kickoff.replace(day=17),
                    status="NS",
                    status_short="NS",
                    home_team_id=-2103,
                    away_team_id=-2104,
                    home_team="England",
                    away_team="Croatia",
                    payload_json={"synthetic": True},
                ),
            ]
        )
        session.flush()
        messages = _calendar_messages(
            session,
            CompetitionConfig(
                key="fifa_world_cup_2026",
                league_id=1,
                season=2026,
                name="FIFA World Cup",
                country="World",
            ),
            kickoff.date(),
            "Europe/Paris",
        )

    assert "CALENDRIER DE GROUPES - FIFA World Cup" in messages[0]
    assert "Groupe A" in messages[0]
    assert "Groupe L" in messages[0]
    assert "Mexico vs South Africa" in messages[0]
    assert "England vs Croatia" in messages[0]


def test_worldcup_daily_matches_include_group_from_standings(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'publish_worldcup_daily.db'}")
    session_factory = create_session_factory(engine)
    snapshot_date = datetime(2026, 5, 26, 0, 0, tzinfo=UTC)
    target_date = datetime(2026, 6, 14, tzinfo=UTC).date()

    with session_scope(session_factory) as session:
        session.add_all(
            [
                models.Team(team_id=-2201, name="Brazil", payload_json={"synthetic": True}),
                models.Team(team_id=-2202, name="Morocco", payload_json={"synthetic": True}),
                models.Team(team_id=-2203, name="Haiti", payload_json={"synthetic": True}),
                models.Team(team_id=-2204, name="Scotland", payload_json={"synthetic": True}),
            ]
        )
        session.add_all(
            [
                models.StandingSnapshot(
                    league_id=1,
                    season=2026,
                    team_id=-2201,
                    snapshot_date=snapshot_date,
                    fetched_at=snapshot_date,
                    rank=1,
                    points=0,
                    goals_diff=0,
                    played=0,
                    payload_json={"group": "Group C"},
                ),
                models.StandingSnapshot(
                    league_id=1,
                    season=2026,
                    team_id=-2202,
                    snapshot_date=snapshot_date,
                    fetched_at=snapshot_date,
                    rank=2,
                    points=0,
                    goals_diff=0,
                    played=0,
                    payload_json={"raw": {"group": "Group C"}},
                ),
                models.StandingSnapshot(
                    league_id=1,
                    season=2026,
                    team_id=-2203,
                    snapshot_date=snapshot_date,
                    fetched_at=snapshot_date,
                    rank=3,
                    points=0,
                    goals_diff=0,
                    played=0,
                    payload_json={"group": "Group C"},
                ),
                models.StandingSnapshot(
                    league_id=1,
                    season=2026,
                    team_id=-2204,
                    snapshot_date=snapshot_date,
                    fetched_at=snapshot_date,
                    rank=4,
                    points=0,
                    goals_diff=0,
                    played=0,
                    payload_json={"group": "Group C"},
                ),
            ]
        )
        session.add_all(
            [
                models.Fixture(
                    fixture_id=-9201,
                    league_id=1,
                    season=2026,
                    round="Group Stage - 1",
                    date=datetime(2026, 6, 14, 18, 0, tzinfo=UTC),
                    status="NS",
                    status_short="NS",
                    home_team_id=-2201,
                    away_team_id=-2202,
                    home_team="Brazil",
                    away_team="Morocco",
                    payload_json={"synthetic": True},
                ),
                models.Fixture(
                    fixture_id=-9202,
                    league_id=1,
                    season=2026,
                    round="Group Stage - 1",
                    date=datetime(2026, 6, 14, 19, 0, tzinfo=UTC),
                    status="NS",
                    status_short="NS",
                    home_team_id=-2203,
                    away_team_id=-2204,
                    home_team="Haiti",
                    away_team="Scotland",
                    payload_json={"synthetic": True},
                ),
            ]
        )
        session.flush()
        messages = _daily_matches_messages(
            session,
            CompetitionConfig(
                key="fifa_world_cup_2026",
                league_id=1,
                season=2026,
                name="FIFA World Cup",
                country="World",
            ),
            target_date,
            "Europe/Paris",
        )

    assert "MATCHS DU JOUR - FIFA World Cup" in messages[0]
    assert "Heure  Grp  Match" in messages[0]
    assert "C    Haiti vs Scotland" in messages[0]
    assert "C    Brazil vs Morocco" in messages[0]
    assert messages[0].index("Brazil vs Morocco") < messages[0].index("Haiti vs Scotland")
    assert messages[0].startswith("```md") and messages[0].endswith("```")


def _seed_daily_publication_data(session) -> None:
    session.add_all(
        [
            models.Team(team_id=-101, name="Synthetic Alpha", payload_json={"synthetic": True}),
            models.Team(team_id=-102, name="Synthetic Beta", payload_json={"synthetic": True}),
            models.Team(team_id=-103, name="Synthetic Gamma", payload_json={"synthetic": True}),
            models.Team(team_id=-104, name="Synthetic Delta", payload_json={"synthetic": True}),
        ]
    )
    snapshot_date = datetime(2026, 5, 2, 8, 0, tzinfo=UTC)
    session.add_all(
        [
            models.StandingSnapshot(
                league_id=61,
                season=2025,
                team_id=-101,
                snapshot_date=snapshot_date,
                fetched_at=snapshot_date,
                rank=1,
                points=70,
                goals_diff=35,
                form="WWWDW",
                all_played=30,
                payload_json={"synthetic": True},
            ),
            models.StandingSnapshot(
                league_id=61,
                season=2025,
                team_id=-102,
                snapshot_date=snapshot_date,
                fetched_at=snapshot_date,
                rank=2,
                points=66,
                goals_diff=29,
                form="WDWWW",
                all_played=30,
                payload_json={"synthetic": True},
            ),
        ]
    )
    session.add_all(
        [
            models.Fixture(
                fixture_id=-9001,
                league_id=61,
                season=2025,
                round="Regular Season - 30",
                date=datetime(2026, 5, 2, 18, 0, tzinfo=UTC),
                status="NS",
                status_short="NS",
                home_team_id=-101,
                away_team_id=-102,
                home_team="Synthetic Alpha",
                away_team="Synthetic Beta",
                payload_json={"synthetic": True},
            ),
            models.Fixture(
                fixture_id=-9002,
                league_id=61,
                season=2025,
                round="Regular Season - 30",
                date=datetime(2026, 5, 3, 18, 0, tzinfo=UTC),
                status="NS",
                status_short="NS",
                home_team_id=-103,
                away_team_id=-104,
                home_team="Synthetic Gamma",
                away_team="Synthetic Delta",
                payload_json={"synthetic": True},
            ),
        ]
    )


def _write_competitions_config(tmp_path: Path) -> Path:
    path = tmp_path / "competitions.yaml"
    path.write_text(
        """
competitions:
  - key: ligue_1
    league_id: 61
    season: 2025
    name: Ligue 1
    country: France
    enabled: true
    source: docs/api_football_reference.json
""".lstrip(),
        encoding="utf-8",
    )
    return path


def _write_discord_channels_config(tmp_path: Path) -> Path:
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
      classement:
        channel_name: "classement"
        enabled: true
      calendrier:
        channel_name: "calendrier"
        enabled: true
      matchs_du_jour:
        channel_name: "matchs-du-jour"
        enabled: true
""".lstrip(),
        encoding="utf-8",
    )
    return path


def _write_discord_webhooks_config(tmp_path: Path) -> Path:
    path = tmp_path / "discord_webhooks.yaml"
    path.write_text(
        """
webhooks:
  ligue1:
    classement:
      webhook_url: ""
      enabled: true
    calendrier:
      webhook_url: ""
      enabled: true
    matchs_du_jour:
      webhook_url: ""
      enabled: true
""".lstrip(),
        encoding="utf-8",
    )
    return path


def _write_real_discord_webhooks_config(tmp_path: Path) -> Path:
    path = tmp_path / "discord_webhooks_real.yaml"
    path.write_text(
        """
webhooks:
  ligue1:
    classement:
      webhook_url: "https://example.invalid/classement"
      enabled: true
    calendrier:
      webhook_url: "https://example.invalid/calendrier"
      enabled: true
    matchs_du_jour:
      webhook_url: "https://example.invalid/matchs-du-jour"
      enabled: true
""".lstrip(),
        encoding="utf-8",
    )
    return path


def _sent_discord_message(channel_key: str, message_type: str, discord_api_message_id: str):
    return models.DiscordMessage(
        competition_key="ligue1",
        league_id=61,
        season=2025,
        channel_key=channel_key,
        message_type=message_type,
        status="sent",
        dry_run=False,
        print_only=False,
        webhook_hash="synthetic",
        webhook_url_hash="synthetic",
        message_hash=discord_api_message_id,
        message_markdown="```md\nold\n```",
        payload_json={
            "content": "```md\nold\n```",
            "discord_api_message_id": discord_api_message_id,
        },
        response_json={"id": discord_api_message_id},
        route_json={"synthetic": True},
    )
