from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from football_predictor.prediction.model_approval import (
    check_production_model_approval,
    require_production_model_approval,
)
from football_predictor.utils.exceptions import PredictionError


def test_production_approval_missing_artifact_is_rejected(tmp_path: Path) -> None:
    result = check_production_model_approval(tmp_path / "model", model_family="v3_1x2")

    assert result.approved is False
    assert result.reason == "approval_artifact_missing"


def test_production_approval_rejection_logs_clear_non_secret_error(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR)

    with pytest.raises(PredictionError, match="approval_artifact_missing"):
        require_production_model_approval(tmp_path / "model", model_family="v3_1x2")

    assert "Production mode refused" in caplog.text
    assert "model_family=v3_1x2" in caplog.text
    assert "approval_artifact_missing" in caplog.text
    assert "discord.com/api/webhooks" not in caplog.text


def test_production_approval_invalid_artifact_is_rejected(tmp_path: Path) -> None:
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / "confidence_thresholds.json").write_text(
        json.dumps(
            {
                "threshold_version": "confidence_thresholds_v1",
                "model_family": "v3_1x2",
                "production_approved": False,
                "thresholds": {"global": {"high": 60.0, "very_high": 80.0}},
            }
        ),
        encoding="utf-8",
    )

    result = check_production_model_approval(model_dir, model_family="v3_1x2")

    assert result.approved is False
    assert result.reason == "approval_artifact_not_approved"


def test_production_approval_valid_artifact_is_allowed(tmp_path: Path) -> None:
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / "confidence_thresholds.json").write_text(
        json.dumps(
            {
                "threshold_version": "confidence_thresholds_v1",
                "model_family": "ou25",
                "production_approved": True,
                "thresholds": {"global": {"high": 60.0, "very_high": 80.0}},
            }
        ),
        encoding="utf-8",
    )

    result = require_production_model_approval(model_dir, model_family="ou25")

    assert result.approved is True
    assert result.reason is None


def test_production_approval_wrong_model_family_is_rejected(tmp_path: Path) -> None:
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / "confidence_thresholds.json").write_text(
        json.dumps(
            {
                "threshold_version": "confidence_thresholds_v1",
                "model_family": "ou25",
                "production_approved": True,
                "thresholds": {"global": {"high": 60.0, "very_high": 80.0}},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(PredictionError, match="approval_artifact_not_approved"):
        require_production_model_approval(model_dir, model_family="v3_1x2")
