"""Report writers for O/U V2 publication backtests."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

JsonDict = dict[str, Any]


def write_ou_v2_backtest_reports(
    *,
    output_dir: Path,
    summary: JsonDict,
    roi_by_edge_bucket: pd.DataFrame,
    roi_by_ev_bucket: pd.DataFrame,
    calibration_bins: pd.DataFrame,
    publication_policy_grid: pd.DataFrame,
) -> dict[str, Path]:
    """Write the O/U V2 JSON, CSV, and Markdown reports."""
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "summary_json": output_dir / "backtest_summary.json",
        "roi_by_edge_bucket_csv": output_dir / "roi_by_edge_bucket.csv",
        "roi_by_ev_bucket_csv": output_dir / "roi_by_ev_bucket.csv",
        "calibration_bins_csv": output_dir / "calibration_bins.csv",
        "publication_policy_grid_csv": output_dir / "publication_policy_grid.csv",
        "markdown": output_dir / "backtest_report.md",
    }
    paths["summary_json"].write_text(
        json.dumps(_json_safe(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    roi_by_edge_bucket.to_csv(paths["roi_by_edge_bucket_csv"], index=False)
    roi_by_ev_bucket.to_csv(paths["roi_by_ev_bucket_csv"], index=False)
    calibration_bins.to_csv(paths["calibration_bins_csv"], index=False)
    publication_policy_grid.to_csv(paths["publication_policy_grid_csv"], index=False)
    paths["markdown"].write_text(_render_markdown(summary), encoding="utf-8")
    return paths


def _render_markdown(summary: JsonDict) -> str:
    recommendation = summary.get("recommendation", {})
    betting = summary.get("betting", {})
    model = summary.get("model_vs_market", {}).get("model", {})
    market = summary.get("model_vs_market", {}).get("market", {})
    clv = summary.get("closing_line_value", {})
    lines = [
        "# Backtest O/U V2 Publication",
        "",
        "## Résumé",
        f"- Dataset: `{summary.get('dataset_path')}`",
        f"- Rows évaluées: {summary.get('row_count')}",
        f"- Folds walk-forward: {summary.get('n_folds')}",
        "",
        "## Modèle Vs Marché",
        (
            "- Modèle: "
            f"Brier `{_fmt(model.get('brier_score'))}`, "
            f"log loss `{_fmt(model.get('log_loss'))}`, "
            f"ECE `{_fmt(model.get('ece'))}`"
        ),
        (
            "- Marché: "
            f"Brier `{_fmt(market.get('brier_score'))}`, "
            f"log loss `{_fmt(market.get('log_loss'))}`, "
            f"ECE `{_fmt(market.get('ece'))}`, "
            f"coverage `{_fmt(market.get('coverage'))}`"
        ),
        "",
        "## Performance Betting Value",
        (
            "- Bets value: "
            f"`{betting.get('total_bets', 0)}` | "
            f"ROI `{_pct(betting.get('roi'))}` | "
            f"profit `{_fmt(betting.get('profit_units'))}` unités | "
            f"hit rate `{_pct(betting.get('hit_rate'))}` | "
            f"drawdown max `{_fmt(betting.get('max_drawdown_units'))}` unités"
        ),
        (
            "- CLV: "
            f"coverage `{_fmt(clv.get('closing_odds_coverage'))}`, "
            f"model_over `{_fmt(clv.get('model_over_clv'))}`, "
            f"pick `{_fmt(clv.get('pick_clv'))}`"
        ),
        "",
        "## Recommandation",
    ]
    if recommendation.get("decision") == "staff_only":
        lines += [
            "- Décision recommandée: `staff-only`.",
            f"- Raison: {recommendation.get('reason')}",
        ]
    else:
        lines += [
            "- Policy recommandée:",
            f"  - min_edge: `{recommendation.get('min_edge')}`",
            f"  - min_ev: `{recommendation.get('min_ev')}`",
            f"  - min_confidence: `{recommendation.get('min_confidence')}`",
            f"  - min_data_quality: `{recommendation.get('min_data_quality')}`",
            f"  - min_bookmaker_count: `{recommendation.get('min_bookmaker_count')}`",
            f"- ROI: `{_pct(recommendation.get('roi'))}`",
            f"- Bets: `{recommendation.get('total_bets')}`",
            f"- Profit: `{_fmt(recommendation.get('profit_units'))}` unités",
        ]
    lines += [
        "",
        "## Fichiers",
        "- `backtest_summary.json`",
        "- `roi_by_edge_bucket.csv`",
        "- `roi_by_ev_bucket.csv`",
        "- `calibration_bins.csv`",
        "- `publication_policy_grid.csv`",
    ]
    return "\n".join(lines) + "\n"


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except Exception:
            return str(value)
    return value


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(numeric) or math.isinf(numeric):
        return "n/a"
    return f"{numeric:.4f}"


def _pct(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(numeric) or math.isinf(numeric):
        return "n/a"
    return f"{numeric * 100:.2f}%"
