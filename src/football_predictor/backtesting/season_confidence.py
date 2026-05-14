"""Season holdout confidence backtest reports."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from football_predictor.backtesting.confidence_calibration import (
    ConfidenceThresholdConfig,
    apply_publication_policy_records,
    build_confidence_threshold_artifact,
    evaluate_thresholds,
)
from football_predictor.backtesting.production_like import FINISHED_STATUSES
from football_predictor.backtesting.v3_dataset_builder import (
    DATE_COL,
    build_v3_base_dataset,
    chronological_splits,
)
from football_predictor.backtesting.v3_evaluator import (
    V2_MODEL_NAME,
    V3_PRIMARY_MODEL_NAME,
    V3BacktestConfig,
    _build_prediction_sets,
    _calibration_baseline_name,
    _confidence_records,
    _metrics_for_prediction_sets,
    _published_only_report,
)
from football_predictor.db import models
from football_predictor.modeling.v3.training import V3TrainingConfig, train_v3_from_dataset
from football_predictor.ou_model.backtesting.ou_dataset_builder import build_ou_training_dataset
from football_predictor.ou_model.backtesting.ou_evaluator import _ou_confidence_records
from football_predictor.ou_model.modeling.ou_train import (
    OUTrainingConfig,
    ou_temporal_split,
    select_ou_feature_names,
    train_ou_model_from_frames,
)
from football_predictor.reference.lookups import PlayersReference
from football_predictor.utils.time import utc_now

JsonDict = dict[str, Any]
ReportFormat = Literal["json", "markdown", "both"]


@dataclass(frozen=True)
class SeasonConfidenceBacktestConfig:
    """Configuration for a full finished-season High/Very High holdout report."""

    league_ids: list[int]
    test_season: int
    train_seasons: list[int]
    output_dir: Path = Path("reports/season_confidence")
    v2_model_dir: Path | None = None
    ou_bet_id: int = 5
    prediction_offset_minutes: int = 30
    min_data_quality_score: float = 60.0
    report_format: ReportFormat = "both"
    ou_fit_boosting: bool = True
    ou_min_rows_for_meta: int = 80
    reuse_existing_datasets: bool = False


@dataclass(frozen=True)
class SeasonConfidenceBacktestResult:
    """Result payload and generated files for the season confidence report."""

    payload: JsonDict
    report_paths: dict[str, Path]
    dataset_paths: dict[str, Path]
    generated_at: str = field(default_factory=lambda: utc_now().isoformat())


def run_season_confidence_backtest(
    session: Session,
    *,
    config: SeasonConfidenceBacktestConfig,
    players_reference: PlayersReference | None = None,
) -> SeasonConfidenceBacktestResult:
    """Train on prior seasons and evaluate High/Very High rows on the test season."""
    _validate_config(config)
    output_dir = config.output_dir
    datasets_dir = output_dir / "datasets"
    artifacts_dir = output_dir / "artifacts"
    output_dir.mkdir(parents=True, exist_ok=True)
    datasets_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    dataset_paths = {
        "v3_train": datasets_dir / "v3_train_m30.parquet",
        "v3_test": datasets_dir / "v3_test_m30.parquet",
        "ou_train": datasets_dir / "ou25_train_m30.parquet",
        "ou_test": datasets_dir / "ou25_test_m30.parquet",
    }

    existing_v3_train = _load_existing_frame(dataset_paths["v3_train"], config=config)
    v3_train = (
        existing_v3_train
        if existing_v3_train is not None
        else build_v3_base_dataset(
            session,
            config.league_ids,
            config.train_seasons,
            save_path=dataset_paths["v3_train"],
            players_reference=players_reference,
            prediction_offset_minutes=config.prediction_offset_minutes,
        )
    )
    existing_v3_test = _load_existing_frame(dataset_paths["v3_test"], config=config)
    v3_test = (
        existing_v3_test
        if existing_v3_test is not None
        else build_v3_base_dataset(
            session,
            config.league_ids,
            [config.test_season],
            save_path=dataset_paths["v3_test"],
            players_reference=players_reference,
            prediction_offset_minutes=config.prediction_offset_minutes,
        )
    )
    existing_ou_train = _load_existing_frame(dataset_paths["ou_train"], config=config)
    ou_train = (
        existing_ou_train
        if existing_ou_train is not None
        else build_ou_training_dataset(
            session,
            config.ou_bet_id,
            league_ids=config.league_ids,
            seasons=config.train_seasons,
            prediction_offset_minutes=config.prediction_offset_minutes,
            save_path=dataset_paths["ou_train"],
            players_reference=players_reference,
        )
    )
    existing_ou_test = _load_existing_frame(dataset_paths["ou_test"], config=config)
    ou_test = (
        existing_ou_test
        if existing_ou_test is not None
        else build_ou_training_dataset(
            session,
            config.ou_bet_id,
            league_ids=config.league_ids,
            seasons=[config.test_season],
            prediction_offset_minutes=config.prediction_offset_minutes,
            save_path=dataset_paths["ou_test"],
            players_reference=players_reference,
        )
    )

    fixture_counts = finished_fixture_counts_by_league(session, config)
    v3_report = _run_v3_holdout(
        train_frame=v3_train,
        test_frame=v3_test,
        train_dataset_path=dataset_paths["v3_train"],
        output_dir=artifacts_dir / "v3",
        config=config,
    )
    ou_report = _run_ou_holdout(
        train_frame=ou_train,
        test_frame=ou_test,
        output_dir=artifacts_dir / "ou25",
        config=config,
    )

    payload: JsonDict = {
        "generated_at": utc_now().isoformat(),
        "mode": "season_holdout_m30_high_very_high",
        "config": _config_payload(config),
        "season_scope": {
            "train_seasons": config.train_seasons,
            "test_season": config.test_season,
            "fixture_counts_by_league": fixture_counts,
            "note": (
                "Only fixtures with final score and status FT/AET/PEN are evaluated; "
                "remaining scheduled matches are excluded."
            ),
        },
        "datasets": {
            "v3_train": {"path": str(dataset_paths["v3_train"]), "row_count": len(v3_train)},
            "v3_test": {"path": str(dataset_paths["v3_test"]), "row_count": len(v3_test)},
            "ou_train": {"path": str(dataset_paths["ou_train"]), "row_count": len(ou_train)},
            "ou_test": {"path": str(dataset_paths["ou_test"]), "row_count": len(ou_test)},
        },
        "reports": {
            "v3_1x2": v3_report,
            "ou25": ou_report,
        },
    }
    report_paths = _write_reports(payload, output_dir, config.report_format)
    return SeasonConfidenceBacktestResult(
        payload=payload,
        report_paths=report_paths,
        dataset_paths=dataset_paths,
    )


def finished_fixture_counts_by_league(
    session: Session,
    config: SeasonConfidenceBacktestConfig,
) -> JsonDict:
    """Return total, finished, and excluded remaining fixture counts by league."""
    output: JsonDict = {}
    for league_id in config.league_ids:
        base = select(func.count()).select_from(models.Fixture).where(
            models.Fixture.league_id == league_id,
            models.Fixture.season == config.test_season,
        )
        total = int(session.scalar(base) or 0)
        finished = int(
            session.scalar(
                base.where(
                    models.Fixture.status_short.in_(FINISHED_STATUSES),
                    models.Fixture.date.is_not(None),
                    models.Fixture.home_goals.is_not(None),
                    models.Fixture.away_goals.is_not(None),
                )
            )
            or 0
        )
        league = session.scalar(
            select(models.League)
            .where(
                models.League.league_id == league_id,
                models.League.season == config.test_season,
            )
            .limit(1)
        )
        output[str(league_id)] = {
            "league_id": league_id,
            "league_name": league.name if league is not None else str(league_id),
            "season": config.test_season,
            "total_fixtures": total,
            "finished_scored": finished,
            "excluded_unfinished": max(total - finished, 0),
        }
    return output


def _load_existing_frame(
    path: Path,
    *,
    config: SeasonConfidenceBacktestConfig,
) -> pd.DataFrame | None:
    if not config.reuse_existing_datasets or not path.exists():
        return None
    if path.suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _run_v3_holdout(
    *,
    train_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    train_dataset_path: Path,
    output_dir: Path,
    config: SeasonConfidenceBacktestConfig,
) -> JsonDict:
    if train_frame.empty:
        return {"status": "skipped", "reason": "empty_v3_train_dataset"}
    if test_frame.empty:
        return {"status": "skipped", "reason": "empty_v3_test_dataset"}

    output_dir.mkdir(parents=True, exist_ok=True)
    v3_config = V3BacktestConfig(
        report_format=config.report_format,
        retrain_v3=True,
        min_data_quality_score=config.min_data_quality_score,
    )
    train_result = train_v3_from_dataset(
        train_dataset_path,
        output_dir / "model",
        v2_model_dir=config.v2_model_dir,
        config=V3TrainingConfig(
            train_ratio=v3_config.train_ratio,
            valid_ratio=v3_config.valid_ratio,
            model_version=v3_config.model_version,
            draw_calibration=v3_config.draw_calibration,
            no_draw_winner_calibration=v3_config.no_draw_winner_calibration,
        ),
    )
    model = train_result.model
    v2_model = model.v2_model
    threshold_frame = _v3_threshold_frame(train_frame, v3_config)
    validation_predictions = _build_prediction_sets(
        threshold_frame,
        model=model,
        v2_model=v2_model,
    )
    test_predictions = _build_prediction_sets(test_frame, model=model, v2_model=v2_model)
    baseline_name = _calibration_baseline_name(validation_predictions)
    test_records = _confidence_records(
        test_frame,
        test_predictions.get(V3_PRIMARY_MODEL_NAME, []),
        test_predictions.get(baseline_name, []),
    )
    confidence_thresholds = build_confidence_threshold_artifact(
        validation_records=_confidence_records(
            threshold_frame,
            validation_predictions.get(V3_PRIMARY_MODEL_NAME, []),
            validation_predictions.get(baseline_name, []),
        ),
        test_records=test_records,
        config=ConfidenceThresholdConfig(
            model_family="v3_1x2",
            min_data_quality_score=config.min_data_quality_score,
        ),
        periods={
            "threshold_validation": _period_payload(threshold_frame),
            "test": _period_payload(test_frame),
        },
    )
    published_report = _published_only_report(
        test_frame,
        test_predictions,
        confidence_thresholds,
        config=v3_config,
    )
    return {
        "status": "completed",
        "model_family": "v3_1x2",
        "train_rows": len(train_frame),
        "threshold_validation_rows": len(threshold_frame),
        "test_rows": len(test_frame),
        "training_artifact_dir": str(output_dir / "model"),
        "baseline_model": baseline_name,
        "metrics": _metrics_for_prediction_sets(
            test_frame,
            test_predictions,
            config=v3_config,
        ),
        "confidence_thresholds": confidence_thresholds,
        "published_only_report": published_report,
        "summary": summarize_v3_published_report(published_report),
        "confidence_only_high_very_high": summarize_confidence_only_records(
            apply_publication_policy_records(
                test_records,
                confidence_thresholds.get("thresholds", {}).get("global", {}),
                config=ConfidenceThresholdConfig(
                    model_family="v3_1x2",
                    min_data_quality_score=config.min_data_quality_score,
                ),
            )
        ),
    }


def _run_ou_holdout(
    *,
    train_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    output_dir: Path,
    config: SeasonConfidenceBacktestConfig,
) -> JsonDict:
    if train_frame.empty:
        return {"status": "skipped", "reason": "empty_ou_train_dataset"}
    if test_frame.empty:
        return {"status": "skipped", "reason": "empty_ou_test_dataset"}

    output_dir.mkdir(parents=True, exist_ok=True)
    train_df, valid_df, cal_df, _unused_prior_test = ou_temporal_split(train_frame)
    threshold_frame = cal_df if len(cal_df) else valid_df
    feature_names = select_ou_feature_names(train_df)
    training_config = OUTrainingConfig(
        min_rows_for_meta=config.ou_min_rows_for_meta,
        fit_lgbm=config.ou_fit_boosting,
        fit_xgb=config.ou_fit_boosting,
        fit_catboost=config.ou_fit_boosting,
    )
    model, metrics = train_ou_model_from_frames(
        train_frame=train_df,
        valid_frame=valid_df,
        cal_frame=cal_df,
        test_frame=test_frame,
        feature_names=feature_names,
        config=training_config,
    )
    model.save(output_dir / "model.joblib")
    (output_dir / "feature_names.json").write_text(
        json.dumps(feature_names, indent=2),
        encoding="utf-8",
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(_json_ready(metrics), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    validation_records = _ou_confidence_records(model, threshold_frame, feature_names)
    test_records = _ou_confidence_records(model, test_frame, feature_names)
    threshold_config = ConfidenceThresholdConfig(
        model_family="ou25",
        min_data_quality_score=config.min_data_quality_score,
    )
    confidence_thresholds = build_confidence_threshold_artifact(
        validation_records=validation_records,
        test_records=test_records,
        config=threshold_config,
        periods={
            "threshold_validation": _period_payload(threshold_frame),
            "test": _period_payload(test_frame),
        },
    )
    thresholds = confidence_thresholds.get("thresholds", {}).get("global", {})
    threshold_report = evaluate_thresholds(
        test_records,
        thresholds,
        config=threshold_config,
    )
    return {
        "status": "completed",
        "model_family": "ou25",
        "train_rows": len(train_frame),
        "threshold_validation_rows": len(threshold_frame),
        "test_rows": len(test_frame),
        "training_artifact_dir": str(output_dir),
        "metrics": metrics,
        "confidence_thresholds": confidence_thresholds,
        "published_only_report": {
            "model_family": "ou25",
            "policy": {
                "threshold_version": confidence_thresholds.get("threshold_version"),
                "min_data_quality_score": confidence_thresholds.get(
                    "min_data_quality_score"
                ),
                "thresholds": thresholds,
            },
            "scopes": {
                "internal_all": threshold_report.get("internal_all", {}),
                "published_only": threshold_report.get("published_only", {}),
                "baseline_on_published": threshold_report.get(
                    "baseline_on_published", {}
                ),
                "eligible_high": threshold_report.get("eligible_high", {}),
                "eligible_very_high": threshold_report.get("eligible_very_high", {}),
            },
            "groups": {
                "league": threshold_report.get("by_league", {}),
                "season": threshold_report.get("by_season", {}),
                "data_quality": threshold_report.get("by_data_quality_bin", {}),
                "confidence_label": threshold_report.get("labels", {}),
            },
        },
        "summary": summarize_ou_published_report(threshold_report),
        "confidence_only_high_very_high": summarize_confidence_only_records(
            apply_publication_policy_records(
                test_records,
                thresholds,
                config=threshold_config,
            )
        ),
    }


def summarize_v3_published_report(report: JsonDict) -> JsonDict:
    """Return compact whole-season and per-league V3 published-only metrics."""
    scopes = report.get("scopes", {})
    published = (
        scopes.get("published_only", {})
        .get(V3_PRIMARY_MODEL_NAME, {})
    )
    baselines = scopes.get("published_only", {})
    by_league: JsonDict = {}
    for league_id, payload in report.get("groups", {}).get("league", {}).items():
        metrics_by_model = payload.get("metrics_by_model", {})
        primary = metrics_by_model.get(V3_PRIMARY_MODEL_NAME, {})
        odds = metrics_by_model.get("odds_only", {})
        v2 = metrics_by_model.get(V2_MODEL_NAME, {})
        by_league[str(league_id)] = {
            "published_rows": primary.get("row_count", payload.get("row_count", 0)),
            "success_rate": primary.get("accuracy"),
            "log_loss": primary.get("log_loss"),
            "brier_score": primary.get("brier_score"),
            "odds_success_rate": odds.get("accuracy"),
            "v2_success_rate": v2.get("accuracy"),
        }
    return {
        "published_rows": published.get("row_count", 0),
        "success_rate": published.get("accuracy"),
        "log_loss": published.get("log_loss"),
        "brier_score": published.get("brier_score"),
        "odds_success_rate": baselines.get("odds_only", {}).get("accuracy"),
        "v2_success_rate": baselines.get(V2_MODEL_NAME, {}).get("accuracy"),
        "by_league": by_league,
    }


def summarize_ou_published_report(report: JsonDict) -> JsonDict:
    """Return compact whole-season and per-league O/U published-only metrics."""
    published = report.get("published_only", {})
    market = report.get("baseline_on_published", {})
    by_league: JsonDict = {}
    for league_id, payload in report.get("by_league", {}).items():
        primary = payload.get("published_only", {})
        market_payload = payload.get("baseline_on_published", {})
        by_league[str(league_id)] = {
            "published_rows": primary.get("row_count", 0),
            "success_rate": primary.get("accuracy"),
            "win_rate": primary.get("win_rate"),
            "log_loss": primary.get("log_loss"),
            "brier_score": primary.get("brier_score"),
            "roi": primary.get("roi"),
            "market_success_rate": market_payload.get("accuracy"),
        }
    return {
        "published_rows": published.get("row_count", 0),
        "success_rate": published.get("accuracy"),
        "win_rate": published.get("win_rate"),
        "log_loss": published.get("log_loss"),
        "brier_score": published.get("brier_score"),
        "roi": published.get("roi"),
        "market_success_rate": market.get("accuracy"),
        "by_league": by_league,
    }


def summarize_confidence_only_records(records: list[JsonDict]) -> JsonDict:
    """Summarize records labeled High/Very High regardless of publication blockers."""
    selected = [
        record
        for record in records
        if record.get("calibrated_label") in {"High", "Very High"}
    ]
    return {
        **_record_metrics(selected),
        "by_league": {
            league_id: _record_metrics(rows)
            for league_id, rows in _group_records(selected, "league_id").items()
        },
        "by_label": {
            label: _record_metrics(rows)
            for label, rows in _group_records(selected, "calibrated_label").items()
        },
        "publication_blocked_rows": sum(
            1 for record in selected if not record.get("publication_allowed")
        ),
        "publication_allowed_rows": sum(
            1 for record in selected if record.get("publication_allowed")
        ),
    }


def _record_metrics(records: list[JsonDict]) -> JsonDict:
    if not records:
        return {
            "row_count": 0,
            "success_rate": None,
            "avg_confidence_score": None,
            "avg_data_quality_score": None,
        }
    return {
        "row_count": len(records),
        "success_rate": _mean(1.0 if record.get("correct") else 0.0 for record in records),
        "avg_confidence_score": _mean(
            float(record["confidence_score"])
            for record in records
            if record.get("confidence_score") is not None
        ),
        "avg_data_quality_score": _mean(
            float(record["data_quality_score"])
            for record in records
            if record.get("data_quality_score") is not None
        ),
    }


def _group_records(records: list[JsonDict], key: str) -> dict[str, list[JsonDict]]:
    groups: dict[str, list[JsonDict]] = {}
    for record in records:
        value = record.get(key)
        if value is None:
            continue
        groups.setdefault(str(value), []).append(record)
    return dict(sorted(groups.items()))


def _mean(values: Any) -> float | None:
    items = [float(value) for value in values]
    if not items:
        return None
    return sum(items) / len(items)


def _v3_threshold_frame(
    train_frame: pd.DataFrame,
    config: V3BacktestConfig,
) -> pd.DataFrame:
    splits = chronological_splits(
        train_frame,
        train_ratio=config.train_ratio,
        valid_ratio=config.valid_ratio,
    )
    if not splits.test.empty:
        return splits.test
    if not splits.valid.empty:
        return splits.valid
    return splits.train


def _period_payload(frame: pd.DataFrame) -> JsonDict:
    if frame.empty or DATE_COL not in frame.columns:
        return {"row_count": int(len(frame)), "start": None, "end": None}
    dates = pd.to_datetime(frame[DATE_COL], utc=True)
    return {
        "row_count": int(len(frame)),
        "start": dates.min().isoformat(),
        "end": dates.max().isoformat(),
    }


def _validate_config(config: SeasonConfidenceBacktestConfig) -> None:
    if not config.league_ids:
        raise ValueError("At least one league_id is required")
    if not config.train_seasons:
        raise ValueError("At least one train season is required")
    if config.test_season in config.train_seasons:
        raise ValueError("test_season must not be included in train_seasons")
    if any(season >= config.test_season for season in config.train_seasons):
        raise ValueError("train_seasons must be strictly before test_season")
    if config.prediction_offset_minutes <= 0:
        raise ValueError("prediction_offset_minutes must be positive")
    if not 0 <= config.min_data_quality_score <= 100:
        raise ValueError("min_data_quality_score must be between 0 and 100")
    if config.report_format not in {"json", "markdown", "both"}:
        raise ValueError("report_format must be json, markdown, or both")


def _write_reports(
    payload: JsonDict,
    output_dir: Path,
    report_format: ReportFormat,
) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    if report_format in {"json", "both"}:
        paths["json"] = output_dir / "season_confidence_report.json"
        paths["json"].write_text(
            json.dumps(_json_ready(payload), indent=2, sort_keys=True),
            encoding="utf-8",
        )
    if report_format in {"markdown", "both"}:
        paths["markdown"] = output_dir / "season_confidence_report.md"
        paths["markdown"].write_text(_markdown_report(payload), encoding="utf-8")
    return paths


def _markdown_report(payload: JsonDict) -> str:
    scope = payload.get("season_scope", {})
    config = payload.get("config", {})
    v3_report = payload.get("reports", {}).get("v3_1x2", {})
    ou_report = payload.get("reports", {}).get("ou25", {})
    v3_summary = v3_report.get("summary", {})
    ou_summary = ou_report.get("summary", {})
    v3_confidence = v3_report.get("confidence_only_high_very_high", {})
    ou_confidence = ou_report.get("confidence_only_high_very_high", {})
    lines = [
        "# Backtest Saison M-30 High / Very High",
        "",
        f"- Saison test: `{config.get('test_season')}`",
        f"- Saisons d'entrainement: `{config.get('train_seasons')}`",
        f"- Prediction time: `kickoff - {config.get('prediction_offset_minutes')} minutes`",
        f"- Data quality minimale: `{config.get('min_data_quality_score')}`",
        "- Discord: `non utilise`",
        "",
        "## Matchs Pris En Compte",
        "",
        "| League | Termines comptes | Restants exclus | Total saison |",
        "| --- | ---: | ---: | ---: |",
    ]
    counts = scope.get("fixture_counts_by_league", {})
    for league_id, payload_count in sorted(counts.items(), key=lambda item: int(item[0])):
        lines.append(
            f"| {payload_count.get('league_name', league_id)} (`{league_id}`) | "
            f"{payload_count.get('finished_scored', 0)} | "
            f"{payload_count.get('excluded_unfinished', 0)} | "
            f"{payload_count.get('total_fixtures', 0)} |"
        )
    lines.extend(
        [
            "",
            "## V3 1X2 Published-Only",
            "",
            _summary_line(v3_summary, "V3"),
            "",
            "| League | Pronos High/Very High | Reussite | Odds | V2 |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    lines.extend(
        _league_rows(
            v3_summary,
            counts,
            baseline_keys=("odds_success_rate", "v2_success_rate"),
        )
    )
    lines.extend(
        [
            "",
            "## V3 1X2 Confidence-Only High / Very High",
            "",
            _confidence_summary_line(v3_confidence, "V3"),
            "",
            "| League | Pronos High/Very High | Reussite | Data quality moy. |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    lines.extend(_confidence_league_rows(v3_confidence, counts))
    lines.extend(
        [
            "",
            "## O/U 2.5 Published-Only",
            "",
            _summary_line(ou_summary, "O/U"),
            "",
            "| League | Pronos High/Very High | Reussite | Marche | ROI |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    lines.extend(_league_rows(ou_summary, counts, baseline_keys=("market_success_rate", "roi")))
    lines.extend(
        [
            "",
            "## O/U 2.5 Confidence-Only High / Very High",
            "",
            _confidence_summary_line(ou_confidence, "O/U"),
            "",
            "| League | Pronos High/Very High | Reussite | Data quality moy. |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    lines.extend(_confidence_league_rows(ou_confidence, counts))
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Les lignes `published-only` appliquent la meme policy que la production: "
            "High/Very High, data quality suffisante et aucun blocker.",
            "- Les matchs non termines ou sans score final sont exclus du denominateur.",
            "- Les datasets sont construits point-in-time a M-30; la cible finale est "
            "ajoutee seulement pour l'evaluation.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _summary_line(summary: JsonDict, label: str) -> str:
    rows = int(summary.get("published_rows") or 0)
    success = _fmt_pct(summary.get("success_rate"))
    return f"- {label}: `{rows}` pronos High/Very High, reussite `{success}`."


def _confidence_summary_line(summary: JsonDict, label: str) -> str:
    rows = int(summary.get("row_count") or 0)
    blocked = int(summary.get("publication_blocked_rows") or 0)
    success = _fmt_pct(summary.get("success_rate"))
    quality = _fmt_number(summary.get("avg_data_quality_score"))
    return (
        f"- {label}: `{rows}` pronos High/Very High par label de confiance, "
        f"reussite `{success}`, data quality moyenne `{quality}`, "
        f"bloques publication `{blocked}`."
    )


def _league_rows(
    summary: JsonDict,
    fixture_counts: JsonDict,
    *,
    baseline_keys: tuple[str, str],
) -> list[str]:
    by_league = summary.get("by_league", {})
    lines: list[str] = []
    for league_id, count_payload in sorted(
        fixture_counts.items(),
        key=lambda item: int(item[0]),
    ):
        payload = by_league.get(str(league_id), {})
        lines.append(
            f"| {count_payload.get('league_name', league_id)} (`{league_id}`) | "
            f"{int(payload.get('published_rows') or 0)} | "
            f"{_fmt_pct(payload.get('success_rate'))} | "
            f"{_fmt_pct(payload.get(baseline_keys[0]))} | "
            f"{_fmt_number(payload.get(baseline_keys[1]))} |"
        )
    return lines


def _confidence_league_rows(summary: JsonDict, fixture_counts: JsonDict) -> list[str]:
    by_league = summary.get("by_league", {})
    lines: list[str] = []
    for league_id, count_payload in sorted(
        fixture_counts.items(),
        key=lambda item: int(item[0]),
    ):
        payload = by_league.get(str(league_id), {})
        lines.append(
            f"| {count_payload.get('league_name', league_id)} (`{league_id}`) | "
            f"{int(payload.get('row_count') or 0)} | "
            f"{_fmt_pct(payload.get('success_rate'))} | "
            f"{_fmt_number(payload.get('avg_data_quality_score'))} |"
        )
    return lines


def _fmt_pct(value: Any) -> str:
    try:
        if value is None:
            return ""
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return ""


def _fmt_number(value: Any) -> str:
    try:
        if value is None:
            return ""
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return ""


def _config_payload(config: SeasonConfidenceBacktestConfig) -> JsonDict:
    payload = asdict(config)
    for key in ("output_dir", "v2_model_dir"):
        if payload.get(key) is not None:
            payload[key] = str(payload[key])
    return payload


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, float) and (
        value != value or value in (float("inf"), float("-inf"))
    ):
        return None
    return value
