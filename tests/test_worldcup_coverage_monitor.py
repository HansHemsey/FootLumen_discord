from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import inspect, select

from football_predictor.db import models
from football_predictor.db.session import (
    create_db_engine,
    create_session_factory,
    init_db,
    session_scope,
)
from football_predictor.worldcup.coverage_monitor import (
    WorldCupCoverageMonitor,
    WorldCupCoverageSummary,
)


def test_api_coverage_observation_registers_and_zero_is_not_useful(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'coverage.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        monitor = WorldCupCoverageMonitor(session)
        observation = monitor.record_observation(
            endpoint="odds_1x2",
            result_count=0,
            requested_at=datetime(2026, 6, 11, 12, tzinfo=UTC),
            write=True,
        )

        records = session.execute(select(models.ApiCoverageObservation)).scalars().all()

    assert observation.useful_payload_flag is False
    assert observation.status == "missing"
    assert len(records) == 1
    assert records[0].useful_payload_flag is False


def test_api_coverage_table_created_by_init_db(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'coverage_schema.db'}")
    init_db(engine)

    inspector = inspect(engine)

    assert "api_coverage_observations" in inspector.get_table_names()
    assert "ix_api_coverage_fixture_endpoint" in _index_names(engine)


def test_worldcup_fixture_quality_drops_when_1x2_odds_are_missing(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'coverage_quality.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    now = datetime(2026, 6, 11, 12, tzinfo=UTC)

    with session_scope(session_factory) as session:
        _seed_worldcup_fixture(session, kickoff=now + timedelta(hours=6))
        monitor = WorldCupCoverageMonitor(session)

        without_odds = monitor.fixture_quality_matrix(session.get(models.Fixture, -901), now=now)
        _seed_1x2_odds(session, fetched_at=now - timedelta(minutes=5))
        with_odds = monitor.fixture_quality_matrix(session.get(models.Fixture, -901), now=now)

    assert without_odds.has_odds_1x2 is False
    assert "odds_1x2_missing" in without_odds.warnings
    assert with_odds.has_odds_1x2 is True
    assert with_odds.data_quality_score > without_odds.data_quality_score


def test_worldcup_coverage_summary_counts_all_fixtures_as_fixture_coverage(
    tmp_path: Path,
) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'coverage_summary.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    now = datetime(2026, 6, 11, 12, tzinfo=UTC)

    with session_scope(session_factory) as session:
        _seed_worldcup_fixture(session, kickoff=now + timedelta(hours=6))
        summary = WorldCupCoverageMonitor(session).build_summary(now=now)

    assert summary.fixtures_total == 1
    assert summary.endpoint_coverage["fixtures"]["useful"] == 1
    assert summary.endpoint_coverage["fixtures"]["coverage_pct"] == 100.0


def test_worldcup_fixture_quality_drops_when_expected_lineups_are_missing(
    tmp_path: Path,
) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'coverage_lineups.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    now = datetime(2026, 6, 11, 18, 30, tzinfo=UTC)

    with session_scope(session_factory) as session:
        _seed_worldcup_fixture(session, kickoff=now + timedelta(minutes=30))
        monitor = WorldCupCoverageMonitor(session)

        without_lineups = monitor.fixture_quality_matrix(
            session.get(models.Fixture, -901),
            now=now,
        )
        _seed_lineups(session, fetched_at=now - timedelta(minutes=5))
        with_lineups = monitor.fixture_quality_matrix(
            session.get(models.Fixture, -901),
            now=now,
        )

    assert without_lineups.lineups_expected is True
    assert without_lineups.has_lineups is False
    assert "lineups_expected_missing" in without_lineups.warnings
    assert with_lineups.has_lineups is True
    assert with_lineups.data_quality_score > without_lineups.data_quality_score


def test_worldcup_coverage_report_generates_files_and_sanitizes_warning(
    tmp_path: Path,
) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'coverage_report.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    now = datetime(2026, 6, 11, 12, tzinfo=UTC)
    secret = "".join(
        [
            "API",
            "_FOOTBALL",
            "_KEY",
            "=",
            "abcdefghijklmnopqrstuvwxyz",
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "0123456789",
        ]
    )

    with session_scope(session_factory) as session:
        _seed_worldcup_fixture(session, kickoff=now + timedelta(hours=6))
        monitor = WorldCupCoverageMonitor(session)
        fixture_quality = monitor.fixture_quality_matrix(
            session.get(models.Fixture, -901),
            now=now,
        )
        observation = monitor.record_observation(
            endpoint="fixtures",
            result_count=1,
            requested_at=now,
            warning=secret,
            write=False,
        )
        summary = WorldCupCoverageSummary(
            competition_key=monitor.competition_key,
            league_id=monitor.league_id,
            season=monitor.season,
            generated_at=now,
            fixtures_total=1,
            endpoint_coverage={"fixtures": {"total": 1, "useful": 1, "coverage_pct": 100.0}},
            fixture_quality=(fixture_quality,),
            observations=(observation,),
        )
        paths = monitor.write_reports(summary, output_dir=tmp_path / "reports")

    summary_text = paths["summary_json"].read_text(encoding="utf-8")
    markdown_text = paths["markdown"].read_text(encoding="utf-8")
    assert paths["summary_json"].exists()
    assert paths["markdown"].exists()
    assert secret not in summary_text
    assert secret not in markdown_text
    assert "<redacted>" in summary_text


def _seed_worldcup_fixture(session, *, kickoff: datetime) -> None:
    session.add_all(
        [
            models.Team(
                team_id=-901,
                name="Synthetic Home",
                country="Synthetic",
                national=True,
                payload_json={"synthetic": True},
            ),
            models.Team(
                team_id=-902,
                name="Synthetic Away",
                country="Synthetic",
                national=True,
                payload_json={"synthetic": True},
            ),
        ]
    )
    session.add(
        models.Fixture(
            fixture_id=-901,
            date=kickoff,
            timestamp=int(kickoff.timestamp()),
            timezone="UTC",
            round="Group Stage - 1",
            league_id=1,
            season=2026,
            status="NS",
            status_short="NS",
            home_team_id=-901,
            away_team_id=-902,
            home_team="Synthetic Home",
            away_team="Synthetic Away",
            payload_json={"synthetic": True, "competition_key": "fifa_world_cup_2026"},
        )
    )
    session.flush()


def _seed_1x2_odds(session, *, fetched_at: datetime) -> None:
    session.add(
        models.OddsSnapshot(
            fixture_id=-901,
            league_id=1,
            season=2026,
            bookmaker_id=-1,
            bookmaker_name="Synthetic Book",
            bet_id=1,
            bet_name="Match Winner",
            fetched_at=fetched_at,
            is_live=False,
            odd_home=2.1,
            odd_draw=3.2,
            odd_away=3.8,
            values_json=[],
            odds_json={"synthetic": True},
            payload_json={"synthetic": True},
        )
    )
    session.flush()


def _seed_lineups(session, *, fetched_at: datetime) -> None:
    for team_id, formation in ((-901, "4-3-3"), (-902, "4-4-2")):
        session.add(
            models.FixtureLineup(
                fixture_id=-901,
                team_id=team_id,
                formation=formation,
                fetched_at=fetched_at,
                start_xi_json=[],
                substitutes_json=[],
                players_json=[],
                payload_json={"synthetic": True},
            )
        )
    session.flush()


def _index_names(engine) -> set[str]:
    return {index["name"] for index in inspect(engine).get_indexes("api_coverage_observations")}
