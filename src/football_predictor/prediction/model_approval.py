"""Production activation guard for backtest-approved model artifacts."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from football_predictor.backtesting.confidence_calibration import (
    THRESHOLD_VERSION,
    ModelFamily,
    confidence_label_for_score,
    is_production_approved_artifact,
)
from football_predictor.prediction.publication_policy import (
    PUBLISHABLE_CONFIDENCE_LABELS,
    normalize_approved_labels,
    normalize_confidence_label,
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


@dataclass(frozen=True)
class RuntimeConfidenceThresholds:
    """Runtime view of calibrated confidence thresholds for prediction publication."""

    model_family: ModelFamily
    artifact_path: Path | None
    status: str
    threshold_version: str | None = None
    thresholds: dict[str, float] | None = None
    approved_labels: tuple[str, ...] = ()
    production_approved: bool = False

    @property
    def usable_thresholds(self) -> bool:
        return self.thresholds is not None

    def label_for_score(self, score: float | int | None, fallback_label: str | None) -> str:
        """Return the calibrated label when thresholds are available."""
        if self.thresholds is None:
            return normalize_confidence_label(fallback_label)
        return confidence_label_for_score(score, self.thresholds)

    def as_metadata(self) -> dict[str, Any]:
        return {
            "threshold_artifact_status": self.status,
            "confidence_threshold_version": self.threshold_version,
            "confidence_thresholds": self.thresholds,
            "approved_labels": list(self.approved_labels),
            "production_approved": self.production_approved,
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


def load_runtime_confidence_thresholds(
    model_dir: Path | str | None,
    *,
    model_family: ModelFamily,
) -> RuntimeConfidenceThresholds:
    """Load calibrated thresholds for runtime labeling without mutating state."""
    path = approval_artifact_path(model_dir)
    if path is None:
        return RuntimeConfidenceThresholds(
            model_family=model_family,
            artifact_path=None,
            status="model_dir_missing",
        )
    if not path.exists():
        return RuntimeConfidenceThresholds(
            model_family=model_family,
            artifact_path=path,
            status="approval_artifact_missing",
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return RuntimeConfidenceThresholds(
            model_family=model_family,
            artifact_path=path,
            status="approval_artifact_invalid_json",
        )
    except OSError:
        return RuntimeConfidenceThresholds(
            model_family=model_family,
            artifact_path=path,
            status="approval_artifact_unreadable",
        )
    if not isinstance(payload, Mapping):
        return RuntimeConfidenceThresholds(
            model_family=model_family,
            artifact_path=path,
            status="approval_artifact_invalid_shape",
        )
    if payload.get("threshold_version") != THRESHOLD_VERSION:
        return RuntimeConfidenceThresholds(
            model_family=model_family,
            artifact_path=path,
            status="approval_artifact_wrong_version",
        )
    if payload.get("model_family") != model_family:
        return RuntimeConfidenceThresholds(
            model_family=model_family,
            artifact_path=path,
            status="approval_artifact_wrong_model_family",
        )
    thresholds = _global_thresholds(payload)
    approved = is_production_approved_artifact(payload, model_family=model_family)
    approved_labels = _approved_labels(payload, approved=approved)
    return RuntimeConfidenceThresholds(
        model_family=model_family,
        artifact_path=path,
        status="approved" if approved else "approval_artifact_not_approved",
        threshold_version=str(payload.get("threshold_version")),
        thresholds=thresholds,
        approved_labels=approved_labels,
        production_approved=approved,
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


def _global_thresholds(payload: Mapping[str, Any]) -> dict[str, float] | None:
    thresholds = payload.get("thresholds")
    if not isinstance(thresholds, Mapping):
        return None
    global_thresholds = thresholds.get("global")
    if not isinstance(global_thresholds, Mapping):
        return None
    try:
        high = float(global_thresholds["high"])
        very_high = float(global_thresholds["very_high"])
    except (KeyError, TypeError, ValueError):
        return None
    if high >= very_high:
        return None
    return {"high": high, "very_high": very_high}


def _approved_labels(payload: Mapping[str, Any], *, approved: bool) -> tuple[str, ...]:
    if not approved:
        return ()
    labels = payload.get("approved_labels")
    if labels is None:
        return tuple(sorted(PUBLISHABLE_CONFIDENCE_LABELS))
    return tuple(sorted(normalize_approved_labels(labels)))
