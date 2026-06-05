#!/usr/bin/env python
"""Build an enriched point-in-time World Cup feature matrix.

Dry-run by default. Use --write to create the matrix and coverage report files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from football_predictor.config.settings import get_settings
from football_predictor.db.session import create_db_engine, create_session_factory, session_scope
from football_predictor.worldcup.enrichment import (
    build_worldcup_feature_matrix,
    write_worldcup_feature_matrix_reports,
)
from football_predictor.worldcup.references import load_worldcup_reference_bundle


def main() -> None:
    args = _parse_args()
    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    bundle = load_worldcup_reference_bundle(
        fifa_ranking_path=settings.world_cup_fifa_ranking_path,
        elo_data_path=settings.world_cup_elo_data_path,
        elo_shortname_path=settings.world_cup_elo_shortname_path,
        historical_results_path=settings.world_cup_historical_results_path,
    )
    with session_scope(session_factory) as session:
        frame = build_worldcup_feature_matrix(
            session,
            league_id=args.league_id,
            season=args.season,
            prediction_offset_hours=args.prediction_offset_hours,
            bundle=bundle,
        )
        result = write_worldcup_feature_matrix_reports(
            frame,
            output_path=args.output,
            report_path=args.report,
            dry_run=not args.write,
        )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league-id", type=int, default=1)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--prediction-offset-hours", type=float, default=24.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/worldcup_2026/feature_matrix.parquet"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/worldcup_2026/feature_matrix_report.md"),
    )
    parser.add_argument("--write", action="store_true", help="Write matrix and report files.")
    return parser.parse_args()


if __name__ == "__main__":
    main()
