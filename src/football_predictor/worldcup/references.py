"""Load and reconcile World Cup reference data."""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class FifaRanking:
    rank: int
    country: str
    points: float
    previous_points: float | None = None
    delta: float | None = None


@dataclass(frozen=True)
class EloReference:
    rank: int
    code: str
    elo: float


@dataclass(frozen=True)
class InternationalMatch:
    match_date: date
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    tournament: str
    city: str | None
    country: str | None
    neutral: bool

    @property
    def target(self) -> str:
        if self.home_score > self.away_score:
            return "HOME"
        if self.home_score < self.away_score:
            return "AWAY"
        return "DRAW"


@dataclass(frozen=True)
class WorldCupReferenceBundle:
    fifa_rankings: dict[str, FifaRanking]
    elo_by_code: dict[str, EloReference]
    elo_alias_to_code: dict[str, str]
    historical_matches: list[InternationalMatch]
    canonical_aliases: dict[str, str] = field(default_factory=dict)

    def canonical_name(self, value: str) -> str:
        normalized = normalize_team_name(value)
        if normalized in self.canonical_aliases:
            return self.canonical_aliases[normalized]
        code = self.elo_alias_to_code.get(normalized)
        if code:
            for alias, alias_code in self.elo_alias_to_code.items():
                if alias_code == code and alias in self.canonical_aliases:
                    return self.canonical_aliases[alias]
        return value.strip()

    def fifa_for_team(self, value: str) -> FifaRanking | None:
        return self.fifa_rankings.get(normalize_team_name(value))

    def elo_for_team(self, value: str) -> EloReference | None:
        code = self.elo_alias_to_code.get(normalize_team_name(value))
        return self.elo_by_code.get(code or "")


MANUAL_CANONICAL_ALIASES: dict[str, str] = {
    "united states": "USA",
    "usa": "USA",
    "etats unis": "USA",
    "etats-unis": "USA",
    "turkey": "Türkiye",
    "turkiye": "Türkiye",
    "turquie": "Türkiye",
    "czechia": "Czech Republic",
    "tchequie": "Czech Republic",
    "czech republic": "Czech Republic",
    "dr congo": "Congo DR",
    "rd du congo": "Congo DR",
    "congo dr": "Congo DR",
    "cape verde": "Cape Verde Islands",
    "cap vert": "Cape Verde Islands",
    "cape verde islands": "Cape Verde Islands",
    "bosnia herzegovina": "Bosnia & Herzegovina",
    "bosnia and herzegovina": "Bosnia & Herzegovina",
    "bosnie herzegovine": "Bosnia & Herzegovina",
    "south korea": "South Korea",
    "coree du sud": "South Korea",
    "ivory coast": "Ivory Coast",
    "cote d ivoire": "Ivory Coast",
    "curacao": "Curaçao",
    "haiti": "Haiti",
}

FIFA_FRENCH_TO_CANONICAL: dict[str, str] = {
    "espagne": "Spain",
    "argentine": "Argentina",
    "angleterre": "England",
    "bresil": "Brazil",
    "pays bas": "Netherlands",
    "maroc": "Morocco",
    "belgique": "Belgium",
    "allemagne": "Germany",
    "croatie": "Croatia",
    "colombie": "Colombia",
    "senegal": "Senegal",
    "mexique": "Mexico",
    "uruguay": "Uruguay",
    "japon": "Japan",
    "suisse": "Switzerland",
    "iran": "Iran",
    "equateur": "Ecuador",
    "autriche": "Austria",
    "australie": "Australia",
    "algerie": "Algeria",
    "egypte": "Egypt",
    "canada": "Canada",
    "norvege": "Norway",
    "panama": "Panama",
    "suede": "Sweden",
    "paraguay": "Paraguay",
    "ecosse": "Scotland",
    "tunisie": "Tunisia",
    "ouzbekistan": "Uzbekistan",
    "qatar": "Qatar",
    "irak": "Iraq",
    "nouvelle zelande": "New Zealand",
    "afrique du sud": "South Africa",
    "arabie saoudite": "Saudi Arabia",
    "jordanie": "Jordan",
    "ghana": "Ghana",
    **MANUAL_CANONICAL_ALIASES,
}


