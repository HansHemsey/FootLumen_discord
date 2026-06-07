"""Fixture DTOs for the FootLumen API."""

from __future__ import annotations

from typing import Any

from football_predictor.web_api.schemas.common import (
    FixtureSummary,
    TeamSummary,
    data_quality_score_from_json,
    paris_datetime,
    safe_datetime,
)


class FixtureSummaryDTO(FixtureSummary):
    """Public fixture summary. Keeps SQLAlchemy and raw payloads out of responses."""


def fixture_summary_from_model(
    fixture: Any,
    *,
    competition_key: str | None = None,
    has_1x2_prediction: bool = False,
    has_ou_prediction: bool = False,
    has_combo: bool = False,
    data_quality_score: float | None = None,
) -> FixtureSummaryDTO:
    inferred_competition_key = competition_key or _infer_competition_key(fixture)
    return FixtureSummaryDTO(
        fixture_id=int(fixture.fixture_id),
        competition_key=inferred_competition_key,
        league_id=getattr(fixture, "league_id", None),
        season=getattr(fixture, "season", None),
        round=getattr(fixture, "round", None),
        kickoff_at_utc=safe_datetime(getattr(fixture, "date", None)),
        kickoff_at_paris=paris_datetime(getattr(fixture, "date", None)),
        status_short=getattr(fixture, "status_short", None),
        status_long=getattr(fixture, "status_long", None) or getattr(fixture, "status", None),
        home_team=TeamSummary(
            team_id=getattr(fixture, "home_team_id", None),
            name=getattr(fixture, "home_team", None),
        ),
        away_team=TeamSummary(
            team_id=getattr(fixture, "away_team_id", None),
            name=getattr(fixture, "away_team", None),
        ),
        home_team_id=getattr(fixture, "home_team_id", None),
        away_team_id=getattr(fixture, "away_team_id", None),
        venue_name=getattr(fixture, "venue_name", None),
        venue_city=getattr(fixture, "venue_city", None),
        has_1x2_prediction=has_1x2_prediction,
        has_ou_prediction=has_ou_prediction,
        has_combo=has_combo,
        data_quality_score=data_quality_score
        if data_quality_score is not None
        else data_quality_score_from_json(getattr(fixture, "payload_json", None)),
    )


def _infer_competition_key(fixture: Any) -> str | None:
    if getattr(fixture, "league_id", None) == 1 and getattr(fixture, "season", None) == 2026:
        return "fifa_world_cup_2026"
    return None
