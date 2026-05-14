"""Production activation guard for backtest-approved model artifacts."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from football_predictor.backtesting.confidence_calibration import (
    ModelFamily,
    is_production_approved_artifact,
)
from football_predictor.utils.exceptions import PredictionError

APPROVAL_ARTIFACT_FILENAME = "confidence_thresholds.json"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProductionApprovalResult:
    """Result of checking whether a model can be activated in production."""

    model_family: ModelFamily
    model_dir: Path | None
    artifact_path: Path | None
    approved: bool
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_family": self.model_family,
            "model_dir": str(self.model_dir) if self.model_dir is not None else None,
            "artifact_path": str(self.artifact_path) if self.artifact_path is not None else None,
            "approved": self.approved,
            "reason": self.reason,
        }


def approval_artifact_path(model_dir: Path | str | None) -> Path | None:
    """Return the expected production approval artifact path for a model directory."""
    if model_dir is None:
        return None
    path = Path(model_dir)
    if path.name == APPROVAL_ARTIFACT_FILENAME:
        return path
    return path / APPROVAL_ARTIFACT_FILENAME


def check_production_model_approval(
    model_dir: Path | str | None,
    *,
    model_family: ModelFamily,
) -> ProductionApprovalResult:
    """Check the local backtest approval artifact without mutating state."""
    path = approval_artifact_path(model_dir)
    resolved_model_dir = Path(model_dir) if model_dir is not None else None
    if path is None:
        return ProductionApprovalResult(
            model_family=model_family,
            model_dir=None,
            artifact_path=None,
            approved=False,
            reason="model_dir_missing",
        )
    if not path.exists():
        return ProductionApprovalResult(
            model_family=model_family,
            model_dir=resolved_model_dir,
            artifact_path=path,
            approved=False,
            reason="approval_artifact_missing",
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ProductionApprovalResult(
            model_family=model_family,
            model_dir=resolved_model_dir,
            artifact_path=path,
            approved=False,
            reason="approval_artifact_invalid_json",
        )
    except OSError:
        return ProductionApprovalResult(
            model_family=model_family,
            model_dir=resolved_model_dir,
            artifact_path=path,
            approved=False,
            reason="approval_artifact_unreadable",
        )
    if not isinstance(payload, Mapping) or not is_production_approved_artifact(
        payload,
        model_family=model_family,
    ):
        return ProductionApprovalResult(
            model_family=model_family,
            model_dir=resolved_model_dir,
            artifact_path=path,
            approved=False,
            reason="approval_artifact_not_approved",
        )
    return ProductionApprovalResult(
        model_family=model_family,
        model_dir=resolved_model_dir,
        artifact_path=path,
        approved=True,
    )


def require_production_model_approval(
    model_dir: Path | str | None,
    *,
    model_family: ModelFamily,
) -> ProductionApprovalResult:
    """Raise a clear error when production mode lacks a valid approval artifact."""
    result = check_production_model_approval(model_dir, model_family=model_family)
    if result.approved:
        return result
    logger.error(
        "Production mode refused: model_family=%s model_dir=%s approval_artifact=%s "
        "reason=%s",
        result.model_family,
        result.model_dir,
        result.artifact_path,
        result.reason,
    )
    raise PredictionError(
        "Production mode requires an approved backtest artifact: "
        f"model_family={result.model_family} "
        f"artifact={result.artifact_path or APPROVAL_ARTIFACT_FILENAME} "
        f"reason={result.reason}"
    )
