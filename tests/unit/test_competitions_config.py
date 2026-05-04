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
