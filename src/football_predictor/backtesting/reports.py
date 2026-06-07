"""Backtesting report exporters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def export_metrics_json(metrics: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    return path


def export_markdown_report(metrics: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_markdown_report(metrics), encoding="utf-8")
    return path


def _markdown_report(metrics: dict[str, Any]) -> str:
    lines = [
        "# Backtest FootLumen",
        "",
        f"- Dataset: `{metrics.get('dataset_path', '')}`",
        f"- Model dir: `{metrics.get('model_dir', '')}`",
        f"- Generated at: `{metrics.get('generated_at', '')}`",
        "",
        "## Résumé Global",
        "",
        "| Modèle | Rows | Coverage | Accuracy | Log loss | Brier |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model_name, model_metrics in metrics.get("metrics", {}).get("test", {}).items():
        lines.append(
            f"| {model_name} | {model_metrics.get('row_count', 0)} | "
            f"{_fmt(model_metrics.get('coverage'))} | {_fmt(model_metrics.get('accuracy'))} | "
            f"{_fmt(model_metrics.get('log_loss'))} | "
            f"{_fmt(model_metrics.get('brier_score'))} |"
        )

    lines.extend(["", "## Période Évaluée", "", "| Split | Rows | Start | End |"])
    lines.append("| --- | ---: | --- | --- |")
    for name, period in metrics.get("periods", {}).items():
        lines.append(
            f"| {name} | {period.get('row_count', 0)} | {period.get('start') or ''} | "
            f"{period.get('end') or ''} |"
        )

    lines.extend(["", "## Performance Par Ligue", ""])
    _append_group_section(lines, metrics, "league_id")
    lines.extend(["", "## Performance Par Saison", ""])
    _append_group_section(lines, metrics, "season")

    lines.extend(["", "## Calibration", ""])
    for model_name, model_metrics in metrics.get("metrics", {}).get("test", {}).items():
        lines.append(f"### {model_name}")
        lines.append("")
        lines.append("| Bin | Count | Avg confidence | Accuracy |")
        lines.append("| ---: | ---: | ---: | ---: |")
        for item in model_metrics.get("calibration_bins", []):
            lines.append(
                f"| {item.get('bin')} | {item.get('count')} | "
                f"{_fmt(item.get('avg_confidence'))} | {_fmt(item.get('accuracy'))} |"
            )
        lines.append("")

    lines.extend(["## Seuils De Confiance", ""])
    for model_name, model_metrics in metrics.get("metrics", {}).get("test", {}).items():
        lines.append(f"### {model_name}")
        lines.append("")
        lines.append("| Threshold | Rows | Coverage | Accuracy |")
        lines.append("| ---: | ---: | ---: | ---: |")
        for item in model_metrics.get("confidence_thresholds", []):
            lines.append(
                f"| {item.get('threshold')} | {item.get('row_count')} | "
                f"{_fmt(item.get('coverage'))} | {_fmt(item.get('accuracy'))} |"
            )
        lines.append("")

    if _has_low_data_quality(metrics):
        lines.extend(
            [
                "## Avertissement Qualité Des Données",
                "",
                "Certaines lignes évaluées ont une qualité de données faible. "
                "Les métriques doivent être interprétées avec prudence.",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _append_group_section(lines: list[str], metrics: dict[str, Any], group_name: str) -> None:
    groups = metrics.get("group_metrics", {}).get("test", {}).get(group_name, {})
    if not groups:
        lines.append("_Non disponible._")
        return
    lines.append("| Groupe | Rows | Modèles |")
    lines.append("| --- | ---: | --- |")
    for value, payload in groups.items():
        model_names = ", ".join(payload.get("metrics", {}).keys())
        lines.append(f"| `{value}` | {payload.get('row_count', 0)} | {model_names} |")


def _has_low_data_quality(metrics: dict[str, Any]) -> bool:
    groups = metrics.get("group_metrics", {}).get("test", {}).get("data_quality_bucket", {})
    return any(str(name).startswith("low") for name in groups)


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)
