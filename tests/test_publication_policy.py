from football_predictor.prediction.publication_policy import (
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
