"""Composite V3 football outcome model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]

from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.modeling.v3.constants import DEFAULT_V3_FINAL_MODEL_VERSION
from football_predictor.modeling.v3.draw_risk_model import DrawRiskModel
from football_predictor.modeling.v3.fusion import (
    deterministic_v3_fusion,
    market_probability_from_row,
)
from football_predictor.modeling.v3.no_draw_winner_model import NoDrawWinnerModel
from football_predictor.modeling.v3.stacker import V3StackerModel


@dataclass
class FootballOutcomeV3Model:
    """Composite V3 model combining Draw Risk, No-Draw Winner, V2, market and stacker."""

    draw_risk_model: DrawRiskModel
    no_draw_winner_model: NoDrawWinnerModel
    stacker_model: V3StackerModel | None = None
    v2_model: Any | None = None
    model_version: str = DEFAULT_V3_FINAL_MODEL_VERSION
    is_v3_composite: bool = True

    def predict_proba(self, frame: pd.DataFrame) -> list[list[float]]:
        """Return final probabilities ordered as HOME, DRAW, AWAY."""
        component_frame = self.predict_component_frame(frame)
        if self.stacker_model is not None:
            return self.stacker_model.predict_proba(component_frame)
        return [
            self._fallback_probability_for_row(row).to_vector()
            for _, row in component_frame.iterrows()
        ]

    def predict_probability_triples(self, frame: pd.DataFrame) -> list[ProbabilityTriple]:
        return [ProbabilityTriple.from_vector(row) for row in self.predict_proba(frame)]

    def predict_component_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Return input rows enriched with V3 component and V2 probability columns."""
        result = frame.copy()
        try:
            draw_probabilities = self.draw_risk_model.predict_draw_proba(frame)
            home_no_draw_probabilities = self.no_draw_winner_model.predict_home_no_draw_proba(frame)
        except Exception:
            fallback = self._v2_or_uniform_probabilities(frame)
            result["p_v2_home"] = [row[0] for row in fallback]
            result["p_v2_draw"] = [row[1] for row in fallback]
            result["p_v2_away"] = [row[2] for row in fallback]
            result["p_v3_draw_risk"] = result["p_v2_draw"]
            result["p_v3_home_no_draw"] = 0.5
            result["p_v3_away_no_draw"] = 0.5
            return result

        result["p_v3_draw_risk"] = draw_probabilities
        result["p_v3_home_no_draw"] = home_no_draw_probabilities
        result["p_v3_away_no_draw"] = [1.0 - value for value in home_no_draw_probabilities]
        v2_probabilities = self._v2_or_uniform_probabilities(frame)
        result["p_v2_home"] = [row[0] for row in v2_probabilities]
        result["p_v2_draw"] = [row[1] for row in v2_probabilities]
        result["p_v2_away"] = [row[2] for row in v2_probabilities]
        return result

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @classmethod
    def load(
        cls,
        model_dir: Path,
        *,
        v2_model_dir: Path | None = None,
    ) -> FootballOutcomeV3Model:
        draw_model = DrawRiskModel.load(model_dir / "draw_risk" / "model.joblib")
        ndw_model = NoDrawWinnerModel.load(model_dir / "no_draw_winner" / "model.joblib")
        stacker_path = model_dir / "stacker" / "model.joblib"
        stacker_model = V3StackerModel.load(stacker_path) if stacker_path.exists() else None
        v2_model = _load_v2_model(v2_model_dir) if v2_model_dir is not None else None
        return cls(
            draw_risk_model=draw_model,
            no_draw_winner_model=ndw_model,
            stacker_model=stacker_model,
            v2_model=v2_model,
        )

    def _fallback_probability_for_row(self, row: pd.Series) -> ProbabilityTriple:
        return deterministic_v3_fusion(
            draw_probability=float(row.get("p_v3_draw_risk", 1.0 / 3.0)),
            home_no_draw_probability=float(row.get("p_v3_home_no_draw", 0.5)),
            v2_probability=[
                float(row.get("p_v2_home", 1.0 / 3.0)),
                float(row.get("p_v2_draw", 1.0 / 3.0)),
                float(row.get("p_v2_away", 1.0 / 3.0)),
            ],
            market_probability=market_probability_from_row(row),
        )

    def _v2_or_uniform_probabilities(self, frame: pd.DataFrame) -> list[list[float]]:
        if self.v2_model is None:
            return [[1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0] for _ in range(len(frame))]
        try:
            return [list(row) for row in self.v2_model.predict_proba(frame)]
        except Exception:
            return [[1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0] for _ in range(len(frame))]


def _load_v2_model(path: Path | None) -> Any | None:
    if path is None:
        return None
    model_path = path / "model.joblib" if path.is_dir() else path
    if not model_path.exists():
        return None
    return joblib.load(model_path)
