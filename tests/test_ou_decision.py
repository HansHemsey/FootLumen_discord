from __future__ import annotations

from football_predictor.ou_model.prediction.ou_decision import decide_ou_prediction
from football_predictor.ou_model.prediction.ou_publication_policy import (
    evaluate_ou_publication,
)


def test_over_forecast_but_under_is_value() -> None:
    decision = decide_ou_prediction(
        p_over=0.54,
        p_under=0.46,
        market_p_over=0.63,
        market_p_under=0.37,
        odd_over=1.50,
        odd_under=2.45,
        data_quality_json={"overall_data_quality_score": 90, "ou_market_bookmaker_count": 6},
    )

    assert decision.forecast_side == "OVER"
    assert decision.forecast_probability == 0.54
    assert decision.value_side == "UNDER"
    assert decision.value_edge is not None and decision.value_edge > 0
    assert decision.value_ev is not None and decision.value_ev > 0
    assert decision.no_bet_reason is None
    assert decision.confidence_score_v2 > 0


def test_over_forecast_and_over_is_value() -> None:
    decision = decide_ou_prediction(
        p_over=0.64,
        p_under=0.36,
        market_p_over=0.56,
        market_p_under=0.44,
        odd_over=1.75,
        odd_under=2.10,
        data_quality_json={"overall_data_quality_score": 80, "ou_market_bookmaker_count": 4},
    )

    assert decision.forecast_side == "OVER"
    assert decision.value_side == "OVER"
    assert decision.value_edge == decision.edge_over
    assert decision.value_ev == decision.ev_over
    assert decision.confidence_label_v2 in {"High", "Very High"}
    assert decision.publication_decision == "public"
    assert decision.ou_decision_version == "ou_v2"
    assert decision.ou_publication_policy_version.startswith("ou_publication_policy_v")


def test_value_pick_with_low_data_quality_goes_to_staff() -> None:
    decision = decide_ou_prediction(
        p_over=0.64,
        p_under=0.36,
        market_p_over=0.56,
        market_p_under=0.44,
        odd_over=1.75,
        odd_under=2.10,
        data_quality_json={"overall_data_quality_score": 50, "ou_market_bookmaker_count": 4},
    )

    assert decision.value_side == "OVER"
    assert decision.publication_decision == "staff"
    assert decision.non_publication_reason == "data_quality_insufficient"


def test_value_pick_with_single_bookmaker_goes_to_staff() -> None:
    decision = decide_ou_prediction(
        p_over=0.64,
        p_under=0.36,
        market_p_over=0.56,
        market_p_under=0.44,
        odd_over=1.75,
        odd_under=2.10,
        data_quality_json={"overall_data_quality_score": 90, "ou_market_bookmaker_count": 1},
    )

    assert decision.value_side == "OVER"
    assert decision.publication_decision == "staff"
    assert decision.non_publication_reason == "bookmaker_count_insufficient"


def test_value_pick_with_missing_bookmaker_count_goes_to_staff() -> None:
    decision = decide_ou_prediction(
        p_over=0.64,
        p_under=0.36,
        market_p_over=0.56,
        market_p_under=0.44,
        odd_over=1.75,
        odd_under=2.10,
        data_quality_json={"overall_data_quality_score": 90},
    )

    assert decision.value_side == "OVER"
    assert decision.bookmaker_count == 0
    assert decision.publication_decision == "staff"
    assert decision.non_publication_reason == "bookmaker_count_insufficient"


def test_publication_policy_rejects_legacy_or_missing_ou_v2_marker() -> None:
    common = {
        "value_side": "OVER",
        "edge_pick": 0.08,
        "ev_pick": 0.15,
        "confidence_score_v2": 82.0,
        "data_quality_score": 88.0,
        "bookmaker_count": 4,
    }

    missing_version = evaluate_ou_publication(**common)
    legacy_version = evaluate_ou_publication(
        **common,
        ou_decision_version="ou_decision_v1",
    )
    v2_version = evaluate_ou_publication(
        **common,
        ou_decision_version="ou_v2",
    )

    assert missing_version.decision == "staff"
    assert missing_version.reason == "legacy_decision_version"
    assert legacy_version.decision == "staff"
    assert legacy_version.reason == "legacy_decision_version"
    assert v2_version.decision == "public"


def test_under_forecast_but_no_side_has_enough_ev() -> None:
    decision = decide_ou_prediction(
        p_over=0.43,
        p_under=0.57,
        market_p_over=0.45,
        market_p_under=0.55,
        odd_over=2.05,
        odd_under=1.75,
        data_quality_json={"overall_data_quality_score": 95, "ou_market_bookmaker_count": 5},
    )

    assert decision.forecast_side == "UNDER"
    assert decision.value_side is None
    assert decision.no_bet_reason == "ev_below_threshold"
    assert decision.publication_decision == "no_bet"
    assert decision.confidence_score_v2 == 0.0


def test_missing_market_means_no_bet() -> None:
    decision = decide_ou_prediction(
        p_over=0.70,
        p_under=0.30,
        market_p_over=None,
        market_p_under=None,
        odd_over=None,
        odd_under=None,
    )

    assert decision.forecast_side == "OVER"
    assert decision.value_side is None
    assert decision.no_bet_reason == "market_unavailable"
    assert decision.publication_decision == "no_bet"


def test_negative_edge_is_not_publishable_even_with_positive_ev() -> None:
    decision = decide_ou_prediction(
        p_over=0.52,
        p_under=0.48,
        market_p_over=0.60,
        market_p_under=0.40,
        odd_over=2.05,
        odd_under=1.80,
        data_quality_json={"overall_data_quality_score": 90, "ou_market_bookmaker_count": 6},
    )

    assert decision.forecast_side == "OVER"
    assert decision.ev_over is not None and decision.ev_over > 0
    assert decision.edge_over is not None and decision.edge_over < 0
    assert decision.value_side is None
    assert decision.no_bet_reason == "edge_below_threshold"


def test_forecast_side_is_not_published_when_forecast_ev_is_negative() -> None:
    decision = decide_ou_prediction(
        p_over=0.56,
        p_under=0.44,
        market_p_over=0.51,
        market_p_under=0.49,
        odd_over=1.70,
        odd_under=1.90,
        data_quality_json={"overall_data_quality_score": 90, "ou_market_bookmaker_count": 6},
    )

    assert decision.forecast_side == "OVER"
    assert decision.edge_over is not None and decision.edge_over > 0
    assert decision.ev_over is not None and decision.ev_over < 0
    assert decision.value_side is None
    assert decision.is_value_pick is False
    assert decision.publication_decision == "no_bet"


def test_confidence_uses_pick_edge_not_edge_over_by_default() -> None:
    under_value = decide_ou_prediction(
        p_over=0.54,
        p_under=0.46,
        market_p_over=0.63,
        market_p_under=0.37,
        odd_over=1.50,
        odd_under=2.45,
        data_quality_json={"overall_data_quality_score": 90, "ou_market_bookmaker_count": 6},
    )
    no_value = decide_ou_prediction(
        p_over=0.54,
        p_under=0.46,
        market_p_over=0.63,
        market_p_under=0.37,
        odd_over=1.50,
        odd_under=2.15,
        data_quality_json={"overall_data_quality_score": 90, "ou_market_bookmaker_count": 6},
    )

    assert under_value.value_side == "UNDER"
    assert under_value.edge_over is not None and under_value.edge_over < 0
    assert under_value.value_edge is not None and under_value.value_edge > 0
    assert under_value.confidence_score_v2 > 0
    assert no_value.value_side is None
    assert no_value.confidence_score_v2 == 0.0
