from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

import football_predictor.worldcup.service as worldcup_service_module
from football_predictor.db import models
from football_predictor.db.session import (
    create_db_engine,
    create_session_factory,
    init_db,
    session_scope,
)
from football_predictor.features.data_quality import DataQuality
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.prediction.service import PredictionOutput
from football_predictor.utils.exceptions import PredictionError
from football_predictor.utils.time import utc_now
from football_predictor.worldcup.blend import (
    WORLD_CUP_BLEND_CONFIG_FILENAME,
    WorldCupBlendConfig,
    load_worldcup_blend_config,
)
from football_predictor.worldcup.blend_optimizer import (
    _select_candidate,
    optimize_worldcup_blend,
)
from football_predictor.worldcup.dynamic import build_worldcup_dynamic_features
from football_predictor.worldcup.features import build_worldcup_dataset
from football_predictor.worldcup.model import (
    WorldCupTrainingConfig,
    train_worldcup_model_from_frame,
)
from football_predictor.worldcup.references import (
    InternationalMatch,
    audit_worldcup_references,
    load_worldcup_reference_bundle,
)
from football_predictor.worldcup.run_daily import run_daily_worldcup_predictions
from football_predictor.worldcup.service import WorldCupPredictionService

WORLD_CUP_TEAMS = [
    "Algeria",
    "Argentina",
    "Australia",
    "Austria",
    "Belgium",
    "Bosnia & Herzegovina",
    "Brazil",
    "Canada",
    "Cape Verde Islands",
    "Colombia",
    "Congo DR",
    "Croatia",
    "Curaçao",
    "Czech Republic",
    "Ecuador",
    "Egypt",
    "England",
    "France",
    "Germany",
    "Ghana",
    "Haiti",
    "Iran",
    "Iraq",
    "Ivory Coast",
    "Japan",
    "Jordan",
    "Mexico",
    "Morocco",
    "Netherlands",
    "New Zealand",
    "Norway",
    "Panama",
    "Paraguay",
    "Portugal",
    "Qatar",
    "Saudi Arabia",
    "Scotland",
    "Senegal",
    "South Africa",
    "South Korea",
    "Spain",
    "Sweden",
    "Switzerland",
    "Tunisia",
    "Türkiye",
    "USA",
    "Uruguay",
    "Uzbekistan",
]


def test_worldcup_references_cover_48_fixture_teams(repo_root: Path) -> None:
    bundle = _bundle(repo_root)

    audit = audit_worldcup_references(WORLD_CUP_TEAMS, bundle)

    assert audit["ok"] is True
    assert audit["matched_count"] == 48
    assert audit["blocking_missing_teams"] == []
    assert audit["elo_missing_teams"] == []
    rows = {row["team"]: row for row in audit["teams"]}
    assert rows["USA"]["canonical_team"] == "USA"
    assert rows["Türkiye"]["historical_available"] is True
    assert rows["Türkiye"]["elo_available"] is True
    assert rows["Congo DR"]["fifa_available"] is True
    assert rows["Congo DR"]["elo_available"] is True
    assert rows["Cape Verde Islands"]["historical_available"] is True
    assert rows["Cape Verde Islands"]["elo_available"] is True
    assert rows["Czech Republic"]["elo_available"] is True
    assert rows["Argentina"]["elo_available"] is True
    assert rows["Spain"]["elo_available"] is True


def test_worldcup_features_are_chronological_and_exclude_target() -> None:
    matches = [
        _match("2024-01-01", "Alpha", "Beta", 1, 0),
        _match("2024-02-01", "Alpha", "Beta", 0, 5),
        _match("2024-03-01", "Alpha", "Beta", 2, 0),
    ]

    frame = build_worldcup_dataset(matches)

    assert frame.loc[0, "wc_home_history_count"] == 0
    assert frame.loc[1, "wc_home_history_count"] == 1
    assert frame.loc[1, "wc_home_last5_goals_for_avg"] == pytest.approx(1.0)
    assert frame.loc[1, "wc_home_last5_goals_against_avg"] == pytest.approx(0.0)
    assert frame.loc[2, "wc_home_history_count"] == 2
    assert frame.loc[2, "wc_home_last5_goals_against_avg"] == pytest.approx(2.5)


