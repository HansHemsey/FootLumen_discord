#!/usr/bin/env python
"""Build dated squad strength snapshots from local PlayerSquad rows.

Dry-run by default. Use --execute to persist snapshots. --write is kept as a
backward-compatible alias.
"""

from __future__ import annotations

import argparse
import json

from football_predictor.config.settings import get_settings
from football_predictor.db.session import (
    create_db_engine,
    create_session_factory,
    init_db,
    session_scope,
)
from football_predictor.utils.time import parse_datetime, utc_now
from football_predictor.worldcup.coverage_monitor import WORLD_CUP_COMPETITION_KEY
from football_predictor.worldcup.enrichment import build_squad_strength_features
from football_predictor.worldcup.references import load_worldcup_reference_bundle


def main() -> None:
    args = _parse_args()
    settings = get_settings()
    snapshot_at = parse_datetime(args.snapshot_at) if args.snapshot_at else utc_now()
    if snapshot_at is None:
        raise SystemExit("--snapshot-at must be an ISO datetime")
    engine = create_db_engine(settings.database_url)
    if args.write:
        init_db(engine)
    session_factory = create_session_factory(engine)
    bundle = load_worldcup_reference_bundle(
        fifa_ranking_path=settings.world_cup_fifa_ranking_path,
        elo_data_path=settings.world_cup_elo_data_path,
        elo_shortname_path=settings.world_cup_elo_shortname_path,
        historical_results_path=settings.world_cup_historical_results_path,
    )
    with session_scope(session_factory) as session:
        result = build_squad_strength_features(
            session,
            snapshot_at=snapshot_at,
            competition_key=args.competition_key,
            league_id=args.league_id,
            season=args.season,
            bundle=bundle,
            write=args.write,
        )
        if not args.write:
            session.rollback()
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league-id", type=int, default=1)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--competition-key", default=WORLD_CUP_COMPETITION_KEY)
    parser.add_argument("--snapshot-at", default=None, help="ISO snapshot time. Defaults to now.")
    parser.add_argument(
        "--execute",
        "--write",
        dest="write",
        action="store_true",
        help="Persist snapshots to DB. Defaults to dry-run.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
