"""Build V3 Draw Risk, No-Draw Winner and stacker datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from football_predictor.backtesting.dataset_builder import build_training_dataset
from football_predictor.reference.lookups import PlayersReference

JsonDict = dict[str, Any]

V3_FEATURE_VERSION = "v3.0"
V3_PREDICTION_OFFSET_MINUTES = 30
DRAW_TARGET_COL = "is_draw"
NDW_TARGET_COL = "home_wins"
OUTCOME_COL = "outcome"
SPLIT_COL = "split"
DATE_COL = "fixture_date"
FIXTURE_ID_COL = "fixture_id"

OUTCOMES = {"HOME", "DRAW", "AWAY"}

STACKER_COLUMNS = [
    FIXTURE_ID_COL,
    DATE_COL,
    "prediction_time",
    OUTCOME_COL,
    "p_v3_draw_risk",
    "p_v3_home_no_draw",
    "p_v3_away_no_draw",
    "p_v2_home",
    "p_v2_draw",
    "p_v2_away",
    "p_market_home",
    "p_market_draw",
    "p_market_away",
    "p_market_home_no_draw",
    "p_market_away_no_draw",
    "p_api_home",
    "p_api_draw",
    "p_api_away",
    "data_quality_score",
    "official_lineup_available_flag",
]


@dataclass(frozen=True)
class V3DatasetSplits:
    train: pd.DataFrame
    valid: pd.DataFrame
    test: pd.DataFrame


def build_v3_base_dataset(
    session: Session,
    league_ids: list[int],
    seasons: list[int],
    *,
    save_path: Path | None = None,
    players_reference: PlayersReference | None = None,
    limit: int | None = None,
    feature_version: str = V3_FEATURE_VERSION,
    prediction_offset_minutes: int = V3_PREDICTION_OFFSET_MINUTES,
) -> pd.DataFrame:
    """Build the shared PIT-safe V3 M-30 fixture dataset."""
    frame = build_training_dataset(
        session,
        league_ids,
        seasons,
        save_path=None,
        players_reference=players_reference,
        limit=limit,
        feature_version=feature_version,
        prediction_offset_minutes=prediction_offset_minutes,
    )
    frame = add_v3_targets(frame)
    if save_path is not None:
        _save_frame(frame, save_path)
    return frame


def build_v3_draw_risk_dataset(
    session: Session,
    league_ids: list[int],
    seasons: list[int],
    *,
    save_path: Path | None = None,
    players_reference: PlayersReference | None = None,
    limit: int | None = None,
    feature_version: str = V3_FEATURE_VERSION,
    prediction_offset_minutes: int = V3_PREDICTION_OFFSET_MINUTES,
) -> pd.DataFrame:
    """Build the binary Draw Risk dataset: target is DRAW vs NOT_DRAW."""
    frame = build_v3_base_dataset(
        session,
        league_ids,
        seasons,
        players_reference=players_reference,
        limit=limit,
        feature_version=feature_version,
        prediction_offset_minutes=prediction_offset_minutes,
    )
    if save_path is not None:
        _save_frame(frame, save_path)
    return frame


def build_v3_no_draw_winner_dataset(
    session: Session,
    league_ids: list[int],
    seasons: list[int],
    *,
    save_path: Path | None = None,
    players_reference: PlayersReference | None = None,
    limit: int | None = None,
    feature_version: str = V3_FEATURE_VERSION,
    prediction_offset_minutes: int = V3_PREDICTION_OFFSET_MINUTES,
) -> pd.DataFrame:
    """Build the binary No-Draw Winner dataset: target is HOME vs AWAY, draws excluded."""
    frame = build_v3_base_dataset(
        session,
        league_ids,
        seasons,
        players_reference=players_reference,
        limit=limit,
        feature_version=feature_version,
        prediction_offset_minutes=prediction_offset_minutes,
    )
    if frame.empty:
        result = frame.copy()
    else:
        result = frame.loc[frame[OUTCOME_COL] != "DRAW"].copy().reset_index(drop=True)
    if save_path is not None:
        _save_frame(result, save_path)
    return result


def add_v3_targets(frame: pd.DataFrame) -> pd.DataFrame:
    """Add V3 target columns without mutating the input frame."""
    result = frame.copy()
    if result.empty:
        for column in (OUTCOME_COL, DRAW_TARGET_COL, NDW_TARGET_COL):
            if column not in result.columns:
                result[column] = pd.Series(dtype="int64" if column != OUTCOME_COL else "object")
        return result
    if "target" not in result.columns:
        raise ValueError("V3 datasets require a target column with HOME/DRAW/AWAY values")
    invalid = set(result["target"].dropna().astype(str)) - OUTCOMES
    if invalid:
        raise ValueError(f"Unknown 1X2 target values: {sorted(invalid)}")
    result[OUTCOME_COL] = result["target"].astype(str)
    result[DRAW_TARGET_COL] = (result[OUTCOME_COL] == "DRAW").astype(int)
    result[NDW_TARGET_COL] = (result[OUTCOME_COL] == "HOME").astype(int)
    result.loc[result[OUTCOME_COL] == "DRAW", NDW_TARGET_COL] = pd.NA
    return result


def add_chronological_split_column(
    frame: pd.DataFrame,
    *,
    train_ratio: float = 0.6,
    valid_ratio: float = 0.2,
    date_col: str = DATE_COL,
) -> pd.DataFrame:
    """Return frame sorted by date with train/valid/test labels."""
    splits = chronological_splits(
        frame,
        train_ratio=train_ratio,
        valid_ratio=valid_ratio,
        date_col=date_col,
    )
    parts: list[pd.DataFrame] = []
    for name, part in (
        ("train", splits.train),
        ("valid", splits.valid),
        ("test", splits.test),
    ):
        labeled = part.copy()
        labeled[SPLIT_COL] = name
        parts.append(labeled)
    if not parts:
        return frame.copy()
    return pd.concat(parts, ignore_index=True)


def chronological_splits(
    frame: pd.DataFrame,
    *,
    train_ratio: float = 0.6,
    valid_ratio: float = 0.2,
    date_col: str = DATE_COL,
) -> V3DatasetSplits:
    """Split a dataset chronologically using 60/20/20 ratios by default."""
    _validate_split_ratios(train_ratio, valid_ratio)
    if date_col not in frame.columns:
        raise ValueError(f"DataFrame must contain {date_col}")
    ordered = frame.sort_values(date_col).reset_index(drop=True)
    row_count = len(ordered)
    train_end = int(row_count * train_ratio)
    valid_end = train_end + int(row_count * valid_ratio)
    return V3DatasetSplits(
        train=ordered.iloc[:train_end].copy(),
        valid=ordered.iloc[train_end:valid_end].copy(),
        test=ordered.iloc[valid_end:].copy(),
    )


def build_v3_stacker_dataset(
    base_frame: pd.DataFrame,
    draw_risk_predictions: pd.DataFrame,
    no_draw_winner_predictions: pd.DataFrame,
    *,
    v2_predictions: pd.DataFrame | None = None,
    split_name: str | None = "valid",
    save_path: Path | None = None,
) -> pd.DataFrame:
    """Join validation/test fixture rows with sub-model predictions for the V3 stacker."""
    if FIXTURE_ID_COL not in base_frame.columns:
        raise ValueError("base_frame must contain fixture_id")
    frame = add_v3_targets(base_frame)
    if split_name is not None:
        if SPLIT_COL not in frame.columns:
            raise ValueError("base_frame must contain split when split_name is provided")
        frame = frame.loc[frame[SPLIT_COL] == split_name].copy()
    frame = _merge_prediction_frame(
        frame,
        draw_risk_predictions,
        required_columns=["p_v3_draw_risk"],
        frame_name="draw_risk_predictions",
    )
    frame = _merge_prediction_frame(
        frame,
        no_draw_winner_predictions,
        required_columns=["p_v3_home_no_draw"],
        frame_name="no_draw_winner_predictions",
    )
    if "p_v3_away_no_draw" not in frame.columns:
        frame["p_v3_away_no_draw"] = 1.0 - frame["p_v3_home_no_draw"]
    if v2_predictions is not None:
        frame = _merge_prediction_frame(
            frame,
            v2_predictions,
            required_columns=["p_v2_home", "p_v2_draw", "p_v2_away"],
            frame_name="v2_predictions",
        )
    else:
        frame = _add_uniform_v2_priors(frame)
    frame = _add_stacker_source_columns(frame)
    result = frame.loc[:, STACKER_COLUMNS].copy()
    _validate_stacker_predictions(result)
    if save_path is not None:
        _save_frame(result, save_path)
    return result


def _validate_split_ratios(train_ratio: float, valid_ratio: float) -> None:
    if train_ratio <= 0 or valid_ratio <= 0:
        raise ValueError("train_ratio and valid_ratio must be positive")
    if train_ratio + valid_ratio >= 1:
        raise ValueError("train_ratio + valid_ratio must be less than 1")


def _merge_prediction_frame(
    frame: pd.DataFrame,
    predictions: pd.DataFrame,
    *,
    required_columns: list[str],
    frame_name: str,
) -> pd.DataFrame:
    missing = [
        column for column in [FIXTURE_ID_COL, *required_columns] if column not in predictions
    ]
    if missing:
        raise ValueError(f"{frame_name} missing required columns: {missing}")
    if predictions[FIXTURE_ID_COL].duplicated().any():
        raise ValueError(f"{frame_name} has duplicate fixture_id rows")
    columns = [FIXTURE_ID_COL, *[c for c in predictions.columns if c != FIXTURE_ID_COL]]
    merged = frame.merge(predictions.loc[:, columns], on=FIXTURE_ID_COL, how="left")
    for column in required_columns:
        if merged[column].isna().any():
            raise ValueError(f"{frame_name} has no {column} for at least one stacker row")
    return merged


def _add_uniform_v2_priors(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["p_v2_home"] = 1.0 / 3.0
    result["p_v2_draw"] = 1.0 / 3.0
    result["p_v2_away"] = 1.0 / 3.0
    return result


def _add_stacker_source_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["p_market_home"] = _first_available(result, ["p_market_home", "market_home"])
    result["p_market_draw"] = _first_available(result, ["p_market_draw", "market_draw"])
    result["p_market_away"] = _first_available(result, ["p_market_away", "market_away"])
    market_total = result["p_market_home"] + result["p_market_away"]
    result["p_market_home_no_draw"] = result["p_market_home"] / market_total
    result["p_market_away_no_draw"] = result["p_market_away"] / market_total
    result.loc[market_total <= 0, ["p_market_home_no_draw", "p_market_away_no_draw"]] = pd.NA
    result["p_api_home"] = _first_available(result, ["p_api_home", "api_pred_home"])
    result["p_api_draw"] = _first_available(result, ["p_api_draw", "api_pred_draw"])
    result["p_api_away"] = _first_available(result, ["p_api_away", "api_pred_away"])
    result["data_quality_score"] = _first_available(
        result, ["data_quality_score", "overall_data_quality_score"]
    )
    if "official_lineup_available_flag" not in result.columns:
        result["official_lineup_available_flag"] = 0
    return result


def _first_available(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    existing = [column for column in columns if column in frame.columns]
    if not existing:
        return pd.Series([pd.NA] * len(frame), index=frame.index)
    result = frame[existing[0]].copy()
    for column in existing[1:]:
        result = result.combine_first(frame[column])
    return result


def _validate_stacker_predictions(frame: pd.DataFrame) -> None:
    required = {
        "p_v3_draw_risk",
        "p_v3_home_no_draw",
        "p_v3_away_no_draw",
        "p_v2_home",
        "p_v2_draw",
        "p_v2_away",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Stacker dataset missing required model columns: {missing}")
    if frame[list(required)].isna().any().any():
        raise ValueError("Stacker dataset has missing model probabilities")


def _save_frame(frame: pd.DataFrame, save_path: Path) -> None:
    save_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = save_path.suffix.casefold()
    if suffix == ".csv":
        frame.to_csv(save_path, index=False)
        return
    if suffix in {".parquet", ".pq"}:
        frame.to_parquet(save_path, index=False, engine="pyarrow")
        return
    raise ValueError("save_path must end with .csv or .parquet")
