#!/usr/bin/env python
"""Generate a World Cup 2026 data coverage report.

Dry-run is the default: no DB observations and no report files are written unless
``--write`` is provided.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from football_predictor.config.settings import get_settings
from football_predictor.db.session import create_db_engine, create_session_factory, session_scope
from football_predictor.worldcup.coverage_monitor import (
    WORLD_CUP_COMPETITION_KEY,
    WorldCupCoverageMonitor,
)
from football_predictor.worldcup.references import load_worldcup_reference_bundle


def main() -> None:
    args = _parse_args()
    settings = get_settings()
    generated_at = datetime.now(tz=UTC)
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    bundle = load_worldcup_reference_bundle(
        fifa_ranking_path=settings.world_cup_fifa_ranking_path,
        elo_data_path=settings.world_cup_elo_data_path,
        elo_shortname_path=settings.world_cup_elo_shortname_path,
        historical_results_path=settings.world_cup_historical_results_path,
    )
    with session_scope(session_factory) as session:
        monitor = WorldCupCoverageMonitor(
            session,
            competition_key=args.competition_key,
            league_id=args.league_id,
            season=args.season,
            bundle=bundle,
        )
        summary = monitor.build_summary(
            now=generated_at,
            write_observations=args.write,
        )
        paths = monitor.write_reports(summary, output_dir=args.output_dir) if args.write else {}

    payload = {
        "dry_run": not args.write,
        "write": args.write,
        "competition_key": args.competition_key,
        "league_id": args.league_id,
        "season": args.season,
        "generated_at": generated_at.isoformat(),
        "fixtures_total": summary.fixtures_total,
        "endpoint_coverage": summary.endpoint_coverage,
        "report_paths": {key: str(path) for key, path in paths.items()},
        "message": (
            "coverage report written"
            if args.write
            else "dry-run only; pass --write to persist observations and reports"
        ),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league-id", type=int, default=1)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument(
        "--competition-key",
        default=WORLD_CUP_COMPETITION_KEY,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/worldcup_2026"),
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Persist DB observations and write report files.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
