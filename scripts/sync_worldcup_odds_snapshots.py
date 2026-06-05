#!/usr/bin/env python
"""Synchronize World Cup 2026 odds markets into odds_snapshots.

Dry-run by default and does not call API-Football. Use --write --refresh-api to ingest.
"""

from __future__ import annotations

import argparse
import json
from datetime import date

from football_predictor.api.api_football_client import ApiFootballClient
from football_predictor.config.settings import get_settings
from football_predictor.db.session import (
    create_db_engine,
    create_session_factory,
    init_db,
    session_scope,
)
from football_predictor.ingestion.ingest_odds import OddsIngestionService
from football_predictor.ou_model.ingestion.ingest_ou_odds import OUOddsIngestionService
from football_predictor.reference.loaders import load_api_football_reference
from football_predictor.worldcup.enrichment import BTTSOddsIngestionService


def main() -> None:
    args = _parse_args()
    markets = _markets(args.markets)
    if not args.write:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "message": "dry-run only; pass --write --refresh-api to call API-Football",
                    "markets": markets,
                    "params": _mode_payload(args),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return
    if not args.refresh_api:
        raise SystemExit("--write requires --refresh-api for live API-Football calls")

    settings = get_settings()
    reference = load_api_football_reference(settings.api_football_reference_path)
    engine = create_db_engine(settings.database_url)
    init_db(engine)
    session_factory = create_session_factory(engine)
    with ApiFootballClient(
        base_url=settings.api_football_base_url,
        api_key=settings.api_football_key,
        timeout=settings.api_football_timeout_seconds,
        raw_snapshot_dir=settings.api_football_raw_snapshot_dir,
        retries=settings.api_football_max_retries,
    ) as client, session_scope(session_factory) as session:
        output = {}
        if "1x2" in markets:
            service = OddsIngestionService(
                session,
                client,
                reference=reference,
                market_bet_name=settings.market_1x2_bet_name,
                market_bet_id=settings.market_1x2_bet_id,
                save_raw=args.save_raw,
            )
            output["1x2"] = _run_odds_mode(service, args).as_dict()
        if "ou25" in markets:
            service = OUOddsIngestionService(
                session,
                client,
                reference=reference,
                ou_bet_id=settings.market_ou25_bet_id,
                save_raw=args.save_raw,
            )
            output["ou25"] = _run_ou_mode(service, args).as_dict()
        if "btts" in markets:
            service = BTTSOddsIngestionService(
                session,
                client,
                bet_id=settings.market_btts_bet_id,
                save_raw=args.save_raw,
            )
            output["btts"] = _run_btts_mode(service, args).as_dict()
    print(json.dumps({"dry_run": False, "markets": output}, indent=2, sort_keys=True))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=int, default=None)
    parser.add_argument("--date", default=None, help="YYYY-MM-DD odds date.")
    parser.add_argument("--league-id", type=int, default=1)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--markets", default="1x2,ou25,btts")
    parser.add_argument("--write", action="store_true", help="Persist odds snapshots.")
    parser.add_argument("--refresh-api", action="store_true", help="Allow live API calls.")
    parser.add_argument("--save-raw", action="store_true", help="Persist raw API snapshots.")
    return parser.parse_args()


def _markets(value: str) -> list[str]:
    allowed = {"1x2", "ou25", "btts"}
    parsed = [item.strip().casefold() for item in value.split(",") if item.strip()]
    invalid = sorted(set(parsed) - allowed)
    if invalid:
        raise SystemExit(f"Unsupported markets: {', '.join(invalid)}")
    return parsed or ["1x2", "ou25", "btts"]


def _mode_payload(args: argparse.Namespace) -> dict[str, object]:
    return {
        "fixture": args.fixture,
        "date": args.date,
        "league_id": args.league_id,
        "season": args.season,
    }


def _target_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _run_odds_mode(service: OddsIngestionService, args: argparse.Namespace):
    target_date = _target_date(args.date)
    if args.fixture is not None:
        return service.ingest_odds_for_fixture(args.fixture)
    if target_date is not None:
        return service.ingest_odds_by_date(
            target_date,
            league_id=args.league_id,
            season=args.season,
        )
    return service.ingest_odds_by_league_season(args.league_id, args.season)


def _run_ou_mode(service: OUOddsIngestionService, args: argparse.Namespace):
    target_date = _target_date(args.date)
    if args.fixture is not None:
        return service.ingest_ou_odds_for_fixture(args.fixture)
    if target_date is not None:
        return service.ingest_ou_odds_by_date(
            target_date,
            league_id=args.league_id,
            season=args.season,
        )
    return service.ingest_ou_odds_by_league_season(args.league_id, args.season)


def _run_btts_mode(service: BTTSOddsIngestionService, args: argparse.Namespace):
    target_date = _target_date(args.date)
    if args.fixture is not None:
        return service.ingest_by_fixture(args.fixture)
    if target_date is not None:
        return service.ingest_by_date(
            target_date,
            league_id=args.league_id,
            season=args.season,
        )
    return service.ingest_by_league_season(args.league_id, args.season)


if __name__ == "__main__":
    main()