def test_worldcup_model_save_load_and_normalized_probabilities(tmp_path: Path) -> None:
    frame = build_worldcup_dataset(_synthetic_matches(150))

    result = train_worldcup_model_from_frame(
        frame,
        tmp_path / "model",
        config=WorldCupTrainingConfig(min_rows_for_calibration=20),
    )
    loaded = result.model.load(result.model_path)
    probabilities = loaded.predict_proba(frame.tail(3))

    assert result.model_path.exists()
    assert (tmp_path / "model" / "metadata.json").exists()
    assert "draw_precision" in result.metrics["test"]
    assert "draw_recall" in result.metrics["test"]
    assert "draw_f1" in result.metrics["test"]
    assert "observed_draw_rate" in result.metrics["test"]
    assert "mean_predicted_p_draw" in result.metrics["test"]
    assert "draw_calibration_bins" in result.metrics["test"]
    assert "confusion_matrix_labeled" in result.metrics["test"]
    assert probabilities
    for row in probabilities:
        assert sum(row) == pytest.approx(1.0)
        assert all(value >= 0 for value in row)


def test_worldcup_blend_config_normalizes_and_ignores_missing_sources() -> None:
    config = WorldCupBlendConfig(
        selected_candidate="synthetic",
        source_weights={"wc_market": 0.8, "wc_rating_dynamic": 0.2},
    )

    weights = config.weights_for_sources({"wc_rating_dynamic", "wc_poisson_dynamic"})

    assert weights == {"wc_rating_dynamic": 1.0}


def test_worldcup_invalid_blend_config_falls_back(tmp_path: Path) -> None:
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / WORLD_CUP_BLEND_CONFIG_FILENAME).write_text("{not-json", encoding="utf-8")

    config = load_worldcup_blend_config(model_dir)

    assert config.selected_candidate == "default_conservative"
    assert config.weights_for_sources({"wc_rating_dynamic", "wc_poisson_dynamic"})


def test_worldcup_optimize_blend_reports_candidates_without_market_api(
    tmp_path: Path,
) -> None:
    frame = build_worldcup_dataset(_synthetic_matches(120))
    dataset = tmp_path / "worldcup.csv"
    output_dir = tmp_path / "reports"
    frame.to_csv(dataset, index=False)

    result = optimize_worldcup_blend(dataset, output_dir=output_dir)

    candidate_names = {row["name"] for row in result.metrics["candidates"]}
    assert "rating_only" in candidate_names
    assert "rating_poisson_60_40" in candidate_names
    assert "rating_poisson_tabular_55_40_05" in candidate_names
    assert "market_rating_poisson_40_35_25" not in candidate_names
    assert result.report_paths["json"].exists()
    assert result.report_paths["markdown"].exists()
    assert result.metrics["dynamic_coverage"]["validation"]["market"] == 0.0


def test_worldcup_select_candidate_applies_tabular_and_test_guardrails() -> None:
    candidate_metrics = [
        _candidate_metric("rating_only", {"wc_rating_dynamic": 1.0}, 1.00, 0.66, 0.90, 0.60),
        _candidate_metric(
            "rating_poisson_60_40",
            {"wc_rating_dynamic": 0.6, "wc_poisson_dynamic": 0.4},
            0.98,
            0.65,
            0.93,
            0.60,
        ),
        _candidate_metric(
            "rating_poisson_tabular_55_40_05",
            {"wc_rating_dynamic": 0.55, "wc_poisson_dynamic": 0.4, "wc_model": 0.05},
            0.99,
            0.64,
            0.93,
            0.59,
            uses_tabular=True,
        ),
        _candidate_metric(
            "current_blend",
            {"wc_rating_dynamic": 0.2, "wc_poisson_dynamic": 0.15, "wc_model": 0.4},
            0.96,
            0.67,
            1.10,
            0.40,
            uses_tabular=True,
        ),
    ]

    selection = _select_candidate(candidate_metrics)

    assert selection["selected_candidate"] == "rating_poisson_60_40"
    assert selection["selection_reason"] == "test_guardrail_fallback_rating_poisson_60_40"


