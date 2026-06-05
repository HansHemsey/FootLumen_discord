#!/usr/bin/env python
"""Ingest national team results into point-in-time World Cup tables.

Dry-run by default. Use --write to persist rows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from football_predictor.config.settings import get_settings
from football_predictor.db.session import (
    create_db_engine,
    create_session_factory,
    init_db,
    session_scope,
)
from football_predictor.worldcup.enrichment import (
    ingest_national_results_csv,
    seed_aliases_from_bundle,
)
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
    with session_scope(session_factory) as session:
        alias_result = seed_aliases_from_bundle(session, bundle, write=args.write)
        result = ingest_national_results_csv(
            session,
            args.input,
            bundle=bundle,
            source=args.source,
            write=args.write,
        )
        if not args.write:
            session.rollback()
    payload = {
        "dry_run": not args.write,
        "aliases": alias_result.as_dict(),
        "matches": result.as_dict(),
        "message": "rows persisted" if args.write else "dry-run only; pass --write to persist",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/reference/historical_worldcup_result.csv"),
    )
    parser.add_argument("--source", default="historical_worldcup_result_csv")
    parser.add_argument("--write", action="store_true", help="Persist rows to DB.")
    return parser.parse_args()


if __name__ == "__main__":
    main()
