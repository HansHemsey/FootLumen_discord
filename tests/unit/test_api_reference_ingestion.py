from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from football_predictor.api.api_football_client import ApiFootballPayload
from football_predictor.api.endpoints import (
    LEAGUES,
    ODDS_BETS,
    ODDS_BOOKMAKERS,
    PLAYERS_SQUADS,
    TEAMS,
)
from football_predictor.config.competitions import CompetitionConfig
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.ingestion.api_reference import ApiReferenceIngestionService

JsonDict = dict[str, Any]


@dataclass
class FakeApiClient:
    responses: dict[tuple[str, tuple[tuple[str, Any], ...]], JsonDict]
    calls: list[tuple[str, dict[str, Any]]]

    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> ApiFootballPayload:
        del save_raw
        safe_params = dict(params or {})
        self.calls.append((endpoint, safe_params))
        key = (endpoint, tuple(sorted(safe_params.items())))
        return ApiFootballPayload(
            endpoint=endpoint,
            params=safe_params,
            payload=self.responses[key],
            fetched_at=datetime(2026, 5, 2, 10, tzinfo=UTC).isoformat(),
            status_code=200,
        )


def test_live_leagues_and_teams_are_snapshotted_and_upserted(tmp_path) -> None:
    competition = _synthetic_competition()
    client = FakeApiClient(
        responses={
            (LEAGUES, (("id", -100), ("season", 2026))): {
                "response": [
                    {
                        "league": {
                            "id": -100,
                            "name": "Synthetic League",
                            "type": "League",
                        },
                        "country": {"name": "Synthetic Country", "code": "SYN"},
                        "seasons": [{"year": 2026, "start": "2026-01-01", "end": "2026-12-31"}],
                    }
                ]
            },
            (TEAMS, (("league", -100), ("season", 2026))): {
                "response": [
                    {
                        "team": {
                            "id": -200,
                            "name": "Synthetic Team",
                            "country": "Synthetic Country",
                        },
                        "venue": {"id": -300, "name": "Synthetic Venue"},
                    }
                ]
            },
        },
        calls=[],
    )
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'ingestion.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        service = ApiReferenceIngestionService(session, client)
        league_summary = service.ingest_leagues([competition])
        team_summary = service.ingest_teams([competition])

        assert league_summary.leagues == 1
        assert team_summary.teams == 1
        assert session.scalar(select(func.count()).select_from(models.RawApiSnapshot)) == 2
        assert session.get(models.League, 1) is not None
        assert session.get(models.Team, -200) is not None
        assert session.get(models.Venue, -300) is not None

    assert client.calls == [
        (LEAGUES, {"id": -100, "season": 2026}),
        (TEAMS, {"league": -100, "season": 2026}),
    ]


def test_live_player_squads_are_snapshotted_and_upserted(tmp_path) -> None:
    competition = _synthetic_competition()
    client = FakeApiClient(
        responses={
            (PLAYERS_SQUADS, (("team", -200),)): {
                "response": [
                    {
                        "team": {"id": -200, "name": "Synthetic Team"},
                        "players": [
                            {
                                "id": -400,
                                "name": "Synthetic Player",
                                "number": 9,
                                "position": "Attacker",
                            }
                        ],
                    }
                ]
            }
        },
        calls=[],
    )
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'squads.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        session.add(models.Team(team_id=-200, name="Synthetic Team", payload_json={}))
        session.add(
            models.TeamSeason(team_id=-200, league_id=-100, season=2026, payload_json={})
        )
        summary = ApiReferenceIngestionService(session, client).ingest_player_squads(
            [competition]
        )

        assert summary.players == 1
        assert summary.squads == 1
        assert session.get(models.Player, -400) is not None
        assert session.scalar(select(func.count()).select_from(models.RawApiSnapshot)) == 1


def test_live_bookmakers_and_bets_are_snapshotted_and_upserted(tmp_path) -> None:
    client = FakeApiClient(
        responses={
            (ODDS_BOOKMAKERS, ()): {"response": [{"id": -500, "name": "Synthetic Book"}]},
            (ODDS_BETS, ()): {"response": [{"id": -600, "name": "Synthetic Bet"}]},
        },
        calls=[],
    )
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'odds_refs.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        service = ApiReferenceIngestionService(session, client)
        bookmakers_summary = service.ingest_bookmakers()
        bets_summary = service.ingest_bets()

        assert bookmakers_summary.bookmakers == 1
        assert bets_summary.bets == 1
        assert session.get(models.Bookmaker, -500) is not None
        assert session.scalar(select(func.count()).select_from(models.Bet)) == 1
        assert session.scalar(select(func.count()).select_from(models.RawApiSnapshot)) == 2


def _synthetic_competition() -> CompetitionConfig:
    # Synthetic DB/API-mock IDs. They are not API-Football examples.
    return CompetitionConfig(
        key="synthetic_competition",
        league_id=-100,
        season=2026,
        name="Synthetic League",
        country="Synthetic Country",
        source="synthetic-test-payload",
    )
