from __future__ import annotations

import pytest

from football_predictor.reference.loaders import load_api_football_reference, load_players_reference
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference
from football_predictor.utils.exceptions import ReferenceValidationError


def test_load_api_football_reference_sample(reference_sample_path) -> None:
    reference = load_api_football_reference(reference_sample_path)

    assert isinstance(reference, ApiFootballReference)
    assert reference.counts()["leagues"] == 1
    assert reference.counts()["teams"] == 2
    assert reference.counts()["fixtures"] == 1


def test_load_players_reference_sample(players_reference_sample_path) -> None:
    players = load_players_reference(players_reference_sample_path)

    assert isinstance(players, PlayersReference)
    assert players.counts()["teams"] == 1
    assert players.counts()["players"] == 2


def test_reference_loader_rejects_non_object_json(tmp_path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ReferenceValidationError):
        load_api_football_reference(path)
