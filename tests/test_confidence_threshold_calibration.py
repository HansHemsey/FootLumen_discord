from __future__ import annotations

from football_predictor.backtesting.confidence_calibration import (
    ConfidenceThresholdConfig,
    apply_publication_policy_records,
    build_confidence_threshold_artifact,
    is_production_approved_artifact,
)


def test_v3_thresholds_use_validation_split_and_published_only_policy() -> None:
    validation = [
        _v3_record(70, True, quality=85, baseline_correct=False, league_id=-10),
        _v3_record(90, True, quality=85, baseline_correct=False, league_id=-10),
        _v3_record(90, True, quality=59, baseline_correct=False, league_id=-10),
        _v3_record(35, False, quality=95, baseline_correct=True, league_id=-10),
    ]
    test = [
        _v3_record(90, False, quality=95, baseline_correct=True, league_id=-10),
        _v3_record(95, False, quality=95, baseline_correct=True, league_id=-10),
    ]

    artifact = build_confidence_threshold_artifact(
        validation_records=validation,
        test_records=test,
        config=ConfidenceThresholdConfig(model_family="v3_1x2"),
        periods={"validation": {"row_count": len(validation)}, "test": {"row_count": len(test)}},
    )

    assert artifact["selection"]["source_split"] == "validation"
    assert artifact["metrics"]["validation"]["published_only"]["row_count"] == 2
    assert artifact["metrics"]["validation"]["published_only"]["accuracy"] == 1.0
    assert artifact["metrics"]["validation"]["labels"]["Very High"]["row_count"] >= 1
    assert artifact["metrics"]["validation"]["by_league"]["-10"]["published_only"][
        "row_count"
    ] == 2


def test_league_thresholds_fallback_when_validation_volume_is_insufficient() -> None:
    validation = [
        _v3_record(70, True, quality=85, baseline_correct=False, league_id=-100),
        _v3_record(90, True, quality=85, baseline_correct=False, league_id=-100),
    ]
    test = [
        _v3_record(70, True, quality=85, baseline_correct=False, league_id=-100),
        _v3_record(90, True, quality=85, baseline_correct=False, league_id=-100),
    ]

    artifact = build_confidence_threshold_artifact(
        validation_records=validation,
        test_records=test,
        config=ConfidenceThresholdConfig(
            model_family="v3_1x2",
            min_league_validation_rows=200,
            min_league_publishable_rows=40,
        ),
    )

    league_payload = artifact["thresholds"]["league_overrides"]["-100"]
    assert league_payload["status"] == "fallback_global"
    assert league_payload["reason"] == "insufficient_validation_rows"


def test_ou_calibration_uses_market_baseline_and_roi() -> None:
    validation = [
        _ou_record(72, True, quality=90, market_correct=False, profit=0.9),
        _ou_record(90, True, quality=90, market_correct=False, profit=0.9),
        _ou_record(45, False, quality=90, market_correct=True, profit=-1.0),
    ]
    test = [
        _ou_record(72, True, quality=90, market_correct=False, profit=0.9),
        _ou_record(90, True, quality=90, market_correct=False, profit=0.9),
    ]

    artifact = build_confidence_threshold_artifact(
        validation_records=validation,
        test_records=test,
        config=ConfidenceThresholdConfig(model_family="ou25"),
    )

    validation_metrics = artifact["metrics"]["validation"]
    assert validation_metrics["published_only"]["row_count"] == 2
    assert validation_metrics["published_only"]["roi"] > 0
    assert validation_metrics["baseline_on_published"]["accuracy"] == 0.0
    assert "published_log_loss_vs_market" in artifact["approval_checks"]


def test_production_like_publication_policy_excludes_weak_labels_and_quality_gate() -> None:
    records = [
        _v3_record(95, True, quality=85, baseline_correct=False, league_id=-10),
        _v3_record(72, True, quality=85, baseline_correct=False, league_id=-10),
        _v3_record(55, True, quality=95, baseline_correct=False, league_id=-10),
        _v3_record(25, True, quality=95, baseline_correct=False, league_id=-10),
        _v3_record(10, True, quality=95, baseline_correct=False, league_id=-10),
        _v3_record(92, True, quality=59, baseline_correct=False, league_id=-10),
    ]

    enriched = apply_publication_policy_records(
        records,
        {"high": 70, "very_high": 90},
        config=ConfidenceThresholdConfig(model_family="v3_1x2", min_data_quality_score=60),
    )

    published = [record for record in enriched if record["publication_allowed"]]
    blocked_reasons = {
        record["publication_decision"]["reason"]
        for record in enriched
        if not record["publication_allowed"]
    }
    assert [record["calibrated_label"] for record in published] == ["Very High", "High"]
    assert {
        "confidence_below_publish_threshold",
        "data_quality_below_publish_threshold",
    } <= blocked_reasons


def test_invalid_or_incomplete_threshold_artifact_is_not_approved() -> None:
    assert not is_production_approved_artifact(None, model_family="v3_1x2")
    assert not is_production_approved_artifact({"production_approved": True})
    assert not is_production_approved_artifact(
        {
            "threshold_version": "confidence_thresholds_v1",
            "model_family": "v3_1x2",
            "production_approved": True,
            "thresholds": {"global": {"high": 90, "very_high": 80}},
        },
        model_family="v3_1x2",
    )


def _v3_record(
    confidence_score: float,
    correct: bool,
    *,
    quality: float,
    baseline_correct: bool,
    league_id: int,
) -> dict:
    return {
        "confidence_score": confidence_score,
        "correct": correct,
        "log_loss": 0.20 if correct else 1.40,
        "brier_score": 0.10 if correct else 0.80,
        "baseline_correct": baseline_correct,
        "baseline_log_loss": 0.90 if not baseline_correct else 0.30,
        "baseline_brier_score": 0.50 if not baseline_correct else 0.10,
        "data_quality": {"publication_data_quality_score": quality},
        "league_id": league_id,
        "season": 2026,
        "p_max": confidence_score / 100,
        "gap": confidence_score / 200,
    }


def _ou_record(
    confidence_score: float,
    correct: bool,
    *,
    quality: float,
    market_correct: bool,
    profit: float,
) -> dict:
    return {
        "confidence_score": confidence_score,
        "correct": correct,
        "log_loss": 0.25 if correct else 1.30,
        "brier_score": 0.12 if correct else 0.70,
        "baseline_correct": market_correct,
        "baseline_log_loss": 0.85 if not market_correct else 0.30,
        "baseline_brier_score": 0.45 if not market_correct else 0.12,
        "data_quality": {"publication_data_quality_score": quality},
        "league_id": -25,
        "season": 2026,
        "edge_abs": confidence_score / 500,
        "stake": 1.0,
        "profit": profit,
    }
