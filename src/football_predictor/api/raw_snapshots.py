"""Raw API-Football snapshot persistence."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from football_predictor.api.exceptions import ApiFootballSnapshotError
from football_predictor.security.sanitize import sanitize_mapping
from football_predictor.utils.time import utc_now


class SnapshotPayload(Protocol):
    @property
    def endpoint(self) -> str: ...

    @property
    def params(self) -> Mapping[str, Any]: ...

    @property
    def payload(self) -> Mapping[str, Any]: ...

    @property
    def fetched_at(self) -> str: ...

    @property
    def status_code(self) -> int: ...

    @property
    def source(self) -> str: ...


class RawApiSnapshotWriter:
    """Write secret-safe raw API snapshots to a local directory."""

    def __init__(self, root_dir: Path | str) -> None:
        self.root_dir = Path(root_dir)

    def write(self, snapshot: SnapshotPayload) -> Path:
        now = utc_now()
        day_dir = self.root_dir / now.strftime("%Y-%m-%d")
        filename = f"{_endpoint_slug(snapshot.endpoint)}_{now.strftime('%Y%m%dT%H%M%S%fZ')}.json"
        path = day_dir / filename
        data = {
            "endpoint": snapshot.endpoint,
            "params": sanitize_mapping(snapshot.params),
            "payload": sanitize_mapping(snapshot.payload),
            "fetched_at": snapshot.fetched_at,
            "status_code": snapshot.status_code,
            "source": snapshot.source,
        }
        try:
            day_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True, default=str),
                encoding="utf-8",
            )
        except OSError as exc:
            raise ApiFootballSnapshotError(f"Could not write API snapshot path={path}") from exc
        return path


def _endpoint_slug(endpoint: str) -> str:
    stripped = endpoint.strip().strip("/") or "root"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", stripped)
