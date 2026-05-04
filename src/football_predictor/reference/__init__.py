"""Local API-Football reference loaders and lookups."""

from football_predictor.reference.exceptions import ReferenceLookupError, ReferenceValidationError
from football_predictor.reference.loaders import (
    load_api_football_reference,
    load_players_cache,
    load_players_reference,
)
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference
from football_predictor.reference.players_cache import PlayersCacheSummary, summarize_players_cache
from football_predictor.reference.schemas import (
    BetRef,
    BookmakerRef,
    FixtureRef,
    LeagueRef,
    PlayerRef,
    TeamRef,
)

__all__ = [
    "ApiFootballReference",
    "BetRef",
    "BookmakerRef",
    "FixtureRef",
    "LeagueRef",
    "PlayerRef",
    "PlayersCacheSummary",
    "PlayersReference",
    "ReferenceLookupError",
    "ReferenceValidationError",
    "TeamRef",
    "load_api_football_reference",
    "load_players_cache",
    "load_players_reference",
    "summarize_players_cache",
]
