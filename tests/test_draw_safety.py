from football_predictor.prediction.draw_safety import (
    DRAW_PROBABILITY_UNDERESTIMATED,
    DRAW_RISK_PROBABILITY_CONTRADICTION,
    DRAW_SAFETY_SEVERE_SKIP_REASON,
    DRAW_SAFETY_SKIP_REASON,
    DRAW_SAFETY_UNAVAILABLE,
    WORLDCUP_BALANCED_MATCH_DRAW_CAP,
    DrawSafetyConfig,
    DrawSafetySignals,
    evaluate_draw_safety,
)


def test_draw_safety_warns_and_caps_high_confidence_when_draw_risk_is_high() -> None:
    decision = evaluate_draw_safety(
        DrawSafetySignals(
            model_family="v3",
            p_home=0.70,
            p_draw=0.19,
            p_away=0.11,
            confidence_label="High",
            confidence_score=78.0,
            draw_risk_probability=0.34,
        )
    )

    assert DRAW_PROBABILITY_UNDERESTIMATED in decision.warnings
    assert decision.severity == "standard"
    assert decision.effective_confidence_label == "Medium"
    assert decision.effective_confidence_score == 67.0
    assert decision.public_blocked is True
    assert decision.skip_reason == DRAW_SAFETY_SKIP_REASON
    assert decision.signals["p_draw"] == 0.19


def test_draw_safety_severe_conflict_is_staff_only() -> None:
    decision = evaluate_draw_safety(
        DrawSafetySignals(
            model_family="v3",
            p_home=0.76,
            p_draw=0.12,
            p_away=0.12,
            confidence_label="Very High",
            confidence_score=91.0,
            draw_risk_probability=0.42,
        )
    )

    assert DRAW_RISK_PROBABILITY_CONTRADICTION in decision.warnings
    assert decision.severity == "severe"
    assert decision.effective_confidence_label == "Low"
    assert decision.effective_confidence_score == 54.0
    assert decision.public_blocked is True
    assert decision.skip_reason == DRAW_SAFETY_SEVERE_SKIP_REASON


def test_draw_safety_disabled_keeps_confidence_unchanged() -> None:
    decision = evaluate_draw_safety(
        DrawSafetySignals(
            model_family="v3",
            p_home=0.70,
            p_draw=0.12,
            p_away=0.18,
            confidence_label="High",
            confidence_score=80.0,
            draw_risk_probability=0.50,
        ),
        config=DrawSafetyConfig(enabled=False),
    )

    assert decision.enabled is False
    assert decision.warnings == []
    assert decision.effective_confidence_label == "High"
    assert decision.effective_confidence_score == 80.0
    assert decision.public_blocked is False


def test_worldcup_balanced_match_without_draw_signal_caps_confidence() -> None:
    decision = evaluate_draw_safety(
        DrawSafetySignals(
            model_family="worldcup_1x2",
            p_home=0.43,
            p_draw=0.18,
            p_away=0.39,
            confidence_label="High",
            confidence_score=74.0,
            is_worldcup=True,
        )
    )

    assert DRAW_SAFETY_UNAVAILABLE in decision.warnings
    assert WORLDCUP_BALANCED_MATCH_DRAW_CAP in decision.warnings
    assert decision.effective_confidence_label == "Medium"
    assert decision.public_blocked is True

