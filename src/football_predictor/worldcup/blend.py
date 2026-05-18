"""Blend configuration and probability mixing for World Cup 1X2."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.utils.logging import get_logger

JsonDict = dict[str, Any]

WORLD_CUP_BLEND_CONFIG_FILENAME = "blend_config.json"
WORLD_CUP_BLEND_VERSION = "worldcup-blend-v1"
WORLD_CUP_BLEND_SOURCES = frozenset(
    {
        "wc_model",
        "wc_rating_dynamic",
        "wc_poisson_dynamic",
        "wc_market",
        "wc_api",
    }
)
_OPTIONAL_DYNAMIC_SOURCES = frozenset({"wc_market", "wc_api"})
_DEFAULT_BASE_WEIGHTS = {
    "wc_rating_dynamic": 0.55,
    "wc_poisson_dynamic": 0.40,
    "wc_model": 0.05,
}
_DEFAULT_LIVE_WEIGHTS = {
    "wc_market": 0.35,
    "wc_rating_dynamic": 0.30,
    "wc_poisson_dynamic": 0.25,
    "wc_model": 0.05,
    "wc_api": 0.05,
}

logger = get_logger(__name__)


@dataclass(frozen=True)
class WorldCupBlendConfig:
    """Source weights selected for World Cup probability blending."""

    version: str = WORLD_CUP_BLEND_VERSION
    selected_candidate: str = "default_conservative"
    source_weights: dict[str, float] = field(default_factory=lambda: dict(_DEFAULT_BASE_WEIGHTS))
    dynamic_source_weights: dict[str, float] = field(
        default_factory=lambda: dict(_DEFAULT_LIVE_WEIGHTS)
    )
    selection_reason: str = "fallback_config_missing"
    metrics: JsonDict = field(default_factory=dict)

    @classmethod
    def default(cls) -> WorldCupBlendConfig:
        return cls()

    @classmethod
    def from_mapping(cls, payload: JsonDict) -> WorldCupBlendConfig:
        source_weights = _validate_weights(payload.get("source_weights"))
        dynamic_source_weights = _validate_weights(payload.get("dynamic_source_weights"))
        return cls(
            version=str(payload.get("version") or WORLD_CUP_BLEND_VERSION),
            selected_candidate=str(payload.get("selected_candidate") or "configured"),
            source_weights=source_weights or dict(_DEFAULT_BASE_WEIGHTS),
            dynamic_source_weights=dynamic_source_weights or dict(_DEFAULT_LIVE_WEIGHTS),
            selection_reason=str(payload.get("selection_reason") or "configured"),
            metrics=payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {},
        )

    @classmethod
    def load(cls, path: Path) -> WorldCupBlendConfig:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("World Cup blend config must be a JSON object")
        return cls.from_mapping(payload)

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(_json_ready(self.as_dict()), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path

    def as_dict(self) -> JsonDict:
        return {
            "version": self.version,
            "selected_candidate": self.selected_candidate,
            "source_weights": _normalize_weights(self.source_weights),
            "dynamic_source_weights": _normalize_weights(self.dynamic_source_weights),
            "selection_reason": self.selection_reason,
            "metrics": self.metrics,
        }

    def weights_for_sources(self, available_sources: set[str]) -> dict[str, float]:
        if available_sources.intersection(_OPTIONAL_DYNAMIC_SOURCES):
            preferred = self.dynamic_source_weights
        else:
            preferred = self.source_weights
        return _normalize_weights(
            {
                source: weight
                for source, weight in preferred.items()
                if source in available_sources and weight > 0
            }
        )


def load_worldcup_blend_config(model_dir_or_path: Path | None) -> WorldCupBlendConfig:
    if model_dir_or_path is None:
        return WorldCupBlendConfig.default()
    config_path = _config_path(model_dir_or_path)
    if not config_path.exists():
        return WorldCupBlendConfig.default()
    try:
        return WorldCupBlendConfig.load(config_path)
    except Exception as exc:
        logger.warning(
            "Invalid World Cup blend config ignored: path=%s error=%s",
            config_path,
            exc,
        )
        return WorldCupBlendConfig.default()


def blend_worldcup_probability_sources(
    sources: dict[str, ProbabilityTriple | None],
    *,
    config: WorldCupBlendConfig | None = None,
    source_weights: dict[str, float] | None = None,
) -> ProbabilityTriple:
    available = {source for source, probability in sources.items() if probability is not None}
    if not available:
        return ProbabilityTriple.uniform()
    weights = (
        _normalize_weights(
            {
                source: weight
                for source, weight in (source_weights or {}).items()
                if source in available and weight > 0
            }
        )
        if source_weights is not None
        else (config or WorldCupBlendConfig.default()).weights_for_sources(available)
    )
    if not weights:
        weights = _normalize_weights({source: 1.0 for source in available})
    return _geometric_blend({source: sources[source] for source in weights}, weights)


def derive_dynamic_source_weights(base_weights: dict[str, float]) -> dict[str, float]:
    normalized_base = _normalize_weights(
        {
            source: weight
            for source, weight in base_weights.items()
            if source in {"wc_model", "wc_rating_dynamic", "wc_poisson_dynamic"} and weight > 0
        }
    )
    if not normalized_base:
        normalized_base = _normalize_weights(_DEFAULT_BASE_WEIGHTS)
    dynamic = {"wc_market": 0.35, "wc_api": 0.05}
    remaining = 0.60
    dynamic.update({source: weight * remaining for source, weight in normalized_base.items()})
    return _normalize_weights(dynamic)


def _geometric_blend(
    sources: dict[str, ProbabilityTriple | None],
    weights: dict[str, float],
) -> ProbabilityTriple:
    logits: list[float] = []
    for index in range(3):
        logits.append(
            sum(
                weights[source] * math.log(max(probability.to_vector()[index], 1e-12))
                for source, probability in sources.items()
                if probability is not None and source in weights
            )
        )
    maximum = max(logits)
    exps = [math.exp(value - maximum) for value in logits]
    total = sum(exps)
    return ProbabilityTriple.from_vector([value / total for value in exps])


def _config_path(model_dir_or_path: Path) -> Path:
    if model_dir_or_path.is_dir():
        return model_dir_or_path / WORLD_CUP_BLEND_CONFIG_FILENAME
    return model_dir_or_path.parent / WORLD_CUP_BLEND_CONFIG_FILENAME


def _validate_weights(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    weights: dict[str, float] = {}
    for source, weight in value.items():
        if source not in WORLD_CUP_BLEND_SOURCES:
            continue
        try:
            parsed = float(weight)
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed) and parsed > 0:
            weights[str(source)] = parsed
    return _normalize_weights(weights)


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weight for weight in weights.values() if weight > 0 and math.isfinite(weight))
    if total <= 0:
        return {}
    return {
        source: weight / total
        for source, weight in weights.items()
        if weight > 0 and math.isfinite(weight)
    }


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
