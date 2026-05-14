from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
from test_feature_builder import _seed_point_in_time_sources
from test_player_xi_features import PREDICTION_TIME, _seed_base
from typer.testing import CliRunner

from football_predictor.backtesting.production_like import (
    ProductionLikeBacktestConfig,
    production_like_prediction_time,
    run_production_like_backtest,
)
from football_predictor.cli import app
from football_predictor.config.settings import Settings
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.ou_model.backtesting.ou_dataset_builder import (
    build_ou_training_dataset,
)


def test_production_like_prediction_time_is_kickoff_minus_30_minutes() -> None:
    kickoff = datetime(2026, 5, 2, 12, 30, tzinfo=UTC)

    assert production_like_prediction_time(kickoff) == datetime(
        2026, 5, 2, 12, tzinfo=UTC
    )


def test_ou_dataset_builder_minutes_offset_takes_precedence(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'ou_dataset_m30.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_finished_target(session)
        frame = build_ou_training_dataset(
            session,
            ou_bet_id=-25,
            league_ids=[-100],
            seasons=[2026],
            prediction_offset_hours=24,
            prediction_offset_minutes=30,
            date_from=PREDICTION_TIME,
            date_to=PREDICTION_TIME + timedelta(hours=1),
        )

    assert len(frame) == 1
    row = frame.iloc[0]
    assert row["fixture_id"] == -900
    assert pd.Timestamp(row["prediction_time"]).to_pydatetime() == PREDICTION_TIME
    assert row["market_ou_bookmaker_count"] == 1
    assert row["ou_market_odd_over"] == 1.9


def test_run_production_like_backtest_writes_combined_reports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'production_like.db'}")
    session_factory = create_session_factory(engine)
    output_dir = tmp_path / "reports"

    def fake_v3_backtest(dataset_path: Path, _model_dir: Path, **kwargs):
        frame = pd.read_parquet(dataset_path)
        assert set(frame["fixture_id"]) == {-900}
        assert pd.Timestamp(frame.iloc[0]["prediction_time"]).to_pydatetime() == (
            PREDICTION_TIME
        )
        assert frame.iloc[0]["market_home"] < 0.9
        return SimpleNamespace(
            payload={
                "periods": {"test": {"row_count": 1}},
                "metrics": {
                    "test": {
                        "v3_stacker_full": {"row_count": 1},
                        "v2_existing": {"row_count": 1},
                        "odds_only": {"row_count": 1},
                        "api_prediction_only": {"row_count": 1},
                        "poisson_baseline": {"row_count": 1},
                    }
                },
                "published_only_report": {
                    "scopes": {
                        "published_only": {
                            "v3_stacker_full": {"row_count": 1},
                            "api_prediction_only": {"row_count": 1},
                            "poisson_baseline": {"row_count": 1},
                        }
                    },
                    "comparisons": {
                        "published_only": {
                            "v3_stacker_full_vs_api_prediction_only": {
                                "log_loss_delta": -0.1,
                            }
                        }
                    },
                },
            },
            report_paths={"json": kwargs["output_dir"] / "v3_backtest_report.json"},
        )

    def fake_ou_backtest(dataset_path: Path, *, output_dir: Path, config):
        frame = pd.read_parquet(dataset_path)
        assert set(frame["fixture_id"]) == {-900}
        assert pd.Timestamp(frame.iloc[0]["prediction_time"]).to_pydatetime() == (
            PREDICTION_TIME
        )
        assert frame.iloc[0]["ou_market_odd_over"] == 1.9
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "published_only_report.json").write_text(
            json.dumps(
                {
                    "model_family": "ou25",
                    "aggregate": {"published_rows": 1},
                    "folds": [
                        {
                            "scopes": {
                                "published_only": {
                                    "ensemble": {"row_count": 1},
                                    "market": {"row_count": 1},
                                }
                            }
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(
            aggregate={"published_only": {"fold_count": 1}},
            confidence_thresholds={"model_family": "ou25"},
        )

    monkeypatch.setattr(
        "football_predictor.backtesting.production_like.run_v3_backtest",
        fake_v3_backtest,
    )
    monkeypatch.setattr(
        "football_predictor.backtesting.production_like.run_ou_backtest",
        fake_ou_backtest,
    )

    with session_scope(session_factory) as session:
        _seed_finished_target(session)
        result = run_production_like_backtest(
            session,
            config=ProductionLikeBacktestConfig(
                league_ids=[-100],
                seasons=[2026],
                output_dir=output_dir,
                v3_model_dir=tmp_path / "models" / "v3",
                ou_bet_id=-25,
                date_from=PREDICTION_TIME,
                date_to=PREDICTION_TIME + timedelta(hours=1),
                ou_n_splits=1,
                ou_min_train_rows=1,
            ),
        )

    assert result.v3_rows == 1
    assert result.ou_rows == 1
    assert result.report_paths["json"].exists()
    assert result.report_paths["markdown"].exists()
    assert result.payload["leakage_checks"]["m30_cutoff"]["v3"]["all_rows_match"] is True
    assert result.payload["leakage_checks"]["m30_cutoff"]["ou25"]["all_rows_match"] is True
    assert result.payload["leakage_checks"]["future_source_rows_present"]["odds_snapshots"] >= 1
    combined = json.loads(result.report_paths["json"].read_text(encoding="utf-8"))
    assert combined["reports"]["v3_1x2"]["published_only_report"]["scopes"][
        "published_only"
    ]["api_prediction_only"]["row_count"] == 1
    assert combined["reports"]["ou25"]["published_only_report"]["aggregate"][
        "published_rows"
    ] == 1


def test_backtest_production_like_cli_passes_offline_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_dir = tmp_path / "reports"

    def fake_settings() -> Settings:
        return Settings(
            DATABASE_URL=f"sqlite:///{tmp_path / 'cli.db'}",
            MARKET_OU25_BET_ID=-25,
            PUBLICATION_MIN_DATA_QUALITY_SCORE=61,
        )

    def fake_run(session, *, config, players_reference=None):
        assert config.league_ids == [-100]
        assert config.seasons == [2026]
        assert config.output_dir == output_dir
        assert config.prediction_offset_minutes == 30
        assert config.min_data_quality_score == 61
        assert config.ou_bet_id == -25
        assert config.report_format == "json"
        assert session is not None
        assert players_reference is None
        return SimpleNamespace(
            v3_rows=1,
            ou_rows=1,
            dataset_paths={"v3": output_dir / "datasets" / "v3_m30.parquet"},
            report_paths={"json": output_dir / "production_like_backtest_report.json"},
            payload={"leakage_checks": {"m30_cutoff": {"v3": {"all_rows_match": True}}}},
        )

    monkeypatch.setattr("football_predictor.cli.get_settings", fake_settings)
    monkeypatch.setattr(
        "football_predictor.backtesting.production_like.run_production_like_backtest",
        fake_run,
    )

    result = CliRunner().invoke(
        app,
        [
            "backtest-production-like",
            "--league-id",
            "-100",
            "--season",
            "2026",
            "--output-dir",
            str(output_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "v3_rows" in result.stdout
    assert "leakage_checks" in result.stdout


def _seed_finished_target(session) -> None:
    _seed_base(session)
    _seed_point_in_time_sources(session)
    session.flush()
    target = session.get(models.Fixture, -900)
    target.date = PREDICTION_TIME + timedelta(minutes=30)
    target.status = "FT"
    target.status_short = "FT"
    target.home_goals = 2
    target.away_goals = 1
    session.add_all(
        [
            models.OddsSnapshot(
                fixture_id=-900,
                league_id=-100,
                season=2026,
                bookmaker_id=-3,
                bookmaker_name="Synthetic O/U Book",
                bet_id=-25,
                bet_name="Over/Under 2.5",
                odd_home=1.9,
                odd_away=1.95,
                values_json=[],
                fetched_at=PREDICTION_TIME - timedelta(hours=1),
                payload_json={"synthetic": True},
            ),
            models.OddsSnapshot(
                fixture_id=-900,
                league_id=-100,
                season=2026,
                bookmaker_id=-3,
                bookmaker_name="Synthetic O/U Book",
                bet_id=-25,
                bet_name="Over/Under 2.5",
                odd_home=1.01,
                odd_away=99.0,
                values_json=[],
                fetched_at=PREDICTION_TIME + timedelta(hours=1),
                payload_json={"synthetic": True},
            ),
        ]
    )
    session.flush()
