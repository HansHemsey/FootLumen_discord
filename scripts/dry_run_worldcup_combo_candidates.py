#!/usr/bin/env python
"""Dry-run World Cup combo sessions and leg candidates without DB writes."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

from football_predictor.config.settings import get_settings
from football_predictor.db.session import create_db_engine, create_session_factory, session_scope
from football_predictor.world_cup_combos.config import load_world_cup_combo_config
from football_predictor.world_cup_combos.cutoff import compute_effective_cutoff
from football_predictor.world_cup_combos.worldcup_combo_leg_selector import (
    WorldCupComboLegSelector,
)
from football_predictor.world_cup_combos.worldcup_combo_sessions import (
    WorldCupComboSessionService,
)


def main() -> None:
    args = _parse_args()
    settings = get_settings()
    config_path = args.config or settings.world_cup_combos_config_path
    config = load_world_cup_combo_config(config_path)
    target_date = date.fromisoformat(args.date) if args.date else None
    generated_at = datetime.now(tz=UTC)

    if not config.enabled:
        print(
            json.dumps(
                {
                    "enabled": False,
                    "config_path": str(config_path),
                    "sessions": 0,
                    "fixtures": 0,
                    "candidates": 0,
                    "generated_at": generated_at.isoformat(),
                    "message": "worldcup_combos disabled; dry-run is a no-op",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as db_session:
        session_service = WorldCupComboSessionService(db_session, config)
        sessions = session_service.build_sessions(target_date=target_date)
        selector = WorldCupComboLegSelector(db_session, config)
        result = selector.select_candidates(sessions, now=generated_at)

    reason_counts = Counter(item.reason for item in result.no_candidates)
    summary = {
        "enabled": True,
        "config_path": str(config_path),
        "target_date": target_date.isoformat() if target_date else None,
        "generated_at": generated_at.isoformat(),
        "sessions": len(result.sessions),
        "fixtures": sum(len(session.fixtures) for session in result.sessions),
        "candidates": len(result.candidates),
        "exclusion_reasons": dict(sorted(reason_counts.items())),
        "session_summaries": [
            {
                "session_key": session.session_key,
                "combo_date_paris": session.combo_date_paris.isoformat(),
                "fixtures": len(session.fixtures),
                "first_kickoff_at": session.first_kickoff_at.isoformat(),
                "last_kickoff_at": session.last_kickoff_at.isoformat(),
                "lock_time": session.lock_time.isoformat(),
                "data_cutoff_time": compute_effective_cutoff(
                    generated_at,
                    session.lock_time,
                ).isoformat(),
                "stage": session.stage,
                "group_matchday": session.group_matchday,
                "is_matchday3": session.is_matchday3,
                "is_knockout": session.is_knockout,
                "warnings": session.warnings,
            }
            for session in result.sessions
        ],
        "candidate_summaries": [
            {
                "fixture_id": candidate.fixture_id,
                "market_type": candidate.market_type.value,
                "market_scope": candidate.market_scope.value,
                "selection": candidate.selection,
                "decimal_odd": round(candidate.decimal_odd, 3),
                "model_probability": round(candidate.model_probability, 4),
                "market_probability": round(candidate.market_probability, 4),
                "edge": round(candidate.edge, 4),
                "ev": round(candidate.ev, 4),
                "confidence_score": round(candidate.confidence_score, 2),
                "data_quality_score": round(candidate.data_quality_score, 2),
                "data_cutoff_time": (
                    candidate.data_cutoff_time.isoformat()
                    if candidate.data_cutoff_time
                    else None
                ),
                "generated_at": (
                    candidate.generated_at.isoformat() if candidate.generated_at else None
                ),
                "lock_time": candidate.lock_time.isoformat() if candidate.lock_time else None,
                "warnings": candidate.warnings,
            }
            for candidate in result.candidates
        ],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to worldcup_combos.yaml. Defaults to settings.",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Optional Paris date filter in YYYY-MM-DD format.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
