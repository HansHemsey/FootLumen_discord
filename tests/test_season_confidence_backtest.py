from pathlib import Path

import pytest

from football_predictor.backtesting.season_confidence import (
    SeasonConfidenceBacktestConfig,
    _markdown_report,
    _validate_config,
    summarize_confidence_only_records,
    summarize_ou_published_report,
    summarize_v3_published_report,
)


def test_summarize_v3_published_report_extracts_success_by_league() -> None:
    report = {
        "scopes": {
            "published_only": {
                "v3_stacker_full": {"row_count": 12, "accuracy": 0.75},
                "odds_only": {"accuracy": 0.5},
                "v2_existing": {"accuracy": 0.58},
            }
        },
        "groups": {
            "league": {
                "39": {
                    "row_count": 7,
                    "metrics_by_model": {
                        "v3_stacker_full": {"row_count": 7, "accuracy": 0.714},
                        "odds_only": {"accuracy": 0.571},
                        "v2_existing": {"accuracy": 0.429},
                    },
                },
                "61": {
                    "row_count": 5,
                    "metrics_by_model": {
                        "v3_stacker_full": {"row_count": 5, "accuracy": 0.8},
                    },
                },
            }
        },
    }

    summary = summarize_v3_published_report(report)

    assert summary["published_rows"] == 12
    assert summary["success_rate"] == 0.75
    assert summary["odds_success_rate"] == 0.5
    assert summary["by_league"]["39"]["published_rows"] == 7
    assert summary["by_league"]["39"]["success_rate"] == 0.714


def test_summarize_ou_published_report_extracts_market_and_roi() -> None:
    report = {
        "published_only": {
            "row_count": 10,
            "accuracy": 0.6,
            "win_rate": 0.6,
            "roi": 0.08,
        },
        "baseline_on_published": {"accuracy": 0.5},
        "by_league": {
            "140": {
                "published_only": {
                    "row_count": 4,
                    "accuracy": 0.75,
                    "win_rate": 0.75,
                    "roi": 0.12,
                },
                "baseline_on_published": {"accuracy": 0.5},
            }
        },
    }

    summary = summarize_ou_published_report(report)

    assert summary["published_rows"] == 10
    assert summary["success_rate"] == 0.6
    assert summary["market_success_rate"] == 0.5
    assert summary["by_league"]["140"]["roi"] == 0.12


def test_summarize_confidence_only_records_ignores_publication_gate() -> None:
    records = [
        {
            "league_id": 39,
            "calibrated_label": "High",
            "correct": True,
            "confidence_score": 52,
            "data_quality_score": 30,
            "publication_allowed": False,
        },
        {
            "league_id": 39,
            "calibrated_label": "Very High",
            "correct": False,
            "confidence_score": 75,
            "data_quality_score": 35,
            "publication_allowed": False,
        },
        {
            "league_id": 61,
            "calibrated_label": "Low",
            "correct": True,
            "confidence_score": 25,
            "data_quality_score": 80,
            "publication_allowed": False,
        },
    ]

    summary = summarize_confidence_only_records(records)

    assert summary["row_count"] == 2
    assert summary["success_rate"] == 0.5
    assert summary["publication_blocked_rows"] == 2
    assert summary["by_league"]["39"]["row_count"] == 2


def test_markdown_report_documents_finished_only_scope() -> None:
    payload = {
        "config": {
            "test_season": 2025,
            "train_seasons": [2022, 2023, 2024],
            "prediction_offset_minutes": 30,
            "min_data_quality_score": 60,
        },
        "season_scope": {
            "fixture_counts_by_league": {
                "39": {
                    "league_name": "Premier League",
                    "finished_scored": 340,
                    "excluded_unfinished": 40,
                    "total_fixtures": 380,
                }
            }
        },
        "reports": {
            "v3_1x2": {
                "summary": {
                    "published_rows": 3,
                    "success_rate": 2 / 3,
                    "by_league": {
                        "39": {
                            "published_rows": 3,
                            "success_rate": 2 / 3,
                            "odds_success_rate": 1 / 3,
                        }
                    },
                }
            },
            "ou25": {
                "summary": {
                    "published_rows": 2,
                    "success_rate": 0.5,
                    "by_league": {
                        "39": {
                            "published_rows": 2,
                            "success_rate": 0.5,
                            "market_success_rate": 1.0,
                            "roi": -0.1,
                        }
                    },
                }
            },
        },
    }

    markdown = _markdown_report(payload)

    assert "kickoff - 30 minutes" in markdown
    assert "Discord: `non utilise`" in markdown
    assert "Premier League (`39`) | 340 | 40 | 380" in markdown
    assert "High/Very High" in markdown


def test_validate_config_rejects_train_season_not_before_test() -> None:
    with pytest.raises(ValueError, match="test_season"):
        _validate_config(
            SeasonConfidenceBacktestConfig(
                league_ids=[39],
                test_season=2025,
                train_seasons=[2024, 2025],
                output_dir=Path("reports/test"),
            )
        )
