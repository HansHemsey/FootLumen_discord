from __future__ import annotations

import logging
from pathlib import Path

import httpx
import pytest

from football_predictor.api.api_football_client import ApiFootballClient
from football_predictor.api.endpoints import FIXTURES, ODDS_MAPPING, PLAYERS_SQUADS
from football_predictor.api.exceptions import ApiFootballRateLimitError, ApiFootballServerError

SYNTHETIC_API_KEY = "synthetic-api-key-value"
SYNTHETIC_BASE_URL = "https://api.example.invalid"


def make_client(
    transport: httpx.MockTransport,
    tmp_path: Path,
    *,
    retries: int = 0,
) -> ApiFootballClient:
    return ApiFootballClient(
        base_url=SYNTHETIC_BASE_URL,
        api_key=SYNTHETIC_API_KEY,
        timeout=5.0,
        snapshot_dir=tmp_path / "api_football",
        retries=retries,
        http_client=httpx.Client(transport=transport),
    )


def test_get_sends_api_key_header_without_network(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"response": [{"kind": "synthetic"}]})

    client = make_client(httpx.MockTransport(handler), tmp_path)

    payload = client.get(FIXTURES, params={"name": "synthetic"})

    assert payload["response"] == [{"kind": "synthetic"}]
    assert requests[0].headers["x-apisports-key"] == SYNTHETIC_API_KEY
    assert requests[0].url.params["name"] == "synthetic"


def test_get_logs_without_api_key(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": []})

    client = make_client(httpx.MockTransport(handler), tmp_path)

    with caplog.at_level(logging.INFO, logger="football_predictor"):
        client.get(ODDS_MAPPING, params={"api_key": SYNTHETIC_API_KEY})

    logs = caplog.text
    assert "API-Football GET" in logs
    assert SYNTHETIC_API_KEY not in logs
    assert "<redacted>" in logs


def test_get_paginate_returns_consolidated_response_and_overwrites_page(
    tmp_path: Path,
) -> None:
    requested_pages: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        requested_pages.append(page)
        assert request.url.params["name"] == "synthetic"
        return httpx.Response(
            200,
            json={
                "response": [{"page": page}],
                "paging": {"current": page, "total": 3},
            },
        )

    client = make_client(httpx.MockTransport(handler), tmp_path)

    payload = client.get(
        PLAYERS_SQUADS,
        params={"name": "synthetic", "page": 99},
        paginate=True,
    )

    assert requested_pages == [1, 2, 3]
    assert payload == [{"page": 1}, {"page": 2}, {"page": 3}]


def test_get_204_returns_empty_structured_response(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    client = make_client(httpx.MockTransport(handler), tmp_path)

    payload = client.get(FIXTURES)

    assert payload == {
        "response": [],
        "errors": [],
        "results": 0,
        "paging": {"current": 1, "total": 1},
    }


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (499, ApiFootballRateLimitError),
        (429, ApiFootballRateLimitError),
        (500, ApiFootballServerError),
    ],
)
def test_get_rate_limit_and_500_raise_specific_errors_without_secret(
    status_code: int,
    expected_error: type[Exception],
    tmp_path: Path,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"response": []})

    client = make_client(httpx.MockTransport(handler), tmp_path)

    with pytest.raises(expected_error) as exc_info:
        client.get(FIXTURES, params={"name": "synthetic"})

    message = str(exc_info.value)
    assert f"status_code={status_code}" in message
    assert f"endpoint={FIXTURES}" in message
    assert "synthetic" in message
    assert SYNTHETIC_API_KEY not in message


def test_get_retries_500_before_success(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(500, json={"response": []})
        return httpx.Response(200, json={"response": [{"retry": "ok"}]})

    client = make_client(httpx.MockTransport(handler), tmp_path, retries=1)

    payload = client.get(FIXTURES)

    assert calls == 2
    assert payload["response"] == [{"retry": "ok"}]


def test_get_save_raw_writes_snapshot_without_api_key(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "response": [{"token": SYNTHETIC_API_KEY}],
                "debug": {"api_key": SYNTHETIC_API_KEY},
            },
        )

    client = make_client(httpx.MockTransport(handler), tmp_path)

    client.get(
        FIXTURES,
        params={"api_key": SYNTHETIC_API_KEY, "name": "synthetic"},
        save_raw=True,
    )

    snapshots = list((tmp_path / "api_football").glob("*/*.json"))
    assert len(snapshots) == 1
    assert snapshots[0].parent.name.count("-") == 2
    assert snapshots[0].name.startswith("fixtures_")

    snapshot_text = snapshots[0].read_text(encoding="utf-8")
    for expected_value in (FIXTURES, "params", "fetched_at", "status_code"):
        assert expected_value in snapshot_text
    assert SYNTHETIC_API_KEY not in snapshot_text
    assert "x-apisports-key" not in snapshot_text
    assert "<redacted>" in snapshot_text


def test_endpoint_constants_do_not_include_ids() -> None:
    useful_endpoints: tuple[str, ...] = (FIXTURES, PLAYERS_SQUADS, ODDS_MAPPING)

    assert useful_endpoints == ("/fixtures", "/players/squads", "/odds/mapping")
    assert all(
        not any(character.isdigit() for character in endpoint)
        for endpoint in useful_endpoints
    )
