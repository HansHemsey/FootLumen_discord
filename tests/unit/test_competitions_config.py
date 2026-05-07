from __future__ import annotations

import json

import pytest

from football_predictor.config.competitions import load_competition_config
from football_predictor.reference.loaders import load_api_football_reference
from football_predictor.utils.exceptions import ReferenceLookupError, ReferenceValidationError


def test_competitions_yaml_resolves_against_reference(repo_root, reference_path) -> None:
    reference = load_api_football_reference(reference_path)

    config_path = repo_root / "config/competitions.example.yaml"

    competitions = load_competition_config(config_path, reference)

    assert len(competitions) == 6
    assert {competition.key for competition in competitions} >= {"ligue_1", "premier_league"}
    assert all(competition.league_id > 0 for competition in competitions)
    assert all(competition.season >= 2025 for competition in competitions)


def test_competitions_history_yaml_allows_historical_seasons(repo_root, reference_path) -> None:
    reference = load_api_football_reference(reference_path)
    config_path = repo_root / "config/competitions_history.yaml"

    competitions = load_competition_config(config_path, reference)

    assert len(competitions) == 20
    assert {competition.season for competition in competitions} == {2022, 2023, 2024, 2025}
    assert {competition.league_id for competition in competitions} == {39, 61, 78, 135, 140}
    assert "fifa_world_cup_2026" not in {competition.reference_key for competition in competitions}
    premier_league_2024 = next(
        competition for competition in competitions if competition.key == "premier_league_2024"
    )
    assert premier_league_2024.reference_key == "premier_league"
    assert premier_league_2024.league_id == 39
    assert premier_league_2024.season == 2024


def test_competitions_history_uses_reference_key_for_id_validation(
    tmp_path,
    reference_path,
) -> None:
    reference = load_api_football_reference(reference_path)
    config_path = tmp_path / "competitions_history.json"
    config_path.write_text(
        json.dumps(
            {
                "competitions": [
                    {
                        "key": "premier_league_2024",
                        "reference_key": "premier_league",
                        "league_id": 39,
                        "season": 2024,
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    competitions = load_competition_config(config_path, reference)

    assert competitions[0].key == "premier_league_2024"
    assert competitions[0].reference_key == "premier_league"
    assert competitions[0].season == 2024


def test_competitions_history_rejects_unknown_reference_key(tmp_path, reference_path) -> None:
    reference = load_api_football_reference(reference_path)
    config_path = tmp_path / "competitions_history.json"
    config_path.write_text(
        json.dumps(
            {
                "competitions": [
                    {
                        "key": "unknown_2024",
                        "reference_key": "unknown_competition",
                        "league_id": 39,
                        "season": 2024,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ReferenceLookupError):
        load_competition_config(config_path, reference)


def test_competitions_json_can_disable_entries(tmp_path, reference_path) -> None:
    reference = load_api_football_reference(reference_path)
    config_path = tmp_path / "competitions.json"
    config_path.write_text(
        json.dumps(
            {
                "competitions": [
                    {
                        "key": "ligue_1",
                        "league_id": 61,
                        "season": 2025,
                        "enabled": True,
                    },
                    {"key": "premier_league", "enabled": False},
                ]
            }
        ),
        encoding="utf-8",
    )

    competitions = load_competition_config(config_path, reference)

    assert len(competitions) == 1
    assert competitions[0].key == "ligue_1"
    assert competitions[0].league_id == 61


def test_competitions_config_rejects_unknown_synthetic_key(tmp_path, reference_path) -> None:
    reference = load_api_football_reference(reference_path)
    config_path = tmp_path / "competitions.json"
    config_path.write_text(
        json.dumps({"competitions": [{"key": "synthetic_unknown_competition"}]}),
        encoding="utf-8",
    )

    with pytest.raises(ReferenceLookupError):
        load_competition_config(config_path, reference)


def test_competitions_config_requires_key_or_id(tmp_path, reference_path) -> None:
    reference = load_api_football_reference(reference_path)
    config_path = tmp_path / "competitions.json"
    config_path.write_text(json.dumps({"competitions": [{"enabled": True}]}), encoding="utf-8")

    with pytest.raises(ReferenceValidationError):
        load_competition_config(config_path, reference)
