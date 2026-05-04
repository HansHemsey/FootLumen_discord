from __future__ import annotations

import pytest

from football_predictor.reference.loaders import (
    load_api_football_reference,
    load_players_cache,
    load_players_reference,
)
from football_predictor.reference.players_cache import summarize_players_cache
from football_predictor.utils.exceptions import ReferenceLookupError, ReferenceValidationError


def test_reference_loads_competitions_and_validates_ids(
    reference_path, players_reference_path
) -> None:
    reference = load_api_football_reference(reference_path)
    players = load_players_reference(players_reference_path)

    first_league = reference.leagues()[0]
    league = reference.find_league_by_id(first_league.league_id, first_league.season)
    first_team_record = league.raw["teams"][0]
    team = reference.find_team_by_id(first_team_record["team_id"], league.league_id)
    fixture = reference.find_fixture_by_id(league.raw["fixtures"][0]["fixture_id"])
    bet = reference.find_bet_by_name("Match Winner")
    bookmaker = reference.all_bookmakers()[0]
    bookmaker_by_name = reference.find_bookmaker_by_name(bookmaker.name)
    squad = players.find_players_by_team(team.team_id)
    player = players.find_player_by_id(squad[0].player_id)

    assert league.name
    assert reference.find_league_by_key(league.key or "").league_id == league.league_id
    assert reference.counts()["teams"] == 144
    assert players.counts()["teams"] == 144
    assert len(reference.all_teams()) == 144
    assert len(reference.all_fixtures()) == 1824
    assert len(reference.all_bets()) == reference.counts()["bets"]
    assert reference.counts()["bets"] > 0
    assert team.name == first_team_record["name"]
    assert fixture.league_id == league.league_id
    assert bet.bet_id > 0
    assert bookmaker_by_name.bookmaker_id == bookmaker.bookmaker_id
    assert player.team_id == team.team_id


def test_reference_raises_for_unknown_synthetic_id(reference_path) -> None:
    reference = load_api_football_reference(reference_path)
    synthetic_unknown_fixture_id = -1

    with pytest.raises(ReferenceLookupError):
        reference.find_fixture_by_id(synthetic_unknown_fixture_id)


def test_players_cache_is_loadable_as_technical_cache(players_cache_path) -> None:
    cache = load_players_cache(players_cache_path)
    summary = summarize_players_cache(players_cache_path)

    assert "teams" in cache
    assert summary.teams == 144
    assert summary.keys > 0


def test_reference_loader_rejects_missing_required_sections(tmp_path) -> None:
    invalid_reference = tmp_path / "invalid_reference.json"
    invalid_reference.write_text("{}", encoding="utf-8")

    with pytest.raises(ReferenceValidationError):
        load_api_football_reference(invalid_reference)
