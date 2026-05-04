from __future__ import annotations

import pytest

from football_predictor.reference.loaders import load_api_football_reference, load_players_reference
from football_predictor.utils.exceptions import ReferenceLookupError


def test_reference_lookups_return_verified_sample_ids(
    reference_sample_path,
    players_reference_sample_path,
) -> None:
    reference = load_api_football_reference(reference_sample_path)
    players = load_players_reference(players_reference_sample_path)

    league = reference.find_league_by_id(61)
    team = reference.find_team_by_name("Angers", league_id=league.league_id)
    fixture = reference.validate_fixture_reference(1387797)
    bookmaker = reference.find_bookmaker_by_id(1)
    bet = reference.find_bet_by_id(1)
    squad = players.find_players_by_team(team.team_id)
    player = players.find_player_by_id(455243)

    assert league.name == "Ligue 1"
    assert team.team_id == 77
    assert fixture.home_team_id == 77
    assert bookmaker.name == "10Bet"
    assert bet.name == "Match Winner"
    assert len(squad) == 2
    assert player.name == "A. Moussaoui"


def test_reference_lookups_raise_for_synthetic_unknown_ids(
    reference_sample_path,
    players_reference_sample_path,
) -> None:
    reference = load_api_football_reference(reference_sample_path)
    players = load_players_reference(players_reference_sample_path)

    with pytest.raises(ReferenceLookupError):
        reference.find_team_by_id(-999)
    with pytest.raises(ReferenceLookupError):
        reference.validate_fixture_reference(-999)
    with pytest.raises(ReferenceLookupError):
        players.find_player_by_id(-999)