def normalize_team_name(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def load_worldcup_reference_bundle(
    *,
    fifa_ranking_path: Path,
    elo_data_path: Path,
    elo_shortname_path: Path,
    historical_results_path: Path,
) -> WorldCupReferenceBundle:
    alias_to_code = load_elo_shortname_aliases(elo_shortname_path)
    canonical_aliases = _canonical_aliases(alias_to_code)
    fifa = load_fifa_rankings(fifa_ranking_path, canonical_aliases=canonical_aliases)
    elo = load_elo_references(elo_data_path)
    historical = load_historical_results(
        historical_results_path,
        canonical_aliases=canonical_aliases,
    )
    return WorldCupReferenceBundle(
        fifa_rankings=fifa,
        elo_by_code=elo,
        elo_alias_to_code=alias_to_code,
        historical_matches=historical,
        canonical_aliases=canonical_aliases,
    )


def load_fifa_rankings(
    path: Path,
    *,
    canonical_aliases: dict[str, str] | None = None,
) -> dict[str, FifaRanking]:
    rankings: dict[str, FifaRanking] = {}
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            country = str(row.get("Pays") or "").strip()
            if not country:
                continue
            canonical = _canonical_from_value(country, canonical_aliases or {})
            ranking = FifaRanking(
                rank=int(float(str(row.get("Classement") or "0").replace(",", "."))),
                country=canonical,
                points=_float(row.get("Total de points")),
                previous_points=_optional_float(row.get("Points précédents")),
                delta=_optional_float(str(row.get("+/-") or "").replace("+", "")),
            )
            rankings[normalize_team_name(canonical)] = ranking
    return rankings


def load_elo_shortname_aliases(path: Path) -> dict[str, str]:
    aliases: dict[str, str] = {}
    with Path(path).open(encoding="utf-8") as handle:
        next(handle, None)
        for line in handle:
            parts = [part.strip() for part in line.rstrip("\n").split("\t") if part.strip()]
            if len(parts) < 2:
                continue
            code = parts[0]
            aliases[normalize_team_name(code)] = code
            for alias in parts[1:]:
                aliases[normalize_team_name(alias)] = code
    return aliases


def load_elo_references(path: Path) -> dict[str, EloReference]:
    rows: dict[str, EloReference] = {}
    with Path(path).open(encoding="utf-8") as handle:
        next(handle, None)
        for line in handle:
            parts = [part.strip() for part in line.rstrip("\n").split("\t")]
            if len(parts) < 4:
                continue
            code = parts[2]
            try:
                rows[code] = EloReference(
                    rank=int(float(parts[0])),
                    code=code,
                    elo=float(parts[3]),
                )
            except ValueError:
                continue
    return rows


def load_historical_results(
    path: Path,
    *,
    canonical_aliases: dict[str, str] | None = None,
) -> list[InternationalMatch]:
    matches: list[InternationalMatch] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                matches.append(
                    InternationalMatch(
                        match_date=date.fromisoformat(str(row["date"])),
                        home_team=_canonical_from_value(row["home_team"], canonical_aliases or {}),
                        away_team=_canonical_from_value(row["away_team"], canonical_aliases or {}),
                        home_score=int(row["home_score"]),
                        away_score=int(row["away_score"]),
                        tournament=str(row.get("tournament") or "").strip(),
                        city=str(row.get("city") or "").strip() or None,
                        country=str(row.get("country") or "").strip() or None,
                        neutral=_bool(row.get("neutral")),
                    )
                )
            except (KeyError, ValueError):
                continue
    return sorted(matches, key=lambda item: item.match_date)


def audit_worldcup_references(
    teams: list[str],
    bundle: WorldCupReferenceBundle,
) -> JsonDict:
    historical_names = {
        normalize_team_name(match.home_team) for match in bundle.historical_matches
    } | {normalize_team_name(match.away_team) for match in bundle.historical_matches}
    rows: list[JsonDict] = []
    for team in sorted(teams):
        canonical = bundle.canonical_name(team)
        norm = normalize_team_name(canonical)
        fifa = bundle.fifa_for_team(canonical)
        elo = bundle.elo_for_team(canonical)
        history_available = norm in historical_names
        rows.append(
            {
                "team": team,
                "canonical_team": canonical,
                "historical_available": history_available,
                "fifa_available": fifa is not None,
                "elo_available": elo is not None,
                "fifa_rank": fifa.rank if fifa else None,
                "elo": elo.elo if elo else None,
            }
        )
    blocking = [
        row["team"]
        for row in rows
        if not row["historical_available"] or not row["fifa_available"]
    ]
    return {
        "team_count": len(rows),
        "matched_count": len(rows) - len(blocking),
        "blocking_missing_teams": blocking,
        "elo_missing_teams": [row["team"] for row in rows if not row["elo_available"]],
        "teams": rows,
        "ok": not blocking,
    }


def _canonical_aliases(alias_to_code: dict[str, str]) -> dict[str, str]:
    aliases: dict[str, str] = dict(MANUAL_CANONICAL_ALIASES)
    for alias in alias_to_code:
        aliases.setdefault(alias, alias.title())
    for french, canonical in FIFA_FRENCH_TO_CANONICAL.items():
        aliases[normalize_team_name(french)] = canonical
    return {normalize_team_name(key): value for key, value in aliases.items()}


def _canonical_from_value(value: object, aliases: dict[str, str]) -> str:
    normalized = normalize_team_name(value)
    if normalized in aliases:
        return aliases[normalized]
    if normalized in FIFA_FRENCH_TO_CANONICAL:
        return FIFA_FRENCH_TO_CANONICAL[normalized]
    return str(value or "").strip()


def _bool(value: object) -> bool:
    return str(value or "").strip().casefold() in {"true", "1", "yes", "y"}


def _float(value: object) -> float:
    return float(str(value or "0").replace(",", "."))


def _optional_float(value: object) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return _float(text)
    except ValueError:
        return None
