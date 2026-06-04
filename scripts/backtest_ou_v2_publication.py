#!/usr/bin/env python3
"""Run the O/U V2 publication/value betting backtest reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from football_predictor.ou_model.backtesting.ou_evaluator import OUBacktestConfig
from football_predictor.ou_model.backtesting.ou_publication_backtest import (
    OUPublicationBacktestConfig,
    load_filtered_ou_publication_dataset,
    run_ou_publication_backtest,
)

JsonDict = dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtest O/U V2 publication/value betting policy.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/processed/training_ou_v1.parquet"),
    )
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--competition")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/ou_v2"))
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument("--min-train-rows", type=int, default=300)
    parser.add_argument("--min-recommended-bets", type=int, default=20)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load/filter the dataset and print a summary without writing reports.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = OUPublicationBacktestConfig(
        ou_backtest_config=OUBacktestConfig(
            n_splits=args.n_splits,
            min_train_rows=args.min_train_rows,
        ),
        min_recommended_bets=args.min_recommended_bets,
    )
    if args.dry_run:
        frame = load_filtered_ou_publication_dataset(
            args.dataset,
            start_date=args.start_date,
            end_date=args.end_date,
            competition=args.competition,
        )
        print(json.dumps(_dry_run_payload(args, config, len(frame)), indent=2, sort_keys=True))
        return

    result = run_ou_publication_backtest(
        args.dataset,
        output_dir=args.output_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        competition=args.competition,
        config=config,
    )
    print(json.dumps(result.summary["recommendation"], indent=2, sort_keys=True, default=str))
    print(f"O/U V2 publication reports saved to {args.output_dir}")


def _dry_run_payload(
    args: argparse.Namespace,
    config: OUPublicationBacktestConfig,
    row_count: int,
) -> JsonDict:
    return {
        "dry_run": True,
        "dataset": str(args.dataset),
        "output_dir": str(args.output_dir),
        "filters": {
            "start_date": args.start_date,
            "end_date": args.end_date,
            "competition": args.competition,
        },
        "row_count_after_filters": row_count,
        "policy_grid": {
            "min_edge": list(config.policy_min_edges),
            "min_ev": list(config.policy_min_evs),
            "min_confidence": list(config.policy_min_confidences),
            "min_data_quality": list(config.policy_min_data_qualities),
            "min_bookmaker_count": list(config.policy_min_bookmaker_counts),
        },
        "reports_would_write": [
            "backtest_summary.json",
            "calibration_bins.csv",
            "roi_by_edge_bucket.csv",
            "roi_by_ev_bucket.csv",
            "roi_by_confidence_bucket.csv",
            "publication_policy_grid.csv",
            "backtest_report.md",
        ],
    }


if __name__ == "__main__":
    main()
