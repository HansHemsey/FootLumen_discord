"""Leakage-aware preprocessing for modeling datasets."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

FORBIDDEN_FEATURE_PATTERNS = (
    r"^target$",
    r"^home_goals$",
    r"^away_goals$",
    r"score_final",
    r"final_score",
    r"full_time",
    r"post_match",
    r"^status$",
    r"^status_short$",
    r"^status_long$",
    r"(^|_)fixture_id$",
    r"(^|_)feature_snapshot_id$",
    r"(^|_)team_id$",
    r"(^|_)league_id$",
    r"(^|_)player_id$",
    r"(^|_)venue_id$",
    r"(^|_)bookmaker_id$",
    r"(^|_)bet_id$",
    r"(^|_)coach_id$",
    r"(^|_)season$",
    r"(^|_)date$",
    r"(^|_)time$",
    r"fetched_at$",
    r"created_at$",
    r"updated_at$",
    r"_json$",
    r"payload",
)


@dataclass(frozen=True)
class PreprocessedDataset:
    features: pd.DataFrame
    target: pd.Series | None
    metadata: pd.DataFrame
    feature_names: list[str]


def features_dict_to_dataframe(
    rows: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    impute: bool = True,
    forbidden_patterns: Sequence[str] = FORBIDDEN_FEATURE_PATTERNS,
) -> pd.DataFrame:
    """Convert feature dicts into a numeric DataFrame with leakage columns removed."""
    if isinstance(rows, Mapping):
        frame = pd.DataFrame([dict(rows)])
    else:
        frame = pd.DataFrame([dict(row) for row in rows])
    return numeric_feature_dataframe(frame, impute=impute, forbidden_patterns=forbidden_patterns)


def separate_metadata_target_features(
    frame: pd.DataFrame,
    *,
    target_column: str = "target",
    impute: bool = True,
    forbidden_patterns: Sequence[str] = FORBIDDEN_FEATURE_PATTERNS,
) -> PreprocessedDataset:
    """Split raw dataset columns into metadata, target and safe numeric features."""
    target = frame[target_column].copy() if target_column in frame.columns else None
    feature_names = select_numeric_feature_names(frame, forbidden_patterns=forbidden_patterns)
    metadata_columns = [column for column in frame.columns if column not in feature_names]
    features = numeric_feature_dataframe(
        frame[feature_names],
        impute=impute,
        forbidden_patterns=(),
    )
    return PreprocessedDataset(
        features=features,
        target=target,
        metadata=frame[metadata_columns].copy(),
        feature_names=list(features.columns),
    )


def numeric_feature_dataframe(
    frame: pd.DataFrame,
    *,
    impute: bool = True,
    forbidden_patterns: Sequence[str] = FORBIDDEN_FEATURE_PATTERNS,
) -> pd.DataFrame:
    selected = (
        [str(column) for column in frame.columns]
        if not forbidden_patterns
        else select_numeric_feature_names(frame, forbidden_patterns=forbidden_patterns)
    )
    columns: dict[str, pd.Series] = {}
    for column in selected:
        series = frame[column]
        if pd.api.types.is_bool_dtype(series):
            columns[column] = series.astype("Int64").astype(float)
        else:
            columns[column] = pd.to_numeric(series, errors="coerce")
    output = pd.DataFrame(columns, index=frame.index)
    if impute:
        output = impute_missing_values(output)
    return output


def select_numeric_feature_names(
    frame: pd.DataFrame,
    *,
    forbidden_patterns: Sequence[str] = FORBIDDEN_FEATURE_PATTERNS,
) -> list[str]:
    names: list[str] = []
    for column in frame.columns:
        column_name = str(column)
        if is_forbidden_feature(column_name, forbidden_patterns):
            continue
        series = frame[column]
        if pd.api.types.is_bool_dtype(series):
            names.append(column_name)
            continue
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().any():
            names.append(column_name)
    return names


def impute_missing_values(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    output = frame.copy()
    for column in output.columns:
        median = output[column].median(skipna=True)
        fill_value = 0.0 if pd.isna(median) else float(median)
        output[column] = output[column].fillna(fill_value)
    return output


def is_forbidden_feature(
    column: str,
    forbidden_patterns: Sequence[str] = FORBIDDEN_FEATURE_PATTERNS,
) -> bool:
    normalized = column.strip()
    return any(re.search(pattern, normalized) for pattern in forbidden_patterns)
