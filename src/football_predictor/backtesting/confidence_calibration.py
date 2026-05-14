"""Calibration helpers for publishable confidence thresholds."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import Any, Literal

from football_predictor.prediction.publication_policy import (
    DEFAULT_MIN_DATA_QUALITY_SCORE,
    evaluate_publication,
    publication_decision_payload,
)

JsonDict = dict[str, Any]
ModelFamily = Literal["v3_1x2", "ou25"]

THRESHOLD_VERSION = "confidence_thresholds_v1"
DEFAULT_HIGH_THRESHOLD = 65.0
DEFAULT_VERY_HIGH_THRESHOLD = 85.0
PUBLISHABLE_LABELS = ("High", "Very High")
LABELS = ("Very High", "High", "Medium", "Low", "Uncertain")


@dataclass(frozen=True)
class ConfidenceThresholdConfig:
    """Configuration for validation-only confidence threshold calibration."""

    model_family: ModelFamily
    min_data_quality_score: float = DEFAULT_MIN_DATA_QUALITY_SCORE
    high_candidates: tuple[float, ...] = (45, 50, 55, 60, 65, 70, 75, 80)
    very_high_candidates: tuple[float, ...] = (70, 75, 80, 85, 90, 95)
    min_label_rows: int = 1
    min_published_rows: int = 1
    min_league_validation_rows: int = 200
    min_league_publishable_rows: int = 40
    max_ou_test_roi_drawdown: float = -0.05


def build_confidence_threshold_artifact(
    *,
    validation_records: list[JsonDict],
    test_records: list[JsonDict],
    config: ConfidenceThresholdConfig,
    periods: Mapping[str, Any] | None = None,
) -> JsonDict:
    """Learn thresholds from validation records and evaluate them on test records."""
    thresholds, validation_selection = _select_thresholds(validation_records, config)
    validation_report = evaluate_thresholds(validation_records, thresholds, config=config)
    test_report = evaluate_thresholds(test_records, thresholds, config=config)
    league_overrides = _league_overrides(validation_records, test_records, config, thresholds)
    approval = _approval_checks(
        validation_report=validation_report,
        test_report=test_report,
        model_family=config.model_family,
        config=config,
    )
    return {
        "threshold_version": THRESHOLD_VERSION,
        "model_family": config.model_family,
        "min_data_quality_score": config.min_data_quality_score,
        "thresholds": {
            "global": thresholds,
            "league_overrides": league_overrides,
        },
        "selection": validation_selection,
        "periods": dict(periods or {}),
        "metrics": {
            "validation": validation_report,
            "test": test_report,
        },
        "approval_checks": approval["checks"],
        "production_approved": approval["approved"],
        "config": asdict(config),
    }


def evaluate_thresholds(
    records: list[JsonDict],
    thresholds: Mapping[str, float],
    *,
    config: ConfidenceThresholdConfig,
) -> JsonDict:
    """Return internal, label and published-only metrics for a threshold pair."""
    labeled = [_record_with_decision(record, thresholds, config) for record in records]
    label_groups = {
        label: [record for record in labeled if record["calibrated_label"] == label]
        for label in LABELS
    }
    eligible_high = [
        record
        for record in labeled
        if record["calibrated_label"] == "High" and record["publication_allowed"]
    ]
    eligible_very_high = [
        record
        for record in labeled
        if record["calibrated_label"] == "Very High" and record["publication_allowed"]
    ]
    published_only = eligible_high + eligible_very_high
    return {
        "thresholds": dict(thresholds),
        "internal_all": _metrics(labeled),
        "baseline_internal_all": _baseline_metrics(labeled),
        "labels": {label: _metrics(rows) for label, rows in label_groups.items()},
        "eligible_high": _metrics(eligible_high),
        "eligible_very_high": _metrics(eligible_very_high),
        "published_only": _metrics(published_only),
        "baseline_on_published": _baseline_metrics(published_only),
        "by_league": _group_metrics(labeled, group_key="league_id"),
        "by_season": _group_metrics(labeled, group_key="season"),
        "by_data_quality_bin": _group_metrics(labeled, group_key="data_quality_bin"),
    }


def apply_publication_policy_records(
    records: list[JsonDict],
    thresholds: Mapping[str, float],
    *,
    config: ConfidenceThresholdConfig,
) -> list[JsonDict]:
    """Return records enriched with calibrated label and production publication policy."""
    return [_record_with_decision(record, thresholds, config) for record in records]


def confidence_label_for_score(
    score: float | int | None,
    thresholds: Mapping[str, float],
) -> str:
    """Apply calibrated publishable labels while preserving lower score buckets."""
    if score is None:
        return "Uncertain"
    value = float(score)
    if value >= float(thresholds["very_high"]):
        return "Very High"
    if value >= float(thresholds["high"]):
        return "High"
    if value >= 45:
        return "Medium"
    if value >= 20:
        return "Low"
    return "Uncertain"


def is_production_approved_artifact(
    payload: Mapping[str, Any] | None,
    *,
    model_family: ModelFamily | None = None,
) -> bool:
    """Return True only for a complete, explicitly approved threshold artifact."""
    if not isinstance(payload, Mapping):
        return False
    if payload.get("threshold_version") != THRESHOLD_VERSION:
        return False
    if model_family is not None and payload.get("model_family") != model_family:
        return False
    thresholds = payload.get("thresholds")
    if not isinstance(thresholds, Mapping):
        return False
    global_thresholds = thresholds.get("global")
    if not isinstance(global_thresholds, Mapping):
        return False
    high = _optional_float(global_thresholds.get("high"))
    very_high = _optional_float(global_thresholds.get("very_high"))
    if high is None or very_high is None or high >= very_high:
        return False
    return payload.get("production_approved") is True


def _select_thresholds(
    validation_records: list[JsonDict],
    config: ConfidenceThresholdConfig,
) -> tuple[JsonDict, JsonDict]:
    best: tuple[tuple[Any, ...], JsonDict, JsonDict] | None = None
    for high in config.high_candidates:
        for very_high in config.very_high_candidates:
            if high >= very_high:
                continue
            thresholds = {"high": float(high), "very_high": float(very_high)}
            report = evaluate_thresholds(validation_records, thresholds, config=config)
            checks = _validation_candidate_checks(report, config.model_family, config)
            published = report["published_only"]
            baseline = report["baseline_on_published"]
            accuracy_delta = _delta(
                published.get("accuracy"),
                baseline.get("accuracy"),
            )
            loss_delta = _delta(published.get("log_loss"), baseline.get("log_loss"))
            sort_key = (
                checks["passed"],
                _none_safe(accuracy_delta),
                -_none_safe(loss_delta),
                int(published.get("row_count") or 0),
                -float(high),
                -float(very_high),
            )
            if best is None or sort_key > best[0]:
                best = (sort_key, thresholds, checks)

    if best is None:
        thresholds = {
            "high": DEFAULT_HIGH_THRESHOLD,
            "very_high": DEFAULT_VERY_HIGH_THRESHOLD,
        }
        return thresholds, {
            "source_split": "validation",
            "passed": False,
            "reason": "no_candidate_thresholds",
        }
    _sort_key, thresholds, checks = best
    return thresholds, {"source_split": "validation", **checks}


def _validation_candidate_checks(
    report: JsonDict,
    model_family: ModelFamily,
    config: ConfidenceThresholdConfig,
) -> JsonDict:
    published = report["published_only"]
    high = report["eligible_high"]
    very_high = report["eligible_very_high"]
    baseline = report["baseline_on_published"]
    has_volume = (
        int(published.get("row_count") or 0) >= config.min_published_rows
        and int(high.get("row_count") or 0) >= config.min_label_rows
        and int(very_high.get("row_count") or 0) >= config.min_label_rows
    )
    monotonic = _monotonic_labels(high, very_high, model_family=model_family)
    if model_family == "v3_1x2":
        beats_baseline = _beats_accuracy_or_loss(published, baseline)
    else:
        beats_baseline = _beats_loss_or_brier(published, baseline)
        beats_baseline = beats_baseline and _metric_at_least(published.get("roi"), 0.0)
    passed = has_volume and monotonic and beats_baseline
    return {
        "passed": passed,
        "has_volume": has_volume,
        "monotonic_labels": monotonic,
        "beats_baseline": beats_baseline,
    }


def _approval_checks(
    *,
    validation_report: JsonDict,
    test_report: JsonDict,
    model_family: ModelFamily,
    config: ConfidenceThresholdConfig,
) -> JsonDict:
    validation_checks = _validation_candidate_checks(validation_report, model_family, config)
    published = test_report["published_only"]
    internal = test_report["internal_all"]
    baseline = test_report["baseline_on_published"]
    high = test_report["eligible_high"]
    very_high = test_report["eligible_very_high"]
    checks: JsonDict = {
        "validation_passed": validation_checks,
        "published_volume": {
            "passed": int(published.get("row_count") or 0) >= config.min_published_rows,
            "row_count": published.get("row_count"),
            "min_rows": config.min_published_rows,
        },
        "label_volume": {
            "passed": (
                int(high.get("row_count") or 0) >= config.min_label_rows
                and int(very_high.get("row_count") or 0) >= config.min_label_rows
            ),
            "high_rows": high.get("row_count"),
            "very_high_rows": very_high.get("row_count"),
            "min_rows": config.min_label_rows,
        },
        "monotonic_labels": {
            "passed": _monotonic_labels(high, very_high, model_family=model_family),
        },
    }
    if model_family == "v3_1x2":
        checks.update(
            {
                "published_accuracy_gt_internal": {
                    "passed": _metric_gt(
                        published.get("accuracy"),
                        internal.get("accuracy"),
                    ),
                    "published_accuracy": published.get("accuracy"),
                    "internal_accuracy": internal.get("accuracy"),
                },
                "published_log_loss_vs_baseline": {
                    "passed": _metric_lte(
                        published.get("log_loss"),
                        baseline.get("log_loss"),
                    ),
                    "published_log_loss": published.get("log_loss"),
                    "baseline_log_loss": baseline.get("log_loss"),
                },
                "published_brier_vs_baseline": {
                    "passed": _metric_lte(
                        published.get("brier_score"),
                        baseline.get("brier_score"),
                    ),
                    "published_brier": published.get("brier_score"),
                    "baseline_brier": baseline.get("brier_score"),
                },
                "league_no_regression": _league_no_regression(test_report),
            }
        )
    else:
        checks.update(
            {
                "published_log_loss_vs_market": {
                    "passed": _metric_lte(
                        published.get("log_loss"),
                        baseline.get("log_loss"),
                    ),
                    "published_log_loss": published.get("log_loss"),
                    "market_log_loss": baseline.get("log_loss"),
                },
                "published_brier_vs_market": {
                    "passed": _metric_lte(
                        published.get("brier_score"),
                        baseline.get("brier_score"),
                    ),
                    "published_brier": published.get("brier_score"),
                    "market_brier": baseline.get("brier_score"),
                },
                "validation_roi_non_negative": {
                    "passed": _metric_at_least(
                        validation_report["published_only"].get("roi"),
                        0.0,
                    ),
                    "roi": validation_report["published_only"].get("roi"),
                },
                "test_roi_not_catastrophic": {
                    "passed": _metric_at_least(
                        published.get("roi"),
                        config.max_ou_test_roi_drawdown,
                    ),
                    "roi": published.get("roi"),
                    "min_roi": config.max_ou_test_roi_drawdown,
                },
            }
        )
    approved = all(
        _passed(payload)
        for payload in checks.values()
    )
    return {"approved": approved, "checks": checks}


def _league_overrides(
    validation_records: list[JsonDict],
    test_records: list[JsonDict],
    config: ConfidenceThresholdConfig,
    fallback_thresholds: Mapping[str, float],
) -> JsonDict:
    output: JsonDict = {}
    league_ids = sorted({
        str(record.get("league_id"))
        for record in validation_records
        if record.get("league_id") is not None
    })
    for league_id in league_ids:
        validation_subset = [
            record for record in validation_records if str(record.get("league_id")) == league_id
        ]
        if len(validation_subset) < config.min_league_validation_rows:
            output[league_id] = {
                "status": "fallback_global",
                "reason": "insufficient_validation_rows",
                "validation_rows": len(validation_subset),
                "thresholds": dict(fallback_thresholds),
            }
            continue
        thresholds, selection = _select_thresholds(validation_subset, config)
        test_subset = [
            record for record in test_records if str(record.get("league_id")) == league_id
        ]
        test_report = evaluate_thresholds(test_subset, thresholds, config=config)
        if int(test_report["published_only"].get("row_count") or 0) < (
            config.min_league_publishable_rows
        ):
            output[league_id] = {
                "status": "fallback_global",
                "reason": "insufficient_publishable_rows",
                "validation_rows": len(validation_subset),
                "published_rows": test_report["published_only"].get("row_count"),
                "thresholds": dict(fallback_thresholds),
            }
            continue
        output[league_id] = {
            "status": "override",
            "thresholds": thresholds,
            "selection": selection,
            "test": {
                "published_only": test_report["published_only"],
                "baseline_on_published": test_report["baseline_on_published"],
            },
        }
    return output


def _record_with_decision(
    record: JsonDict,
    thresholds: Mapping[str, float],
    config: ConfidenceThresholdConfig,
) -> JsonDict:
    score = _optional_float(record.get("confidence_score"))
    label = confidence_label_for_score(score, thresholds)
    data_quality = record.get("data_quality")
    if not isinstance(data_quality, Mapping):
        data_quality = {}
    decision = evaluate_publication(
        label,
        data_quality,
        min_data_quality_score=config.min_data_quality_score,
    )
    enriched = dict(record)
    enriched["calibrated_label"] = label
    enriched["publication_decision"] = publication_decision_payload(decision)
    enriched["publication_allowed"] = decision.allowed
    enriched["data_quality_score"] = decision.data_quality_score
    enriched["data_quality_bin"] = _data_quality_bin(decision.data_quality_score)
    return enriched


def _metrics(records: list[JsonDict]) -> JsonDict:
    if not records:
        return {
            "row_count": 0,
            "accuracy": None,
            "win_rate": None,
            "log_loss": None,
            "brier_score": None,
            "roi": None,
            "avg_confidence_score": None,
            "avg_data_quality_score": None,
            "avg_p_max": None,
            "avg_gap": None,
            "avg_edge_abs": None,
        }
    correct_values = [1.0 if record.get("correct") else 0.0 for record in records]
    roi_payload = _roi(records)
    return {
        "row_count": len(records),
        "accuracy": _mean(correct_values),
        "win_rate": _mean(correct_values),
        "log_loss": _mean_numeric(record.get("log_loss") for record in records),
        "brier_score": _mean_numeric(record.get("brier_score") for record in records),
        "roi": roi_payload["roi"],
        "total_staked": roi_payload["total_staked"],
        "net_profit": roi_payload["net_profit"],
        "avg_confidence_score": _mean_numeric(
            record.get("confidence_score") for record in records
        ),
        "avg_data_quality_score": _mean_numeric(
            record.get("data_quality_score") for record in records
        ),
        "avg_p_max": _mean_numeric(record.get("p_max") for record in records),
        "avg_gap": _mean_numeric(record.get("gap") for record in records),
        "avg_edge_abs": _mean_numeric(record.get("edge_abs") for record in records),
    }


def _baseline_metrics(records: list[JsonDict]) -> JsonDict:
    if not records:
        return {
            "row_count": 0,
            "accuracy": None,
            "log_loss": None,
            "brier_score": None,
        }
    correct = [
        1.0 if record.get("baseline_correct") else 0.0
        for record in records
        if record.get("baseline_correct") is not None
    ]
    return {
        "row_count": len(records),
        "accuracy": _mean(correct),
        "log_loss": _mean_numeric(record.get("baseline_log_loss") for record in records),
        "brier_score": _mean_numeric(record.get("baseline_brier_score") for record in records),
    }


def _group_metrics(records: list[JsonDict], *, group_key: str) -> JsonDict:
    groups: dict[str, list[JsonDict]] = {}
    for record in records:
        value = record.get(group_key)
        if value is None:
            continue
        groups.setdefault(str(value), []).append(record)
    return {
        group: {
            "row_count": len(rows),
            "internal_all": _metrics(rows),
            "published_only": _metrics(
                [record for record in rows if record.get("publication_allowed")]
            ),
            "baseline_on_published": _baseline_metrics(
                [record for record in rows if record.get("publication_allowed")]
            ),
        }
        for group, rows in sorted(groups.items())
    }


def _league_no_regression(test_report: JsonDict) -> JsonDict:
    regressions: list[JsonDict] = []
    for league_id, payload in test_report.get("by_league", {}).items():
        row_count = int(payload.get("row_count") or 0)
        if row_count < 100:
            continue
        published = payload.get("published_only", {})
        baseline = payload.get("baseline_on_published", {})
        delta = _delta(published.get("log_loss"), baseline.get("log_loss"))
        if delta is not None and delta > 0.005:
            regressions.append(
                {
                    "league_id": league_id,
                    "row_count": row_count,
                    "log_loss_delta": delta,
                }
            )
    return {
        "passed": not regressions,
        "regressions": regressions,
    }


def _roi(records: list[JsonDict]) -> JsonDict:
    total_staked = 0.0
    net_profit = 0.0
    for record in records:
        stake = _optional_float(record.get("stake"))
        profit = _optional_float(record.get("profit"))
        if stake is None or profit is None:
            continue
        total_staked += stake
        net_profit += profit
    return {
        "roi": net_profit / total_staked if total_staked > 0 else None,
        "total_staked": total_staked,
        "net_profit": net_profit,
    }


def _monotonic_labels(
    high: Mapping[str, Any],
    very_high: Mapping[str, Any],
    *,
    model_family: ModelFamily,
) -> bool:
    high_value = _optional_float(high.get("win_rate" if model_family == "ou25" else "accuracy"))
    very_high_value = _optional_float(
        very_high.get("win_rate" if model_family == "ou25" else "accuracy")
    )
    if high_value is None or very_high_value is None:
        return False
    if very_high_value >= high_value:
        return True
    if model_family == "ou25":
        high_edge = _optional_float(high.get("avg_edge_abs"))
        very_high_edge = _optional_float(very_high.get("avg_edge_abs"))
        return (
            high_edge is not None
            and very_high_edge is not None
            and very_high_edge > high_edge
        )
    return False


def _beats_accuracy_or_loss(metrics: Mapping[str, Any], baseline: Mapping[str, Any]) -> bool:
    return _metric_at_least(metrics.get("accuracy"), baseline.get("accuracy")) or _metric_lte(
        metrics.get("log_loss"),
        baseline.get("log_loss"),
    )


def _beats_loss_or_brier(metrics: Mapping[str, Any], baseline: Mapping[str, Any]) -> bool:
    return _metric_lte(metrics.get("log_loss"), baseline.get("log_loss")) or _metric_lte(
        metrics.get("brier_score"),
        baseline.get("brier_score"),
    )


def _metric_gt(left: Any, right: Any) -> bool:
    left_value = _optional_float(left)
    right_value = _optional_float(right)
    return left_value is not None and right_value is not None and left_value > right_value


def _metric_at_least(left: Any, right: Any) -> bool:
    left_value = _optional_float(left)
    right_value = _optional_float(right)
    return left_value is not None and right_value is not None and left_value >= right_value


def _metric_lte(left: Any, right: Any) -> bool:
    left_value = _optional_float(left)
    right_value = _optional_float(right)
    return left_value is not None and right_value is not None and left_value <= right_value


def _passed(payload: Any) -> bool:
    if not isinstance(payload, Mapping):
        return False
    if "passed" in payload:
        return payload.get("passed") is True
    return all(_passed(value) for value in payload.values() if isinstance(value, Mapping))


def _data_quality_bin(score: float | None) -> str:
    if score is None:
        return "missing"
    if score < 25:
        return "0_25"
    if score < 50:
        return "25_50"
    if score < 75:
        return "50_75"
    return "75_100"


def _mean(values: Iterable[float]) -> float | None:
    items = [float(value) for value in values]
    if not items:
        return None
    return sum(items) / len(items)


def _mean_numeric(values: Iterable[Any]) -> float | None:
    items = [
        value
        for value in (_optional_float(item) for item in values)
        if value is not None
    ]
    return _mean(items)


def _optional_float(value: Any) -> float | None:
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(resolved):
        return None
    return resolved


def _delta(left: Any, right: Any) -> float | None:
    left_value = _optional_float(left)
    right_value = _optional_float(right)
    if left_value is None or right_value is None:
        return None
    return left_value - right_value


def _none_safe(value: float | None) -> float:
    return float("-inf") if value is None else float(value)