def test_predict_worldcup_fixture_persists_prediction(tmp_path: Path, repo_root: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'wc.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    bundle = _bundle(repo_root)
    with session_scope(session_factory) as session:
        _seed_worldcup_fixture(session, fixture_id=9001)
        service = WorldCupPredictionService(session, bundle, model_dir=tmp_path / "missing")

        output = service.predict_fixture(
            9001,
            datetime(2026, 6, 11, 18, 30, tzinfo=UTC),
        )

        assert output.model_prediction_id is not None
        assert output.feature_snapshot_id is not None
        total_probability = (
            output.probabilities.p_home
            + output.probabilities.p_draw
            + output.probabilities.p_away
        )
        assert total_probability == pytest.approx(1.0)
        assert session.get(models.ModelPrediction, output.model_prediction_id) is not None


def test_worldcup_dynamic_features_ignore_future_snapshots(
    tmp_path: Path,
    repo_root: Path,
) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'wc_dynamic.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    cutoff = datetime(2026, 6, 11, 18, 30, tzinfo=UTC)
    with session_scope(session_factory) as session:
        _seed_worldcup_fixture(session, fixture_id=9004)
        _seed_player(session, player_id=101, team_id=1)
        _seed_odds(session, fixture_id=9004, fetched_at=cutoff - timedelta(minutes=20))
        _seed_odds(
            session,
            fixture_id=9004,
            fetched_at=cutoff + timedelta(minutes=5),
            odds=(9.0, 1.2, 9.0),
        )
        session.add_all(
            [
                models.ApiPredictionSnapshot(
                    fixture_id=9004,
                    fetched_at=cutoff - timedelta(minutes=10),
                    percent_home=60.0,
                    percent_draw=25.0,
                    percent_away=15.0,
                    payload_json={},
                ),
                models.ApiPredictionSnapshot(
                    fixture_id=9004,
                    fetched_at=cutoff + timedelta(minutes=10),
                    percent_home=5.0,
                    percent_draw=5.0,
                    percent_away=90.0,
                    payload_json={},
                ),
                models.FixtureLineup(
                    fixture_id=9004,
                    team_id=1,
                    formation="4-3-3",
                    fetched_at=cutoff - timedelta(minutes=15),
                    start_xi_json=[{"player": {"id": 101}}],
                    substitutes_json=[],
                    players_json=[],
                    payload_json={},
                ),
                models.FixtureLineup(
                    fixture_id=9004,
                    team_id=2,
                    formation="4-4-2",
                    fetched_at=cutoff - timedelta(minutes=15),
                    start_xi_json=[],
                    substitutes_json=[],
                    players_json=[],
                    payload_json={},
                ),
                models.FixtureLineup(
                    fixture_id=9004,
                    team_id=2,
                    formation="3-4-3",
                    fetched_at=cutoff + timedelta(minutes=15),
                    start_xi_json=[],
                    substitutes_json=[],
                    players_json=[],
                    payload_json={},
                ),
                models.Injury(
                    fixture_id=9004,
                    team_id=1,
                    player_id=101,
                    fetched_at=cutoff - timedelta(minutes=30),
                    type="Suspended",
                    reason="Suspended",
                    payload_json={},
                ),
                models.Injury(
                    fixture_id=9004,
                    team_id=2,
                    player_id=201,
                    fetched_at=cutoff + timedelta(minutes=30),
                    type="Suspended",
                    reason="Suspended",
                    payload_json={},
                ),
            ]
        )
        session.flush()
        fixture = session.get(models.Fixture, 9004)

        features = build_worldcup_dynamic_features(session, fixture, cutoff)

    assert features["wc_market_available_flag"] == 1
    assert features["p_wc_market_home"] > features["p_wc_market_away"]
    assert features["p_wc_api_home"] == pytest.approx(0.60)
    assert features["wc_official_lineup_home_available_flag"] == 1
    assert features["wc_official_lineup_away_available_flag"] == 1
    assert features["away_team_official_formation"] == "4-4-2"
    assert features["wc_injuries_available_flag"] == 1
    assert features["wc_dynamic_source_count"] == 4


def test_worldcup_prediction_uses_dynamic_market_and_api(
    tmp_path: Path,
    repo_root: Path,
) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'wc_dynamic_predict.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    cutoff = datetime(2026, 6, 11, 18, 30, tzinfo=UTC)
    with session_scope(session_factory) as session:
        _seed_worldcup_fixture(session, fixture_id=9005)
        _seed_odds(session, fixture_id=9005, fetched_at=cutoff - timedelta(minutes=5))
        session.add(
            models.ApiPredictionSnapshot(
                fixture_id=9005,
                fetched_at=cutoff - timedelta(minutes=5),
                percent_home=55.0,
                percent_draw=25.0,
                percent_away=20.0,
                payload_json={},
            )
        )
        service = WorldCupPredictionService(session, _bundle(repo_root), model_dir=tmp_path)

        output = service.predict_fixture(9005, cutoff)

        assert output.market_probabilities is not None
        assert output.api_probabilities is not None
        assert "wc_market" in output.sources_used
        assert "wc_api" in output.sources_used
        assert output.data_quality_json["worldcup_dynamic_market_available"] is True


def test_worldcup_predict_refresh_data_calls_dynamic_refresh(
    monkeypatch,
    tmp_path: Path,
    repo_root: Path,
) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'wc_refresh.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    calls = []

    def fake_refresh(self, fixture_id: int, *, api_client, save_raw: bool):
        calls.append((fixture_id, api_client, save_raw))
        return {"fixture_id": fixture_id, "save_raw": save_raw}

    monkeypatch.setattr(WorldCupPredictionService, "_refresh_dynamic_data", fake_refresh)
    with session_scope(session_factory) as session:
        _seed_worldcup_fixture(session, fixture_id=9006)
        service = WorldCupPredictionService(session, _bundle(repo_root), model_dir=tmp_path)

        output = service.predict_fixture(
            9006,
            refresh_data=True,
            save_raw=True,
            api_client=object(),
        )

    assert calls
    assert calls[0][0] == 9006
    assert calls[0][2] is True
    assert output.refresh_summary["save_raw"] is True


def test_worldcup_refresh_records_independent_source_health(
    monkeypatch,
    tmp_path: Path,
    repo_root: Path,
) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'wc_refresh_health.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    cutoff = datetime(2026, 6, 11, 12, 0, tzinfo=UTC)
    _install_refresh_fakes(
        monkeypatch,
        failures={"api_prediction", "lineups"},
    )

    with session_scope(session_factory) as session:
        _seed_worldcup_fixture(session, fixture_id=9011)
        service = WorldCupPredictionService(
            session,
            _bundle(repo_root),
            model_dir=tmp_path,
            reference=object(),
        )

        output = service.predict_fixture(
            9011,
            cutoff,
            refresh_data=True,
            api_client=object(),
        )

    source_health = {
        row["source_name"]: row["status"]
        for row in output.refresh_summary["source_health"]
    }
    assert source_health["odds"] == "success"
    assert source_health["api_prediction"] == "failed"
    assert source_health["lineups"] == "failed"
    assert "odds_failed" not in output.refresh_summary["warnings"]
    assert "api_prediction_failed" in output.refresh_summary["warnings"]
    assert "lineups_failed" in output.data_quality_json["warnings"]
    assert output.data_quality_json["source_health"]


def test_worldcup_refresh_odds_failure_adds_warning(
    monkeypatch,
    tmp_path: Path,
    repo_root: Path,
) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'wc_refresh_odds_failure.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    cutoff = datetime(2026, 6, 11, 12, 0, tzinfo=UTC)
    _install_refresh_fakes(monkeypatch, failures={"odds"})

    with session_scope(session_factory) as session:
        _seed_worldcup_fixture(session, fixture_id=9012)
        service = WorldCupPredictionService(
            session,
            _bundle(repo_root),
            model_dir=tmp_path,
            reference=object(),
        )

        output = service.predict_fixture(
            9012,
            cutoff,
            refresh_data=True,
            api_client=object(),
        )

    assert "odds_failed" in output.refresh_summary["warnings"]
    assert "odds_failed" in output.data_quality_json["warnings"]
    assert output.data_quality_json["overall_data_quality_score"] < 100


def test_worldcup_refresh_lineups_failure_close_to_kickoff_caps_confidence(
    monkeypatch,
    tmp_path: Path,
    repo_root: Path,
) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'wc_refresh_lineups_cap.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    kickoff = datetime(2026, 6, 11, 19, 0, tzinfo=UTC)
    cutoff = kickoff - timedelta(minutes=30)
    _install_refresh_fakes(monkeypatch, failures={"lineups"})

    with session_scope(session_factory) as session:
        _seed_worldcup_fixture(session, fixture_id=9013, kickoff=kickoff)
        service = WorldCupPredictionService(
            session,
            _bundle(repo_root),
            model_dir=tmp_path,
            reference=object(),
        )

        output = service.predict_fixture(
            9013,
            cutoff,
            refresh_data=True,
            api_client=object(),
        )

    assert "lineups_failed_close_to_kickoff" in output.data_quality_json["warnings"]
    assert output.confidence_label in {"Uncertain", "Low"}
    assert output.confidence_score <= 54.0


def test_predict_worldcup_rejects_non_worldcup_fixture(tmp_path: Path, repo_root: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'wc_reject.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        _seed_worldcup_fixture(session, fixture_id=9002, league_id=39, season=2025)
        service = WorldCupPredictionService(session, _bundle(repo_root))

        with pytest.raises(Exception, match="World Cup 2026"):
            service.predict_fixture(9002)


def test_worldcup_daily_low_confidence_goes_to_staff(
    monkeypatch,
    tmp_path: Path,
    repo_root: Path,
) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'wc_daily.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    kickoff = utc_now() + timedelta(minutes=10)
    service_calls = []

    class FakeWorldCupPredictionService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def predict_fixture(self, fixture_id: int, prediction_time=None, **kwargs):
            service_calls.append({"fixture_id": fixture_id, "kwargs": kwargs})
            return PredictionOutput(
                fixture_id=fixture_id,
                match_label="Mexico vs South Africa",
                competition="FIFA World Cup 2026",
                match_date=kickoff,
                prediction_time=prediction_time or utc_now(),
                probabilities=ProbabilityTriple(0.44, 0.31, 0.25),
                predicted_result="HOME",
                confidence_label="Low",
                confidence_score=35.0,
                explanations=["Synthetic low confidence"],
                data_quality=DataQuality(),
                data_quality_json={"overall_data_quality_score": 70},
                model_version="worldcup-test",
                model_prediction_id=123,
            )

    class FakeDelivery:
        def __init__(self) -> None:
            self.calls = []

        def send_markdown(self, markdown: str, **kwargs):
            self.calls.append({"markdown": markdown, **kwargs})
            return SimpleNamespace(status="sent", discord_message_id=77)

    monkeypatch.setattr(
        "football_predictor.worldcup.run_daily.WorldCupPredictionService",
        FakeWorldCupPredictionService,
    )
    with session_scope(session_factory) as session:
        _seed_worldcup_fixture(session, fixture_id=9003, kickoff=kickoff)
        delivery = FakeDelivery()
        api_client = object()
        summary = run_daily_worldcup_predictions(
            session,
            _bundle(repo_root),
            target_date=kickoff.astimezone().date(),
            send_discord=True,
            refresh_data=True,
            api_client=api_client,
            dry_run=False,
            delivery=delivery,
        )

    assert summary.confidence_skipped == 1
    assert service_calls[0]["kwargs"]["refresh_data"] is True
    assert service_calls[0]["kwargs"]["api_client"] is api_client
    assert len(delivery.calls) == 1
    assert delivery.calls[0]["channel_key"] == "predictions_staff"
    assert delivery.calls[0]["message_type"] == "prediction_skipped"


def test_worldcup_daily_draw_safety_blocks_public_high_confidence(
    monkeypatch,
    tmp_path: Path,
    repo_root: Path,
) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'wc_daily_draw_safety.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    kickoff = utc_now() + timedelta(minutes=10)

    class FakeWorldCupPredictionService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def predict_fixture(self, fixture_id: int, prediction_time=None, **kwargs):
            return PredictionOutput(
                fixture_id=fixture_id,
                match_label="Mexico vs South Africa",
                competition="FIFA World Cup 2026",
                match_date=kickoff,
                prediction_time=prediction_time or utc_now(),
                probabilities=ProbabilityTriple(0.70, 0.12, 0.18),
                predicted_result="HOME",
                confidence_label="High",
                confidence_score=72.0,
                explanations=["Synthetic high confidence"],
                data_quality=DataQuality(),
                data_quality_json={"overall_data_quality_score": 70},
                model_version="worldcup-test",
                model_prediction_id=123,
                draw_safety_json={
                    "severity": "severe",
                    "skip_reason": "draw_safety_severe_conflict",
                    "warnings": ["draw_risk_probability_contradiction"],
                    "signals": {"p_draw": 0.12, "source_draw_probability": 0.42},
                },
            )

    class FakeDelivery:
        def __init__(self) -> None:
            self.calls = []

        def send_markdown(self, markdown: str, **kwargs):
            self.calls.append({"markdown": markdown, **kwargs})
            return SimpleNamespace(status="sent", discord_message_id=77)

    monkeypatch.setattr(
        "football_predictor.worldcup.run_daily.WorldCupPredictionService",
        FakeWorldCupPredictionService,
    )
    with session_scope(session_factory) as session:
        _seed_worldcup_fixture(session, fixture_id=9007, kickoff=kickoff)
        delivery = FakeDelivery()
        summary = run_daily_worldcup_predictions(
            session,
            _bundle(repo_root),
            target_date=kickoff.astimezone().date(),
            send_discord=True,
            dry_run=False,
            delivery=delivery,
        )

    assert summary.sent == 0
    assert summary.confidence_skipped == 1
    assert summary.results[0].reason == "draw_safety_severe_conflict"
    assert len(delivery.calls) == 1
    assert delivery.calls[0]["channel_key"] == "predictions_staff"
    assert delivery.calls[0]["payload_metadata"]["skip_reason"] == "draw_safety_severe_conflict"


def _bundle(repo_root: Path):
    return load_worldcup_reference_bundle(
        fifa_ranking_path=repo_root / "data/reference/classement_fifa_officiel.csv",
        elo_data_path=repo_root / "data/reference/elo_wc_teams_data.tsv",
        elo_shortname_path=repo_root / "data/reference/elo_wc_teams_shortname.tsv",
        historical_results_path=repo_root / "data/reference/historical_worldcup_result.csv",
    )


def _match(
    match_date: str,
    home: str,
    away: str,
    home_score: int,
    away_score: int,
    *,
    tournament: str = "Friendly",
) -> InternationalMatch:
    return InternationalMatch(
        match_date=date.fromisoformat(match_date),
        home_team=home,
        away_team=away,
        home_score=home_score,
        away_score=away_score,
        tournament=tournament,
        city=None,
        country=None,
        neutral=True,
    )


def _synthetic_matches(count: int) -> list[InternationalMatch]:
    teams = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"]
    matches: list[InternationalMatch] = []
    for index in range(count):
        home = teams[index % len(teams)]
        away = teams[(index + 1) % len(teams)]
        if index % 3 == 0:
            home_score, away_score = 2, 0
        elif index % 3 == 1:
            home_score, away_score = 1, 1
        else:
            home_score, away_score = 0, 2
        matches.append(
            _match(
                (date(2016, 1, 1) + timedelta(days=index * 7)).isoformat(),
                home,
                away,
                home_score,
                away_score,
                tournament="FIFA World Cup qualification" if index % 4 == 0 else "Friendly",
            )
        )
    return matches


def _candidate_metric(
    name: str,
    weights: dict[str, float],
    validation_log_loss: float,
    validation_brier: float,
    test_log_loss: float,
    test_accuracy: float,
    *,
    uses_tabular: bool = False,
) -> dict:
    return {
        "name": name,
        "source_weights": weights,
        "uses_tabular": uses_tabular,
        "validation": {
            "row_count": 10,
            "log_loss": validation_log_loss,
            "brier_score": validation_brier,
            "accuracy": 0.5,
        },
        "test": {
            "row_count": 10,
            "log_loss": test_log_loss,
            "brier_score": validation_brier,
            "accuracy": test_accuracy,
        },
    }


def _seed_worldcup_fixture(
    session,
    *,
    fixture_id: int,
    league_id: int = 1,
    season: int = 2026,
    kickoff: datetime | None = None,
) -> None:
    kickoff = kickoff or datetime(2026, 6, 11, 19, 0, tzinfo=UTC)
    session.add_all(
        [
            models.Team(team_id=1, name="Mexico", payload_json={}),
            models.Team(team_id=2, name="South Africa", payload_json={}),
        ]
    )
    session.flush()
    session.add(
        models.Fixture(
            fixture_id=fixture_id,
            date=kickoff,
            league_id=league_id,
            season=season,
            status="NS",
            status_short="NS",
            home_team_id=1,
            away_team_id=2,
            home_team="Mexico",
            away_team="South Africa",
            payload_json={},
        )
    )
    session.flush()


def _seed_player(session, *, player_id: int, team_id: int) -> None:
    session.add(
        models.Player(
            player_id=player_id,
            name=f"Player {player_id}",
            payload_json={},
        )
    )
    session.add(
        models.PlayerSquad(
            player_id=player_id,
            team_id=team_id,
            league_id=1,
            season=2026,
            position="Attacker",
            fetched_at=datetime(2026, 6, 1, tzinfo=UTC),
            payload_json={},
        )
    )
    session.flush()


def _seed_odds(
    session,
    *,
    fixture_id: int,
    fetched_at: datetime,
    odds: tuple[float, float, float] = (1.8, 3.5, 4.8),
) -> None:
    home, draw, away = odds
    session.add(
        models.OddsSnapshot(
            fixture_id=fixture_id,
            league_id=1,
            season=2026,
            bookmaker_id=8,
            bookmaker_name="Synthetic",
            bet_id=1,
            bet_name="Match Winner",
            fetched_at=fetched_at,
            is_live=False,
            odd_home=home,
            odd_draw=draw,
            odd_away=away,
            values_json=[],
            odds_json={},
            payload_json={},
        )
    )
    session.flush()


class _FakeRefreshSummary:
    def __init__(self, source: str) -> None:
        self.source = source

    def as_dict(self) -> dict[str, object]:
        return {"source": self.source, "ok": True}


def _install_refresh_fakes(monkeypatch, *, failures: set[str]) -> None:
    class FakeFixtureIngestionService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def ingest_fixture_by_id(self, _fixture_id: int) -> _FakeRefreshSummary:
            if "fixtures" in failures:
                raise PredictionError("fixtures refresh failed")
            return _FakeRefreshSummary("fixtures")

    class FakeFixtureDetailsIngestionService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def ingest_injuries_for_fixture(self, _fixture_id: int) -> _FakeRefreshSummary:
            if "injuries" in failures:
                raise PredictionError("injuries refresh failed")
            return _FakeRefreshSummary("injuries")

        def ingest_api_prediction(self, _fixture_id: int) -> _FakeRefreshSummary:
            if "api_prediction" in failures:
                raise PredictionError("api prediction refresh failed")
            return _FakeRefreshSummary("api_prediction")

        def ingest_fixture_lineups(self, _fixture_id: int) -> _FakeRefreshSummary:
            if "lineups" in failures:
                raise PredictionError("lineups refresh failed")
            return _FakeRefreshSummary("lineups")

    class FakeOddsIngestionService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def ingest_odds_for_fixture(self, _fixture_id: int) -> _FakeRefreshSummary:
            if "odds" in failures:
                raise PredictionError("odds refresh failed")
            return _FakeRefreshSummary("odds")

    monkeypatch.setattr(
        worldcup_service_module,
        "FixtureIngestionService",
        FakeFixtureIngestionService,
    )
    monkeypatch.setattr(
        worldcup_service_module,
        "FixtureDetailsIngestionService",
        FakeFixtureDetailsIngestionService,
    )
    monkeypatch.setattr(
        worldcup_service_module,
        "OddsIngestionService",
        FakeOddsIngestionService,
    )
