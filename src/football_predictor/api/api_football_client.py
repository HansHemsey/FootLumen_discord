"""Central API-Football v3 client."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import httpx

from football_predictor.api.exceptions import (
    ApiFootballClientError,
    ApiFootballError,
    ApiFootballPaginationError,
    ApiFootballRateLimitError,
    ApiFootballServerError,
)
from football_predictor.api.rate_limit import RetryPolicy
from football_predictor.api.raw_snapshots import RawApiSnapshotWriter
from football_predictor.security.sanitize import sanitize_text
from football_predictor.utils.logging import get_logger, sanitize_mapping
from football_predictor.utils.time import utc_now

JsonDict = dict[str, Any]
QueryParams = Mapping[str, Any]


@dataclass(frozen=True)
class ApiFootballPayload:
    endpoint: str
    params: JsonDict
    payload: JsonDict
    fetched_at: str
    status_code: int
    source: str = "api-football"


class ApiFootballClient:
    """GET-only API-Football client with retries, pagination and raw snapshots."""

    def __init__(
        self,
        base_url: str = "https://v3.football.api-sports.io",
        api_key: str | None = None,
        timeout: float = 20.0,
        snapshot_dir: Path | str | None = Path("data/raw/api_football"),
        *,
        retries: int = 2,
        http_client: httpx.Client | None = None,
        raw_snapshot_dir: Path | str | None = None,
        snapshot_writer: RawApiSnapshotWriter | None = None,
    ) -> None:
        if not api_key:
            raise ApiFootballError("API_FOOTBALL_KEY is required for live API calls")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retry_policy = RetryPolicy(retries)
        self._client = http_client or httpx.Client(timeout=timeout)
        self._owns_client = http_client is None
        self.logger = get_logger(__name__)

        resolved_snapshot_dir = raw_snapshot_dir if raw_snapshot_dir is not None else snapshot_dir
        self.snapshot_writer = snapshot_writer
        if self.snapshot_writer is None and resolved_snapshot_dir is not None:
            self.snapshot_writer = RawApiSnapshotWriter(resolved_snapshot_dir)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> ApiFootballClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        paginate: bool = False,
        *,
        save_raw: bool = False,
    ) -> JsonDict | list[Any]:
        """Return a JSON response, or a consolidated response list when paginating."""
        normalized_endpoint = self._normalize_endpoint(endpoint)
        normalized_params = dict(params or {})
        if paginate:
            return self._get_paginated(normalized_endpoint, normalized_params, save_raw=save_raw)

        payload = self._get_payload(normalized_endpoint, normalized_params)
        self._write_snapshot(payload, save_raw)
        return payload.payload

    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> ApiFootballPayload:
        """Return response metadata plus JSON payload for ingestion internals."""
        normalized_endpoint = self._normalize_endpoint(endpoint)
        payload = self._get_payload(normalized_endpoint, dict(params or {}))
        self._write_snapshot(payload, save_raw)
        return payload

    def get_paginated(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> list[Any]:
        """Compatibility wrapper around get(..., paginate=True)."""
        return cast(list[Any], self.get(endpoint, params=params, paginate=True, save_raw=save_raw))

    def _get_payload(self, endpoint: str, params: JsonDict) -> ApiFootballPayload:
        response = self._request_with_retry(endpoint, params)
        return self._handle_response(endpoint, params, response)

    def _get_paginated(
        self,
        endpoint: str,
        params: JsonDict,
        *,
        save_raw: bool,
    ) -> list[Any]:
        base_params = dict(params)
        page_params = dict(base_params)
        page_params["page"] = 1
        first_page = self._get_payload(endpoint, page_params)
        first_response = self._extract_response_list(endpoint, first_page.payload)
        paging = self._read_paging(first_page.payload)
        if paging is None:
            self._write_snapshot(first_page, save_raw)
            return first_response

        _current_page, total_pages = paging
        consolidated = list(first_response)
        pages = [first_page]
        for page_number in range(2, total_pages + 1):
            current_params = dict(base_params)
            current_params["page"] = page_number
            page_payload = self._get_payload(endpoint, current_params)
            pages.append(page_payload)
            consolidated.extend(self._extract_response_list(endpoint, page_payload.payload))

        if save_raw:
            self._write_snapshot(
                self._build_paginated_snapshot(endpoint, base_params, consolidated, pages),
                save_raw=True,
            )
        return consolidated

    def _request_with_retry(self, endpoint: str, params: JsonDict) -> httpx.Response:
        url = f"{self.base_url}{endpoint}"
        last_error: Exception | None = None
        for attempt_index in self.retry_policy.attempts:
            try:
                self.logger.info(
                    "API-Football GET endpoint=%s params=%s attempt=%s",
                    endpoint,
                    sanitize_mapping(params),
                    attempt_index + 1,
                )
                response = self._client.get(
                    url,
                    params=params,
                    headers={"x-apisports-key": self.api_key},
                    timeout=self.timeout,
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if self.retry_policy.should_retry(attempt_index):
                    self.logger.warning(
                        "API-Football transport error endpoint=%s attempt=%s",
                        endpoint,
                        attempt_index + 1,
                    )
                    continue
                raise ApiFootballError(
                    f"API-Football request failed endpoint={endpoint}: {sanitize_text(str(exc))}"
                ) from exc

            self.logger.info(
                "API-Football response endpoint=%s status_code=%s attempt=%s",
                endpoint,
                response.status_code,
                attempt_index + 1,
            )
            if self.retry_policy.should_retry(attempt_index, response.status_code):
                continue
            return response

        raise ApiFootballError(
            f"API-Football request failed endpoint={endpoint}: {sanitize_text(str(last_error))}"
        )

    def _handle_response(
        self,
        endpoint: str,
        params: JsonDict,
        response: httpx.Response,
    ) -> ApiFootballPayload:
        if response.status_code == 204:
            return self._empty_response(endpoint, params, response.status_code)
        if response.status_code in {429, 499}:
            raise ApiFootballRateLimitError(
                self._exception_message("Rate limit", endpoint, params, response.status_code)
            )
        if response.status_code >= 500:
            raise ApiFootballServerError(
                self._exception_message("API server error", endpoint, params, response.status_code)
            )
        if response.status_code >= 400:
            raise ApiFootballClientError(
                self._exception_message("API client error", endpoint, params, response.status_code)
            )

        try:
            raw_payload = response.json()
        except ValueError as exc:
            raise ApiFootballError(f"Invalid JSON payload endpoint={endpoint}") from exc
        if not isinstance(raw_payload, dict):
            raise ApiFootballError(f"Unexpected payload type endpoint={endpoint}")
        payload = cast(JsonDict, raw_payload)
        return ApiFootballPayload(
            endpoint=endpoint,
            params=dict(params),
            payload=payload,
            fetched_at=utc_now().isoformat(),
            status_code=response.status_code,
        )

    def _write_snapshot(self, payload: ApiFootballPayload, save_raw: bool) -> None:
        if not save_raw:
            return
        if self.snapshot_writer is None:
            raise ApiFootballError("Raw snapshot writing requested without a snapshot writer")
        path = self.snapshot_writer.write(payload)
        self.logger.info(
            "API-Football raw snapshot written endpoint=%s path=%s",
            payload.endpoint,
            path,
        )

    @staticmethod
    def _normalize_endpoint(endpoint: str) -> str:
        stripped = endpoint.strip()
        return stripped if stripped.startswith("/") else f"/{stripped}"

    @staticmethod
    def _empty_response(endpoint: str, params: JsonDict, status_code: int) -> ApiFootballPayload:
        return ApiFootballPayload(
            endpoint=endpoint,
            params=dict(params),
            payload={
                "response": [],
                "errors": [],
                "results": 0,
                "paging": {"current": 1, "total": 1},
            },
            fetched_at=utc_now().isoformat(),
            status_code=status_code,
        )

    @staticmethod
    def _extract_response_list(endpoint: str, payload: JsonDict) -> list[Any]:
        response = payload.get("response", [])
        if not isinstance(response, list):
            raise ApiFootballPaginationError(
                f"Cannot paginate non-list response endpoint={endpoint}"
            )
        return response

    @staticmethod
    def _read_paging(payload: JsonDict) -> tuple[int, int] | None:
        paging = payload.get("paging")
        if paging is None:
            return None
        if not isinstance(paging, Mapping):
            raise ApiFootballPaginationError("API-Football paging metadata must be an object")
        current_raw = paging.get("current")
        total_raw = paging.get("total")
        if current_raw is None or total_raw is None:
            return None
        try:
            current = int(current_raw)
            total = int(total_raw)
        except (TypeError, ValueError) as exc:
            raise ApiFootballPaginationError(
                "Invalid paging metadata "
                f"current={sanitize_text(str(current_raw))} total={sanitize_text(str(total_raw))}"
            ) from exc
        if current < 1 or total < current:
            raise ApiFootballPaginationError(
                f"Invalid paging metadata current={current} total={total}"
            )
        return current, total

    @staticmethod
    def _build_paginated_snapshot(
        endpoint: str,
        params: JsonDict,
        consolidated: list[Any],
        pages: list[ApiFootballPayload],
    ) -> ApiFootballPayload:
        return ApiFootballPayload(
            endpoint=endpoint,
            params=dict(params),
            payload={
                "response": consolidated,
                "results": len(consolidated),
                "paging": {"current": len(pages), "total": len(pages)},
            },
            fetched_at=utc_now().isoformat(),
            status_code=pages[-1].status_code,
        )

    @staticmethod
    def _exception_message(
        reason: str,
        endpoint: str,
        params: JsonDict,
        status_code: int,
    ) -> str:
        return (
            f"{reason} endpoint={endpoint} status_code={status_code} "
            f"params={sanitize_mapping(params)}"
        )
