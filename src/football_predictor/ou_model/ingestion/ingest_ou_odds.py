"""Over/Under 2.5 odds ingestion.

O/U odds are stored in the existing odds_snapshots table:
  odd_home = Over 2.5 odd
  odd_away = Under 2.5 odd
  odd_draw = NULL

The API-Football /odds endpoint returns bet_id=5 ("Goals Over/Under") with values
like [{"value": "Over 2.5", "odd": "1.85"}, {"value": "Under 2.5", "odd": "1.95"}, ...].
The existing 1X2 parser cannot handle these labels, so this module provides its own parser.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

from sqlalchemy.orm import Session

from football_predictor.api.endpoints import ODDS
from football_predictor.db import models
from football_predictor.db.repositories import insert_raw_api_snapshot, upsert_by_fields
from football_predictor.ou_model.constants import OU_BET_NAME, OU_THRESHOLD
from football_predictor.reference.lookups import ApiFootballReference
from football_predictor.utils.logging import get_logger
from football_predictor.utils.time import parse_datetime, utc_now

logger = get_logger(__name__)

JsonDict = dict[str, Any]


class ApiFootballPayloadClient(Protocol):
    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> Any:
        ...


@dataclass
class OUOddsIngestionSummary:
    odds_stored: int = 0
    fixtures_processed: int = 0
    bookmakers_seen: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "odds_stored": self.odds_stored,
            "fixtures_processed": self.fixtures_processed,
            "bookmakers_seen": self.bookmakers_seen,
            "skipped": self.skipped,
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _parse_decimal(value: Any) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if f > 1 and math.isfinite(f) else None


def _extract_ou_pair(
    values_json: list[dict[str, Any]],
    threshold: float,
) -> tuple[float, float] | None:
    """Extract (odd_over, odd_under) for the given threshold from API values list."""
    over_label = f"Over {threshold:g}"
    under_label = f"Under {threshold:g}"
    odd_over: float | None = None
    odd_under: float | None = None
    for entry in values_json:
        label = str(entry.get("value", "")).strip()
        odd = _parse_decimal(entry.get("odd"))
        if odd is None:
            continue
        if label == over_label:
            odd_over = odd
        elif label == under_label:
            odd_under = odd
    if odd_over is not None and odd_under is not None:
        return odd_over, odd_under
    return None


def _parse_ou_odds_rows(
    payload: JsonDict,
    *,
    target_bet_id: int,
    threshold: float,
    fetched_at: Any,
    ingestion_source: str = "api-football",
) -> list[JsonDict]:
    """Parse API /odds response into upsert-ready dicts for O/U odds."""
    rows: list[JsonDict] = []
    for fixture_row in payload.get("response", []):
        fixture_info = fixture_row.get("fixture") or {}
        fixture_id = fixture_info.get("id") or fixture_row.get("fixture_id")
        if fixture_id is None:
            continue
        league_info = fixture_row.get("league") or {}
        league_id = league_info.get("id")
        season = league_info.get("season")

        bookmakers = fixture_row.get("bookmakers")
        if not isinstance(bookmakers, list):
            continue
        for bk in bookmakers:
            bookmaker_id = bk.get("id")
            bookmaker_name = bk.get("name", "")
            bets = bk.get("bets") or []
            for bet in bets:
                if bet.get("id") != target_bet_id:
                    continue
                values = bet.get("values") or []
                pair = _extract_ou_pair(values, threshold)
                if pair is None:
                    continue
                odd_over, odd_under = pair
                rows.append({
                    "fixture_id": int(fixture_id),
                    "league_id": int(league_id) if league_id is not None else None,
                    "season": int(season) if season is not None else None,
                    "bookmaker_id": int(bookmaker_id) if bookmaker_id is not None else None,
                    "bookmaker_name": bookmaker_name,
                    "bet_id": target_bet_id,
                    "bet_name": OU_BET_NAME,
                    "odd_home": odd_over,   # Over 2.5
                    "odd_draw": None,       # no draw for O/U
                    "odd_away": odd_under,  # Under 2.5
                    "fetched_at": fetched_at,
                    "is_live": False,
                    "ingestion_source": ingestion_source,
                })
    return rows


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class OUOddsIngestionService:
    """Ingest Over/Under 2.5 odds from API-Football into odds_snapshots.

    Does NOT delegate to OddsIngestionService because the "Goals Over/Under"
    bet (bet_id=5) uses "Over 2.5"/"Under 2.5" value labels that the 1X2
    parser cannot handle.
    """

    def __init__(
        self,
        session: Session,
        client: ApiFootballPayloadClient,
        *,
        reference: ApiFootballReference,
        ou_bet_id: int | None = None,
        threshold: float = OU_THRESHOLD,
        save_raw: bool = False,
    ) -> None:
        self.session = session
        self.client = client
        self.reference = reference
        self.threshold = threshold
        self.save_raw = save_raw

        if ou_bet_id is not None:
            self.ou_bet_id = ou_bet_id
        else:
            try:
                self.ou_bet_id = reference.find_bet_by_name(OU_BET_NAME).bet_id
            except Exception:
                self.ou_bet_id = 5  # API-Football standard id for Goals Over/Under
        logger.info("OUOddsIngestionService ready: bet_id=%d threshold=%.1f", self.ou_bet_id, self.threshold)

    def ingest_ou_odds_for_fixture(
        self,
        fixture_id: int,
    ) -> OUOddsIngestionSummary:
        return self._ingest({"fixture": fixture_id})

    def ingest_ou_odds_by_date(
        self,
        target_date: date,
        *,
        league_id: int | None = None,
        season: int | None = None,
    ) -> OUOddsIngestionSummary:
        params: JsonDict = {"date": target_date.isoformat()}
        if league_id is not None:
            params["league"] = league_id
        if season is not None:
            params["season"] = season
        return self._ingest(params)

    def ingest_ou_odds_by_league_season(
        self,
        league_id: int,
        season: int,
    ) -> OUOddsIngestionSummary:
        return self._ingest({"league": league_id, "season": season})

    def _ingest(self, base_params: JsonDict) -> OUOddsIngestionSummary:
        summary = OUOddsIngestionSummary()
        fetch_params = {**base_params, "bet": self.ou_bet_id}
        page = 1
        total_pages = 1
        while page <= total_pages:
            params = {**fetch_params, "page": page}
            try:
                api_payload = self.client.get_payload(ODDS, params, save_raw=self.save_raw)
            except Exception as exc:
                summary.errors.append(str(exc))
                break

            if self.save_raw:
                try:
                    insert_raw_api_snapshot(
                        self.session,
                        endpoint=api_payload.endpoint,
                        params_json=api_payload.params,
                        payload_json=api_payload.payload,
                        fetched_at=parse_datetime(api_payload.fetched_at) or utc_now(),
                        status_code=api_payload.status_code,
                        source=api_payload.source,
                    )
                except Exception as exc:
                    logger.warning("Could not insert raw snapshot: %s", exc)

            paging = api_payload.payload.get("paging") or {}
            total_pages = int(paging.get("total") or 1)

            fetched_at = parse_datetime(api_payload.fetched_at) or utc_now()
            rows = _parse_ou_odds_rows(
                api_payload.payload,
                target_bet_id=self.ou_bet_id,
                threshold=self.threshold,
                fetched_at=fetched_at,
            )

            fixtures_in_page: set[int] = set()
            bookmakers_in_page: set[int] = set()
            for row in rows:
                try:
                    self._upsert_bookmaker(row)
                    self._upsert_odds(row)
                    summary.odds_stored += 1
                    fixtures_in_page.add(row["fixture_id"])
                    if row["bookmaker_id"] is not None:
                        bookmakers_in_page.add(row["bookmaker_id"])
                except Exception as exc:
                    summary.errors.append(f"fixture={row.get('fixture_id')}: {exc}")
                    logger.warning("O/U odds upsert error: %s", exc)

            if not rows:
                summary.skipped += 1

            summary.fixtures_processed += len(fixtures_in_page)
            summary.bookmakers_seen += len(bookmakers_in_page)
            self.session.flush()
            page += 1

        return summary

    def _upsert_bookmaker(self, row: JsonDict) -> None:
        bk_id = row.get("bookmaker_id")
        if bk_id is None:
            return
        upsert_by_fields(
            self.session,
            models.Bookmaker,
            {"bookmaker_id": bk_id},
            {"name": row.get("bookmaker_name") or ""},
        )

    def _upsert_odds(self, row: JsonDict) -> None:
        match_fields = {
            "fixture_id": row["fixture_id"],
            "bookmaker_id": row["bookmaker_id"],
            "bet_id": row["bet_id"],
            "fetched_at": row["fetched_at"],
            "is_live": False,
        }
        update_fields = {
            "odd_home": row["odd_home"],
            "odd_draw": row["odd_draw"],
            "odd_away": row["odd_away"],
            "payload_json": {
                "home": row["odd_home"],
                "away": row["odd_away"],
                "ingestion_source": row["ingestion_source"],
                "threshold": self.threshold,
            },
        }
        upsert_by_fields(self.session, models.OddsSnapshot, match_fields, update_fields)
