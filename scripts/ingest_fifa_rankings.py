#!/usr/bin/env python
"""Ingest dated FIFA ranking snapshots.

Dry-run by default. --snapshot-date is required to avoid undated current-rank leakage.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from football_predictor.config.settings import get_settings
from football_predictor.db.session import (
    create_db_engine,
    create_session_factory,
    init_db,
    session_scope,
)
from football_predictor.worldcup.enrichment import import_fifa_ranking_snapshots
from football_predictor.worldcup.references import load_worldcup_reference_bundle


def main() -> None:
    args = _parse_args()
    settings = get_settings()
    snapshot_date = date.fromisoformat(args.snapshot_date)
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
        result = import_fifa_ranking_snapshots(
            session,
            args.input,
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
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/reference/classement_fifa_officiel.csv"),
    )
    parser.add_argument("--snapshot-date", required=True, help="Ranking date, YYYY-MM-DD.")
    parser.add_argument("--source", default="fifa_csv")
    parser.add_argument("--write", action="store_true", help="Persist snapshots to DB.")
    return parser.parse_args()


if __name__ == "__main__":
    main()
