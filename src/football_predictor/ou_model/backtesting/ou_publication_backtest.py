"""Publication-focused backtest for the O/U 2.5 V2 decision layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import numpy as np
import pandas as pd

from football_predictor.ou_model.backtesting.ou_evaluator import (
    OUBacktestConfig,
    run_ou_backtest,
)
from football_predictor.ou_model.backtesting.ou_metrics import (
    binary_brier_score,
    binary_log_loss,
    calibration_bins_binary,
    expected_calibration_error,
    flat_stake_betting_metrics,
)
from football_predictor.ou_model.backtesting.ou_report_writer import (
    write_ou_v2_backtest_reports,
)
from football_predictor.ou_model.prediction.ou_decision import decide_ou_prediction

JsonDict = dict[str, Any]

EDGE_BUCKETS = (
    (0.00, 0.02, "0-2 pts"),
    (0.02, 0.04, "2-4 pts"),
    (0.04, 0.06, "4-6 pts"),
    (0.06, float("inf"), "6+ pts"),
)
EV_BUCKETS = (
    (0.00, 0.02, "0-2 %"),
    (0.02, 0.04, "2-4 %"),
    (0.04, 0.08, "4-8 %"),
    (0.08, float("inf"), "8+ %"),
)
CONFIDENCE_BUCKETS = (
    (0.00, 55.0, "<55"),
    (55.0, 65.0, "55-65"),
    (65.0, 80.0, "65-80"),
    (80.0, float("inf"), "80+"),
)


@dataclass(frozen=True)
class OUPublicationBacktestConfig:
    ou_backtest_config: OUBacktestConfig = field(default_factory=OUBacktestConfig)
    policy_min_edges: tuple[float, ...] = (0.02, 0.03, 0.04, 0.05)
    policy_min_evs: tuple[float, ...] = (0.02, 0.03, 0.05)
    policy_min_confidences: tuple[float, ...] = (55.0, 60.0, 65.0, 70.0)
    policy_min_data_qualities: tuple[float, ...] = (60.0, 70.0, 80.0)
    policy_min_bookmaker_counts: tuple[int, ...] = (1, 2, 3)
    min_recommended_bets: int = 20


@dataclass(frozen=True)
class OUPublicationBacktestResult:
    summary: JsonDict
    evaluated_predictions: pd.DataFrame
    roi_by_edge_bucket: pd.DataFrame
    roi_by_ev_bucket: pd.DataFrame
    roi_by_confidence_bucket: pd.DataFrame
    calibration_bins: pd.DataFrame
    publication_policy_grid: pd.DataFrame
    output_paths: dict[str, Path]


def run_ou_publication_backtest(
    dataset_path: Path,
    *,
    output_dir: Path = Path("reports/ou_v2"),
    config: OUPublicationBacktestConfig | None = None,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
    competition: str | int | None = None,
) -> OUPublicationBacktestResult:
    """Run a walk-forward O/U backtest focused on publishable value decisions."""
    resolved_config = config or OUPublicationBacktestConfig()
    filtered_dataset_path = _filtered_dataset_path(
        dataset_path,
        start_date=start_date,
        end_date=end_date,
        competition=competition,
    )
    backtest = run_ou_backtest(
        filtered_dataset_path,
        output_dir=None,
        config=resolved_config.ou_backtest_config,
    )
    raw_rows = [
        row
        for fold in backtest.folds
        for row in fold.prediction_rows
    ]
    evaluated = evaluate_ou_publication_rows(raw_rows)
    calibration = calibration_report_frame(evaluated)
    edge_bucket = roi_by_bucket_frame(evaluated, "edge_bucket", EDGE_BUCKETS)
    ev_bucket = roi_by_bucket_frame(evaluated, "ev_bucket", EV_BUCKETS)
    confidence_bucket = roi_by_bucket_frame(
        evaluated,
        "confidence_bucket",
        CONFIDENCE_BUCKETS,
    )
    policy_grid = publication_policy_grid_frame(evaluated, resolved_config)
    summary = build_publication_summary(
        evaluated,
        calibration,
        policy_grid,
        dataset_path=dataset_path,
        filtered_dataset_path=filtered_dataset_path,
        filters={
            "start_date": _date_filter_label(start_date),
            "end_date": _date_filter_label(end_date),
            "competition": str(competition) if competition is not None else None,
        },
        n_folds=len(backtest.folds),
        aggregate_backtest=backtest.aggregate,
        config=resolved_config,
    )
    output_paths = write_ou_v2_backtest_reports(
        output_dir=output_dir,
        summary=summary,
        roi_by_edge_bucket=edge_bucket,
        roi_by_ev_bucket=ev_bucket,
        roi_by_confidence_bucket=confidence_bucket,
        calibration_bins=calibration,
        publication_policy_grid=policy_grid,
    )
    return OUPublicationBacktestResult(
        summary=summary,
        evaluated_predictions=evaluated,
        roi_by_edge_bucket=edge_bucket,
        roi_by_ev_bucket=ev_bucket,
        roi_by_confidence_bucket=confidence_bucket,
        calibration_bins=calibration,
        publication_policy_grid=policy_grid,
        output_paths=output_paths,
    )


def filter_ou_publication_dataset(
    frame: pd.DataFrame,
    *,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
    competition: str | int | None = None,
) -> pd.DataFrame:
    """Return a filtered copy of an O/U dataset before walk-forward splitting."""
    filtered = frame.copy()
    if start_date is not None or end_date is not None:
        if "fixture_date" not in filtered.columns:
            raise ValueError("Date filters require a fixture_date column")
        fixture_dates = pd.to_datetime(filtered["fixture_date"], utc=True, errors="coerce")
        if start_date is not None:
            filtered = filtered[fixture_dates >= _timestamp_utc(start_date)]
            fixture_dates = fixture_dates.loc[filtered.index]
        if end_date is not None:
            end_ts = _timestamp_utc(end_date)
            if _is_date_only(end_date):
                end_ts = end_ts + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
            filtered = filtered[fixture_dates <= end_ts]

    if competition is not None:
        filtered = _filter_competition(filtered, competition)

    if "target_ou25" in filtered.columns:
        filtered = filtered[filtered["target_ou25"].notna()]

    return filtered.reset_index(drop=True)


def load_filtered_ou_publication_dataset(
    dataset_path: Path,
    *,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
    competition: str | int | None = None,
) -> pd.DataFrame:
    """Load and filter an O/U publication backtest dataset."""
    if dataset_path.suffix in (".parquet", ".pq"):
        frame = pd.read_parquet(dataset_path)
    else:
        frame = pd.read_csv(dataset_path)
    return filter_ou_publication_dataset(
        frame,
        start_date=start_date,
        end_date=end_date,
        competition=competition,
    )


def _filtered_dataset_path(
    dataset_path: Path,
    *,
    start_date: date | str | None,
    end_date: date | str | None,
    competition: str | int | None,
) -> Path:
    if start_date is None and end_date is None and competition is None:
        return dataset_path
    filtered = load_filtered_ou_publication_dataset(
        dataset_path,
        start_date=start_date,
        end_date=end_date,
        competition=competition,
    )
    if filtered.empty:
        raise ValueError("Filtered O/U publication dataset is empty")
    suffix = dataset_path.suffix if dataset_path.suffix else ".csv"
    with NamedTemporaryFile(
        prefix="ou_publication_backtest_",
        suffix=suffix,
        delete=False,
    ) as temp:
        temp_path = Path(temp.name)
    if suffix in (".parquet", ".pq"):
        filtered.to_parquet(temp_path, index=False)
    else:
        filtered.to_csv(temp_path, index=False)
    return temp_path


def _filter_competition(frame: pd.DataFrame, competition: str | int) -> pd.DataFrame:
    competition_text = str(competition).strip()
    if competition_text.isdigit() and "league_id" in frame.columns:
        league_ids = pd.to_numeric(frame["league_id"], errors="coerce")
        return frame[league_ids == int(competition_text)]

    text_columns = ("competition", "competition_key", "league_name")
    available = [column for column in text_columns if column in frame.columns]
    if not available:
        raise ValueError(
            "Competition filter requires league_id or one of: "
            "competition, competition_key, league_name"
        )
    normalized = competition_text.casefold()
    mask = pd.Series(False, index=frame.index)
    for column in available:
        mask |= frame[column].astype(str).str.casefold().eq(normalized)
    return frame[mask]


def evaluate_ou_publication_rows(rows: list[JsonDict]) -> pd.DataFrame:
    """Apply O/U V2 decisions to out-of-fold prediction rows."""
    evaluated: list[JsonDict] = []
    for row in rows:
        target = _optional_int(row.get("target_ou25"))
        if target is None:
            continue
        data_quality_score = _optional_float(row.get("data_quality_score"))
        bookmaker_count = _optional_float(row.get("bookmaker_count"))
        odds_payload = _point_in_time_odds_payload(row)
        decision = decide_ou_prediction(
            p_over=float(row["p_over"]),
            p_under=float(row["p_under"]),
            market_p_over=odds_payload["market_p_over"],
            market_p_under=odds_payload["market_p_under"],
            odd_over=odds_payload["odd_over"],
            odd_under=odds_payload["odd_under"],
            data_quality_json={
                "ou_data_quality_score": data_quality_score,
                "ou_market_bookmaker_count": bookmaker_count,
            },
        )
        payload = {
            **row,
            "target_ou25": target,
            "market_p_over": odds_payload["market_p_over"],
            "market_p_under": odds_payload["market_p_under"],
            "odd_over": odds_payload["odd_over"],
            "odd_under": odds_payload["odd_under"],
            **decision.as_payload(),
        }
        payload["edge_bucket"] = _bucket_label(payload.get("edge_pick"), EDGE_BUCKETS)
        payload["ev_bucket"] = _bucket_label(payload.get("ev_pick"), EV_BUCKETS)
        payload["confidence_bucket"] = _bucket_label(
            payload.get("confidence_score_v2"),
            CONFIDENCE_BUCKETS,
        )
        payload["bet_won"] = _bet_won(payload)
        payload["bet_profit_units"] = _bet_profit_units(payload)
        evaluated.append(payload)
    return pd.DataFrame(evaluated)


def calibration_report_frame(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[JsonDict] = []
    if frame.empty:
        return pd.DataFrame(columns=[
            "source", "bin_lower", "bin_upper", "count", "mean_predicted",
            "actual_fraction", "ece",
        ])
    y_true = frame["target_ou25"].astype(int).tolist()
    model_bins = calibration_bins_binary(y_true, frame["p_over"].astype(float).tolist())
    model_ece = expected_calibration_error(model_bins)
    rows.extend({"source": "model", **item, "ece": model_ece} for item in model_bins)

    market_frame = frame.dropna(subset=["market_p_over"])
    if not market_frame.empty:
        market_bins = calibration_bins_binary(
            market_frame["target_ou25"].astype(int).tolist(),
            market_frame["market_p_over"].astype(float).tolist(),
        )
        market_ece = expected_calibration_error(market_bins)
        rows.extend({"source": "market", **item, "ece": market_ece} for item in market_bins)
    return pd.DataFrame(rows)


def roi_by_bucket_frame(
    frame: pd.DataFrame,
    column: str,
    buckets: tuple[tuple[float, float, str], ...],
) -> pd.DataFrame:
    rows: list[JsonDict] = []
    value_frame = frame[frame["value_side"].notna()] if not frame.empty else frame
    for _, _, label in buckets:
        part = value_frame[value_frame[column] == label] if not value_frame.empty else value_frame
        rows.append({"bucket": label, **_betting_metrics(part)})
    return pd.DataFrame(rows)


def publication_policy_grid_frame(
    frame: pd.DataFrame,
    config: OUPublicationBacktestConfig,
) -> pd.DataFrame:
    rows: list[JsonDict] = []
    for min_edge in config.policy_min_edges:
        for min_ev in config.policy_min_evs:
            for min_confidence in config.policy_min_confidences:
                for min_data_quality in config.policy_min_data_qualities:
                    for min_bookmaker_count in config.policy_min_bookmaker_counts:
                        selected = _select_policy_rows(
                            frame,
                            min_edge=min_edge,
                            min_ev=min_ev,
                            min_confidence=min_confidence,
                            min_data_quality=min_data_quality,
                            min_bookmaker_count=min_bookmaker_count,
                        )
                        metrics = _betting_metrics(selected)
                        rows.append({
                            "min_edge": min_edge,
                            "min_ev": min_ev,
                            "min_confidence": min_confidence,
                            "min_data_quality": min_data_quality,
                            "min_bookmaker_count": min_bookmaker_count,
                            **metrics,
                        })
    return pd.DataFrame(rows)


def build_publication_summary(
    frame: pd.DataFrame,
    calibration: pd.DataFrame,
    policy_grid: pd.DataFrame,
    *,
    dataset_path: Path,
    filtered_dataset_path: Path,
    filters: JsonDict,
    n_folds: int,
    aggregate_backtest: JsonDict,
    config: OUPublicationBacktestConfig,
) -> JsonDict:
    recommendation = recommend_publication_policy(
        policy_grid,
        min_recommended_bets=config.min_recommended_bets,
    )
    value_frame = frame[frame["value_side"].notna()] if not frame.empty else frame
    return {
        "dataset_path": str(dataset_path),
        "filtered_dataset_path": str(filtered_dataset_path),
        "filters": filters,
        "row_count": int(len(frame)),
        "n_folds": n_folds,
        "aggregate_backtest": aggregate_backtest,
        "model_vs_market": _model_vs_market_metrics(frame, calibration),
        "betting": _betting_metrics(value_frame),
        "closing_line_value": _closing_line_value_summary(frame),
        "by_confidence_label_v2": _group_betting_metrics(frame, "confidence_label_v2"),
        "by_league_id": _group_betting_metrics(frame, "league_id"),
        "recommendation": recommendation,
    }


def recommend_publication_policy(
    policy_grid: pd.DataFrame,
    *,
    min_recommended_bets: int = 20,
) -> JsonDict:
    if policy_grid.empty:
        return {"decision": "staff_only", "reason": "empty_policy_grid"}
    eligible = policy_grid[
        (policy_grid["total_bets"] >= min_recommended_bets)
        & (policy_grid["roi"] > 0)
    ].copy()
    if eligible.empty:
        best = policy_grid.sort_values(["roi", "total_bets"], ascending=[False, False]).head(1)
        payload: JsonDict = {
            "decision": "staff_only",
            "reason": "no_positive_roi_policy_with_min_volume",
        }
        if not best.empty:
            payload["best_observed_policy"] = best.iloc[0].to_dict()
        return payload
    eligible = eligible.sort_values(
        ["roi", "profit_units", "total_bets", "max_drawdown_units"],
        ascending=[False, False, False, True],
    )
    row = eligible.iloc[0].to_dict()
    row["decision"] = "public"
    return row


def _model_vs_market_metrics(frame: pd.DataFrame, calibration: pd.DataFrame) -> JsonDict:
    if frame.empty:
        return {"model": {}, "market": {}}
    y = frame["target_ou25"].astype(int).tolist()
    model_p = frame["p_over"].astype(float).tolist()
    model_bins = calibration[calibration["source"] == "model"]
    result: JsonDict = {
        "model": {
            "row_count": len(frame),
            "brier_score": binary_brier_score(y, model_p),
            "log_loss": binary_log_loss(y, model_p),
            "ece": _first_ece(model_bins),
        }
    }
    market = frame.dropna(subset=["market_p_over"])
    if market.empty:
        result["market"] = {
            "row_count": 0,
            "coverage": 0.0,
            "brier_score": None,
            "log_loss": None,
            "ece": None,
        }
    else:
        market_bins = calibration[calibration["source"] == "market"]
        result["market"] = {
            "row_count": len(market),
            "coverage": len(market) / len(frame),
            "brier_score": binary_brier_score(
                market["target_ou25"].astype(int).tolist(),
                market["market_p_over"].astype(float).tolist(),
            ),
            "log_loss": binary_log_loss(
                market["target_ou25"].astype(int).tolist(),
                market["market_p_over"].astype(float).tolist(),
            ),
            "ece": _first_ece(market_bins),
        }
    return result


def _closing_line_value_summary(frame: pd.DataFrame) -> JsonDict:
    if (
        frame.empty
        or "closing_odd_over" not in frame.columns
        or "closing_odd_under" not in frame.columns
    ):
        return {
            "closing_odds_coverage": 0.0,
            "model_over_clv": None,
            "pick_clv": None,
        }
    closing = frame.dropna(subset=["closing_odd_over", "closing_odd_under"]).copy()
    if closing.empty:
        return {
            "closing_odds_coverage": 0.0,
            "model_over_clv": None,
            "pick_clv": None,
        }
    closing["closing_p_over"] = closing.apply(
        lambda row: _market_p_over(row["closing_odd_over"], row["closing_odd_under"]),
        axis=1,
    )
    model_over_clv = float((closing["p_over"] - closing["closing_p_over"]).mean())
    pick_clv_values: list[float] = []
    for _, row in closing[closing["value_side"].notna()].iterrows():
        closing_p_over = float(row["closing_p_over"])
        closing_p_pick = closing_p_over if row["value_side"] == "OVER" else 1.0 - closing_p_over
        if pd.notna(row.get("p_pick")):
            pick_clv_values.append(float(row["p_pick"]) - closing_p_pick)
    return {
        "closing_odds_coverage": len(closing) / len(frame),
        "model_over_clv": model_over_clv,
        "pick_clv": float(np.mean(pick_clv_values)) if pick_clv_values else None,
    }


def _group_betting_metrics(frame: pd.DataFrame, column: str) -> list[JsonDict]:
    if frame.empty or column not in frame.columns:
        return []
    rows: list[JsonDict] = []
    value_frame = frame[frame["value_side"].notna()]
    for value, part in value_frame.groupby(column, dropna=False):
        rows.append({"group": str(value), **_betting_metrics(part)})
    rows.sort(key=lambda item: (-int(item["total_bets"]), item["group"]))
    return rows


def _select_policy_rows(
    frame: pd.DataFrame,
    *,
    min_edge: float,
    min_ev: float,
    min_confidence: float,
    min_data_quality: float,
    min_bookmaker_count: int,
) -> pd.DataFrame:
    if frame.empty:
        return frame
    mask = (
        frame["value_side"].notna()
        & (frame["edge_pick"].fillna(-999.0) >= min_edge)
        & (frame["ev_pick"].fillna(-999.0) >= min_ev)
        & (frame["confidence_score_v2"].fillna(-999.0) >= min_confidence)
        & (frame["data_quality_score"].fillna(-999.0) >= min_data_quality)
    )
    if "bookmaker_count" in frame.columns:
        mask &= frame["bookmaker_count"].fillna(0) >= min_bookmaker_count
    elif min_bookmaker_count > 0:
        mask &= False
    return frame[mask]


def _point_in_time_odds_payload(row: JsonDict) -> JsonDict:
    odd_over = _optional_float(row.get("odd_over"))
    odd_under = _optional_float(row.get("odd_under"))
    market_p_over = _optional_float(row.get("market_p_over"))
    market_p_under = _optional_float(row.get("market_p_under"))
    if _odds_after_cutoff(row):
        odd_over = None
        odd_under = None
        market_p_over = None
        market_p_under = None
    return {
        "odd_over": odd_over,
        "odd_under": odd_under,
        "market_p_over": market_p_over,
        "market_p_under": market_p_under,
    }


def _odds_after_cutoff(row: JsonDict) -> bool:
    odds_time = _first_datetime(
        row,
        (
            "odds_fetched_at",
            "ou_odds_fetched_at",
            "market_ou_fetched_at",
            "ou_market_fetched_at",
            "odd_fetched_at",
            "odds_last_update",
        ),
    )
    cutoff_time = _first_datetime(
        row,
        (
            "cutoff_time",
            "data_cutoff_time",
            "prediction_time",
        ),
    )
    return odds_time is not None and cutoff_time is not None and odds_time > cutoff_time


def _first_datetime(row: JsonDict, keys: tuple[str, ...]) -> pd.Timestamp | None:
    for key in keys:
        if key not in row:
            continue
        value = row.get(key)
        if value is None:
            continue
        timestamp = pd.to_datetime(value, utc=True, errors="coerce")
        if not pd.isna(timestamp):
            return timestamp
    return None


def _timestamp_utc(value: date | str) -> pd.Timestamp:
    timestamp = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(timestamp):
        raise ValueError(f"Invalid date filter value: {value!r}")
    return timestamp


def _is_date_only(value: date | str) -> bool:
    if isinstance(value, date) and not isinstance(value, pd.Timestamp):
        return True
    return isinstance(value, str) and len(value.strip()) == 10


def _date_filter_label(value: date | str | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _betting_metrics(frame: pd.DataFrame) -> JsonDict:
    if frame.empty:
        return flat_stake_betting_metrics([], [], [])
    return flat_stake_betting_metrics(
        frame["target_ou25"].astype(int).tolist(),
        frame["value_side"].tolist(),
        frame["odd_pick"].tolist(),
    )


def _bucket_label(value: Any, buckets: tuple[tuple[float, float, str], ...]) -> str:
    numeric = _optional_float(value)
    if numeric is None:
        return "none"
    for low, high, label in buckets:
        if low <= numeric < high:
            return label
    return buckets[-1][2]


def _bet_won(row: JsonDict) -> bool | None:
    side = row.get("value_side")
    if side == "OVER":
        return int(row["target_ou25"]) == 1
    if side == "UNDER":
        return int(row["target_ou25"]) == 0
    return None


def _bet_profit_units(row: JsonDict) -> float | None:
    won = row.get("bet_won")
    odd = _optional_float(row.get("odd_pick"))
    if won is None or odd is None or odd <= 1:
        return None
    return odd - 1.0 if won else -1.0


def _market_p_over(odd_over: Any, odd_under: Any) -> float:
    odd_over_f = float(odd_over)
    odd_under_f = float(odd_under)
    q_over = 1.0 / odd_over_f
    q_under = 1.0 / odd_under_f
    return q_over / (q_over + q_under)


def _first_ece(frame: pd.DataFrame) -> float | None:
    if frame.empty or "ece" not in frame.columns:
        return None
    value = frame["ece"].dropna()
    return float(value.iloc[0]) if not value.empty else None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(parsed):
        return None
    return parsed


def _optional_int(value: Any) -> int | None:
    numeric = _optional_float(value)
    if numeric is None:
        return None
    return int(numeric)
