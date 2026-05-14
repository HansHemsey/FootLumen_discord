"""Offline production-like M-30 backtest orchestration."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from football_predictor.backtesting.v3_dataset_builder import build_v3_base_dataset
from football_predictor.backtesting.v3_evaluator import V3BacktestConfig, run_v3_backtest
from football_predictor.db import models
from football_predictor.ou_model.backtesting.ou_dataset_builder import (
    build_ou_training_dataset,
)
from football_predictor.ou_model.backtesting.ou_evaluator import (
    OUBacktestConfig,
    run_ou_backtest,
)
from football_predictor.reference.lookups import PlayersReference
from football_predictor.utils.time import ensure_aware_utc, utc_now

JsonDict = dict[str, Any]
ReportFormat = Literal["json", "markdown", "both"]
FINISHED_STATUSES = {"FT", "AET", "PEN"}


@dataclass(frozen=True)
class ProductionLikeBacktestConfig:
    """Configuration for an offline backtest that mirrors late production runs."""

    league_ids: list[int]
    seasons: list[int]
    output_dir: Path = Path("reports/production_like")
    v3_model_dir: Path = Path("data/models/v3")
    v2_model_dir: Path | None = None
    ou_model_dir: Path | None = None
    ou_bet_id: int = 5
    prediction_offset_minutes: int = 30
    min_data_quality_score: float = 60.0
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int | None = None
    report_format: ReportFormat = "both"
    retrain_v3: bool = False
    ou_n_splits: int = 5
    ou_min_train_rows: int = 300


@dataclass(frozen=True)
class ProductionLikeBacktestResult:
    """Combined report metadata for production-like backtests."""

    payload: JsonDict
    report_paths: dict[str, Path]
    dataset_paths: dict[str, Path]
    v3_rows: int
    ou_rows: int
    generated_at: str = field(default_factory=lambda: utc_now().isoformat())


def production_like_prediction_time(
    kickoff: datetime,
    *,
    prediction_offset_minutes: int = 30,
) -> datetime:
    """Return the historical cutoff for a production late prediction."""
    return ensure_aware_utc(kickoff) - timedelta(minutes=prediction_offset_minutes)


def run_production_like_backtest(
    session: Session,
    *,
    config: ProductionLikeBacktestConfig,
    players_reference: PlayersReference | None = None,
) -> ProductionLikeBacktestResult:
    """Build M-30 datasets, run existing evaluators, and write a combined report."""
    _validate_config(config)
    output_dir = config.output_dir
    datasets_dir = output_dir / "datasets"
    v3_output_dir = output_dir / "v3"
    ou_output_dir = output_dir / "ou"
    output_dir.mkdir(parents=True, exist_ok=True)
    datasets_dir.mkdir(parents=True, exist_ok=True)

    v3_dataset_path = datasets_dir / "v3_m30.parquet"
    ou_dataset_path = datasets_dir / "ou25_m30.parquet"

    v3_frame = build_v3_base_dataset(
        session,
        config.league_ids,
        config.seasons,
        save_path=v3_dataset_path,
        players_reference=players_reference,
        limit=config.limit,
        prediction_offset_minutes=config.prediction_offset_minutes,
        date_from=config.date_from,
        date_to=config.date_to,
    )
    ou_frame = build_ou_training_dataset(
        session,
        config.ou_bet_id,
        league_ids=config.league_ids,
        seasons=config.seasons,
        prediction_offset_minutes=config.prediction_offset_minutes,
        save_path=ou_dataset_path,
        players_reference=players_reference,
        limit=config.limit,
        date_from=config.date_from,
        date_to=config.date_to,
    )

    leakage_checks = _build_leakage_checks(
        session,
        v3_frame=v3_frame,
        ou_frame=ou_frame,
        config=config,
    )
    v3_result = None
    ou_result = None
    v3_report: JsonDict = {"status": "skipped", "reason": "empty_v3_dataset"}
    ou_report: JsonDict = {"status": "skipped", "reason": "empty_ou_dataset"}

    if not v3_frame.empty:
        v3_result = run_v3_backtest(
            v3_dataset_path,
            config.v3_model_dir,
            v2_model_dir=config.v2_model_dir,
            output_dir=v3_output_dir,
            config=V3BacktestConfig(
                report_format=config.report_format,
                retrain_v3=config.retrain_v3,
                min_data_quality_score=config.min_data_quality_score,
            ),
        )
        v3_report = _v3_report_payload(v3_result)

    if not ou_frame.empty:
        ou_result = run_ou_backtest(
            ou_dataset_path,
            output_dir=ou_output_dir,
            config=OUBacktestConfig(
                n_splits=config.ou_n_splits,
                min_train_rows=config.ou_min_train_rows,
            ),
        )
        ou_report = _ou_report_payload(ou_result, ou_output_dir)

    payload: JsonDict = {
        "generated_at": utc_now().isoformat(),
        "mode": "production_like_m30",
        "config": _config_payload(config),
        "datasets": {
            "v3": {"path": str(v3_dataset_path), "row_count": int(len(v3_frame))},
            "ou25": {"path": str(ou_dataset_path), "row_count": int(len(ou_frame))},
        },
        "leakage_checks": leakage_checks,
        "reports": {
            "v3_1x2": v3_report,
            "ou25": ou_report,
        },
    }
    report_paths = _write_combined_reports(payload, output_dir, config.report_format)
    dataset_paths = {"v3": v3_dataset_path, "ou25": ou_dataset_path}
    return ProductionLikeBacktestResult(
        payload=payload,
        report_paths=report_paths,
        dataset_paths=dataset_paths,
        v3_rows=int(len(v3_frame)),
        ou_rows=int(len(ou_frame)),
    )


def _validate_config(config: ProductionLikeBacktestConfig) -> None:
    if not config.league_ids:
        raise ValueError("Production-like backtest requires at least one league_id")
    if not config.seasons:
        raise ValueError("Production-like backtest requires at least one season")
    if config.prediction_offset_minutes <= 0:
        raise ValueError("prediction_offset_minutes must be positive")
    if not 0 <= config.min_data_quality_score <= 100:
        raise ValueError("min_data_quality_score must be between 0 and 100")
    if config.report_format not in {"json", "markdown", "both"}:
        raise ValueError("report_format must be json, markdown, or both")


def _build_leakage_checks(
    session: Session,
    *,
    v3_frame: pd.DataFrame,
    ou_frame: pd.DataFrame,
    config: ProductionLikeBacktestConfig,
) -> JsonDict:
    eligible_count = _eligible_finished_fixture_count(session, config)
    return {
        "prediction_offset_minutes": config.prediction_offset_minutes,
        "expected_prediction_time_rule": "fixture_date - 30 minutes",
        "eligible_finished_fixtures": eligible_count,
        "excluded_fixtures": {
            "v3": max(eligible_count - len(v3_frame), 0),
            "ou25": max(eligible_count - len(ou_frame), 0),
        },
        "m30_cutoff": {
            "v3": _m30_cutoff_check(v3_frame, config.prediction_offset_minutes),
            "ou25": _m30_cutoff_check(ou_frame, config.prediction_offset_minutes),
        },
        "future_source_rows_present": _future_source_counts(
            session,
            _combined_fixture_frame(v3_frame, ou_frame),
        ),
        "target_leakage_fields": {
            "v3_features": _target_columns_present(v3_frame),
            "ou_features": _target_columns_present(ou_frame),
            "note": (
                "Target columns may exist in datasets for evaluation, "
                "but feature snapshots strip them."
            ),
        },
    }


def _eligible_finished_fixture_count(
    session: Session,
    config: ProductionLikeBacktestConfig,
) -> int:
    stmt = select(func.count()).select_from(models.Fixture).where(
        models.Fixture.league_id.in_(config.league_ids),
        models.Fixture.season.in_(config.seasons),
        models.Fixture.status_short.in_(FINISHED_STATUSES),
        models.Fixture.date.is_not(None),
        models.Fixture.home_goals.is_not(None),
        models.Fixture.away_goals.is_not(None),
    )
    if config.date_from is not None:
        stmt = stmt.where(models.Fixture.date >= ensure_aware_utc(config.date_from))
    if config.date_to is not None:
        stmt = stmt.where(models.Fixture.date <= ensure_aware_utc(config.date_to))
    count = int(session.scalar(stmt) or 0)
    if config.limit is not None:
        return min(count, config.limit)
    return count


def _m30_cutoff_check(frame: pd.DataFrame, offset_minutes: int) -> JsonDict:
    if frame.empty:
        return {"row_count": 0, "all_rows_match": True, "violations": []}
    if "fixture_date" not in frame.columns or "prediction_time" not in frame.columns:
        return {
            "row_count": int(len(frame)),
            "all_rows_match": False,
            "violations": [{"reason": "missing_fixture_date_or_prediction_time"}],
        }
    violations: list[JsonDict] = []
    for index, row in frame.iterrows():
        fixture_date = _utc_timestamp(row["fixture_date"])
        prediction_time = _utc_timestamp(row["prediction_time"])
        expected = fixture_date - pd.Timedelta(minutes=offset_minutes)
        if prediction_time != expected:
            violations.append(
                {
                    "position": int(index),
                    "fixture_id": _json_value(row.get("fixture_id")),
                    "fixture_date": fixture_date.isoformat(),
                    "prediction_time": prediction_time.isoformat(),
                    "expected_prediction_time": expected.isoformat(),
                }
            )
    return {
        "row_count": int(len(frame)),
        "all_rows_match": not violations,
        "violations": violations[:20],
    }


def _future_source_counts(session: Session, frame: pd.DataFrame) -> JsonDict:
    counts = {
        "odds_snapshots": 0,
        "api_prediction_snapshots": 0,
        "fixture_lineups": 0,
        "injuries": 0,
        "standing_snapshots": 0,
    }
    if frame.empty or "fixture_id" not in frame.columns or "prediction_time" not in frame.columns:
        return counts
    seen: set[tuple[int, str]] = set()
    for row in frame.to_dict(orient="records"):
        fixture_id = _optional_int(row.get("fixture_id"))
        prediction_time_raw = row.get("prediction_time")
        if fixture_id is None or prediction_time_raw is None:
            continue
        key = (fixture_id, str(prediction_time_raw))
        if key in seen:
            continue
        seen.add(key)
        cutoff = ensure_aware_utc(_utc_timestamp(prediction_time_raw).to_pydatetime())
        teams = [
            team_id
            for team_id in (
                _optional_int(row.get("home_team_id")),
                _optional_int(row.get("away_team_id")),
            )
            if team_id is not None
        ]
        league_id = _optional_int(row.get("league_id"))
        season = _optional_int(row.get("season"))
        counts["odds_snapshots"] += _count_after(
            session,
            models.OddsSnapshot,
            models.OddsSnapshot.fixture_id == fixture_id,
            models.OddsSnapshot.fetched_at > cutoff,
        )
        counts["api_prediction_snapshots"] += _count_after(
            session,
            models.ApiPredictionSnapshot,
            models.ApiPredictionSnapshot.fixture_id == fixture_id,
            models.ApiPredictionSnapshot.fetched_at > cutoff,
        )
        counts["fixture_lineups"] += _count_after(
            session,
            models.FixtureLineup,
            models.FixtureLineup.fixture_id == fixture_id,
            models.FixtureLineup.fetched_at > cutoff,
        )
        if teams:
            counts["injuries"] += _count_after(
                session,
                models.Injury,
                or_(
                    models.Injury.fixture_id == fixture_id,
                    models.Injury.team_id.in_(teams),
                ),
                models.Injury.fetched_at > cutoff,
            )
        if teams and league_id is not None and season is not None:
            counts["standing_snapshots"] += _count_after(
                session,
                models.StandingSnapshot,
                models.StandingSnapshot.team_id.in_(teams),
                models.StandingSnapshot.league_id == league_id,
                models.StandingSnapshot.season == season,
                or_(
                    models.StandingSnapshot.snapshot_date > cutoff,
                    models.StandingSnapshot.fetched_at > cutoff,
                ),
            )
    return counts


def _combined_fixture_frame(v3_frame: pd.DataFrame, ou_frame: pd.DataFrame) -> pd.DataFrame:
    frames = [frame for frame in (v3_frame, ou_frame) if not frame.empty]
    if not frames:
        return pd.DataFrame()
    columns = sorted(set().union(*(set(frame.columns) for frame in frames)))
    normalized = [frame.reindex(columns=columns) for frame in frames]
    return pd.concat(normalized, ignore_index=True).drop_duplicates(
        subset=["fixture_id", "prediction_time"],
        keep="first",
    )


def _count_after(session: Session, model: Any, *conditions: Any) -> int:
    return int(session.scalar(select(func.count()).select_from(model).where(*conditions)) or 0)


def _target_columns_present(frame: pd.DataFrame) -> list[str]:
    return [
        column
        for column in ("target", "target_ou25", "home_goals", "away_goals", "total_goals")
        if column in frame.columns
    ]


def _v3_report_payload(result: Any) -> JsonDict:
    payload = getattr(result, "payload", {}) or {}
    return {
        "status": "completed",
        "periods": payload.get("periods", {}),
        "metrics": payload.get("metrics", {}),
        "comparisons": payload.get("published_only_report", {}).get("comparisons", {}),
        "published_only_report": payload.get("published_only_report", {}),
        "report_paths": {
            key: str(path) for key, path in getattr(result, "report_paths", {}).items()
        },
    }


def _ou_report_payload(result: Any, output_dir: Path) -> JsonDict:
    published_path = output_dir / "published_only_report.json"
    published_only = _read_json(published_path) if published_path.exists() else {}
    return {
        "status": "completed",
        "aggregate": getattr(result, "aggregate", {}),
        "confidence_thresholds": getattr(result, "confidence_thresholds", {}),
        "published_only_report": published_only,
        "report_paths": {
            "json": str(output_dir / "backtest_results.json"),
            "confidence_thresholds": str(output_dir / "confidence_thresholds.json"),
            "published_only_json": str(published_path),
            "published_only_markdown": str(output_dir / "published_only_report.md"),
        },
    }


def _write_combined_reports(
    payload: JsonDict,
    output_dir: Path,
    report_format: ReportFormat,
) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    if report_format in {"json", "both"}:
        paths["json"] = output_dir / "production_like_backtest_report.json"
        paths["json"].write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
    if report_format in {"markdown", "both"}:
        paths["markdown"] = output_dir / "production_like_backtest_report.md"
        paths["markdown"].write_text(_markdown_report(payload), encoding="utf-8")
    return paths


def _markdown_report(payload: JsonDict) -> str:
    datasets = payload.get("datasets", {})
    leakage = payload.get("leakage_checks", {})
    v3 = payload.get("reports", {}).get("v3_1x2", {})
    ou = payload.get("reports", {}).get("ou25", {})
    lines = [
        "# Backtest Production-Like M-30",
        "",
        f"- Generated at: `{payload.get('generated_at')}`",
        f"- Mode: `{payload.get('mode')}`",
        "",
        "## Datasets",
        "",
        "| Family | Rows | Path |",
        "| --- | ---: | --- |",
        f"| V3 1X2 | {datasets.get('v3', {}).get('row_count', 0)} | "
        f"`{datasets.get('v3', {}).get('path', '')}` |",
        f"| O/U 2.5 | {datasets.get('ou25', {}).get('row_count', 0)} | "
        f"`{datasets.get('ou25', {}).get('path', '')}` |",
        "",
        "## Leakage Checks",
        "",
        f"- Prediction offset minutes: `{leakage.get('prediction_offset_minutes')}`",
        f"- Eligible finished fixtures: `{leakage.get('eligible_finished_fixtures')}`",
        f"- V3 M-30 all rows match: "
        f"`{leakage.get('m30_cutoff', {}).get('v3', {}).get('all_rows_match')}`",
        f"- O/U M-30 all rows match: "
        f"`{leakage.get('m30_cutoff', {}).get('ou25', {}).get('all_rows_match')}`",
        f"- Future source rows present: `{leakage.get('future_source_rows_present', {})}`",
        "",
        "## V3 1X2",
        "",
        f"- Status: `{v3.get('status')}`",
        f"- Published rows: "
        f"`{_published_rows(v3.get('published_only_report', {}), 'v3_stacker_full')}`",
        "",
        "## O/U 2.5",
        "",
        f"- Status: `{ou.get('status')}`",
        f"- Published rows: "
        f"`{_published_rows_ou(ou.get('published_only_report', {}))}`",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _published_rows(report: JsonDict, model_name: str) -> int | None:
    value = (
        report.get("scopes", {})
        .get("published_only", {})
        .get(model_name, {})
        .get("row_count")
    )
    return int(value) if value is not None else None


def _published_rows_ou(report: JsonDict) -> int | None:
    aggregate = report.get("aggregate", {})
    value = aggregate.get("published_rows")
    return int(value) if value is not None else None


def _config_payload(config: ProductionLikeBacktestConfig) -> JsonDict:
    payload = asdict(config)
    for key in ("output_dir", "v3_model_dir", "v2_model_dir", "ou_model_dir"):
        if payload.get(key) is not None:
            payload[key] = str(payload[key])
    for key in ("date_from", "date_to"):
        if payload.get(key) is not None:
            payload[key] = ensure_aware_utc(payload[key]).isoformat()
    return payload


def _read_json(path: Path) -> JsonDict:
    return json.loads(path.read_text(encoding="utf-8"))


def _optional_int(value: Any) -> int | None:
    try:
        if pd.isna(value):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _utc_timestamp(value: Any) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value
