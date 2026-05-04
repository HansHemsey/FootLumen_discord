from __future__ import annotations

import pytest

from football_predictor.features.pseudo_xg import heuristic_pseudo_xg
from football_predictor.features.stat_parsing import parse_fixture_statistics, parse_stat_number


def test_heuristic_pseudo_xg_is_stable_and_uses_penalties() -> None:
    stats = {
        "shots_on_goal": 5,
        "shots_insidebox": 6,
        "shots_outsidebox": 4,
        "total_shots": 12,
    }

    pseudo_xg = heuristic_pseudo_xg(stats, penalties=1)

    assert pseudo_xg == pytest.approx(2.07)
    assert heuristic_pseudo_xg({}) is None


def test_parse_fixture_statistics_supports_api_football_labels_and_percentages() -> None:
    parsed = parse_fixture_statistics(
        [
            {"type": "Shots on Goal", "value": 5},
            {"type": "Shots off Goal", "value": "4"},
            {"type": "Shots insidebox", "value": 6},
            {"type": "Shots outsidebox", "value": 4},
            {"type": "Total Shots", "value": 12},
            {"type": "Blocked Shots", "value": 3},
            {"type": "Fouls", "value": 10},
            {"type": "Corner Kicks", "value": 4},
            {"type": "Offsides", "value": 2},
            {"type": "Ball Possession", "value": "55%"},
            {"type": "Yellow Cards", "value": 2},
            {"type": "Red Cards", "value": 1},
            {"type": "Goalkeeper Saves", "value": 3},
            {"type": "Total passes", "value": 500},
            {"type": "Passes accurate", "value": 430},
            {"type": "Passes %", "value": "86%"},
        ],
        penalties=0,
    )

    assert parsed["shots_on_goal"] == 5
    assert parsed["shots_off_goal"] == 4
    assert parsed["shots_insidebox"] == 6
    assert parsed["shots_outsidebox"] == 4
    assert parsed["total_shots"] == 12
    assert parsed["blocked_shots"] == 3
    assert parsed["fouls"] == 10
    assert parsed["corners"] == 4
    assert parsed["offsides"] == 2
    assert parsed["possession"] == 55
    assert parsed["yellow_cards"] == 2
    assert parsed["red_cards"] == 1
    assert parsed["cards"] == 3
    assert parsed["goalkeeper_saves"] == 3
    assert parsed["passes_total"] == 500
    assert parsed["passes_accurate"] == 430
    assert parsed["pass_accuracy"] == 86
    assert parsed["pseudo_xg"] == pytest.approx(1.31)


def test_parse_stat_number_handles_numbers_and_percent_strings() -> None:
    assert parse_stat_number("55%") == 55
    assert parse_stat_number("1,234") == 1234
    assert parse_stat_number(None) is None
