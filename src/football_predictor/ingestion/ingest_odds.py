"""Prematch odds ingestion and storage."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

from sqlalchemy.orm import Session

from football_predictor.api.api_football_client import ApiFootballPayload
from football_predictor.api.endpoints import ODDS
from football_predictor.db import models
from football_predictor.db.repositories import insert_raw_api_snapshot, upsert_by_fields
from football_predictor.features.odds_features import resolve_1x2_bet_id
from football_predictor.ingestion.parsers import parse_odds_snapshot_rows
from football_predictor.reference.lookups import ApiFootballReference
from football_predictor.utils.exceptions import ReferenceLookupError
from football_predictor.utils.logging import get_logger
from football_predictor.utils.time import parse_datetime, utc_now

JsonDict = dict[str, Any]

logger = get_logger(__name__)


class ApiFootballPayloadClient(Protocol):
    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> ApiFootballPayload:
        ...


@dataclass
class OddsIngestionSummary:
    odds: int = 0
    raw_snapshots: int = 0
    bookmakers: int = 0
    bets: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def merge(self, other: OddsIngestionSummary) -> OddsIngestionSummary:
        self.odds += other.odds
        self.raw_snapshots += other.raw_snapshots
        self.bookmakers += other.bookmakers
        self.bets += other.bets
        self.skipped += other.skipped
        self.errors.extend(other.errors)
        return self

    def as_dict(self) -> dict[str, int | list[str]]:
        return {
            "odds": self.odds,
            "raw_snapshots": self.raw_snapshots,
            "bookmakers": self.bookmakers,
            "bets": self.bets,
            "skipped": self.skipped,
            "errors": self.errors,
        }


class OddsIngestionService:
    """Ingest API-Football prematch `/odds` payloads."""

    def __init__(
        self,
        session: Session,
        client: ApiFootballPayloadClient,
        *,
        reference: ApiFootballReference,
        market_bet_name: str = "Match Winner",
        market_bet_id: int | None = None,
        save_raw: bool = False,
    ) -> None:
        self.session = session
        self.client = client
        self.reference = reference
        self.market_bet_id = resolve_1x2_bet_id(
            reference,
            configured_bet_id=market_bet_id,
            configured_bet_name=market_bet_name,
        )
        self.market_bet_name = reference.find_bet_by_id(self.market_bet_id).name
        self.save_raw = save_raw

    def ingest_odds_for_fixture(
        self,
        fixture_id: int,
        *,
        bookmaker: int | None = None,
        bet: int | str | None = None,
        bookmaker_ids: Iterable[int] | None = None,
    ) -> OddsIngestionSummary:
        self._warn_if_unknown_fixture(fixture_id)
        return self._ingest(
            {"fixture": fixture_id},
            bookmaker_ids=self._bookmaker_ids(bookmaker, bookmaker_ids),
            target_bet_id=self._resolve_bet_id(bet),
        )

    def ingest_odds_by_date(
        self,
        target_date: date,
        *,
        league_id: int | None = None,
        season: int | None = None,
        bookmaker: int | None = None,
        bet: int | str | None = None,
        bookmaker_ids: Iterable[int] | None = None,
    ) -> OddsIngestionSummary:
        params: JsonDict = {"date": target_date.isoformat()}
        if league_id is not None:
            self._warn_if_unknown_league(league_id, season)
            params["league"] = league_id
        if season is not None:
            params["season"] = season
        return self._ingest(
            params,
            bookmaker_ids=self._bookmaker_ids(bookmaker, bookmaker_ids),
            target_bet_id=self._resolve_bet_id(bet),
        )

    def ingest_odds_by_league_season(
        self,
        league_id: int,
        season: int,
        *,
        bookmaker: int | None = None,
        bet: int | str | None = None,
        bookmaker_ids: Iterable[int] | None = None,
    ) -> OddsIngestionSummary:
        self._warn_if_unknown_league(league_id, season)
        return self._ingest(
            {"league": league_id, "season": season},
            bookmaker_ids=self._bookmaker_ids(bookmaker, bookmaker_ids),
            target_bet_id=self._resolve_bet_id(bet),
        )

    def _ingest(
        self,
        base_params: JsonDict,
        *,
        bookmaker_ids: Iterable[int] | None,
        target_bet_id: int,
    ) -> OddsIngestionSummary:
        summary = OddsIngestionSummary()
        bookmaker_list = list(bookmaker_ids or [])
        if not bookmaker_list:
            summary.merge(self._ingest_params(base_params, target_bet_id=target_bet_id))
            return summary
        for bookmaker_id in bookmaker_list:
            self._warn_if_unknown_bookmaker(bookmaker_id)
            params = {**base_params, "bookmaker": bookmaker_id}
            summary.merge(self._ingest_params(params, target_bet_id=target_bet_id))
        return summary

    def _ingest_params(self, params: JsonDict, *, target_bet_id: int) -> OddsIngestionSummary:
        summary = OddsIngestionSummary()
        fetch_params = {**params, "bet": target_bet_id}
        for payload in self._fetch_paginated(fetch_params):
            summary.raw_snapshots += 1
            fetched_at = parse_datetime(payload.fetched_at) or utc_now()
            rows = parse_odds_snapshot_rows(
                payload.payload,
                target_bet_id=target_bet_id,
                fetched_at=fetched_at,
                ingestion_source=payload.source,
            )
            if not rows:
                summary.skipped += 1
            for row in rows:
                self._upsert_references(row, summary)
                self._upsert_odds(row)
                summary.odds += 1
        self.session.flush()
        return summary

    def _resolve_bet_id(self, bet: int | str | None) -> int:
        if bet is None:
            return self.market_bet_id
        if isinstance(bet, int):
            return self.reference.find_bet_by_id(bet).bet_id
        return self.reference.find_bet_by_name(bet).bet_id

    @staticmethod
    def _bookmaker_ids(
        bookmaker: int | None,
        bookmaker_ids: Iterable[int] | None,
    ) -> list[int] | None:
        values = list(bookmaker_ids or [])
        if bookmaker is not None:
            values.append(bookmaker)
        return values or None

    def _fetch_paginated(self, params: JsonDict) -> list[ApiFootballPayload]:
        payloads: list[ApiFootballPayload] = []
        page = 1
        total = 1
        while page <= total:
            page_params = {**params, "page": page}
            payload = self.client.get_payload(ODDS, page_params, save_raw=self.save_raw)
            self._insert_raw_snapshot(payload)
            payloads.append(payload)
            paging = payload.payload.get("paging")
            if isinstance(paging, dict):
                total = int(paging.get("total") or 1)
            page += 1
        return payloads

    def _insert_raw_snapshot(self, payload: ApiFootballPayload) -> None:
        insert_raw_api_snapshot(
            self.session,
            endpoint=payload.endpoint,
            params_json=payload.params,
            payload_json=payload.payload,
            fetched_at=parse_datetime(payload.fetched_at) or utc_now(),
            status_code=payload.status_code,
            source=payload.source,
        )

    def _upsert_references(self, row: JsonDict, summary: OddsIngestionSummary) -> None:
        bookmaker_id = row.get("bookmaker_id")
        if bookmaker_id is not None:
            try:
                self.reference.find_bookmaker_by_id(int(bookmaker_id))
            except ReferenceLookupError:
                logger.warning(
                    "Bookmaker id not found in local reference; continuing odds ingestion "
                    "bookmaker_id=%s",
                    bookmaker_id,
                )
            upsert_by_fields(
                self.session,
                models.Bookmaker,
                {"bookmaker_id": int(bookmaker_id)},
                {
                    "name": row.get("bookmaker_name") or "",
                    "payload_json": {
                        "id": bookmaker_id,
                        "name": row.get("bookmaker_name"),
                        "ingestion_source": row["payload_json"].get("ingestion_source"),
                    },
                },
            )
            summary.bookmakers += 1

        bet_id = row.get("bet_id")
        if bet_id is not None:
            self.reference.find_bet_by_id(int(bet_id))
            upsert_by_fields(
                self.session,
                models.Bet,
                {"bet_id": int(bet_id), "bet_type": "prematch"},
                {
                    "name": row.get("bet_name") or self.market_bet_name,
                    "bet_type": "prematch",
                    "payload_json": {
                        "id": bet_id,
                        "name": row.get("bet_name"),
                        "ingestion_source": row["payload_json"].get("ingestion_source"),
                    },
                },
            )
            summary.bets += 1

    def _upsert_odds(self, row: JsonDict) -> None:
        match_fields = {
            "fixture_id": row.pop("fixture_id"),
            "bookmaker_id": row.pop("bookmaker_id"),
            "bet_id": row.pop("bet_id"),
            "fetched_at": row.pop("fetched_at"),
            "is_live": False,
        }
        upsert_by_fields(self.session, models.OddsSnapshot, match_fields, row)

    def _warn_if_unknown_fixture(self, fixture_id: int) -> None:
        try:
            self.reference.validate_fixture_reference(fixture_id)
        except ReferenceLookupError:
            logger.warning(
                "Fixture id not found in local reference; continuing odds ingestion fixture_id=%s",
                fixture_id,
            )

    def _warn_if_unknown_league(self, league_id: int, season: int | None) -> None:
        try:
            self.reference.find_league_by_id(league_id, season)
        except ReferenceLookupError:
            logger.warning(
                "League id not found in local reference; continuing odds ingestion "
                "league_id=%s season=%s",
                league_id,
                season,
            )

    def _warn_if_unknown_bookmaker(self, bookmaker_id: int) -> None:
        try:
            self.reference.find_bookmaker_by_id(bookmaker_id)
        except ReferenceLookupError:
            logger.warning(
                "Bookmaker id not found in local reference; continuing odds ingestion "
                "bookmaker_id=%s",
                bookmaker_id,
            )
