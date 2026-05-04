from __future__ import annotations

import pytest

from football_predictor.features.odds_features import (
    OddsQuote,
    consensus_probabilities,
    implied_probabilities_without_margin,
)


def test_decimal_odds_are_converted_without_margin() -> None:
    quote = OddsQuote(bookmaker_id=None, odd_home=2.0, odd_draw=4.0, odd_away=4.0)
    implied = implied_probabilities_without_margin(quote)

    assert implied.probabilities.p_home == pytest.approx(0.5)
    assert implied.probabilities.p_draw == pytest.approx(0.25)
    assert implied.probabilities.p_away == pytest.approx(0.25)
    assert implied.overround == pytest.approx(0.0)


def test_consensus_weights_lower_overround_more() -> None:
    quotes = [
        OddsQuote(bookmaker_id=None, odd_home=2.0, odd_draw=4.0, odd_away=4.0),
        OddsQuote(bookmaker_id=None, odd_home=1.8, odd_draw=3.5, odd_away=4.2),
    ]

    consensus = consensus_probabilities(quotes)

    assert consensus is not None
    assert consensus.bookmaker_count == 2
    assert sum(consensus.probabilities.as_dict().values()) == pytest.approx(1.0)
    assert consensus.dispersion >= 0
