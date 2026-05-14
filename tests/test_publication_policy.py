from football_predictor.prediction.publication_policy import (
    CONFIDENCE_SKIP_REASON,
    DATA_QUALITY_BLOCKER_REASON,
    DATA_QUALITY_MISSING_REASON,
    DATA_QUALITY_SKIP_REASON,
    evaluate_publication,
    extract_data_quality_score,
    is_publishable_confidence,
    normalize_confidence_label,
)


def test_publishable_confidence_accepts_high_and_very_high_forms() -> None:
    assert is_publishable_confidence("High")
    assert is_publishable_confidence("HIGH")
    assert is_publishable_confidence("Very High")
    assert is_publishable_confidence("VERY_HIGH")
    assert is_publishable_confidence("VERY HIGH")
    assert normalize_confidence_label("very_high") == "Very High"


def test_publishable_confidence_rejects_medium_low_uncertain() -> None:
    assert not is_publishable_confidence("Medium")
    assert not is_publishable_confidence("LOW")
    assert not is_publishable_confidence("Uncertain")
    assert not is_publishable_confidence(None)


def test_evaluate_publication_allows_high_with_minimum_quality() -> None:
    decision = evaluate_publication("High", {"overall_data_quality_score": 60})

    assert decision.allowed is True
    assert decision.reason is None
    assert decision.confidence_label == "High"
    assert decision.data_quality_score == 60


def test_evaluate_publication_allows_very_high_with_minimum_quality() -> None:
    decision = evaluate_publication("VERY_HIGH", {"overall_data_quality_score": 60})

    assert decision.allowed is True
    assert decision.confidence_label == "Very High"


def test_evaluate_publication_rejects_non_publishable_confidence_even_with_quality() -> None:
    decision = evaluate_publication("Medium", {"overall_data_quality_score": 90})

    assert decision.allowed is False
    assert decision.reason == CONFIDENCE_SKIP_REASON
    assert decision.data_quality_score == 90


def test_evaluate_publication_rejects_missing_quality_score() -> None:
    decision = evaluate_publication("High", {})

    assert decision.allowed is False
    assert decision.reason == DATA_QUALITY_MISSING_REASON


def test_evaluate_publication_rejects_quality_below_threshold() -> None:
    decision = evaluate_publication("High", {"overall_data_quality_score": 59.9})

    assert decision.allowed is False
    assert decision.reason == DATA_QUALITY_SKIP_REASON
    assert decision.data_quality_score == 59.9


def test_evaluate_publication_rejects_quality_blockers_even_with_high_score() -> None:
    decision = evaluate_publication(
        "High",
        {
            "publication_data_quality_score": 95,
            "publication_blockers": ["odds_1x2_future_snapshot"],
        },
    )

    assert decision.allowed is False
    assert decision.reason == DATA_QUALITY_BLOCKER_REASON
    assert decision.data_quality_blockers == ("odds_1x2_future_snapshot",)


def test_extract_data_quality_score_supports_publication_keys() -> None:
    assert extract_data_quality_score({"publication_data_quality_score": 61}) == 61
    assert extract_data_quality_score({"overall_data_quality_score": 62}) == 62
    assert extract_data_quality_score({"data_quality_score": 63}) == 63
    assert extract_data_quality_score({"ou_data_quality_score": 64}) == 64


def test_extract_data_quality_score_skips_invalid_priority_key() -> None:
    assert (
        extract_data_quality_score(
            {
                "publication_data_quality_score": "not-a-score",
                "overall_data_quality_score": 66,
            }
        )
        == 66
    )
