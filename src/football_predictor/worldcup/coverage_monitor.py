"""World Cup 2026 API coverage and fixture quality monitoring."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.security.sanitize import sanitize_text, sanitize_value
from football_predictor.utils.time import ensure_aware_utc, utc_now
from football_predictor.worldcup.features import build_features_for_fixture
from football_predictor.worldcup.references import WorldCupReferenceBundle

JsonDict = dict[str, Any]
WORLD_CUP_COMPETITION_KEY = "fifa_world_cup_2026"
WORLD_CUP_LEAGUE_ID = 1
WORLD_CUP_SEASON = 2026
COVERAGE_ENDPOINTS = (
    "fixtures",
    "standings",
    "odds_1x2",
    "odds_ou",
    "predictions",
    "lineups",
    "injuries",
    "fixture_statistics",
    "events",
    "player_statistics",
)
LINEUPS_EXPECTED_WITHIN_MINUTES = 90


@dataclass(frozen=True)
class CoverageObservationDraft:
    competition_key: str
    league_id: int
    season: int
    endpoint: str
    requested_at: datetime
    status: str
    result_count: int
    useful_payload_flag: bool
    fixture_id: int | None = None
    team_id: int | None = None
    error_code: str | None = None
    warning: str | None = None

    def to_json_dict(self) -> JsonDict:
        payload = asdict(self)
        payload["requested_at"] = self.requested_at.isoformat()
        return sanitize_value(payload)


@dataclass(frozen=True)
class WorldCupFixtureQuality:
    fixture_id: int
    match_label: str
    kickoff_at: datetime | None
    status_short: str | None
    has_international_history: bool
    has_elo: bool
    has_fifa_rank: bool
    has_odds_1x2: bool
    has_odds_ou: bool
    has_api_prediction: bool
    has_lineups: bool
    lineups_expected: bool
    has_injuries: bool
    has_group_state: bool
    has_squad_strength: bool
    data_quality_score: float
    missing_sources: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_json_dict(self) -> JsonDict:
        payload = asdict(self)
        payload["kickoff_at"] = self.kickoff_at.isoformat() if self.kickoff_at else None
        payload["missing_sources"] = list(self.missing_sources)
        payload["warnings"] = list(self.warnings)
        return sanitize_value(payload)


@dataclass(frozen=True)
class WorldCupCoverageSummary:
    competition_key: str
    league_id: int
    season: int
    generated_at: datetime
    fixtures_total: int
    endpoint_coverage: JsonDict
    fixture_quality: tuple[WorldCupFixtureQuality, ...]
    observations: tuple[CoverageObservationDraft, ...] = field(default_factory=tuple)

    def to_json_dict(self) -> JsonDict:
        return sanitize_value(
            {
                "competition_key": self.competition_key,
                "league_id": self.league_id,
                "season": self.season,
                "generated_at": self.generated_at.isoformat(),
                "fixtures_total": self.fixtures_total,
                "endpoint_coverage": self.endpoint_coverage,
                "fixture_quality": [
                    fixture.to_json_dict() for fixture in self.fixture_quality
                ],
                "observations": [row.to_json_dict() for row in self.observations],
            }
        )


class WorldCupCoverageMonitor:
    """Inspect persisted World Cup data without making API calls."""

    def __init__(
        self,
        session: Session,
        *,
        competition_key: str = WORLD_CUP_COMPETITION_KEY,
        league_id: int = WORLD_CUP_LEAGUE_ID,
        season: int = WORLD_CUP_SEASON,
        bundle: WorldCupReferenceBundle | None = None,
    ) -> None:
        self.session = session
        self.competition_key = competition_key
        self.league_id = league_id
        self.season = season
        self.bundle = bundle

    def record_observation(
        self,
        *,
        endpoint: str,
        requested_at: datetime | None = None,
        result_count: int = 0,
        useful_payload_flag: bool | None = None,
        status: str | None = None,
        fixture_id: int | None = None,
        team_id: int | None = None,
        error_code: str | None = None,
        warning: str | None = None,
        write: bool = True,
    ) -> CoverageObservationDraft:
        useful = bool(result_count > 0) if useful_payload_flag is None else useful_payload_flag
        resolved_status = status or ("available" if useful else "missing")
        draft = CoverageObservationDraft(
            competition_key=self.competition_key,
            league_id=self.league_id,
            season=self.season,
            endpoint=endpoint,
            fixture_id=fixture_id,
            team_id=team_id,
            requested_at=ensure_aware_utc(requested_at or utc_now()),
            status=resolved_status,
            result_count=max(int(result_count), 0),
            useful_payload_flag=useful,
            error_code=error_code,
            warning=sanitize_text(warning) if warning else None,
        )
        if write:
            self.session.add(
                models.ApiCoverageObservation(
                    competition_key=draft.competition_key,
                    league_id=draft.league_id,
                    season=draft.season,
                    endpoint=draft.endpoint,
                    fixture_id=draft.fixture_id,
                    team_id=draft.team_id,
                    requested_at=draft.requested_at,
                    status=draft.status,
                    result_count=draft.result_count,
                    useful_payload_flag=draft.useful_payload_flag,
                    error_code=draft.error_code,
                    warning=draft.warning,
                )
            )
            self.session.flush()
        return draft

    def build_summary(
        self,
        *,
        now: datetime | None = None,
        write_observations: bool = False,
    ) -> WorldCupCoverageSummary:
        generated_at = ensure_aware_utc(now or utc_now())
        fixtures = self.worldcup_fixtures()
        observations = self._coverage_observations(
            fixtures,
            requested_at=generated_at,
            write=write_observations,
        )
        fixture_quality = tuple(
            self.fixture_quality_matrix(fixture, now=generated_at) for fixture in fixtures
        )
        return WorldCupCoverageSummary(
            competition_key=self.competition_key,
            league_id=self.league_id,
            season=self.season,
            generated_at=generated_at,
            fixtures_total=len(fixtures),
            endpoint_coverage=self._endpoint_coverage(
                fixtures,
                fixture_quality,
                generated_at,
            ),
            fixture_quality=fixture_quality,
            observations=tuple(observations),
        )

    def worldcup_fixtures(self) -> list[models.Fixture]:
        statement = (
            select(models.Fixture)
            .where(models.Fixture.league_id == self.league_id)
            .where(models.Fixture.season == self.season)
            .order_by(models.Fixture.date.asc(), models.Fixture.fixture_id.asc())
        )
        return list(self.session.execute(statement).scalars())

    def fixture_quality_matrix(
        self,
        fixture: models.Fixture,
        *,
        now: datetime | None = None,
    ) -> WorldCupFixtureQuality:
        current_time = ensure_aware_utc(now or utc_now())
        cutoff = _fixture_cutoff(fixture, current_time)
        static = self._static_quality_flags(fixture, cutoff)
        dynamic = {
            "has_odds_1x2": self._has_1x2_odds(fixture.fixture_id, cutoff),
            "has_odds_ou": self._has_ou_odds(fixture.fixture_id, cutoff),
            "has_api_prediction": self._count_api_predictions(fixture.fixture_id, cutoff) > 0,
            "has_lineups": self._count_lineups(fixture.fixture_id, cutoff) >= 2,
            "has_injuries": self._count_injuries(fixture, cutoff) > 0,
            "has_group_state": self._has_group_state(fixture, cutoff),
            "has_squad_strength": self._has_squad_strength(fixture),
        }
        lineups_expected = _lineups_expected(fixture, current_time)
        score, missing_sources, warnings = _fixture_quality_score(
            static=static,
            dynamic=dynamic,
            lineups_expected=lineups_expected,
        )
        return WorldCupFixtureQuality(
            fixture_id=fixture.fixture_id,
            match_label=f"{fixture.home_team} vs {fixture.away_team}",
            kickoff_at=ensure_aware_utc(fixture.date) if fixture.date else None,
            status_short=fixture.status_short,
            lineups_expected=lineups_expected,
            data_quality_score=score,
            missing_sources=tuple(missing_sources),
            warnings=tuple(warnings),
            **static,
            **dynamic,
        )

    def write_reports(
        self,
        summary: WorldCupCoverageSummary,
        *,
        output_dir: Path | str = Path("reports/worldcup_2026"),
    ) -> dict[str, Path]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        summary_path = output_path / "data_coverage_summary.json"
        report_path = output_path / "data_coverage_report.md"
        summary_path.write_text(
            json.dumps(summary.to_json_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        report_path.write_text(_markdown_report(summary), encoding="utf-8")
        return {"summary_json": summary_path, "markdown": report_path}

    def _coverage_observations(
        self,
        fixtures: list[models.Fixture],
        *,
        requested_at: datetime,
        write: bool,
    ) -> list[CoverageObservationDraft]:
        observations = [
            self.record_observation(
                endpoint="fixtures",
                requested_at=requested_at,
                result_count=len(fixtures),
                write=write,
            ),
            self.record_observation(
                endpoint="standings",
                requested_at=requested_at,
                result_count=self._count_standings(requested_at),
                write=write,
            ),
        ]
        for fixture in fixtures:
            cutoff = _fixture_cutoff(fixture, requested_at)
            endpoint_counts = {
                "odds_1x2": int(self._has_1x2_odds(fixture.fixture_id, cutoff)),
                "odds_ou": int(self._has_ou_odds(fixture.fixture_id, cutoff)),
                "predictions": self._count_api_predictions(fixture.fixture_id, cutoff),
                "lineups": self._count_lineups(fixture.fixture_id, cutoff),
                "injuries": self._count_injuries(fixture, cutoff),
                "fixture_statistics": self._count_fixture_statistics(
                    fixture.fixture_id,
                    cutoff,
                ),
                "events": self._count_events(fixture.fixture_id, cutoff),
                "player_statistics": self._count_player_statistics(
                    fixture.fixture_id,
                    cutoff,
                ),
            }
            for endpoint, count in endpoint_counts.items():
                observations.append(
                    self.record_observation(
                        endpoint=endpoint,
                        requested_at=requested_at,
                        fixture_id=fixture.fixture_id,
                        result_count=count,
                        write=write,
                    )
                )
        return observations

    def _endpoint_coverage(
        self,
        fixtures: list[models.Fixture],
        fixture_quality: tuple[WorldCupFixtureQuality, ...],
        generated_at: datetime,
    ) -> JsonDict:
        total = len(fixtures)
        coverage: JsonDict = {
            "fixtures": _coverage_row(total, total),
            "standings": _coverage_row(1, int(self._count_standings(generated_at) > 0)),
        }
        flag_by_endpoint = {
            "odds_1x2": "has_odds_1x2",
            "odds_ou": "has_odds_ou",
            "predictions": "has_api_prediction",
            "lineups": "has_lineups",
            "injuries": "has_injuries",
            "fixture_statistics": None,
            "events": None,
            "player_statistics": None,
        }
        for endpoint, field_name in flag_by_endpoint.items():
            if field_name is None:
                useful = sum(
                    int(self._fixture_endpoint_count(fixture, endpoint, generated_at) > 0)
                    for fixture in fixtures
                )
            else:
                useful = sum(int(bool(getattr(row, field_name))) for row in fixture_quality)
            coverage[endpoint] = _coverage_row(total, useful)
        return coverage

    def _fixture_endpoint_count(
        self,
        fixture: models.Fixture,
        endpoint: str,
        generated_at: datetime,
    ) -> int:
        cutoff = _fixture_cutoff(fixture, generated_at)
        if endpoint == "fixture_statistics":
            return self._count_fixture_statistics(fixture.fixture_id, cutoff)
        if endpoint == "events":
            return self._count_events(fixture.fixture_id, cutoff)
        if endpoint == "player_statistics":
            return self._count_player_statistics(fixture.fixture_id, cutoff)
        return 0

    def _static_quality_flags(
        self,
        fixture: models.Fixture,
        cutoff: datetime,
    ) -> dict[str, bool]:
        if self.bundle is None or fixture.date is None:
            return {
                "has_international_history": False,
                "has_elo": False,
                "has_fifa_rank": False,
            }
        features = build_features_for_fixture(
            fixture.home_team,
            fixture.away_team,
            cutoff.date(),
            bundle=self.bundle,
            neutral=True,
        )
        return {
            "has_international_history": bool(
                int(features.get("wc_home_history_count") or 0) >= 10
                and int(features.get("wc_away_history_count") or 0) >= 10
            ),
            "has_elo": bool(
                features.get("wc_current_elo_home_available")
                and features.get("wc_current_elo_away_available")
            ),
            "has_fifa_rank": bool(
                features.get("wc_fifa_home_available")
                and features.get("wc_fifa_away_available")
            ),
        }

    def _has_1x2_odds(self, fixture_id: int, cutoff: datetime) -> bool:
        statement = (
            select(func.count(models.OddsSnapshot.id))
            .where(models.OddsSnapshot.fixture_id == fixture_id)
            .where(models.OddsSnapshot.fetched_at <= cutoff)
            .where(models.OddsSnapshot.is_live.is_(False))
            .where(models.OddsSnapshot.bet_id == 1)
            .where(models.OddsSnapshot.odd_home.is_not(None))
            .where(models.OddsSnapshot.odd_draw.is_not(None))
            .where(models.OddsSnapshot.odd_away.is_not(None))
        )
        return int(self.session.execute(statement).scalar() or 0) > 0

    def _has_ou_odds(self, fixture_id: int, cutoff: datetime) -> bool:
        statement = (
            select(func.count(models.OddsSnapshot.id))
            .where(models.OddsSnapshot.fixture_id == fixture_id)
            .where(models.OddsSnapshot.fetched_at <= cutoff)
            .where(models.OddsSnapshot.is_live.is_(False))
            .where(models.OddsSnapshot.bet_id == 5)
            .where(models.OddsSnapshot.odd_home.is_not(None))
            .where(models.OddsSnapshot.odd_away.is_not(None))
        )
        return int(self.session.execute(statement).scalar() or 0) > 0

    def _count_api_predictions(self, fixture_id: int, cutoff: datetime) -> int:
        return self._count_table(
            models.ApiPredictionSnapshot,
            models.ApiPredictionSnapshot.fixture_id == fixture_id,
            models.ApiPredictionSnapshot.fetched_at <= cutoff,
        )

    def _count_lineups(self, fixture_id: int, cutoff: datetime) -> int:
        return len(
            {
                row[0]
                for row in self.session.execute(
                    select(models.FixtureLineup.team_id)
                    .where(models.FixtureLineup.fixture_id == fixture_id)
                    .where(models.FixtureLineup.fetched_at <= cutoff)
                ).all()
            }
        )

    def _count_injuries(self, fixture: models.Fixture, cutoff: datetime) -> int:
        return self._count_table(
            models.Injury,
            models.Injury.fetched_at <= cutoff,
            (
                (models.Injury.fixture_id == fixture.fixture_id)
                | (
                    models.Injury.team_id.in_([fixture.home_team_id, fixture.away_team_id])
                    & (models.Injury.league_id == self.league_id)
                    & (models.Injury.season == self.season)
                )
            ),
        )

    def _count_fixture_statistics(self, fixture_id: int, cutoff: datetime) -> int:
        return self._count_table(
            models.FixtureStatistics,
            models.FixtureStatistics.fixture_id == fixture_id,
            models.FixtureStatistics.fetched_at <= cutoff,
        )

    def _count_events(self, fixture_id: int, cutoff: datetime) -> int:
        return self._count_table(
            models.FixtureEvent,
            models.FixtureEvent.fixture_id == fixture_id,
            models.FixtureEvent.fetched_at <= cutoff,
        )

    def _count_player_statistics(self, fixture_id: int, cutoff: datetime) -> int:
        return self._count_table(
            models.FixturePlayerStats,
            models.FixturePlayerStats.fixture_id == fixture_id,
            models.FixturePlayerStats.fetched_at <= cutoff,
        )

    def _count_standings(self, cutoff: datetime) -> int:
        return self._count_table(
            models.StandingSnapshot,
            models.StandingSnapshot.league_id == self.league_id,
            models.StandingSnapshot.season == self.season,
            models.StandingSnapshot.fetched_at <= cutoff,
        )

    def _has_group_state(self, fixture: models.Fixture, cutoff: datetime) -> bool:
        teams = [fixture.home_team_id, fixture.away_team_id]
        statement = (
            select(func.count(models.StandingSnapshot.id))
            .where(models.StandingSnapshot.league_id == self.league_id)
            .where(models.StandingSnapshot.season == self.season)
            .where(models.StandingSnapshot.team_id.in_(teams))
            .where(models.StandingSnapshot.fetched_at <= cutoff)
        )
        return int(self.session.execute(statement).scalar() or 0) >= 2

    def _has_squad_strength(self, fixture: models.Fixture) -> bool:
        teams = [fixture.home_team_id, fixture.away_team_id]
        statement = (
            select(func.count(models.PlayerSquad.id))
            .where(models.PlayerSquad.league_id == self.league_id)
            .where(models.PlayerSquad.season == self.season)
            .where(models.PlayerSquad.team_id.in_(teams))
        )
        return int(self.session.execute(statement).scalar() or 0) >= 2

    def _count_table(self, model: type[Any], *conditions: Any) -> int:
        statement = select(func.count(model.id))
        for condition in conditions:
            statement = statement.where(condition)
        return int(self.session.execute(statement).scalar() or 0)


def _fixture_quality_score(
    *,
    static: dict[str, bool],
    dynamic: dict[str, bool],
    lineups_expected: bool,
) -> tuple[float, list[str], list[str]]:
    weights = {
        "has_international_history": 18.0,
        "has_elo": 12.0,
        "has_fifa_rank": 12.0,
        "has_odds_1x2": 14.0,
        "has_odds_ou": 5.0,
        "has_api_prediction": 8.0,
        "has_lineups": 12.0 if lineups_expected else 6.0,
        "has_injuries": 6.0,
        "has_group_state": 5.0,
        "has_squad_strength": 8.0,
    }
    flags = {**static, **dynamic}
    score = 0.0
    missing_sources: list[str] = []
    warnings: list[str] = []
    for key, weight in weights.items():
        if flags.get(key):
            score += weight
        else:
            missing_sources.append(key.removeprefix("has_"))
    if not lineups_expected and not flags.get("has_lineups"):
        warnings.append("lineups_not_expected_yet")
    if lineups_expected and not flags.get("has_lineups"):
        warnings.append("lineups_expected_missing")
    if not flags.get("has_odds_1x2"):
        warnings.append("odds_1x2_missing")
    if not flags.get("has_api_prediction"):
        warnings.append("api_prediction_missing")
    return round(max(0.0, min(100.0, score)), 1), missing_sources, warnings


def _fixture_cutoff(fixture: models.Fixture, now: datetime) -> datetime:
    current_time = ensure_aware_utc(now)
    if fixture.date is None:
        return current_time
    kickoff = ensure_aware_utc(fixture.date)
    return min(current_time, kickoff)


def _lineups_expected(fixture: models.Fixture, now: datetime) -> bool:
    if fixture.date is None:
        return False
    status = (fixture.status_short or fixture.status or "").upper()
    if status not in {"", "NS", "TBD"}:
        return True
    kickoff = ensure_aware_utc(fixture.date)
    return kickoff - ensure_aware_utc(now) <= timedelta(minutes=LINEUPS_EXPECTED_WITHIN_MINUTES)


def _coverage_row(total: int, useful: int) -> JsonDict:
    if total <= 0:
        return {"total": 0, "useful": 0, "missing": 0, "coverage_pct": 0.0}
    useful = max(0, min(useful, total))
    return {
        "total": total,
        "useful": useful,
        "missing": total - useful,
        "coverage_pct": round((useful / total) * 100.0, 1),
    }


def _markdown_report(summary: WorldCupCoverageSummary) -> str:
    payload = summary.to_json_dict()
    lines = [
        "# CDM 2026 - Couverture Des Données",
        "",
        f"- Généré : {payload['generated_at']}",
        f"- Compétition : {summary.competition_key}",
        f"- League/season : {summary.league_id}/{summary.season}",
        f"- Fixtures : {summary.fixtures_total}",
        "",
        "## Couverture Par Source",
        "",
        "| Source | Utile | Total | Couverture |",
        "| --- | ---: | ---: | ---: |",
    ]
    for endpoint in COVERAGE_ENDPOINTS:
        row = payload["endpoint_coverage"].get(endpoint, {})
        lines.append(
            f"| {endpoint} | {row.get('useful', 0)} | "
            f"{row.get('total', 0)} | {row.get('coverage_pct', 0.0):.1f}% |"
        )
    lines.extend(["", "## Fixtures À Surveiller", ""])
    weak_rows = [
        row
        for row in payload["fixture_quality"]
        if float(row.get("data_quality_score") or 0.0) < 70.0
    ][:20]
    if not weak_rows:
        lines.append("Aucune fixture sous 70/100 dans ce rapport.")
    else:
        for row in weak_rows:
            missing = ", ".join(row.get("missing_sources") or []) or "n.d."
            lines.append(
                f"- `{row['fixture_id']}` {row['match_label']} : "
                f"{row['data_quality_score']}/100, manquants: {missing}"
            )
    return sanitize_text("\n".join(lines) + "\n")
