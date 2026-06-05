#!/usr/bin/env python
"""Compute dated national Elo snapshots from persisted international matches.

Dry-run by default. Use --execute to persist snapshots. --write is kept as a
backward-compatible alias.
"""

from __future__ import annotations

import argparse
import json
from datetime import date

from football_predictor.config.settings import get_settings
from football_predictor.db.session import (
    create_db_engine,
    create_session_factory,
    init_db,
    session_scope,
)
from football_predictor.worldcup.enrichment import compute_national_elo_snapshots
from football_predictor.worldcup.references import load_worldcup_reference_bundle


def main() -> None:
    args = _parse_args()
    settings = get_settings()
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
    snapshot_date = date.fromisoformat(args.snapshot_date) if args.snapshot_date else None
    with session_scope(session_factory) as session:
        result = compute_national_elo_snapshots(
            session,
            snapshot_date=snapshot_date,
            bundle=bundle,
            source=args.source,
            write=args.write,
        )
        if not args.write:
            session.rollback()
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-date", default=None, help="Optional YYYY-MM-DD cutoff.")
    parser.add_argument("--source", default="computed_national_history")
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
