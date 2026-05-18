"""World Cup dataset build helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]

from football_predictor.worldcup.features import build_worldcup_dataset
from football_predictor.worldcup.references import (
    WorldCupReferenceBundle,
    audit_worldcup_references,
)


def build_and_save_worldcup_dataset(
    bundle: WorldCupReferenceBundle,
    *,
    output: Path | None = None,
    audited_teams: list[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    coverage = (
        audit_worldcup_references(audited_teams, bundle)
        if audited_teams is not None
        else {"ok": True, "team_count": 0, "teams": []}
    )
    if audited_teams is not None and not coverage.get("ok"):
        raise ValueError(
            "World Cup references do not cover all teams: "
            f"{coverage.get('blocking_missing_teams')}"
        )
    frame = build_worldcup_dataset(bundle.historical_matches)
    if output is not None:
        save_frame(frame, output)
    return frame, coverage


def save_frame(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        frame.to_csv(path, index=False)
        return
    if suffix == ".parquet":
        frame.to_parquet(path, index=False, engine="pyarrow")
        return
    raise ValueError("output path must end with .csv or .parquet")
